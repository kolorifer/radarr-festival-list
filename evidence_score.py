"""Research-only normalized multi-source evidence scoring.

Each active source family contributes at most 100 points. IMDb and Letterboxd
are now separate audience families (100 points each). TMDb audience evidence is
calculated alongside them but kept experimental until the three audience-source
modes are compared.
"""

import json
import math
from pathlib import Path

BACKCATALOG = Path("backcatalog-details.json")
INSTITUTIONAL = Path("sources/phase-b-institutional.json")
QUALIFIERS = Path("simulation-qualifiers.json")
AUDIENCE = Path("audience-ratings.json")
SOURCE_SNAPSHOT = Path("sources/evidence-families.json")
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
ACTIVE_AUDIENCE_FAMILIES = ("imdb_audience", "letterboxd_audience")
ALL_FAMILIES = NON_AUDIENCE_FAMILIES + ACTIVE_AUDIENCE_FAMILIES


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
    """Experimental TMDb audience score, 0..100.

    ReelDB exposes TMDb rating on a 0..100 scale. TMDb has a materially smaller
    voting population than IMDb/Letterboxd, so breadth reaches full confidence
    at 10k votes rather than 100k; 100 or fewer votes earn no breadth credit.
    """
    tmdb = (reeldb or {}).get("tmdb") or {}
    return _rating_component(tmdb.get("rating"), tmdb.get("votes"), 65.0, 85.0, 100, 10000)


def audience_points(reeldb):
    """Legacy helper: mean of IMDb and Letterboxd component scores."""
    components = [x for x in (imdb_points(reeldb), letterboxd_points(reeldb)) if x > 0]
    return round(sum(components) / len(components), 2) if components else 0.0


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


def build_rows(backcatalog, institutional, qualifiers, audience, snapshot):
    candidates = {x["imdb_id"]: x for x in backcatalog.get("candidates", []) if x.get("imdb_id")}
    institutions = {x["imdb_id"]: x for x in institutional.get("films", []) if x.get("imdb_id")}
    qualifier_map = {x["imdb_id"]: x for x in qualifiers if x.get("imdb_id")}
    snapshot_films = snapshot.get("films") or {}
    ratings = audience.get("ratings") or {}
    ranked = ranked_indexes(snapshot)

    ids = set(candidates) | set(institutions) | set(qualifier_map) | set(snapshot_films)
    rows = []
    for imdb_id in sorted(ids):
        candidate = candidates.get(imdb_id, {})
        inst = institutions.get(imdb_id, {})
        qual = qualifier_map.get(imdb_id, {})
        snap = snapshot_films.get(imdb_id, {})
        title = candidate.get("title") or inst.get("title") or qual.get("title") or snap.get("title")
        year = candidate.get("year") or inst.get("year") or qual.get("year") or snap.get("year")
        year_int = int(year) if str(year).isdigit() else None
        tspdt_rank = candidate.get("tspdt_rank")

        points = {}
        evidence = {}
        experimental_points = {}
        experimental_evidence = {}
        eligibility = {key: True for key in ALL_FAMILIES}

        tspdt = ranked_points(tspdt_rank, TSPDT_DEPTH)
        if tspdt:
            points["tspdt_21c"] = tspdt
            evidence["tspdt_21c"] = [f"TSPDT 21st Century #{tspdt_rank}"]

        for key in RANKED_FAMILIES:
            spec = ranked[key]
            cutoff = spec.get("eligible_through_year")
            if year_int and cutoff and year_int > int(cutoff):
                eligibility[key] = False
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
        imdb_score = imdb_points(rr)
        if imdb_score:
            points["imdb_audience"] = imdb_score
            evidence["imdb_audience"] = ["IMDb rating + vote breadth"]
        lb_score = letterboxd_points(rr)
        if lb_score:
            points["letterboxd_audience"] = lb_score
            evidence["letterboxd_audience"] = ["Letterboxd rating + vote breadth"]
        tmdb_score = tmdb_points(rr)
        if tmdb_score:
            experimental_points["tmdb_audience"] = tmdb_score
            experimental_evidence["tmdb_audience"] = ["TMDb rating + vote breadth (experimental)"]

        eligible_sources = [k for k, ok in eligibility.items() if ok]
        eligible_max = 100 * len(eligible_sources)
        total = round(sum(points.values()), 2)
        rows.append({
            "title": title,
            "year": year,
            "imdb_id": imdb_id,
            "tspdt_rank": tspdt_rank,
            "source_points": points,
            "source_evidence": evidence,
            "experimental_source_points": experimental_points,
            "experimental_source_evidence": experimental_evidence,
            "overall_score": total,
            "source_hits": len(points),
            "eligible_sources": len(eligible_sources),
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
    rows = build_rows(backcatalog, institutional, qualifiers, audience, snapshot)

    payload = {
        "mode": "research-evidence-score-v4-split-audience",
        "qualification_unchanged": True,
        "score_policy": {
            "per_source_family_scale": "0..100",
            "ranked_formula": "100 - 99 * (rank - 1) / (depth - 1)",
            "raw_score": "sum of independent eligible family points; not rescaled to 1000",
            "late_film_policy": "sources published before a film existed are ineligible, not zero",
            "audience_policy": "IMDb and Letterboxd are independent active 0..100 sources; TMDb is calculated as an experimental third 0..100 source",
            "notes": [
                "For a 100-item ranked list the mapping is exactly 100,99,...,1.",
                "TSPDT preserves its full 1000-film depth on the same 1..100 scale.",
                "US institutional = Academy + Golden Globes, capped at 100.",
                "European recognition = BAFTA + Cannes + Berlin + Venice + European Film Awards, capped at 100.",
                "Independent cinema = Sundance + Film Independent Spirit + Gotham, capped at 100.",
                "Critics-groups consensus = NSFC + NYFCC + LAFCA Best Film wins; 35 points per group, capped at 100.",
                "IMDb and Letterboxd each contribute up to 100 active points.",
                "TMDb is present in ReelDB's cached payload already; no extra API calls are required for the comparison.",
            ],
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
            "imdb_audience": {"type": "audience", "max_points": 100, "active": True},
            "letterboxd_audience": {"type": "audience", "max_points": 100, "active": True},
            "tmdb_audience": {"type": "audience", "max_points": 100, "active": False, "experimental": True},
        },
        "current_score_ceiling": 1000,
        "experimental_three_source_ceiling": 1100,
        "count": len(rows),
        "films": rows,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"films": len(rows), "score_ceiling": 1000, "top": rows[:5]}))


if __name__ == "__main__":
    main()
