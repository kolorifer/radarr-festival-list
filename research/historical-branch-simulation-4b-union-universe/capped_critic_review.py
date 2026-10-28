"""Render the capped broad-critic experiment into a compact human review.

Research-only. No scoring or qualification state is changed.
"""

import json
from pathlib import Path

SOURCE = Path("critical-consensus-experiment.json")
OUTPUT = Path("capped-critic-review.md")
CAPS = ("capped30_conservative", "capped40_conservative", "capped50_conservative")


def summary_table(data):
    lines = [
        "| Variant | Top-100 overlap | Mean +critic pts | >=250 selected / promotions | >=225 selected / promotions |",
        "|---|---:|---:|---:|---:|",
    ]
    for key in CAPS:
        v = data[key]
        t250 = v["thresholds"]["250"]
        t225 = v["thresholds"]["225"]
        lines.append(
            f"| {key} | {v['top100_overlap_with_base']}/100 | {v['mean_positive_critic_delta']:.1f} | "
            f"{t250['selected']} / {t250['promotions_vs_old']} | {t225['selected']} / {t225['promotions_vs_old']} |"
        )
    return "\n".join(lines)


def cross_table(rows):
    lines = [
        "| Film | Base → new | Audience | Broad critic add | Previously had non-audience? |",
        "|---|---:|---:|---:|:---:|",
    ]
    for r in rows:
        title = str(r.get("title") or "").replace("|", "\\|")
        year = r.get("year") or "?"
        lines.append(
            f"| {title} ({year}) | {float(r.get('base_score') or 0):.1f} → {float(r.get('new_score') or 0):.1f} | "
            f"{float(r.get('audience') or 0):.1f} | {float(r.get('broad_critic_points') or 0):.1f} | "
            f"{'yes' if r.get('had_non_audience_before') else 'no'} |"
        )
    if not rows:
        lines.append("| — | — | — | — | — |")
    return "\n".join(lines)


def control_table(v):
    lines = ["| Control | Base → new | Broad critic add |", "|---|---:|---:|"]
    for title, r in v.get("controls", {}).items():
        lines.append(
            f"| {title} | {float(r.get('base_score') or 0):.1f} → {float(r.get('new_score') or 0):.1f} | "
            f"{float(r.get('broad_points') or 0):.1f} |"
        )
    return "\n".join(lines)


def main():
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    variants = payload["variants"]
    chosen = variants["capped40_conservative"]
    sections = [
        "# Capped broad-critic review",
        "",
        "Diagnostic only. Metacritic + Rotten Tomatoes critic consensus stays inside the existing critics family; score ceiling remains 1000.",
        "",
        "## 30 / 40 / 50 point cap comparison",
        "",
        summary_table(variants),
        "",
        "## 40-point cap: films newly crossing 250",
        "",
        cross_table(chosen["threshold_crossers_vs_base_unqualified"]["250"]),
        "",
        "## 40-point cap: films newly crossing 225",
        "",
        cross_table(chosen["threshold_crossers_vs_base_unqualified"]["225"]),
        "",
        "## 40-point cap: calibration controls",
        "",
        control_table(chosen),
        "",
    ]
    OUTPUT.write_text("\n".join(sections), encoding="utf-8")
    print(json.dumps({
        "cap40_crossers_250": len(chosen["threshold_crossers_vs_base_unqualified"]["250"]),
        "cap40_crossers_225": len(chosen["threshold_crossers_vs_base_unqualified"]["225"]),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
