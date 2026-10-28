"""Research-only normalized multi-source evidence scoring.

Non-audience evidence contributes up to 800 points. Audience evidence is a
single 200-point block built from IMDb, Letterboxd and Trakt equally. Each raw
audience component is calibrated on 0..100 and then scaled by 2/3, so the three
populations together can contribute at most 200. TMDb remains diagnostic only.

Audience-discovery seeds widen the research universe but never qualify a film by
themselves. Existing route qualification remains frozen while the score is
calibrated.
"""

import json
import math
from pathlib import Path

BACKCATALOG = Path("backcatalog-details.json")
INSTITUTIONAL = Path("sources/phase-b-institutional.json")
QUALIFIERS = Path("simulation-qualifiers.json")
AUDIENCE = Path("audience-ratings.json")
SOURCE_SNAPSHOT = Path("sources/evidence-families.json")
DISCOVERY = Path("sources/imdb-audience-discovery.json")
OUTPUT = Path("evidence-scores.json")

TSPDT_DEPTH = 1000
RANKED_FAMILIES = ("sight_sound", "bbc_21c", "nyt_21c")
NON_AUDIENCE_FAMILIES = (
    "tspdt_21c",
    "sight_sound",
    "bbc_21c",
    "nyt_21c",
    "us_institutional",
    "european_recognition",
    "independent_cinema",
    "critics_groups_consensus",
)
AUDIENCE_COMPONENTS = ("imdb_audience", "letterboxd_audience", "trakt_audience")
AUDIENCE_SCALE = 2.0 / 3.0
AUDIENCE_BLOCK_MAX = 200
AUDIENCE_GATEWAY_MIN = 130
AUDIENCE_GATEWAY_COMPONENT_MIN = 50


def ranked_points(rank, depth):
    """Map rank 1..depth onto 100..1 linearly."""
    if not isinstance(rank, int) or not isinstance(depth, int) or depth < 1:
        return 0.0
    if rank < 1 or rank > depth:
        return 0.0
    if depth == 1:
        return 100.0
    return round(100.0 - (99.0 * (rank - 1) / (depth - 1)), 2)


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def log_confidence(votes, low=1000, full=100000):
    """Log-scaled breadth confidence: tiny samples are strongly discounted."""
    if not isinstance(votes, (int, float)) or votes <= low:
        return 0.0
    if votes >= full:
        return 1.0
    return clamp01(math.log10(votes / low) / math.log10(full / low))


def _rating_component(rating, votes, rating_floor, rating_full, vote_low, vote_full):
    if not isinstance(rating, (int, float)) or not isinstance(votes, (int, float)):
        return 0.0
    if rating_full <= rating_floor:
        return 0.0
    quality = clamp01((float(rating) - rating_floor) / (rating_full - rating_floor)) * 100.0
    return round(quality * log_confidence(votes, vote_low, vote_full), 2)


def imdb_points(reeldb):
    imdb = (reeldb or {}).get("imdb") or {}
    return _rating_component(imdb.get("rating"), imdb.get("votes"), 6.5, 8.5, 1000, 100000)


def letterboxd_points(reeldb):
    lb = (reeldb or {}).get("letterboxd") or {}
    votes = lb.get("votes") if lb.get("votes") is not None else lb.get("ratings")
    return _rating_component(lb.get("rating"), votes, 3.0, 4.3, 1000, 100000)


def tmdb_points(reeldb):
    """Diagnostic TMDb audience score, 0..100; not included in overall score."""
    tmdb = (reeldb or {}).get("tmdb") or {}
    return _rating_component(tmdb.get("rating"), tmdb.get("votes"), 65.0, 85.0, 100, 10000)


def trakt_points(reeldb):
    """Calibrated Trakt audience score, 0..100."""
    trakt = (reeldb or {}).get("trakt") or {}
    return _rating_component(trakt.get("rating"), trakt.get("votes"), 65.0, 85.0, 100, 10000)


def audience_raw_components(reeldb):
    return {
        "imdb_audience": imdb_points(reeldb),
        "letterboxd_audience": letterboxd_points(reeldb),
        "trakt_audience": trakt_points(reeldb),
    }


def audience_points(reeldb):
    """Active three-population audience block, 0..200."""
    return round(sum(audience_raw_components(reeldb).values()) * AUDIENCE_SCALE, 2)


def audience_gateway_pass(raw_components):
    total = sum(raw_components.values()) * AUDIENCE_SCALE
    strong_sources = sum(1 for value in raw_components.values() if value >= AUDIENCE_GATEWAY_COMPONENT_MIN)
    return total >= AUDIENCE_GATEWAY_MIN and strong_sources >= 2


def _load(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def ranked_indexes(snapshot):
    out = {}
    for key in RANKED_FAMILIES:
        source = (snapshot.get("ranked_sources") or {}).get(key) or {}
        out[key] = {
            "depth": int(source.get("published_depth") or 100),
            "eligible_through_year": source.get("eligible_through_year"),
            "films": {x.get("imdb_id"): x for x in source.get("films", []) if x.get("imdb_id")},
        }
    return out


def build_rows(backcatalog, institutional, qualifiers, audience, snapshot, discovery=None):
    discovery = discovery or {}
    candidates = {x["imdb_id"]: x for x in backcatalog.get("candidates", []) if x.get("imdb_id")}
    institutions = {x["imdb_id"]: x for x in institutional.get("films", []) if x.get("imdb_id")}
    qualifier_map = {x["imdb_id"]: x for x in qualifiers if x.get("imdb_id")}
    snapshot_films = snapshot.get("films") or {}
    discovery_map = {x["imdb_id"]: x for x in discovery.get("films", []) if x.get("imdb_id")}
    ratings = audience.get("ratings") or {}
    ranked = ranked_indexes(snapshot)

    ids = set(candidates) | set(institutions) | set(qualifier_map) | set(snapshot_films) | set(discovery_map)
    rows = []
    for imdb_id in sorted(ids):
        candidate = candidates.get(imdb_id, {})
        inst = institutions.get(imdb_id, {})
        qual = qualifier_map.get(imdb_id, {})
        snap = snapshot_films.get(imdb_id, {})
        seed = discovery_map.get(imdb_id, {})
        title = candidate.get("title") or inst.get("title") or qual.get("title") or snap.get("title") or seed.get("title")
        year = candidate.get("year") or inst.get("year") or qual.get("year") or snap.get("year") or seed.get("year")
        year_int = int(year) if str(year).isdigit() else None
        tspdt_rank = candidate.get("tspdt_rank")

        candidate_sources = []
        if candidate:
            candidate_sources.append("tspdt")
        if inst:
            candidate_sources.append("institutional")
        if snap:
            candidate_sources.append("evidence_snapshot")
        if seed:
            candidate_sources.append("audience_discovery")

        points = {}
        evidence = {}
        experimental_points = {}
        experimental_evidence = {}
        nonaud_eligibility = {key: True for key in NON_AUDIENCE_FAMILIES}

        tspdt = ranked_points(tspdt_rank, TSPDT_DEPTH)
        if tspdt:
            points["tspdt_21c"] = tspdt
            evidence["tspdt_21c"] = [f"TSPDT 21st Century #{tspdt_rank}"]

        for key in RANKED_FAMILIES:
            spec = ranked[key]
            cutoff = spec.get("eligible_through_year")
            if year_int and cutoff and year_int > int(cutoff):
                nonaud_eligibility[key] = False
                continue
            hit = spec["films"].get(imdb_id)
            if hit:
                score = ranked_points(int(hit["rank"]), int(spec["depth"]))
                if score:
                    points[key] = score
                    evidence[key] = [f"{key} #{hit['rank']}"]

        family_scores = snap.get("family_scores") or {}
        family_evidence = snap.get("family_evidence") or {}
        for key in (
            "us_institutional",
            "european_recognition",
            "independent_cinema",
            "critics_groups_consensus",
        ):
            value = family_scores.get(key)
            if isinstance(value, (int, float)) and value > 0:
                points[key] = round(min(100.0, float(value)), 2)
                evidence[key] = family_evidence.get(key, [])

        rr = (ratings.get(imdb_id) or {}).get("reeldb") or {}
        if not rr and seed.get("imdb_rating") is not None and seed.get("imdb_votes") is not None:
            rr = {"imdb": {"rating": seed.get("imdb_rating"), "votes": seed.get("imdb_votes")}}

        raw_audience = audience_raw_components(rr)
        for key, raw_value in raw_audience.items():
            if raw_value > 0:
                points[key] = round(raw_value * AUDIENCE_SCALE, 2)
                evidence[key] = [f"{key.replace('_audience', '').title()} rating + vote breadth; 2/3 audience-block weight"]

        tmdb_score = tmdb_points(rr)
        if tmdb_score:
            experimental_points["tmdb_audience"] = tmdb_score
            experimental_evidence["tmdb_audience"] = ["TMDb rating + vote breadth (diagnostic only)"]

        nonaud_points = sum(value for key, value in points.items() if key in NON_AUDIENCE_FAMILIES)
        audience_total = round(sum(raw_audience.values()) * AUDIENCE_SCALE, 2)
        gateway = bool(seed) and audience_gateway_pass(raw_audience)
        has_nonaud = nonaud_points > 0

        eligible_nonaud_sources = [key for key, ok in nonaud_eligibility.items() if ok]
        eligible_max = 100 * len(eligible_nonaud_sources) + AUDIENCE_BLOCK_MAX
        total = round(sum(points.values()), 2)
        rows.append({
            "title": title,
            "year": year,
            "imdb_id": imdb_id,
            "tspdt_rank": tspdt_rank,
            "candidate_sources": candidate_sources,
            "audience_discovery_seed": bool(seed),
            "audience_discovery_tier": seed.get("discovery_tier"),
            "audience_gateway_pass": gateway,
            "has_non_audience_evidence": has_nonaud,
            "audience_only_candidate": bool(gateway and not has_nonaud),
            "audience_raw_points": {k: round(v, 2) for k, v in raw_audience.items()},
            "audience_score": audience_total,
            "source_points": points,
            "source_evidence": evidence,
            "experimental_source_points": experimental_points,
            "experimental_source_evidence": experimental_evidence,
            "overall_score": total,
            "source_hits": len(points),
            "eligible_sources": len(eligible_nonaud_sources) + 1,
            "eligible_max_score": eligible_max,
            "eligible_score_pct": round(100.0 * total / eligible_max, 2) if eligible_max else 0.0,
            "qualified": bool(qual),
            "routes": qual.get("routes", []),
        })

    rows.sort(key=lambda r: (-r["overall_score"], -r["source_hits"], r["title"] or ""))
    for position, row in enumerate(rows, 1):
        row["overall_rank"] = position
    return rows


def main():
    backcatalog = _load(BACKCATALOG, {})
    institutional = _load(INSTITUTIONAL, {})
    qualifiers = _load(QUALIFIERS, [])
    audience = _load(AUDIENCE, {})
    snapshot = _load(SOURCE_SNAPSHOT, {})
    discovery = _load(DISCOVERY, {})
    rows = build_rows(backcatalog, institutional, qualifiers, audience, snapshot, discovery)

    payload = {
        "mode": "research-evidence-score-v6-audience200-discovery",
        "qualification_unchanged": True,
        "score_policy": {
            "non_audience_max": 800,
            "audience_max": 200,
            "current_score_ceiling": 1000,
            "ranked_formula": "100 - 99 * (rank - 1) / (depth - 1)",
            "late_film_policy": "sources published before a film existed are ineligible, not zero",
            "audience_policy": "IMDb, Letterboxd and Trakt are calibrated separately on 0..100 then each multiplied by 2/3; combined maximum 200",
            "audience_discovery_policy": "IMDb public datasets provide broad 2000+ discovery seeds; cross-audience support is flagged, but audience alone never qualifies",
            "audience_gateway": {
                "combined_min": AUDIENCE_GATEWAY_MIN,
                "component_min": AUDIENCE_GATEWAY_COMPONENT_MIN,
                "minimum_components_at_or_above_component_min": 2,
            },
        },
        "sources": {
            "tspdt_21c": {"type": "ranked", "depth": TSPDT_DEPTH, "max_points": 100},
            "sight_sound": {"type": "ranked", "depth": 100, "max_points": 100},
            "bbc_21c": {"type": "ranked", "depth": 100, "max_points": 100, "eligible_through_year": 2016},
            "nyt_21c": {"type": "ranked", "depth": 100, "max_points": 100, "eligible_through_year": 2025},
            "us_institutional": {"type": "family", "max_points": 100},
            "european_recognition": {"type": "family", "max_points": 100},
            "independent_cinema": {"type": "family", "max_points": 100},
            "critics_groups_consensus": {"type": "family", "max_points": 100},
            "imdb_audience": {"type": "audience_component", "raw_max": 100, "active_max": 66.67, "active": True},
            "letterboxd_audience": {"type": "audience_component", "raw_max": 100, "active_max": 66.67, "active": True},
            "trakt_audience": {"type": "audience_component", "raw_max": 100, "active_max": 66.67, "active": True},
            "tmdb_audience": {"type": "audience", "max_points": 100, "active": False, "diagnostic": True},
        },
        "current_score_ceiling": 1000,
        "count": len(rows),
        "discovery_seed_count": sum(r["audience_discovery_seed"] for r in rows),
        "audience_gateway_pass_count": sum(r["audience_gateway_pass"] for r in rows),
        "audience_only_candidate_count": sum(r["audience_only_candidate"] for r in rows),
        "films": rows,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "films": len(rows),
        "score_ceiling": 1000,
        "discovery_seeds": payload["discovery_seed_count"],
        "gateway_pass": payload["audience_gateway_pass_count"],
        "audience_only": payload["audience_only_candidate_count"],
        "top": rows[:5],
    }))


if __name__ == "__main__":
    main()
