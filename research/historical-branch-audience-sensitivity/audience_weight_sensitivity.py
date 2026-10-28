"""Compare audience-family weights without changing the research score formula.

The current evidence score gives every source family a 100-point ceiling. This
script asks what happens if the *same* audience evidence is worth 125, 150 or
200 points instead. It never changes evidence-scores.json or qualification.
"""

import json
from pathlib import Path

INPUT = Path("evidence-scores.json")
OUTPUT = Path("audience-weight-sensitivity.json")
MULTIPLIERS = (1.0, 1.25, 1.5, 2.0)

POSITIVE_CONTROLS = [
    "Melancholia", "Get Out", "The Tree of Life", "Boyhood", "The Lives of Others",
    "Lost in Translation", "The White Ribbon", "Dogville", "The Turin Horse", "Arrival",
    "12 Years a Slave", "Gravity", "The Wolf of Wall Street", "Fish Tank",
    "Blue Is the Warmest Colour", "Winter Sleep", "Shame", "Nocturnal Animals",
    "Once Upon a Time in... Hollywood", "Donnie Darko", "There Will Be Blood", "Dune",
    "Dune: Part Two", "Midsommar", "Blade Runner 2049", "Memento", "1917",
    "Mad Max: Fury Road", "Her", "Ex Machina", "Manchester by the Sea", "Into the Wild",
    "The Lobster", "The Killing of a Sacred Deer", "Past Lives", "The Machinist",
    "Scott Pilgrim vs. the World", "Tenet", "The Batman", "The Departed",
]
OTHER_CONTROLS = ["Amores Perros", "A Prophet", "Caché", "Phantom Thread", "La Commune (Paris, 1871)"]
FOCUS = {
    "Blade Runner 2049", "Ex Machina", "Midsommar", "Scott Pilgrim vs. the World",
    "Dune", "Into the Wild", "1917", "Nocturnal Animals", "Manchester by the Sea",
    "La Commune (Paris, 1871)",
}


def adjusted_rows(rows, multiplier):
    adjusted = []
    bonus_factor = multiplier - 1.0
    for row in rows:
        audience = float((row.get("source_points") or {}).get("audience_consensus") or 0.0)
        score = round(float(row.get("overall_score") or 0.0) + bonus_factor * audience, 2)
        item = {**row, "adjusted_score": score, "audience_points": audience}
        adjusted.append(item)
    adjusted.sort(key=lambda r: (-r["adjusted_score"], -r.get("source_hits", 0), r.get("title") or ""))
    for rank, row in enumerate(adjusted, 1):
        row["adjusted_rank"] = rank
    return adjusted


def control_rows(adjusted, names):
    by_title = {}
    for row in adjusted:
        by_title.setdefault(row.get("title"), row)
    out = []
    missing = []
    for title in names:
        row = by_title.get(title)
        if not row:
            missing.append(title)
            continue
        out.append({
            "title": title,
            "year": row.get("year"),
            "score": row["adjusted_score"],
            "rank": row["adjusted_rank"],
            "audience": row["audience_points"],
            "base_rank": row.get("overall_rank"),
            "rank_change": (row.get("overall_rank") or row["adjusted_rank"]) - row["adjusted_rank"],
        })
    return out, missing


def top_summary(adjusted, n=50):
    top = adjusted[:n]
    with_audience = [r for r in top if r["audience_points"] > 0]
    audience_avg = round(sum(r["audience_points"] for r in with_audience) / len(with_audience), 2) if with_audience else 0.0
    strong_audience = sum(1 for r in top if r["audience_points"] >= 75)
    weak_audience = sum(1 for r in top if 0 < r["audience_points"] < 50)
    return {
        "n": n,
        "with_audience_data": len(with_audience),
        "mean_audience_points": audience_avg,
        "audience_75_plus": strong_audience,
        "audience_below_50": weak_audience,
        "titles": [r.get("title") for r in top],
    }


def main():
    payload = json.loads(INPUT.read_text())
    rows = payload.get("films", [])
    result = {
        "mode": "audience-weight-sensitivity-v1",
        "production_unchanged": True,
        "qualification_unchanged": True,
        "base_family_ceiling": payload.get("current_score_ceiling"),
        "interpretation": "Multiplier changes only the audience_consensus contribution; all other evidence is held fixed.",
        "scenarios": {},
    }

    for multiplier in MULTIPLIERS:
        adjusted = adjusted_rows(rows, multiplier)
        positives, missing_positive = control_rows(adjusted, POSITIVE_CONTROLS)
        others, missing_other = control_rows(adjusted, OTHER_CONTROLS)
        result["scenarios"][str(multiplier)] = {
            "audience_max_points": round(100 * multiplier),
            "effective_score_ceiling": (payload.get("current_score_ceiling") or 900) + round(100 * (multiplier - 1)),
            "top_50": top_summary(adjusted, 50),
            "positive_controls": positives,
            "other_controls": others,
            "focus_controls": [x for x in positives + others if x["title"] in FOCUS],
            "missing": missing_positive + missing_other,
        }

    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    compact = {
        multiplier: {
            "audience_max": scenario["audience_max_points"],
            "top50_mean_audience": scenario["top_50"]["mean_audience_points"],
            "focus": scenario["focus_controls"],
        }
        for multiplier, scenario in result["scenarios"].items()
    }
    print(json.dumps(compact, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
