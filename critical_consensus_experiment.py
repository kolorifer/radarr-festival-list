"""Research experiment: broaden the existing 100-point critics family.

Uses cached Metacritic critic and Rotten Tomatoes critic aggregates as two broad
professional-critic populations. They are combined inside the existing critics
family rather than added as new 100-point families, so the 800+200 architecture
and 1000-point ceiling remain unchanged.

No qualification rules or production files are changed by this script.
"""

import json
import math
from pathlib import Path

SCORES = Path("evidence-scores.json")
RATINGS = Path("audience-ratings.json")
OUTPUT = Path("critical-consensus-experiment.json")

VARIANTS = {
    "balanced": {
        "mc": (60, 90, 10, 50),
        "rt": (60, 95, 30, 200),
    },
    "conservative": {
        "mc": (65, 90, 15, 60),
        "rt": (70, 95, 50, 250),
    },
    "strict": {
        "mc": (70, 90, 20, 75),
        "rt": (75, 95, 75, 300),
    },
}

CONTROLS = (
    "Blade Runner 2049",
    "Ex Machina",
    "Prisoners",
    "Shutter Island",
    "The Batman",
    "Tenet",
    "The Machinist",
    "Dune: Part Two",
    "Midsommar",
    "Nocturnal Animals",
    "Scott Pilgrim vs. the World",
    "La Commune (Paris, 1871)",
)


def clamp01(v):
    return max(0.0, min(1.0, float(v)))


def critic_component(rating, reviews, rating_floor, rating_full, review_min, review_full):
    if not isinstance(rating, (int, float)) or not isinstance(reviews, (int, float)):
        return 0.0
    if reviews < review_min or rating <= rating_floor:
        return 0.0
    quality = clamp01((float(rating) - rating_floor) / (rating_full - rating_floor)) * 100.0
    if reviews >= review_full:
        confidence = 1.0
    elif review_full <= review_min:
        confidence = 1.0
    else:
        breadth = clamp01(math.log(float(reviews) / review_min) / math.log(review_full / review_min))
        confidence = 0.6 + 0.4 * breadth
    return round(quality * confidence, 2)


def aggregate_score(rr, spec):
    mc = (rr or {}).get("metacritic") or {}
    rt = (rr or {}).get("tomatoes") or {}
    mc_score = critic_component(mc.get("rating"), mc.get("votes"), *spec["mc"])
    rt_score = critic_component(rt.get("rating"), rt.get("votes"), *spec["rt"])
    available = [x for x in (mc_score, rt_score) if x > 0]
    if len(available) == 2:
        combined = sum(available) / 2.0
    elif len(available) == 1:
        combined = available[0] * 0.75
    else:
        combined = 0.0
    return round(combined, 2), round(mc_score, 2), round(rt_score, 2)


def merge_family(existing, aggregate):
    existing = float(existing or 0)
    aggregate = float(aggregate or 0)
    if existing <= 0:
        return round(min(100.0, aggregate), 2)
    if aggregate <= 0:
        return round(min(100.0, existing), 2)
    strongest = max(existing, aggregate)
    corroboration = min(existing, aggregate) * 0.25
    return round(min(100.0, strongest + corroboration), 2)


def summarize_variant(base_rows, ratings, name, spec):
    experimental = []
    for row in base_rows:
        rr = ((ratings.get(row.get("imdb_id")) or {}).get("reeldb") or {})
        aggregate, mc, rt = aggregate_score(rr, spec)
        old_critics = float((row.get("source_points") or {}).get("critics_groups_consensus") or 0)
        new_critics = merge_family(old_critics, aggregate)
        new_score = round(float(row.get("overall_score") or 0) - old_critics + new_critics, 2)
        exp = dict(row)
        exp.update({
            "experimental_score": new_score,
            "old_critics_family": round(old_critics, 2),
            "aggregate_critics": aggregate,
            "metacritic_component": mc,
            "tomatoes_component": rt,
            "experimental_critics_family": new_critics,
            "critic_delta": round(new_critics - old_critics, 2),
        })
        experimental.append(exp)

    experimental.sort(key=lambda r: (-r["experimental_score"], r.get("title") or ""))
    for rank, row in enumerate(experimental, 1):
        row["experimental_rank"] = rank

    base_top100 = {r.get("imdb_id") for r in base_rows[:100]}
    new_top100 = {r.get("imdb_id") for r in experimental[:100]}

    controls = {}
    by_title = {r.get("title"): r for r in experimental}
    for title in CONTROLS:
        r = by_title.get(title)
        if not r:
            continue
        controls[title] = {
            "base_score": r.get("overall_score"),
            "new_score": r.get("experimental_score"),
            "base_rank": r.get("overall_rank"),
            "new_rank": r.get("experimental_rank"),
            "old_critics": r.get("old_critics_family"),
            "metacritic": r.get("metacritic_component"),
            "tomatoes": r.get("tomatoes_component"),
            "aggregate": r.get("aggregate_critics"),
            "new_critics": r.get("experimental_critics_family"),
        }

    thresholds = {}
    for floor in (300, 275, 250, 225, 200):
        selected = [
            r for r in experimental
            if r["experimental_score"] >= floor
            and (
                bool(r.get("has_non_audience_evidence"))
                or r.get("experimental_critics_family", 0) > 0
            )
        ]
        thresholds[str(floor)] = {
            "selected": len(selected),
            "promotions_vs_old": sum(not bool(r.get("qualified")) for r in selected),
            "old_qualified_retained": sum(bool(r.get("qualified")) for r in selected),
        }

    newly_covered = [
        r for r in experimental
        if not r.get("has_non_audience_evidence")
        and r.get("experimental_critics_family", 0) > 0
    ]
    newly_covered.sort(key=lambda r: (-r["experimental_score"], r.get("title") or ""))

    deltas = [r["critic_delta"] for r in experimental if r["critic_delta"] > 0]
    return {
        "variant": name,
        "top100_overlap_with_base": len(base_top100 & new_top100),
        "films_with_positive_critic_delta": len(deltas),
        "mean_positive_critic_delta": round(sum(deltas) / len(deltas), 2) if deltas else 0,
        "thresholds": thresholds,
        "controls": controls,
        "newly_non_audience_covered_top40": [
            {
                "title": r.get("title"),
                "year": r.get("year"),
                "base_score": r.get("overall_score"),
                "new_score": r.get("experimental_score"),
                "new_rank": r.get("experimental_rank"),
                "audience": r.get("audience_score"),
                "aggregate_critics": r.get("aggregate_critics"),
                "metacritic_component": r.get("metacritic_component"),
                "tomatoes_component": r.get("tomatoes_component"),
            }
            for r in newly_covered[:40]
        ],
    }


def main():
    scores = json.loads(SCORES.read_text(encoding="utf-8"))
    base_rows = scores.get("films") or []
    ratings_payload = json.loads(RATINGS.read_text(encoding="utf-8"))
    ratings = ratings_payload.get("ratings") or {}

    results = {
        name: summarize_variant(base_rows, ratings, name, spec)
        for name, spec in VARIANTS.items()
    }
    out = {
        "mode": "research-critical-consensus-experiment-v1",
        "qualification_unchanged": True,
        "score_ceiling_unchanged": 1000,
        "policy": "Metacritic critics + Rotten Tomatoes critics are merged inside the existing 100-point critics family; they do not create new score families.",
        "cached_ratings": len(ratings),
        "variants": results,
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        name: {
            "top100_overlap": result["top100_overlap_with_base"],
            "positive_deltas": result["films_with_positive_critic_delta"],
            "mean_delta": result["mean_positive_critic_delta"],
            "thresholds": result["thresholds"],
            "controls": result["controls"],
        }
        for name, result in results.items()
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
