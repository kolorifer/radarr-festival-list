import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

MIN_SCORE = 2
OUTPUT = Path("curated.json")
DETAIL_OUTPUT = Path("curated-details.json")
FESTIVAL_INPUT = Path("festival.json")
YEAR = 2026

URLS = {
    "venice": "https://www.labiennale.org/en/news/official-awards-83rd-venice-international-film-festival",
    "berlin": "https://letterboxd.com/berlinale_ifb/list/winners-of-the-76th-berlin-international/detail/",
    "letterboxd": "https://letterboxd.com/crew/list/best-of-cannes-2026/",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; radarr-festival-list/1.0)"}

# Cannes blocks GitHub-hosted runners with HTTP 403. Keep its film-level 2026
# jury results as explicit data, verified against the official results and Reuters.
# Acting/performance prizes are deliberately ignored.
CANNES_2026 = [
    ("Fjord", 2, "Cannes: Palme d'Or"),
    ("Minotaur", 1, "Cannes: Grand Prix"),
    ("The Dreamed Adventure", 1, "Cannes: Jury Prize"),
    ("Fatherland", 1, "Cannes: Best Director"),
    ("La Bola Negra", 1, "Cannes: Best Director"),
]

VENICE_AWARDS = {
    "GOLDEN LION FOR BEST FILM": 2, "SILVER LION – GRAND JURY PRIZE": 1,
    "SILVER LION - GRAND JURY PRIZE": 1, "SILVER LION – AWARD FOR BEST DIRECTOR": 1,
    "SILVER LION - AWARD FOR BEST DIRECTOR": 1, "SPECIAL JURY PRIZE": 1,
    "AWARD FOR BEST SCREENPLAY": 1,
}
BERLIN_AWARDS = {
    "Golden Bear for Best Film": 2, "Silver Bear Grand Jury Prize": 1,
    "Silver Bear Jury Prize": 1, "Silver Bear for Best Director": 1,
    "Silver Bear for Best Screenplay": 1, "Silver Bear for Outstanding Artistic Contribution": 1,
}


def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def lines(url):
    return [clean(x) for x in get_soup(url).stripped_strings if clean(x)]


def title_after(ls, i, skip=8):
    """Find the next plausible title after an award label."""
    noise = ("directed by", "by ", "for the film", "jury", "award", "prize", "best ", "to:")
    for x in ls[i + 1:i + 1 + skip]:
        low = x.lower()
        if len(x) < 2 or any(low.startswith(n) for n in noise):
            continue
        if re.search(r"\b(19|20)\d{2}\b", x) and len(x) > 40:
            continue
        return x
    return None


def parse_award_page(url, award_map, source):
    ls = lines(url)
    out = []
    for i, text in enumerate(ls):
        key = next((k for k in award_map if k.lower() == text.lower().rstrip(":")), None)
        if not key:
            continue
        title = title_after(ls, i)
        if title:
            title = re.split(r"\s+by\s+", title, maxsplit=1, flags=re.I)[0].strip()
            out.append((title, award_map[key], f"{source}: {key}"))
    return out


def parse_letterboxd_hq():
    soup = get_soup(URLS["letterboxd"])
    titles = []
    for tag in soup.select("[data-film-name]"):
        title = clean(tag.get("data-film-name", ""))
        if title and title not in titles:
            titles.append(title)
    if not titles:
        for tag in soup.find_all("h2"):
            title = clean(tag.get_text(" ", strip=True))
            if title and title.lower() not in {"best of cannes 2026"} and title not in titles:
                titles.append(title)
    if not titles:
        raise RuntimeError("Could not parse Letterboxd HQ Cannes list")
    return [(t, 1, "Letterboxd HQ: Best of Cannes 2026") for t in titles[:30]]


def parse_berlin():
    soup = get_soup(URLS["berlin"])
    out = []
    for h2 in soup.find_all("h2"):
        title = clean(h2.get_text(" ", strip=True))
        if not title:
            continue
        context = []
        node = h2
        for _ in range(5):
            node = node.find_next()
            if not node:
                break
            context.append(clean(node.get_text(" ", strip=True)))
        blob = " | ".join(context)
        for award, score in BERLIN_AWARDS.items():
            if award.lower() in blob.lower():
                out.append((title, score, f"Berlinale: {award}"))
                break
    if not out:
        raise RuntimeError("Could not parse Berlinale winners")
    return out


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

    signals = list(CANNES_2026)
    signals += parse_award_page(URLS["venice"], VENICE_AWARDS, "Venice")
    signals += parse_berlin()
    signals += parse_letterboxd_hq()

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
