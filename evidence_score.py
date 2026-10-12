"""Research-only normalized multi-source evidence scoring.

Every independent source family contributes on a 0..100 scale. Ranked lists are
normalized across their published depth so a 100-film list maps exactly 100, 99,
..., 1 while a 1000-film list still gives its last-ranked film 1 point instead of
throwing away ranks 101..1000.

This file does not change Phase 4 qualification routes. It adds an orthogonal,
inspectable score that can later be calibrated and surfaced in movie-intel.
"""

import json
from pathlib import Path

BACKCATALOG = Path("backcatalog-details.json")
INSTITUTIONAL = Path("sources/phase-b-institutional.json")
QUALIFIERS = Path("simulation-qualifiers.json")
OUTPUT = Path("evidence-scores.json")

# TSPDT's published 21st-century list depth. Use the published depth, not the
# number of entries we happened to resolve, so points remain stable over time.
TSPDT_DEPTH = 1000
INSTITUTIONAL_MAX_STRENGTH = 3


def ranked_points(rank, depth):
    """Map rank 1..depth onto 100..1 linearly.

    For a depth-100 source this is exactly 100, 99, ..., 1.
    For a deeper source the same 1..100 scale preserves the full list.
    """
    if not isinstance(rank, int) or not isinstance(depth, int) or depth < 1:
        return 0.0
    if rank < 1 or rank > depth:
        return 0.0
    if depth == 1:
        return 100.0
    return round(100.0 - (99.0 * (rank - 1) / (depth - 1)), 2)


def institutional_points(strength):
    """Map the existing 0..3 institutional evidence strength onto 0..100.

    This is deliberately proportional rather than a new hand-tuned point table.
    As Phase B gains separate Academy/Cannes/Venice/Berlin source families, each
    can receive its own explicit source score instead of being bundled here.
    """
    if not isinstance(strength, (int, float)) or strength <= 0:
        return 0.0
    bounded = min(float(strength), float(INSTITUTIONAL_MAX_STRENGTH))
    return round(100.0 * bounded / INSTITUTIONAL_MAX_STRENGTH, 2)


def build_rows(backcatalog, institutional, qualifiers):
    candidates = {
        x["imdb_id"]: x
        for x in backcatalog.get("candidates", [])
        if x.get("imdb_id")
    }
    institutions = {
        x["imdb_id"]: x
        for x in institutional.get("films", [])
        if x.get("imdb_id")
    }
    qualifier_map = {
        x["imdb_id"]: x
        for x in qualifiers
        if x.get("imdb_id")
    }

    rows = []
    for imdb_id in sorted(set(candidates) | set(institutions) | set(qualifier_map)):
        candidate = candidates.get(imdb_id, {})
        inst = institutions.get(imdb_id, {})
        qual = qualifier_map.get(imdb_id, {})

        title = candidate.get("title") or inst.get("title") or qual.get("title")
        year = candidate.get("year") or inst.get("year") or qual.get("year")
        tspdt_rank = candidate.get("tspdt_rank")
        inst_strength = inst.get("institutional_strength", 0)

        source_points = {}
        tspdt = ranked_points(tspdt_rank, TSPDT_DEPTH)
        if tspdt:
            source_points["tspdt_21c"] = tspdt
        inst_score = institutional_points(inst_strength)
        if inst_score:
            source_points["institutional_recognition"] = inst_score

        rows.append({
            "title": title,
            "year": year,
            "imdb_id": imdb_id,
            "tspdt_rank": tspdt_rank,
            "institutional_strength": inst_strength,
            "source_points": source_points,
            "overall_score": round(sum(source_points.values()), 2),
            "source_hits": len(source_points),
            "qualified": bool(qual),
            "routes": qual.get("routes", []),
        })

    rows.sort(key=lambda r: (-r["overall_score"], -r["source_hits"], r["title"] or ""))
    for position, row in enumerate(rows, 1):
        row["overall_rank"] = position
    return rows


def main():
    backcatalog = json.loads(BACKCATALOG.read_text())
    institutional = json.loads(INSTITUTIONAL.read_text())
    qualifiers = json.loads(QUALIFIERS.read_text())
    rows = build_rows(backcatalog, institutional, qualifiers)

    payload = {
        "mode": "research-evidence-score-v1",
        "qualification_unchanged": True,
        "score_policy": {
            "per_source_scale": "0..100",
            "ranked_formula": "100 - 99 * (rank - 1) / (depth - 1)",
            "missing_source": 0,
            "audience_in_overall_score": False,
            "notes": [
                "A 100-item ranked source maps exactly 100,99,...,1.",
                "Longer lists preserve their full published depth on the same 1..100 scale.",
                "Scores are raw sums across source families; they are not normalized to 1000.",
                "The total ceiling grows by 100 whenever a new independent source family is added.",
                "IMDb and Letterboxd stay separate for now so audience popularity cannot dominate critical/institutional evidence.",
            ],
        },
        "sources": {
            "tspdt_21c": {"type": "ranked", "depth": TSPDT_DEPTH, "max_points": 100},
            "institutional_recognition": {"type": "categorical", "max_strength": 3, "max_points": 100},
        },
        "current_score_ceiling": 200,
        "count": len(rows),
        "films": rows,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"films": len(rows), "score_ceiling": 200, "top": rows[:5]}))


if __name__ == "__main__":
    main()
