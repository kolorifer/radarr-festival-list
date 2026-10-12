"""Apply capped broad professional-critic consensus to the research evidence score.

Metacritic critic score and Rotten Tomatoes critic score are combined using the
conservative calibration tested in critical_consensus_experiment.py. Their
combined evidence is scaled to at most 40 points and merged *inside* the existing
100-point critics_groups_consensus family. This preserves the 1000-point ceiling:
800 non-audience + 200 audience.

This script only rewrites research evidence-scores.json. Frozen qualification
routes and production feeds remain untouched.
"""

import json
import math
from pathlib import Path

SCORES = Path("evidence-scores.json")
RATINGS = Path("audience-ratings.json")
BROAD_CAP = 40.0


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def critic_component(rating, reviews, rating_floor, rating_full, review_min, review_full):
    if not isinstance(rating, (int, float)) or not isinstance(reviews, (int, float)):
        return 0.0
    if reviews < review_min or rating <= rating_floor:
        return 0.0
    quality = clamp01((float(rating) - rating_floor) / (rating_full - rating_floor)) * 100.0
    if reviews >= review_full:
        confidence = 1.0
    else:
        breadth = clamp01(math.log(float(reviews) / review_min) / math.log(review_full / review_min))
        confidence = 0.6 + 0.4 * breadth
    return round(quality * confidence, 2)


def broad_critic_raw(reeldb):
    """Return raw 0..100 broad critic consensus plus its two components."""
    mc = (reeldb or {}).get("metacritic") or {}
    rt = (reeldb or {}).get("tomatoes") or {}
    mc_score = critic_component(mc.get("rating"), mc.get("votes"), 65.0, 90.0, 15, 60)
    rt_score = critic_component(rt.get("rating"), rt.get("votes"), 70.0, 95.0, 50, 250)
    available = [value for value in (mc_score, rt_score) if value > 0]
    if len(available) == 2:
        combined = sum(available) / 2.0
    elif len(available) == 1:
        combined = available[0] * 0.75
    else:
        combined = 0.0
    return round(combined, 2), round(mc_score, 2), round(rt_score, 2)


def broad_critic_points(reeldb):
    raw, _, _ = broad_critic_raw(reeldb)
    return round(raw * BROAD_CAP / 100.0, 2)


def merge_critics_family(existing, broad_points):
    """Keep the stronger critic signal and add 25% corroboration from the weaker."""
    existing = float(existing or 0)
    broad_points = float(broad_points or 0)
    if existing <= 0:
        return round(min(100.0, broad_points), 2)
    if broad_points <= 0:
        return round(min(100.0, existing), 2)
    return round(min(100.0, max(existing, broad_points) + 0.25 * min(existing, broad_points)), 2)


def apply(payload, ratings_payload):
    ratings = ratings_payload.get("ratings") or {}
    rows = payload.get("films") or []
    positive = 0
    newly_covered = 0

    for row in rows:
        rr = ((ratings.get(row.get("imdb_id")) or {}).get("reeldb") or {})
        raw, mc_score, rt_score = broad_critic_raw(rr)
        broad = round(raw * BROAD_CAP / 100.0, 2)
        points = row.setdefault("source_points", {})
        evidence = row.setdefault("source_evidence", {})
        existing = float(points.get("critics_groups_consensus") or 0)
        merged = merge_critics_family(existing, broad)
        delta = round(merged - existing, 2)

        row["broad_critic_consensus"] = {
            "raw_0_100": raw,
            "active_points_max_40": broad,
            "metacritic_component": mc_score,
            "rotten_tomatoes_component": rt_score,
        }

        if delta <= 0:
            continue

        positive += 1
        had_nonaud = bool(row.get("has_non_audience_evidence"))
        if not had_nonaud:
            newly_covered += 1

        points["critics_groups_consensus"] = merged
        old_evidence = list(evidence.get("critics_groups_consensus") or [])
        old_evidence.append(
            f"Broad critics: Metacritic + Rotten Tomatoes; raw {raw:.2f}/100, capped contribution {broad:.2f}/40"
        )
        evidence["critics_groups_consensus"] = old_evidence

        row["overall_score"] = round(float(row.get("overall_score") or 0) + delta, 2)
        if existing <= 0:
            row["source_hits"] = int(row.get("source_hits") or 0) + 1
        row["has_non_audience_evidence"] = True
        row["audience_only_candidate"] = False
        max_score = float(row.get("eligible_max_score") or 0)
        row["eligible_score_pct"] = round(100.0 * row["overall_score"] / max_score, 2) if max_score else 0.0
        sources = row.setdefault("candidate_sources", [])
        if "broad_critic_consensus" not in sources:
            sources.append("broad_critic_consensus")

    rows.sort(key=lambda r: (-float(r.get("overall_score") or 0), -int(r.get("source_hits") or 0), r.get("title") or ""))
    for rank, row in enumerate(rows, 1):
        row["overall_rank"] = rank

    payload["mode"] = "research-evidence-score-v8-audience200-broadcritics40-officialss250"
    payload["qualification_unchanged"] = True
    policy = payload.setdefault("score_policy", {})
    policy["broad_critic_policy"] = (
        "Metacritic critic + Rotten Tomatoes critic consensus uses conservative review-count confidence, "
        "scaled to max 40 and merged inside the existing 100-point critics family; strongest signal + 25% corroboration"
    )
    policy["sight_sound_policy"] = (
        "Sight & Sound uses the official BFI 2022 critics' poll top 250, with published tie positions and a 250-entry rank scale; "
        "sources published before a film existed remain ineligible rather than zero."
    )
    sources_meta = payload.setdefault("sources", {})
    sources_meta.setdefault("sight_sound", {}).update({
        "type": "ranked",
        "depth": 250,
        "max_points": 100,
        "eligible_through_year": 2022,
        "source": "BFI Sight and Sound 2022 Critics' Poll",
        "source_url": "https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time",
    })
    critics_meta = sources_meta.setdefault("critics_groups_consensus", {"type": "family", "max_points": 100})
    critics_meta.update({
        "max_points": 100,
        "broad_critic_component_active": True,
        "broad_critic_component_max": 40,
        "broad_critic_sources": ["Metacritic critics", "Rotten Tomatoes critics"],
    })
    payload["broad_critic_positive_count"] = positive
    payload["broad_critic_new_non_audience_count"] = newly_covered
    return payload


def main():
    payload = json.loads(SCORES.read_text(encoding="utf-8"))
    ratings = json.loads(RATINGS.read_text(encoding="utf-8"))
    payload = apply(payload, ratings)
    SCORES.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "films": len(payload.get("films") or []),
        "broad_critic_positive": payload.get("broad_critic_positive_count"),
        "new_non_audience_coverage": payload.get("broad_critic_new_non_audience_count"),
        "top": [
            {"rank": r.get("overall_rank"), "title": r.get("title"), "score": r.get("overall_score")}
            for r in (payload.get("films") or [])[:5]
        ],
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
