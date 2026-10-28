"""Conservative TMDb resolver used for poster/link enrichment.

The resolver never guesses between ambiguous title/year matches. Successful
lookups are cached locally so notification traffic does not repeatedly hit TMDb.
"""
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TOKEN = os.environ.get("TMDB_API_TOKEN", "").strip()
CACHE_PATH = Path(os.environ.get("TMDB_CACHE_PATH", ROOT / "tmdb-cache.json"))


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _year(value):
    text = str(value or "")
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else None


def _load_cache():
    try:
        data = json.loads(CACHE_PATH.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache):
    try:
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True))
    except OSError:
        pass


def _get(path, params=None):
    if not TOKEN:
        return None
    url = API_BASE + path
    if params:
        url += "?" + urlencode(params)
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json",
            "User-Agent": "movie-intel/1.0",
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _compact(details):
    if not isinstance(details, dict) or not details.get("id"):
        return None
    ext = details.get("external_ids") or {}
    poster_path = details.get("poster_path")
    release_date = details.get("release_date")
    genres = [x.get("name") for x in (details.get("genres") or []) if x.get("name")]
    return {
        "tmdb_id": details.get("id"),
        "imdb_id": ext.get("imdb_id"),
        "title": details.get("title") or details.get("original_title"),
        "original_title": details.get("original_title"),
        "year": _year(release_date),
        "release_date": release_date,
        "poster_url": IMAGE_BASE + poster_path if poster_path else None,
        "tmdb_url": f"https://www.themoviedb.org/movie/{details.get('id')}",
        "imdb_url": f"https://www.imdb.com/title/{ext.get('imdb_id')}/" if ext.get("imdb_id") else None,
        "tmdb_rating": details.get("vote_average"),
        "tmdb_votes": details.get("vote_count"),
        "genres": genres,
        "runtime": details.get("runtime"),
    }


def _details(tmdb_id):
    payload = _get(f"/movie/{int(tmdb_id)}", {"append_to_response": "external_ids", "language": "en-US"})
    return _compact(payload)


def _search_exact(title, year):
    payload = _get(
        "/search/movie",
        {
            "query": title,
            "year": year or "",
            "include_adult": "false",
            "language": "en-US",
            "page": 1,
        },
    )
    results = (payload or {}).get("results") or []
    key = _norm(title)
    wanted_year = str(year) if year else None
    matches = []
    for row in results:
        row_year = _year(row.get("release_date"))
        title_match = key in {_norm(row.get("title")), _norm(row.get("original_title"))}
        year_match = not wanted_year or row_year == wanted_year
        if title_match and year_match:
            matches.append(row)
    if len(matches) != 1:
        return None
    return _details(matches[0]["id"])


def _find_by_imdb(imdb_id):
    if not imdb_id:
        return None
    payload = _get(f"/find/{quote(str(imdb_id))}", {"external_source": "imdb_id", "language": "en-US"})
    rows = (payload or {}).get("movie_results") or []
    if len(rows) != 1:
        return None
    return _details(rows[0]["id"])


def resolve_movie(title, year=None, imdb_id=None):
    """Resolve a movie without guessing.

    IMDb ID is preferred when already known. Otherwise TMDb text search is only
    accepted when exactly one result matches normalized title/original title and
    year. Successful results are cached by both title/year and IMDb ID.
    """
    cache = _load_cache()
    title_key = f"title:{_norm(title)}:{year or ''}"
    imdb_key = f"imdb:{imdb_id}" if imdb_id else None

    if imdb_key and imdb_key in cache:
        return cache[imdb_key]
    if title_key in cache:
        return cache[title_key]
    if not TOKEN:
        return None

    resolved = _find_by_imdb(imdb_id) if imdb_id else None
    if not resolved:
        resolved = _search_exact(title, year)
    if not resolved:
        return None

    cache[title_key] = resolved
    if resolved.get("imdb_id"):
        cache[f"imdb:{resolved['imdb_id']}"] = resolved
    _save_cache(cache)
    return resolved
