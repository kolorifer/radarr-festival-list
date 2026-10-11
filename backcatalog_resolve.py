"""More tolerant and rate-limit-safe IMDb resolver for backcatalog.py."""
import json
import time
from difflib import SequenceMatcher
from urllib.error import HTTPError
from urllib.parse import quote

import backcatalog as bc

# Confirmed title variants where IMDb's primary English title is unrelated to the
# title used by TSPDT. Fuzzy matching handles ordinary spelling/localisation variants.
PRIMARY_TITLE_ALIASES = {
    ("La Ciénaga", 2001): "The Swamp",
}

# A small number of works are treated as films by TSPDT but differently by IMDb.
# The suggestion service still returns tt IDs, so we deliberately do not filter qid/type.


def similarity(a, b):
    a = bc.normalized_title(a)
    b = bc.normalized_title(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def fetch_json_with_retry(url, attempts=6):
    for attempt in range(attempts):
        try:
            return json.loads(bc.fetch(url))
        except HTTPError as exc:
            if exc.code != 429 or attempt == attempts - 1:
                raise
            # IMDb suggestion starts throttling bursty GitHub runners. Back off
            # progressively rather than turning rate limits into false unresolved films.
            time.sleep(1.5 * (2 ** attempt))
    raise RuntimeError("unreachable")


def imdb_lookup(title, year):
    query_title = PRIMARY_TITLE_ALIASES.get((title, year), title)
    url = f"https://v2.sg.media-imdb.com/suggestion/x/{quote(query_title)}.json"
    data = fetch_json_with_retry(url)
    candidates = []
    for position, item in enumerate(data.get("d", [])):
        imdb_id = item.get("id", "")
        item_title = item.get("l", "")
        item_year = item.get("y")
        if not imdb_id.startswith("tt"):
            continue
        if not isinstance(item_year, int) or abs(item_year - year) > 1:
            continue
        sim = similarity(query_title, item_title)
        # 0.78 accepts Splendour/Splendor and Autumn/Fall style variants while
        # year proximity plus IMDb search relevance protects against collisions.
        if sim < 0.78:
            continue
        candidates.append((abs(item_year - year), -sim, position, imdb_id, item_title, item_year))
    if not candidates:
        return None
    _, _, _, imdb_id, item_title, item_year = min(candidates)
    return imdb_id, item_title, item_year


bc.imdb_lookup = imdb_lookup

if __name__ == "__main__":
    bc.main()
