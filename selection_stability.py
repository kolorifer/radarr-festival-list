"""Measure how sensitive the guarded hybrid policy is to nearby thresholds.

Research-only. The active research score and frozen route qualification are not
changed. The experiment varies the score promotion floor and legacy-retention
floor around the current 225 / 175 candidate while keeping the two-independent-
non-audience-family safeguard fixed.
"""

import json
from pathlib import Path

from hybrid_selection_experiment import evaluate, legacy_keep, score_keep

SCORES = Path("evidence-scores.json")
OUTPUT_JSON = Path("selection-stability.json")
OUTPUT_MD = Path("selection-stability.md")

NEW_FLOORS = (215, 220, 225, 230, 235)
LEGACY_FLOORS = (165, 175, 185)
ANCHOR = {
    "new_floor": 225,
    "legacy_floor": 175,
    "protect_multi_route": True,
    "min_non_audience_families": 2,
}


def selected_ids(rows, policy):
    out = set()
    for row in rows:
        if score_keep(row, policy["new_floor"], policy["min_non_audience_families"]) or legacy_keep(
            row, policy["legacy_floor"], policy["protect_multi_route"]
        ):
            out.add(row.get("imdb_id"))
    return out


def compact(row):
    return {
        "rank": row.get("overall_rank"),
        "title": row.get("title"),
        "year": row.get("year"),
        "imdb_id": row.get("imdb_id"),
        "score": row.get("overall_score"),
        "audience": row.get("audience_score"),
        "qualified_old": bool(row.get("qualified")),
        "routes": row.get("routes") or [],
    }


def policy(new_floor, legacy_floor):
    return {
        "new_floor": new_floor,
        "legacy_floor": legacy_floor,
        "protect_multi_route": True,
        "min_non_audience_families": 2,
    }


def main():
    payload = json.loads(SCORES.read_text(encoding="utf-8"))
    rows = payload.get("films") or []
    by_id = {r.get("imdb_id"): r for r in rows}

    anchor_ids = selected_ids(rows, ANCHOR)
    anchor_result = evaluate(rows, ANCHOR)
    grid = {}

    for legacy_floor in LEGACY_FLOORS:
        for new_floor in NEW_FLOORS:
            spec = policy(new_floor, legacy_floor)
            result = evaluate(rows, spec)
            ids = selected_ids(rows, spec)
            added = sorted(ids - anchor_ids, key=lambda iid: -(float((by_id[iid].get("overall_score") or 0))))
            removed = sorted(anchor_ids - ids, key=lambda iid: float((by_id[iid].get("overall_score") or 0)))
            key = f"new{new_floor}_legacy{legacy_floor}"
            grid[key] = {
                "policy": spec,
                "selected": result["selected"],
                "promotions_vs_old": result["promotions_vs_old"],
                "legacy_retained": result["legacy_retained"],
                "legacy_dropped": result["legacy_dropped"],
                "delta_selected_vs_anchor": result["selected"] - anchor_result["selected"],
                "added_vs_anchor": len(added),
                "removed_vs_anchor": len(removed),
                "added_titles": [compact(by_id[iid]) for iid in added[:40]],
                "removed_titles": [compact(by_id[iid]) for iid in removed[:40]],
            }

    score_boundary = [
        compact(row)
        for row in rows
        if not row.get("qualified")
        and 210 <= float(row.get("overall_score") or 0) < 240
    ]
    score_boundary.sort(key=lambda row: (-float(row["score"] or 0), row["title"]))

    legacy_boundary = [
        compact(row)
        for row in rows
        if row.get("qualified")
        and 160 <= float(row.get("overall_score") or 0) < 190
    ]
    legacy_boundary.sort(key=lambda row: (-float(row["score"] or 0), row["title"]))

    out = {
        "mode": "research-selection-stability-v1",
        "qualification_unchanged": True,
        "score_unchanged": True,
        "score_mode": payload.get("mode"),
        "anchor_policy": ANCHOR,
        "anchor": {
            k: anchor_result[k]
            for k in ("selected", "promotions_vs_old", "legacy_retained", "legacy_dropped")
        },
        "grid": grid,
        "promotion_boundary_210_240": score_boundary,
        "legacy_boundary_160_190": legacy_boundary,
    }
    OUTPUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Guarded selection stability",
        "",
        "Research-only sensitivity check. All variants keep the two independent non-audience-family safeguard; only the new-film score floor and old-route retention floor move around the current 225 / 175 candidate.",
        "",
        f"Anchor: **{anchor_result['selected']} selected = {anchor_result['promotions_vs_old']} promotions + {anchor_result['legacy_retained']} legacy retained; {anchor_result['legacy_dropped']} legacy dropped.**",
        "",
        "| New floor | Legacy floor | Selected | Promotions | Legacy retained | Legacy dropped | Δ selected vs anchor |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for legacy_floor in LEGACY_FLOORS:
        for new_floor in NEW_FLOORS:
            row = grid[f"new{new_floor}_legacy{legacy_floor}"]
            lines.append(
                f"| {new_floor} | {legacy_floor} | {row['selected']} | {row['promotions_vs_old']} | "
                f"{row['legacy_retained']} | {row['legacy_dropped']} | {row['delta_selected_vs_anchor']:+d} |"
            )

    lines.extend([
        "",
        "## Score-promotion boundary (unqualified films, 210–239.99)",
        "",
        "| Film | Score | Audience |",
        "|---|---:|---:|",
    ])
    for row in score_boundary:
        lines.append(f"| {row['title']} ({row['year']}) | {row['score']:.1f} | {float(row['audience'] or 0):.1f} |")

    lines.extend([
        "",
        "## Legacy-retention boundary (old qualifiers, 160–189.99)",
        "",
        "| Film | Score | Routes |",
        "|---|---:|---|",
    ])
    for row in legacy_boundary:
        lines.append(f"| {row['title']} ({row['year']}) | {row['score']:.1f} | {', '.join(row['routes']) or '—'} |")

    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "anchor": out["anchor"],
        "grid": {
            key: {
                "selected": value["selected"],
                "promotions": value["promotions_vs_old"],
                "legacy_dropped": value["legacy_dropped"],
                "delta": value["delta_selected_vs_anchor"],
            }
            for key, value in grid.items()
        },
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
