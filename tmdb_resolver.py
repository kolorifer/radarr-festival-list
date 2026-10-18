"""Conservative TMDb resolver used for poster/link enrichment.

The resolver never guesses between ambiguous title/year matches. Successful
lookups are cached locally so notification traffic does not repeatedly hit TMDb.
"""
import json
import math
import os
import re
from contextvars import ContextVar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TOKEN = os.environ.get("TMDB_API_TOKEN", "").strip()
CACHE_PATH = Path(os.environ.get("TMDB_CACHE_PATH", ROOT / "tmdb-cache.json"))

# Duplicate exact title+year matches need an order-of-magnitude lead AND a
# substantial absolute gap. Popularity alone is not an identity match.
_DUPLICATE_POPULARITY_MIN_RATIO = 10.0
_DUPLICATE_POPULARITY_MIN_GAP = 10.0
_REASON = ContextVar('resolution_reason', default='unresolved')


def resolution_reason():
    return _REASON.get()


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
        _REASON.set('resolver_unconfigured')
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
        _REASON.set('metadata_api_unavailable')
        return None


def _compact(details):
    if not isinstance(details, dict) or not details.get("id"):
        return None
    ext = details.get("external_ids") or {}
    if not isinstance(ext, dict):
        ext = {}
    poster_path = details.get("poster_path")
    release_date = details.get("release_date")
    genres = [x.get("name") for x in (details.get("genres") or [])
              if isinstance(x, dict) and isinstance(x.get("name"), str)]
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
    if payload is None:
        return None
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
    if not matches:
        _REASON.set('no_exact_match')
        return None
    if len(matches) > 1:
        _REASON.set('ambiguous_exact_matches')
        # Do not extend the duplicate exception to searches without a year.
        if not wanted_year:
            return None
        for row in matches:
            popularity = row.get("popularity")
            # Missing/invalid data on ANY exact candidate leaves ambiguity.
            if (type(popularity) not in (int, float)
                    or not math.isfinite(popularity) or popularity < 0):
                return None
        matches.sort(key=lambda row: row["popularity"], reverse=True)
        top, runner_up = matches[0]["popularity"], matches[1]["popularity"]
        # Inclusive thresholds; comparison with the runner-up covers all others.
        # A known zero is allowed, but the absolute gap still must be >= 10.
        if (top < _DUPLICATE_POPULARITY_MIN_RATIO * runner_up
                or top - runner_up < _DUPLICATE_POPULARITY_MIN_GAP):
            return None
    _REASON.set('details_unavailable')
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
    accepted for a unique normalized title/original-title and year match, or an
    exact title+year duplicate with >= 10x popularity AND >= 10 points of lead
    over the runner-up (all exact candidates need valid popularity). Successful
    results are cached by both title/year and IMDb ID.
    """
    _REASON.set('unresolved')
    cache = _load_cache()
    title_key = f"title:{_norm(title)}:{year or ''}"
    imdb_key = f"imdb:{imdb_id}" if imdb_id else None

    if imdb_key and imdb_key in cache:
        return cache[imdb_key]
    if title_key in cache:
        cached = cache[title_key]
        if not imdb_id or cached.get('imdb_id') == imdb_id:
            return cached
    if not TOKEN:
        _REASON.set('resolver_unconfigured')
        return None

    resolved = _find_by_imdb(imdb_id) if imdb_id else None
    if not resolved:
        resolved = _search_exact(title, year)
    if not resolved:
        return None
    if imdb_id and resolved.get('imdb_id') != imdb_id:
        _REASON.set('identity_conflict')
        return None

    cache[title_key] = resolved
    if resolved.get("imdb_id"):
        cache[f"imdb:{resolved['imdb_id']}"] = resolved
    _save_cache(cache)
    return resolved
