"""More tolerant and rate-limit-safe IMDb resolver for backcatalog.py."""
import json
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote

import backcatalog as bc
import film_identity as fi

PRIMARY_TITLE_ALIASES = {
    ("La Ciénaga", 2001): "The Swamp",
}

VERIFIED_IMDB = {
    ("Margaret", 2011): ("tt0466893", "Margaret", 2011),
    ("Lovers Rock", 2020): ("tt10551102", "Lovers Rock", 2020),
    ("The World", 2004): ("tt0423176", "The World", 2004),
    ("The Circle", 2000): ("tt0255094", "The Circle", 2000),
    ("L' Enfant", 2005): ("tt0456396", "The Child", 2005),
    ("Borat: Cultural Learnings of America for Make Benefit Glorious Nation of Kazakhstan", 2006): ("tt0443453", "Borat", 2006),
    ("Shara", 2003): ("tt0363060", "Sharasôju", 2003),
    ("Le Quattro Volte", 2010): ("tt1646975", "The Four Times", 2010),
    ("Days", 2020): ("tt11697820", "Days", 2020),
    ("Notre musique", 2004): ("tt0360845", "Our Music", 2004),
    ("Playing", 2007): ("tt1165293", "Jogo de cena", 2007),
    ("La Captive", 2000): ("tt0216605", "The Captive", 2000),
    ("The Sun", 2005): ("tt0439817", "The Sun", 2005),
    ("Eden", 2014): ("tt3090634", "Eden", 2014),
    ("At Sea", 2007): ("tt1829648", "At Sea", 2007),
    ("Dune: Part One", 2021): ("tt1160419", "Dune", 2021),
    ("Santiago", 2007): ("tt1002543", "Santiago", 2007),
    ("The Mouth of the Wolf", 2009): ("tt1603480", "The Mouth of the Wolf", 2009),
    ("Heremias", 2006): ("tt0843515", "Heremias, Book One: The Legend of the Lizard Princess", 2006),
    ("Hat Wolff von Amerongen Konkursdelikte begangen?", 2004): ("tt0499138", "Wolff von Amerongen: Did He Commit Bankruptcy Offences?", 2004),
    ("Daratt", 2006): ("tt0825241", "Dry Season", 2006),
    ("Une Visite au Louvre", 2004): ("tt0405418", "A Visit to the Louvre", 2004),
    ("The Secret of the Grain", 2007): ("tt0487419", "The Secret of the Grain", 2007),
    ("Barbara", 2012): ("tt2178941", "Barbara", 2012),
    ("Mia madre", 2015): ("tt3013610", "My Mother", 2015),
    ("Aurora", 2010): ("tt1403047", "Aurora", 2010),
    ("Lady Vengeance", 2005): ("tt0451094", "Lady Vengeance", 2005),
    ("Amy", 2015): ("tt2870648", "Amy", 2015),
    ("Of Time and the City", 2008): ("tt1232790", "Of Time and the City", 2008),
    ("Trilogy: The Weeping Meadow", 2004): ("tt0366721", "Trilogia: To livadi pou dakryzei", 2004),
    ("Operai, contadini", 2001): ("tt0305923", "Workers, Peasants", 2001),
    ("Black Sun", 2005): ("tt0478101", "Black Sun", 2005),
    ("Quei loro incontri", 2006): ("tt0815227", "These Encounters of Theirs", 2006),
    ("Mangrove", 2020): ("tt10551100", "Mangrove", 2020),
    ("America", 2019): ("tt6217698", "America", 2019),
    ("Ex Libris: The New York Public Library", 2017): ("tt6209282", "Ex Libris", 2017),
    ("The 3 Rooms of Melancholia", 2004): ("tt0424272", "The 3 Rooms of Melancholia", 2004),
    ("The Heart of the World", 2000): ("tt0260948", "The Heart of the World", 2000),
    ("La Vie nouvelle", 2002): ("tt0310313", "A New Life", 2002),
    ("No", 2012): ("tt2059255", "No", 2012),
    ("Stevie", 2002): ("tt0334416", "Stevie", 2002),
    ("Tristram Shandy: A Cock and Bull Story", 2005): ("tt0423409", "Tristram Shandy", 2005),
    ("Material", 2009): ("tt1380807", "Material", 2009),
    ("Where Does Your Hidden Smile Lie?", 2001): ("tt0342866", "Where Does Your Hidden Smile Lie?", 2001),
    ("Jackie", 2016): ("tt1619029", "Jackie", 2016),
}

# backcatalog.py resolves concurrently. Serialize outbound IMDb suggestion requests and
# leave a small gap between them so six workers cannot burst into IMDb's 429 limit.
_REQUEST_LOCK = threading.Lock()
_NEXT_REQUEST_AT = 0.0
REQUEST_INTERVAL = 0.40


def _rate_limited_fetch(url):
    global _NEXT_REQUEST_AT
    with _REQUEST_LOCK:
        now = time.monotonic()
        if now < _NEXT_REQUEST_AT:
            time.sleep(_NEXT_REQUEST_AT - now)
        try:
            return bc.fetch(url)
        finally:
            _NEXT_REQUEST_AT = time.monotonic() + REQUEST_INTERVAL


def fetch_json_with_retry(url, attempts=8):
    for attempt in range(attempts):
        try:
            return json.loads(_rate_limited_fetch(url))
        except HTTPError as exc:
            if exc.code != 429 or attempt == attempts - 1:
                raise
            time.sleep(min(10 * (attempt + 1), 60))
    raise RuntimeError("unreachable")


def imdb_lookup(title, year, source_metadata=None):
    verified = fi.verified_identity(title, year)
    if verified:
        return verified["imdb_id"], verified["title"], verified["year"]
    source = {**(source_metadata or {}), "title": title, "year": year}
    query_title = PRIMARY_TITLE_ALIASES.get((title, year), title)
    url = f"https://v2.sg.media-imdb.com/suggestion/x/{quote(query_title)}.json"
    data = fetch_json_with_retry(url)
    candidates = []
    for item in data.get("d", []):
        iid = item.get("id", "")
        if not iid.startswith("tt"):
            continue
        metadata = fi.cached_metadata(iid)
        aliases = (query_title,) if query_title != title else ()
        if fi.accepts(source, item, metadata, aliases):
            candidates.append((iid, item["l"], item["y"]))
    return candidates[0] if len(candidates) == 1 else None


bc.imdb_lookup = imdb_lookup

if __name__ == "__main__":
    bc.main()
