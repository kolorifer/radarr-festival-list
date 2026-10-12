"""Focused review of the leading hybrid policy: new>=225 + legacy>=175.

Diagnostic only. This report concentrates on the uncertain boundary: newly
promoted films between 225 and 250, legacy films retained below 225, and legacy
films dropped below 175. It does not alter qualification or production feeds.
"""

import json
from pathlib import Path

from hybrid_selection_experiment import evaluate

SCORES = Path("evidence-scores.json")
OUTPUT = Path("hybrid-policy-review.md")
POLICY = {"new_floor": 225, "legacy_floor": 175, "protect_multi_route": True}

GROUPS = {
    "Canon": ("tspdt_21c", "sight_sound"),
    "BBC": ("bbc_21c",),
    "NYT": ("nyt_21c",),
    "US": ("us_institutional",),
    "Europe": ("european_recognition",),
    "Indie": ("independent_cinema",),
    "Critics": ("critics_groups_consensus",),
}


def evidence_summary(row):
    points = row.get("source_points") or {}
    values = []
    for label, keys in GROUPS.items():
        value = sum(float(points.get(key) or 0) for key in keys)
        if value > 0:
            values.append((value, label))
    values.sort(reverse=True)
    return ", ".join(f"{label} {value:.0f}" for value, label in values) or "none"


def line(row):
    title = str(row.get("title") or "").replace("|", "\\|")
    routes = ", ".join(row.get("routes") or []) or "—"
    return (
        f"| {row.get('overall_rank')} | {title} ({row.get('year')}) | {float(row.get('overall_score') or 0):.1f} | "
        f"{float(row.get('audience_score') or 0):.1f} | {evidence_summary(row)} | {routes} |"
    )


def table(rows):
    out = [
        "| # | Film | Score | Audience | Non-audience evidence | Old route |",
        "|---:|---|---:|---:|---|---|",
    ]
    out.extend(line(row) for row in rows)
    if not rows:
        out.append("| — | — | — | — | — | — |")
    return "\n".join(out)


def main():
    payload = json.loads(SCORES.read_text(encoding="utf-8"))
    rows = payload.get("films") or []
    result = evaluate(rows, POLICY)
    old_ids = {r.get("imdb_id") for r in rows if r.get("qualified")}
    selected = [
        r for r in rows
        if (
            (float(r.get("overall_score") or 0) >= POLICY["new_floor"] and r.get("has_non_audience_evidence"))
            or (
                r.get("qualified")
                and (
                    float(r.get("overall_score") or 0) >= POLICY["legacy_floor"]
                    or len(r.get("routes") or []) >= 2
                )
            )
        )
    ]
    selected_ids = {r.get("imdb_id") for r in selected}

    boundary_promotions = [
        r for r in selected
        if r.get("imdb_id") not in old_ids and 225 <= float(r.get("overall_score") or 0) < 250
    ]
    retained_legacy_low = [
        r for r in selected
        if r.get("qualified") and 175 <= float(r.get("overall_score") or 0) < 225
    ]
    dropped = [r for r in rows if r.get("qualified") and r.get("imdb_id") not in selected_ids]

    boundary_promotions.sort(key=lambda r: (-float(r.get("overall_score") or 0), r.get("title") or ""))
    retained_legacy_low.sort(key=lambda r: (-float(r.get("overall_score") or 0), r.get("title") or ""))
    dropped.sort(key=lambda r: (-float(r.get("overall_score") or 0), r.get("title") or ""))

    sections = [
        "# Hybrid policy review — new ≥225, legacy ≥175",
        "",
        "Diagnostic only. New films still require non-audience evidence; old multi-route qualifiers remain protected below the legacy floor.",
        "",
        f"Selected **{result['selected']}** films: **{result['promotions_vs_old']}** promotions, **{result['legacy_retained']}** legacy retained, **{result['legacy_dropped']}** legacy dropped.",
        "",
        "## Boundary promotions: 225–249.99",
        "",
        "These are the films most likely to determine whether 225 is too permissive.",
        "",
        table(boundary_promotions),
        "",
        "## Legacy retained below 225",
        "",
        "These survive only because the old route system still supplies useful historical signal down to 175.",
        "",
        table(retained_legacy_low),
        "",
        "## Legacy dropped below 175",
        "",
        "These are the films the balanced policy would deliberately stop carrying forward.",
        "",
        table(dropped),
        "",
    ]
    OUTPUT.write_text("\n".join(sections), encoding="utf-8")
    print(json.dumps({
        "selected": result["selected"],
        "promotions": result["promotions_vs_old"],
        "retained": result["legacy_retained"],
        "dropped": result["legacy_dropped"],
        "boundary_promotions": len(boundary_promotions),
        "retained_legacy_175_225": len(retained_legacy_low),
        "dropped_titles": [r.get("title") for r in dropped],
    }, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
