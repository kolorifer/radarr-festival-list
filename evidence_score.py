"""Research-only normalized multi-source evidence scoring.

Each source family contributes at most 100 points. The raw overall score is the
sum of independent families, so the ceiling grows naturally as genuinely new
families are added. Phase-4 qualification routes remain unchanged.
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
ALL_FAMILIES = (
    "tspdt_21c",
    "sight_sound",
    "bbc_21c",
    "nyt_21c",
    "us_institutional",
    "european_recognition",
    "independent_cinema",
    "critics_groups_consensus",
    "audience_consensus",
)


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


def audience_points(reeldb):
    """One 0..100 audience family combining quality and breadth.

    IMDb and Letterboxd each earn a quality score, then vote volume discounts
    small samples. Popularity alone cannot exceed the family cap and a tiny cult
    audience cannot masquerade as broad consensus.
    """
    if not isinstance(reeldb, dict):
        return 0.0
    components = []
    imdb = reeldb.get("imdb") or {}
    if isinstance(imdb.get("rating"), (int, float)) and isinstance(imdb.get("votes"), (int, float)):
        quality = clamp01((float(imdb["rating"]) - 6.5) / 2.0) * 100.0
        components.append(quality * log_confidence(imdb["votes"]))
    lb = reeldb.get("letterboxd") or {}
    lb_votes = lb.get("votes") if lb.get("votes") is not None else lb.get("ratings")
    if isinstance(lb.get("rating"), (int, float)) and isinstance(lb_votes, (int, float)):
        quality = clamp01((float(lb["rating"]) - 3.0) / 1.3) * 100.0
        components.append(quality * log_confidence(lb_votes))
    if not components:
        return 0.0
    return round(sum(components) / len(components), 2)


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
        audience_score = audience_points(rr)
        if audience_score:
            points["audience_consensus"] = audience_score
            evidence["audience_consensus"] = ["IMDb + Letterboxd quality/breadth convergence"]

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
        "mode": "research-evidence-score-v3",
        "qualification_unchanged": True,
        "score_policy": {
            "per_source_family_scale": "0..100",
            "ranked_formula": "100 - 99 * (rank - 1) / (depth - 1)",
            "raw_score": "sum of independent eligible family points; not rescaled to 1000",
            "late_film_policy": "sources published before a film existed are ineligible, not zero",
            "audience_policy": "one capped family; IMDb and Letterboxd ratings are discounted by log-scaled vote breadth",
            "notes": [
                "For a 100-item ranked list the mapping is exactly 100,99,...,1.",
                "TSPDT preserves its full 1000-film depth on the same 1..100 scale.",
                "US institutional = Academy + Golden Globes, capped at 100.",
                "European recognition = BAFTA + Cannes + Berlin + Venice + European Film Awards, capped at 100.",
                "Independent cinema = Sundance + Film Independent Spirit + Gotham, capped at 100.",
                "Critics-groups consensus = NSFC + NYFCC + LAFCA Best Film wins; 35 points per group, capped at 100.",
                "Audience remains one 0..100 family for this calibration; its weight is intentionally unchanged until the expanded-source run is evaluated.",
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
            "audience_consensus": {"type": "family", "max_points": 100},
        },
        "current_score_ceiling": 900,
        "count": len(rows),
        "films": rows,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"films": len(rows), "score_ceiling": 900, "top": rows[:5]}))


if __name__ == "__main__":
    main()
