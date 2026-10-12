"""Compare possible score-driven selection rules without changing qualification.

Research-only. Reads evidence-scores.json and reports how alternative thresholds
would behave versus the frozen Phase-4 routes. Audience alone is never allowed
to select a film: every simulated rule requires non-audience evidence.
"""

import json
from pathlib import Path

SCORES = Path("evidence-scores.json")
OUTPUT = Path("score-rule-experiment.json")

NON_AUDIENCE_FAMILIES = {
    "tspdt_21c",
    "sight_sound",
    "bbc_21c",
    "nyt_21c",
    "us_institutional",
    "european_recognition",
    "independent_cinema",
    "critics_groups_consensus",
}

FLOORS = (400, 350, 325, 300, 275, 250, 225, 200)


def non_audience_hits(row):
    points = row.get("source_points") or {}
    return sum(1 for key in NON_AUDIENCE_FAMILIES if float(points.get(key) or 0) > 0)


def strongest_non_audience(row):
    points = row.get("source_points") or {}
    return max((float(points.get(key) or 0) for key in NON_AUDIENCE_FAMILIES), default=0.0)


def compact(row):
    return {
        "rank": row.get("overall_rank"),
        "title": row.get("title"),
        "year": row.get("year"),
        "imdb_id": row.get("imdb_id"),
        "score": row.get("overall_score"),
        "audience": row.get("audience_score"),
        "non_audience_hits": non_audience_hits(row),
        "strongest_non_audience": round(strongest_non_audience(row), 2),
        "qualified_old": bool(row.get("qualified")),
        "old_routes": row.get("routes") or [],
    }


def evaluate(rows, floor, min_non_audience_hits=1):
    selected = [
        r for r in rows
        if float(r.get("overall_score") or 0) >= floor
        and non_audience_hits(r) >= min_non_audience_hits
    ]
    old_qualified = [r for r in rows if r.get("qualified")]
    selected_ids = {r.get("imdb_id") for r in selected}
    old_ids = {r.get("imdb_id") for r in old_qualified}
    promoted = [r for r in selected if r.get("imdb_id") not in old_ids]
    excluded_old = [r for r in old_qualified if r.get("imdb_id") not in selected_ids]
    return {
        "selected": len(selected),
        "old_qualified_retained": len(old_ids & selected_ids),
        "promotions_vs_old": len(promoted),
        "old_qualified_excluded": len(excluded_old),
        "top_promotions": [compact(r) for r in promoted[:40]],
        "lowest_selected": [compact(r) for r in selected[-15:]],
        "lowest_old_excluded": [compact(r) for r in sorted(excluded_old, key=lambda x: (x.get("overall_score") or 0, x.get("title") or ""))[:20]],
    }


def main():
    payload = json.loads(SCORES.read_text())
    rows = payload.get("films") or []

    grid = {}
    for floor in FLOORS:
        grid[str(floor)] = {
            "any_non_audience": evaluate(rows, floor, 1),
            "two_non_audience_families": evaluate(rows, floor, 2),
        }

    review_zone = [
        compact(r) for r in rows
        if not r.get("qualified")
        and 200 <= float(r.get("overall_score") or 0) < 350
        and non_audience_hits(r) >= 1
    ]

    out = {
        "mode": "research-score-rule-experiment-v1",
        "qualification_unchanged": True,
        "policy": "diagnostic only; all simulated score rules require non-audience evidence",
        "film_count": len(rows),
        "old_qualified_count": sum(bool(r.get("qualified")) for r in rows),
        "grid": grid,
        "review_zone_unqualified_200_to_350": review_zone[:150],
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "films": len(rows),
        "old_qualified": out["old_qualified_count"],
        "summary": {
            floor: {
                "any": {
                    k: v for k, v in spec["any_non_audience"].items()
                    if k in {"selected", "old_qualified_retained", "promotions_vs_old", "old_qualified_excluded"}
                },
                "two": {
                    k: v for k, v in spec["two_non_audience_families"].items()
                    if k in {"selected", "old_qualified_retained", "promotions_vs_old", "old_qualified_excluded"}
                },
            }
            for floor, spec in grid.items()
        },
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
