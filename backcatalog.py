import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

# Audit-only historical canon layer. Nothing here is connected to Radarr yet.
MIN_YEAR = 2000
MAX_YEAR = 2023
TSPDT_URL = "https://theyshootpictures.com/21stcentury_allfilms_table.php"
CACHE = Path("sources/tspdt-21c.json")

# Independent canon signals from the 2022 Sight & Sound polls.
SIGHT_SOUND_CRITICS = {
    ("In the Mood for Love", 2000), ("Mulholland Drive", 2001),
    ("The Gleaners & I", 2000), ("Spirited Away", 2001),
    ("Tropical Malady", 2004), ("Moonlight", 2016), ("Get Out", 2017),
    ("Parasite", 2019), ("Portrait of a Lady on Fire", 2019),
}
SIGHT_SOUND_DIRECTORS = {
    ("In the Mood for Love", 2000), ("Mulholland Drive", 2001),
    ("La Ciénaga", 2001), ("Tropical Malady", 2004), ("A Separation", 2011),
    ("Eternal Sunshine of the Spotless Mind", 2004), ("Caché", 2005),
    ("Yi Yi", 2000), ("Moonlight", 2016), ("Parasite", 2019),
}

# Major festival top prizes, 2000-2023. Festival-year and film-year occasionally differ;
# keys use the film year used by TSPDT/IMDb so signals attach to the correct work.
CANNES_PALME = {
    ("Dancer in the Dark", 2000), ("The Son's Room", 2001), ("The Pianist", 2002),
    ("Elephant", 2003), ("Fahrenheit 9/11", 2004), ("L'Enfant", 2005),
    ("The Wind That Shakes the Barley", 2006), ("4 Months, 3 Weeks and 2 Days", 2007),
    ("The Class", 2008), ("The White Ribbon", 2009),
    ("Uncle Boonmee Who Can Recall His Past Lives", 2010), ("The Tree of Life", 2011),
    ("Amour", 2012), ("Blue Is the Warmest Colour", 2013), ("Winter Sleep", 2014),
    ("Dheepan", 2015), ("I, Daniel Blake", 2016), ("The Square", 2017),
    ("Shoplifters", 2018), ("Parasite", 2019), ("Titane", 2021),
    ("Triangle of Sadness", 2022), ("Anatomy of a Fall", 2023),
}
VENICE_GOLDEN_LION = {
    ("The Circle", 2000), ("Monsoon Wedding", 2001), ("The Magdalene Sisters", 2002),
    ("The Return", 2003), ("Vera Drake", 2004), ("Brokeback Mountain", 2005),
    ("Still Life", 2006), ("Lust, Caution", 2007), ("The Wrestler", 2008),
    ("Lebanon", 2009), ("Somewhere", 2010), ("Faust", 2011), ("Pietà", 2012),
    ("Sacro GRA", 2013), ("A Pigeon Sat on a Branch Reflecting on Existence", 2014),
    ("From Afar", 2015), ("The Woman Who Left", 2016), ("The Shape of Water", 2017),
    ("Roma", 2018), ("Joker", 2019), ("Nomadland", 2020), ("Happening", 2021),
    ("All the Beauty and the Bloodshed", 2022), ("Poor Things", 2023),
}
BERLIN_GOLDEN_BEAR = {
    ("Magnolia", 1999), ("Intimacy", 2001), ("Bloody Sunday", 2002), ("Spirited Away", 2001),
    ("In This World", 2002), ("Head-On", 2004), ("U-Carmen eKhayelitsha", 2005),
    ("Grbavica", 2006), ("Tuya's Marriage", 2006), ("Elite Squad", 2007),
    ("The Milk of Sorrow", 2009), ("Honey", 2010), ("A Separation", 2011),
    ("Caesar Must Die", 2012), ("Child's Pose", 2013), ("Black Coal, Thin Ice", 2014),
    ("Taxi", 2015), ("Fire at Sea", 2016), ("On Body and Soul", 2017),
    ("Touch Me Not", 2018), ("Synonyms", 2019), ("There Is No Evil", 2020),
    ("Bad Luck Banging or Loony Porn", 2021), ("Alcarràs", 2022), ("On the Adamant", 2023),
}

# Taste is a tie-breaker, never the gatekeeper. Unknown films get no penalty.
TASTE = {
    ("Moonlight", 2016): 1.0, ("Melancholia", 2011): 1.0, ("Get Out", 2017): 1.0,
    ("The Tree of Life", 2011): 1.0, ("Boyhood", 2014): 1.0,
    ("The Lives of Others", 2006): 1.0, ("Lost in Translation", 2003): 1.0,
    ("The White Ribbon", 2009): 1.0, ("Dogville", 2003): 1.0,
    ("The Turin Horse", 2011): 0.5, ("A Prophet", 2009): 0.5,
}

# Watch state affects recommended Radarr monitoring only; it never removes a canonical film.
WATCHED = {
    ("Moonlight", 2016), ("Melancholia", 2011), ("Get Out", 2017),
    ("The Tree of Life", 2011), ("Boyhood", 2014), ("The Lives of Others", 2006),
    ("Lost in Translation", 2003), ("The White Ribbon", 2009), ("Dogville", 2003),
    ("The Turin Horse", 2011), ("A Prophet", 2009), ("Caché", 2005),
    ("La Ciénaga", 2001), ("Uncle Boonmee Who Can Recall His Past Lives", 2010),
    ("Mulholland Drive", 2001), ("Under the Skin", 2013),
    ("A.I. Artificial Intelligence", 2001), ("Children of Men", 2006),
    ("Platform", 2000), ("Brokeback Mountain", 2005), ("Amour", 2012),
    ("Dancer in the Dark", 2000), ("Crouching Tiger, Hidden Dragon", 2000),
    ("Zodiac", 2007), ("The Piano Teacher", 2001), ("The Great Beauty", 2013),
    ("Hunger", 2008), ("Moulin Rouge!", 2001), ("Fish Tank", 2009),
    ("Let the Right One In", 2008), ("Blue Is the Warmest Colour", 2013),
    ("The Return", 2003),
}

ALIASES = {
    ("Mulholland Dr.", 2001): "Mulholland Drive",
    ("Ciénaga, La", 2001): "La Ciénaga",
}


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (radarr-festival-list audit)"})
    with urlopen(req, timeout=30) as response:
        return response.read()


def article_first(title):
    articles = "The|A|An|La|Le|Les|El|Los|Las|Il|Lo|Gli|I|L'|Un|Une"
    m = re.match(rf"^(.*), ({articles})$", title, flags=re.IGNORECASE)
    return f"{m.group(2)} {m.group(1)}" if m else title


def clean_tspdt_title(title):
    title = re.sub(r"\s*\[\d{4}\]\s*$", "", title).strip()
    return article_first(title)


def scrape_tspdt():
    soup = BeautifulSoup(fetch(TSPDT_URL), "html.parser")
    rows = []
    for tr in soup.select("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.select("td")]
        if len(cells) < 7 or not cells[0].isdigit(): continue
        rank = int(cells[0]); title_raw = cells[2]
        if "[TV]" in title_raw: continue
        try: year = int(cells[4])
        except ValueError: continue
        rows.append({"rank": rank, "title": clean_tspdt_title(title_raw), "tspdt_title": title_raw,
                     "director": cells[3], "year": year, "country": cells[5],
                     "runtime": int(cells[6]) if cells[6].isdigit() else None})
    if len(rows) < 900: raise RuntimeError(f"TSPDT parse returned only {len(rows)} films")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows


def load_tspdt():
    try: return scrape_tspdt(), "live"
    except Exception as exc:
        if CACHE.exists():
            print(f"WARNING: live TSPDT refresh failed; using cache: {exc}")
            return json.loads(CACHE.read_text(encoding="utf-8")), "cache"
        raise


def tspdt_points(rank):
    if rank <= 25: return 5.0
    if rank <= 50: return 4.0
    if rank <= 100: return 3.0
    if rank <= 250: return 2.0
    if rank <= 500: return 1.0
    return 0.5


def canonical_key(title, year):
    title = article_first(title.strip())
    title = ALIASES.get((title, year), title)
    return title, year


def normalized_title(title):
    text = unicodedata.normalize("NFKD", title.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text)


def imdb_lookup(title, year):
    url = f"https://v2.sg.media-imdb.com/suggestion/x/{quote(title)}.json"
    data = json.loads(fetch(url)); norm = normalized_title(title); matches = []
    for item in data.get("d", []):
        imdb_id = item.get("id", ""); item_title = item.get("l", ""); item_year = item.get("y")
        if not imdb_id.startswith("tt"): continue
        if not isinstance(item_year, int) or abs(item_year - year) > 1: continue
        if normalized_title(item_title) != norm: continue
        matches.append((abs(item_year - year), imdb_id, item_title, item_year))
    if not matches: return None
    _, imdb_id, item_title, item_year = min(matches)
    return imdb_id, item_title, item_year


def score_row(row):
    title, year = canonical_key(row["title"], row["year"]); key = (title, year)
    score = tspdt_points(row["rank"]); signals = [f"TSPDT 21st-century #{row['rank']}"]
    if key in SIGHT_SOUND_CRITICS: score += 3.0; signals.append("Sight & Sound 2022 critics top 100")
    if key in SIGHT_SOUND_DIRECTORS: score += 2.0; signals.append("Sight & Sound 2022 directors top 100")
    if key in CANNES_PALME: score += 1.0; signals.append("Cannes Palme d'Or")
    if key in VENICE_GOLDEN_LION: score += 1.0; signals.append("Venice Golden Lion")
    if key in BERLIN_GOLDEN_BEAR: score += 1.0; signals.append("Berlin Golden Bear")
    taste = TASTE.get(key, 0)
    if taste: score += taste; signals.append(f"personal-positive +{taste:g}")
    return title, score, signals, key in WATCHED


def resolve_one(row):
    title, score, signals, watched = score_row(row)
    match = imdb_lookup(title, row["year"])
    if not match: return None, {"title": title, "year": row["year"], "tspdt_rank": row["rank"]}
    imdb_id, resolved_title, resolved_year = match
    return {"title": resolved_title, "year": resolved_year, "imdb_id": imdb_id,
            "tspdt_rank": row["rank"], "score": score, "signals": signals,
            "director": row["director"], "country": row["country"], "runtime": row["runtime"],
            "status": "candidate", "watch_state": "watched" if watched else "unknown",
            "recommended_monitored": not watched}, None


def main():
    tspdt, source_mode = load_tspdt(); universe = [r for r in tspdt if MIN_YEAR <= r["year"] <= MAX_YEAR]
    print(f"TSPDT source={source_mode}; {len(universe)} films in {MIN_YEAR}-{MAX_YEAR}")
    details, unresolved = [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(resolve_one, row): row for row in universe}
        for i, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            try:
                item, miss = future.result()
                if item: details.append(item)
                if miss: unresolved.append(miss)
            except Exception as exc:
                unresolved.append({"title": row["title"], "year": row["year"], "tspdt_rank": row["rank"], "error": str(exc)})
            if i % 100 == 0: print(f"Resolved {i}/{len(universe)}")
    details.sort(key=lambda x: (-x["score"], x["tspdt_rank"])); unresolved.sort(key=lambda x: x["tspdt_rank"])
    radarr = [{"title": x["title"], "imdb_id": x["imdb_id"]} for x in details]
    audit = {"mode": "audit-only", "year_range": [MIN_YEAR, MAX_YEAR],
             "source": "TSPDT 21st Century Top 1000", "source_mode": source_mode,
             "scoring": {"TSPDT_1_25": 5, "TSPDT_26_50": 4, "TSPDT_51_100": 3,
                         "TSPDT_101_250": 2, "TSPDT_251_500": 1, "TSPDT_501_1000": 0.5,
                         "Sight_and_Sound_critics_top100": 3, "Sight_and_Sound_directors_top100": 2,
                         "Cannes_Palme": 1, "Venice_Golden_Lion": 1, "Berlin_Golden_Bear": 1,
                         "taste": "0 to +1; ranking/tie-break only"},
             "watch_policy": "watched films remain candidates but recommended_monitored=false",
             "universe_count": len(universe), "resolved_count": len(details), "unresolved_count": len(unresolved),
             "candidates": details, "unresolved": unresolved}
    Path("backcatalog-details.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path("backcatalog.json").write_text(json.dumps(radarr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Audit only: {len(details)} resolved, {len(unresolved)} unresolved")
    for row in details[:50]: print(f"{row['score']:>4g}  TSPDT #{row['tspdt_rank']:>3}  {row['title']} ({row['year']})  {row['imdb_id']}")

if __name__ == "__main__": main()
