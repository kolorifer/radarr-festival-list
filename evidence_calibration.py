"""Print score rows for calibration films without influencing the scoring model.

These titles are diagnostic controls only. They are deliberately read after
`evidence-scores.json` is generated and never feed back into qualification or
source weighting.
"""
import json
from pathlib import Path

SCORES = Path("evidence-scores.json")

POSITIVE_CONTROLS = [
    "Melancholia",
    "Get Out",
    "The Tree of Life",
    "Boyhood",
    "The Lives of Others",
    "Lost in Translation",
    "The White Ribbon",
    "Dogville",
    "The Turin Horse",
    "Arrival",
    "12 Years a Slave",
    "Gravity",
    "The Wolf of Wall Street",
    "Fish Tank",
    "Blue Is the Warmest Colour",
    "Winter Sleep",
    "Shame",
    "Nocturnal Animals",
    "Once Upon a Time in... Hollywood",
    "Donnie Darko",
    "There Will Be Blood",
    "Dune",
    "Dune: Part Two",
    "Midsommar",
    "Blade Runner 2049",
    "Memento",
    "1917",
    "Mad Max: Fury Road",
    "Her",
    "Ex Machina",
    "Manchester by the Sea",
    "Into the Wild",
    "The Lobster",
    "The Killing of a Sacred Deer",
    "Past Lives",
    "The Machinist",
    "Scott Pilgrim vs. the World",
    "Tenet",
    "The Batman",
    "The Departed",
]

OTHER_CONTROLS = [
    "Amores Perros",
    "A Prophet",
    "Caché",
    "Phantom Thread",
    "La Commune (Paris, 1871)",
]


def compact(row):
    return {
        "title": row["title"],
        "year": row["year"],
        "score": row["overall_score"],
        "max": row["eligible_max_score"],
        "pct": row["eligible_score_pct"],
        "rank": row["overall_rank"],
        "hits": row["source_hits"],
        "points": row["source_points"],
    }


def main():
    data = json.loads(SCORES.read_text())
    rows = data["films"]
    by_title = {}
    for row in rows:
        by_title.setdefault(row["title"].casefold(), []).append(row)

    def resolve(title):
        exact = by_title.get(title.casefold(), [])
        if exact:
            return exact[0]
        # Conservative fallback for punctuation/title variants in the research set.
        needle = title.casefold().replace(":", "").replace("...", "")
        candidates = [r for r in rows if r["title"] and r["title"].casefold().replace(":", "").replace("...", "") == needle]
        return candidates[0] if len(candidates) == 1 else None

    report = {"positive_controls": [], "other_controls": [], "missing": []}
    for group_name, titles in (("positive_controls", POSITIVE_CONTROLS), ("other_controls", OTHER_CONTROLS)):
        for title in titles:
            row = resolve(title)
            if row:
                report[group_name].append(compact(row))
            else:
                report["missing"].append(title)
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
