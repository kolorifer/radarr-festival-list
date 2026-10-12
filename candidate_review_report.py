"""Generate a compact research review of score-driven candidate changes.

This is diagnostic only. It does not alter the frozen qualification routes.
"""

import json
from pathlib import Path

SCORES = Path("evidence-scores.json")
OUTPUT = Path("candidate-review.md")

NON_AUDIENCE = (
    "tspdt_21c",
    "sight_sound",
    "bbc_21c",
    "nyt_21c",
    "us_institutional",
    "european_recognition",
    "independent_cinema",
    "critics_groups_consensus",
)

LABELS = {
    "tspdt_21c": "TSPDT",
    "sight_sound": "S&S",
    "bbc_21c": "BBC",
    "nyt_21c": "NYT",
    "us_institutional": "US inst.",
    "european_recognition": "Europe",
    "independent_cinema": "Indie",
    "critics_groups_consensus": "Critics",
}


def nonaud(row):
    points = row.get("source_points") or {}
    return {k: float(points.get(k) or 0) for k in NON_AUDIENCE if float(points.get(k) or 0) > 0}


def evidence_summary(row):
    values = sorted(nonaud(row).items(), key=lambda kv: (-kv[1], kv[0]))
    return ", ".join(f"{LABELS[k]} {v:.0f}" for k, v in values) or "none"


def table(rows, limit=None):
    if limit is not None:
        rows = rows[:limit]
    out = [
        "| # | Film | Score | Audience /200 | Non-audience evidence |",
        "|---:|---|---:|---:|---|",
    ]
    for r in rows:
        title = str(r.get("title") or "").replace("|", "\\|")
        year = r.get("year") or "?"
        out.append(
            f"| {r.get('overall_rank')} | {title} ({year}) | {float(r.get('overall_score') or 0):.1f} | "
            f"{float(r.get('audience_score') or 0):.1f} | {evidence_summary(r)} |"
        )
    if not rows:
        out.append("| — | — | — | — | — |")
    return "\n".join(out)


def main():
    payload = json.loads(SCORES.read_text())
    rows = payload.get("films") or []

    unqualified_nonaud = [r for r in rows if not r.get("qualified") and nonaud(r)]
    old_low = [r for r in rows if r.get("qualified") and float(r.get("overall_score") or 0) < 200]
    audience_only = [
        r for r in rows
        if not r.get("qualified") and not nonaud(r) and float(r.get("audience_score") or 0) >= 140
    ]

    sections = [
        "# Candidate review — 2000+ research model",
        "",
        "Diagnostic only. Frozen route qualification is unchanged. Audience alone never selects a film.",
        "",
        f"Universe: **{len(rows)}** films · currently route-qualified: **{sum(bool(r.get('qualified')) for r in rows)}**.",
        "",
        "## High-confidence score promotions (>=300)",
        "",
        table([r for r in unqualified_nonaud if float(r.get("overall_score") or 0) >= 300]),
        "",
        "## Main threshold review zone (250–299.99)",
        "",
        table([r for r in unqualified_nonaud if 250 <= float(r.get("overall_score") or 0) < 300]),
        "",
        "## Lower review zone (225–249.99)",
        "",
        table([r for r in unqualified_nonaud if 225 <= float(r.get("overall_score") or 0) < 250]),
        "",
        "## Old-route qualifiers below 200",
        "",
        "These reveal where the previous route model is much more canon/niche-friendly than the continuous score.",
        "",
        table(sorted(old_low, key=lambda r: -(float(r.get("overall_score") or 0)))),
        "",
        "## Strong audience-only candidates (>=140/200)",
        "",
        "These are deliberately not selectable yet; they expose missing non-audience coverage rather than a reason to weaken the safeguard.",
        "",
        table(sorted(audience_only, key=lambda r: -(float(r.get("audience_score") or 0))), limit=60),
        "",
    ]
    OUTPUT.write_text("\n".join(sections), encoding="utf-8")
    print(json.dumps({
        "high_promotions": sum(1 for r in unqualified_nonaud if float(r.get("overall_score") or 0) >= 300),
        "review_250_300": sum(1 for r in unqualified_nonaud if 250 <= float(r.get("overall_score") or 0) < 300),
        "review_225_250": sum(1 for r in unqualified_nonaud if 225 <= float(r.get("overall_score") or 0) < 250),
        "old_qualified_below_200": len(old_low),
        "audience_only_140_plus": len(audience_only),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
