import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import requests

MIN_SCORE = 2
OUTPUT = Path("curated.json")
DETAIL_OUTPUT = Path("curated-details.json")
FESTIVAL_INPUT = Path("festival.json")
YEAR = 2026
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; radarr-festival-list/1.0)"}

# Completed 2026 festival/editorial results are kept as explicit, auditable data.
# Cannes and Letterboxd block GitHub-hosted runners, so scraping them in Actions is
# unreliable. Acting/performance prizes are deliberately ignored.
CANNES_2026 = [
    ("Fjord", 2, "Cannes: Palme d'Or"),
    ("Minotaur", 1, "Cannes: Grand Prix"),
    ("The Dreamed Adventure", 1, "Cannes: Jury Prize"),
    ("Fatherland", 1, "Cannes: Best Director"),
    ("La Bola Negra", 1, "Cannes: Best Director"),
]

BERLIN_2026 = [
    ("Yellow Letters", 2, "Berlinale: Golden Bear for Best Film"),
    ("Salvation", 1, "Berlinale: Silver Bear Grand Jury Prize"),
    ("Queen at Sea", 1, "Berlinale: Silver Bear Jury Prize"),
    ("Everybody Digs Bill Evans", 1, "Berlinale: Silver Bear for Best Director"),
    ("Nina Roza", 1, "Berlinale: Silver Bear for Best Screenplay"),
    ("Yo (Love Is a Rebellious Bird)", 1, "Berlinale: Silver Bear for Outstanding Artistic Contribution"),
]

VENICE_2026 = [
    ("Woman Unknown", 2, "Venice: Golden Lion for Best Film"),
    ("Possible Love", 1, "Venice: Silver Lion - Grand Jury Prize"),
    ("DAU", 1, "Venice: Silver Lion - Best Director"),
    ("A Good Little Soldier", 1, "Venice: Best Screenplay"),
    ("NAZA", 1, "Venice: Special Jury Prize"),
]

LETTERBOXD_CANNES_2026 = [
    "All of a Sudden", "La Bola Negra", "Clarissa", "Club Kid", "Coward",
    "Dua", "Hope", "I'll Be Gone in June", "I See Buildings Fall Like Lightning",
    "La Gradiva", "The Man I Love", "Paper Tiger", "The Samurai and the Prisoner",
    "Tangles", "Teenage Sex and Death at Camp Miasma",
]


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def imdb_lookup(title):
    url = f"https://v3.sg.media-imdb.com/suggestion/x/{quote(title)}.json"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    candidates = r.json().get("d", [])
    exact = [c for c in candidates if norm(c.get("l", "")) == norm(title) and re.fullmatch(r"tt\d+", c.get("id", ""))]
    pool = exact or [c for c in candidates if re.fullmatch(r"tt\d+", c.get("id", ""))]
    if not pool:
        return None
    pool.sort(key=lambda c: (abs((c.get("y") or YEAR) - YEAR), 0 if c in exact else 1))
    c = pool[0]
    return {"title": c.get("l") or title, "imdb_id": c["id"]}


def main():
    festival = json.loads(FESTIVAL_INPUT.read_text(encoding="utf-8"))
    by_name = {norm(m["title"]): m for m in festival}
    scores = defaultdict(int)
    reasons = defaultdict(list)
    display = {}

    for m in festival:
        k = norm(m["title"])
        scores[k] += 1
        reasons[k].append("IMDb Festival list")
        display[k] = m["title"]

    signals = list(CANNES_2026) + list(BERLIN_2026) + list(VENICE_2026)
    signals += [(t, 1, "Letterboxd HQ: Best of Cannes 2026") for t in LETTERBOXD_CANNES_2026]

    for title, points, reason in signals:
        k = norm(title)
        if not k:
            continue
        scores[k] += points
        reasons[k].append(reason)
        display.setdefault(k, title)

    details = []
    radarr = []
    seen_ids = set()
    for k in sorted(scores, key=lambda x: (-scores[x], display[x])):
        title = display[k]
        resolved = by_name.get(k) or imdb_lookup(title)
        row = {"title": title, "score": scores[k], "reasons": reasons[k]}
        if resolved:
            row["imdb_id"] = resolved["imdb_id"]
            row["title"] = resolved["title"]
        details.append(row)
        if scores[k] >= MIN_SCORE and resolved and resolved["imdb_id"] not in seen_ids:
            seen_ids.add(resolved["imdb_id"])
            radarr.append({"title": resolved["title"], "imdb_id": resolved["imdb_id"]})

    if not radarr:
        raise RuntimeError("Curated feed is empty; refusing to overwrite output")
    OUTPUT.write_text(json.dumps(radarr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DETAIL_OUTPUT.write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"MIN_SCORE={MIN_SCORE}: wrote {len(radarr)} movies to {OUTPUT}")
    for row in details:
        if row["score"] >= MIN_SCORE:
            print(f"  {row['score']}  {row['title']}  [{'; '.join(row['reasons'])}]")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
