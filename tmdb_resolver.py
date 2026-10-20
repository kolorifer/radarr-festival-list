"""Conservative TMDb resolver used for poster/link enrichment.

The resolver never guesses between ambiguous title/year matches. Successful
lookups are cached locally so notification traffic does not repeatedly hit TMDb.
"""
import json
import math
import os
import re
import threading
import time
import unicodedata
from collections import OrderedDict
from contextvars import ContextVar
from pathlib import Path
from identity_request_guard import reserve, cooldown
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

class _NoMetadataRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

urlopen = build_opener(_NoMetadataRedirect).open

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
_ID_CACHE = OrderedDict()
_ID_LOCK = threading.Lock()


def valid_imdb_id(value):
    return isinstance(value, str) and re.fullmatch(r'tt[0-9]{7,12}', value) is not None


def valid_tmdb_id(value):
    return (type(value) in (str, int)
            and re.fullmatch(r'[1-9][0-9]{0,9}', str(value)) is not None)


def _identity_title(value):
    # Context check ONLY after an exact ID lookup; never broaden text search.
    text = unicodedata.normalize('NFC', str(value or '')).casefold().replace('&', 'and')
    return ''.join(c for c in text if c.isalnum())


def _minor_title_typo(observed, candidate):
    """One alphabetic edit in one long word; never remove words or numbers."""
    def words(value):
        text = unicodedata.normalize('NFC', str(value or '')).casefold().replace('&', 'and')
        return re.findall(r"[^\W_]+", text)
    left, right = words(observed), words(candidate)
    if len(left) != len(right) or sum(map(len, right)) < 8:
        return False
    differences = [(a, b) for a, b in zip(left, right) if a != b]
    if len(differences) != 1:
        return False
    a, b = differences[0]
    if (min(len(a), len(b)) < 6 or not a.isalpha() or not b.isalpha()
            or re.fullmatch('[ivxlcdm]+', a) or re.fullmatch('[ivxlcdm]+', b)):
        return False
    if len(a) == len(b):
        changed = [i for i in range(len(a)) if a[i] != b[i]]
        return (len(changed) == 1 or
                (len(changed) == 2 and changed[1] == changed[0] + 1
                 and a[changed[0]] == b[changed[1]] and a[changed[1]] == b[changed[0]]))
    if abs(len(a) - len(b)) != 1:
        return False
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    i = next((i for i in range(len(shorter)) if longer[i] != shorter[i]), len(shorter))
    return longer[:i] + longer[i + 1:] == shorter


def _identity_result(status, reason, imdb_id=None):
    result = {'identity_status': status, 'identity_reason': reason}
    if valid_imdb_id(imdb_id):
        result['imdb_id'] = imdb_id
    return result


def _resolve_external(title, year, imdb_id, tmdb_id, allow_minor_typo=False):
    """No title-search fallback, even on missing mapping or provider failure."""
    if imdb_id:
        payload = _get(f'/find/{imdb_id}', {'external_source': 'imdb_id', 'language': 'en-US'})
        if not isinstance(payload, dict):
            return _identity_result('unresolved', _REASON.get() if _REASON.get() in {'metadata_auth_failure','metadata_rate_limited','metadata_record_missing','metadata_redirect'} else 'metadata_api_unavailable', imdb_id)
        rows = payload.get('movie_results')
        if not isinstance(rows, list):
            return _identity_result('needs_review', 'invalid_metadata', imdb_id)
        if payload.get('tv_results') or payload.get('tv_episode_results') or payload.get('person_results'):
            return _identity_result('needs_review', 'non_movie_identity', imdb_id)
        if not rows:
            return _identity_result('imdb_associated', 'tmdb_mapping_missing', imdb_id)
        if len(rows) != 1 or not isinstance(rows[0], dict) or not valid_tmdb_id(rows[0].get('id')):
            return _identity_result('needs_review', 'ambiguous_id_mapping', imdb_id)
        found_id = int(rows[0]['id'])
        if tmdb_id and found_id != int(tmdb_id):
            return _identity_result('needs_review', 'identity_conflict', imdb_id)
        tmdb_id = found_id
    details = _get(f'/movie/{int(tmdb_id)}', {
        'append_to_response': 'external_ids,alternative_titles,translations,release_dates',
        'language': 'en-US',
    })
    if not isinstance(details, dict):
        return _identity_result('unresolved', _REASON.get() if _REASON.get() in {'metadata_auth_failure','metadata_rate_limited','metadata_record_missing','metadata_redirect'} else 'metadata_api_unavailable', imdb_id)
    if type(details.get('id')) is not int or details['id'] != int(tmdb_id) or not details.get('title'):
        return _identity_result('needs_review', 'invalid_movie_identity', imdb_id)
    ext = details.get('external_ids')
    canonical_imdb = ext.get('imdb_id') if isinstance(ext, dict) else None
    if ((imdb_id and canonical_imdb != imdb_id)
            or (canonical_imdb is not None and not valid_imdb_id(canonical_imdb))):
        return _identity_result('needs_review', 'identity_conflict', imdb_id)

    titles = [details.get('title'), details.get('original_title')]
    alternatives = details.get('alternative_titles') or {}
    translations = details.get('translations') or {}
    dates = details.get('release_dates') or {}
    if not all(isinstance(x, dict) for x in (alternatives, translations, dates)):
        return _identity_result('needs_review', 'invalid_metadata', imdb_id)
    titles.extend(row.get('title') for row in alternatives.get('titles', []) if isinstance(row, dict))
    for row in translations.get('translations', []):
        if isinstance(row, dict) and isinstance(row.get('data'), dict):
            titles.append(row['data'].get('title'))
    wanted_title = _identity_title(title)
    exact_title = bool(wanted_title) and wanted_title in {_identity_title(x) for x in titles if x}
    typo = (not exact_title and allow_minor_typo is True and valid_imdb_id(imdb_id)
            and any(_minor_title_typo(title, x) for x in titles if x))
    if not exact_title and not typo:
        return _identity_result('needs_review', 'title_conflict', imdb_id)
    years = {_year(details.get('release_date'))}
    for country in dates.get('results', []):
        if isinstance(country, dict):
            years.update(_year(row.get('release_date')) for row in country.get('release_dates', [])
                         if isinstance(row, dict))
    if not re.fullmatch(r'[0-9]{4}', str(year)) or str(year) not in years:
        return _identity_result('needs_review', 'year_conflict', imdb_id)
    result = _compact(details)
    result.update(identity_status='verified_tmdb', identity_reason='external_id_verified')
    if typo:
        result['identity_title_basis'] = 'tracker_minor_typo'
    result['matched_release_year'] = str(year)
    result['identity_year_basis'] = 'canonical_date' if str(year) == result['year'] else 'release_dates'
    return result


def resolve_external_movie(title, year, *, imdb_id=None, tmdb_id=None, allow_minor_typo=False):
    """Validate source IDs and context in an isolated, bounded, expiring cache.

    Never read/write the legacy title cache. The key includes the exact context
    and both supplied IDs, so a cached ID cannot bypass a new conflict.
    """
    if ((imdb_id is not None and not valid_imdb_id(imdb_id))
            or (tmdb_id is not None and not valid_tmdb_id(tmdb_id))
            or (imdb_id is None and tmdb_id is None)):
        return _identity_result('needs_review', 'invalid_external_id')
    key = (str(title), str(year), imdb_id, str(tmdb_id), allow_minor_typo is True)
    if not _ID_LOCK.acquire(blocking=False):
        return _identity_result('unresolved', 'metadata_lookup_busy', imdb_id)
    try:
        cached = _ID_CACHE.get(key)
        if cached and cached[0] > time.monotonic():
            return dict(cached[1])
        try:
            result = _resolve_external(title, year, imdb_id, tmdb_id, allow_minor_typo)
        except (TypeError, ValueError, KeyError, AttributeError):
            result = _identity_result('needs_review', 'invalid_metadata', imdb_id)
        ttl = 900 if result['identity_status'] == 'verified_tmdb' else 60
        _ID_CACHE[key] = (time.monotonic() + ttl, dict(result))
        _ID_CACHE.move_to_end(key)
        while len(_ID_CACHE) > 256:
            _ID_CACHE.popitem(last=False)
        return result
    finally:
        _ID_LOCK.release()


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
    _REASON.set('unresolved')
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
        reserve('tmdb')
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        if exc.code in (401,403):
            _REASON.set('metadata_auth_failure');cooldown('tmdb',auth=True)
        elif exc.code==429:
            from email.utils import parsedate_to_datetime
            value=exc.headers.get('Retry-After','60') if exc.headers else '60'
            try:pause=max(60,int(value))
            except (TypeError,ValueError):
                try:pause=max(60,parsedate_to_datetime(value).timestamp()-time.time())
                except (TypeError,ValueError,OverflowError):pause=60
            cooldown('tmdb',pause);_REASON.set('metadata_rate_limited')
        elif exc.code==404:_REASON.set('metadata_record_missing')
        elif 300<=exc.code<400:_REASON.set('metadata_redirect')
        else:_REASON.set('metadata_api_unavailable')
        return None
    except (URLError, TimeoutError, json.JSONDecodeError):
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
