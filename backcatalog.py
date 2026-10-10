import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

# Audit-only historical canon layer. Nothing here is connected to Radarr yet.
MIN_YEAR = 2000
MAX_YEAR = 2023
MIN_SCORE = 2

CANDIDATES = [
    ("In the Mood for Love", 2000, 7, ["TSPDT 21st-century: elite tier", "Sight & Sound 2022 critics: #5"]),
    ("Mulholland Drive", 2001, 7, ["TSPDT 21st-century: elite tier", "Sight & Sound 2022 critics: #8"]),
    ("Yi Yi", 2000, 6, ["TSPDT 21st-century: elite tier", "Sight & Sound 2022 critics: =#90", "Sight & Sound 2022 directors: =#93"]),
    ("Moonlight", 2016, 6, ["TSPDT 21st-century: top tier", "Sight & Sound 2022 critics: =#60", "Sight & Sound 2022 directors: =#93"]),
    ("The Tree of Life", 2011, 5, ["TSPDT 21st-century: top tier", "major festival/canon signal"]),
    ("Tropical Malady", 2004, 5, ["TSPDT 21st-century: top tier", "Sight & Sound 2022 critics: =#95"]),
    ("The Gleaners & I", 2000, 5, ["TSPDT 21st-century: top tier", "Sight & Sound 2022 critics top 100"]),
    ("Get Out", 2017, 5, ["TSPDT 21st-century: top tier", "Sight & Sound 2022 critics: =#95"]),
    ("Goodbye, Dragon Inn", 2003, 4, ["TSPDT 21st-century: high tier", "Sight & Sound 2022 critics: =#108"]),
    ("Werckmeister Harmonies", 2000, 4, ["TSPDT 21st-century: high tier", "strong international canon signal"]),
    ("Phantom Thread", 2017, 3, ["TSPDT 21st-century: high tier"]),
    ("The Act of Killing", 2012, 3, ["TSPDT 21st-century: high tier", "major documentary canon signal"]),
    ("Boyhood", 2014, 3, ["TSPDT 21st-century: high tier"]),
    ("Once Upon a Time in Anatolia", 2011, 3, ["TSPDT 21st-century: high tier", "Cannes Grand Prix"]),
    ("Elephant", 2003, 3, ["TSPDT 21st-century: high tier", "Cannes Palme d'Or"]),
    ("The Death of Mr. Lazarescu", 2005, 3, ["TSPDT 21st-century: high tier", "Cannes Un Certain Regard winner"]),
    ("Punch-Drunk Love", 2002, 3, ["TSPDT 21st-century: high tier"]),
    ("The Lives of Others", 2006, 3, ["TSPDT 21st-century: high tier", "major awards signal"]),
    ("The Master", 2012, 3, ["TSPDT 21st-century: high tier"]),
    ("Morvern Callar", 2002, 2, ["TSPDT 21st-century: strong tier"]),
    ("A Prophet", 2009, 3, ["TSPDT 21st-century: strong tier", "Cannes Grand Prix"]),
    ("Synecdoche, New York", 2008, 2, ["TSPDT 21st-century: strong tier"]),
    ("Caché", 2005, 4, ["TSPDT 21st-century: elite/high tier", "Sight & Sound 2022 directors: =#93"]),
]

EXCLUDED_AFTER_REVIEW = {
    "La Ciénaga": "watched; did not like",
    "Uncle Boonmee Who Can Recall His Past Lives": "watched; did not like",
}


def imdb_lookup(title, year):
    url = f"https://v2.sg.media-imdb.com/suggestion/x/{quote(title)}.json"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as response:
        data = json.load(response)
    same_title = []
    same_year = []
    for item in data.get("d", []):
        imdb_id = item.get("id", "")
        if not imdb_id.startswith("tt"):
            continue
        item_title = item.get("l", "")
        item_year = item.get("y")
        row = (imdb_id, item_title, item_year)
        if item_title.casefold() == title.casefold() and item_year == year:
            return row
        if item_title.casefold() == title.casefold():
            same_title.append(row)
        if item_year == year:
            same_year.append(row)
    if same_title:
        return same_title[0]
    # IMDb can expose an alternate/translated title. A same-year result is a
    # useful fallback for this small reviewed candidate set, but keep failures
    # non-fatal so one title can never break the whole audit.
    if len(same_year) == 1:
        return same_year[0]
    return None


def main():
    details = []
    radarr = []
    unresolved = []
    for title, year, score, signals in CANDIDATES:
        if not (MIN_YEAR <= year <= MAX_YEAR) or score < MIN_SCORE:
            continue
        try:
            match = imdb_lookup(title, year)
        except Exception as exc:
            unresolved.append({"title": title, "year": year, "error": str(exc)})
            print(f"WARNING: IMDb lookup failed for {title} ({year}): {exc}")
            continue
        if not match:
            unresolved.append({"title": title, "year": year, "error": "no unambiguous IMDb match"})
            print(f"WARNING: unresolved IMDb title: {title} ({year})")
            continue
        imdb_id, resolved_title, resolved_year = match
        details.append({
            "title": resolved_title,
            "year": resolved_year or year,
            "imdb_id": imdb_id,
            "score": score,
            "signals": signals,
            "status": "candidate",
        })
        radarr.append({"title": resolved_title, "imdb_id": imdb_id})

    details.sort(key=lambda x: (-x["score"], x["year"], x["title"]))
    radarr_order = {x["imdb_id"]: i for i, x in enumerate(details)}
    radarr.sort(key=lambda x: radarr_order[x["imdb_id"]])

    audit = {
        "mode": "audit-only",
        "year_range": [MIN_YEAR, MAX_YEAR],
        "min_score": MIN_SCORE,
        "candidates": details,
        "unresolved": unresolved,
        "excluded_after_review": EXCLUDED_AFTER_REVIEW,
    }
    Path("backcatalog-details.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path("backcatalog.json").write_text(json.dumps(radarr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audit only: wrote {len(radarr)} candidates to backcatalog.json; {len(unresolved)} unresolved")
    for row in details:
        print(f"{row['score']}  {row['title']} ({row['year']})  {row['imdb_id']}")


if __name__ == "__main__":
    main()
