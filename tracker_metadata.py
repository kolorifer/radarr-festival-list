"""Opt-in TorrentLeech listing metadata. Never request torrent/download URLs.

Only the listing's structural release heading and IMDb field are consumed.
Private URLs and credentials never appear in returned results or diagnostics.
"""
import hashlib
import json
import os
import re
import stat
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

from tmdb_resolver import valid_imdb_id
from identity_request_guard import reserve, cooldown

MAX_BODY = 1_000_000
_LOCK = threading.Lock()
_CACHE = OrderedDict()
_NEXT_REQUEST = 0.0


def _result(reason, imdb_id=None):
    result = {'source': 'torrentleech_listing', 'reason': reason}
    if imdb_id:
        result['imdb_id'] = imdb_id
    return result


def cookie_file(path):
    """Validate a dedicated owner-only JSON cookie map, with no symlink reads."""
    if not path or not Path(path).is_absolute():
        raise ValueError('invalid cookie file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 16384):
            raise ValueError('invalid cookie file')
        cookies = json.loads(stream.read(16385))
    if not isinstance(cookies, dict) or not cookies:
        raise ValueError('invalid cookie map')
    for name, value in cookies.items():
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', name)
                or not isinstance(value, str) or not value or len(value) > 8192
                or any(ord(c) < 33 or ord(c) > 126 or c in ';,' for c in value)):
            raise ValueError('invalid cookie map')
    return cookies


def valid_listing_url(value):
    if not isinstance(value, str) or len(value) > 200:
        return False
    # Canonical byte-level allowlist also rejects ports, escapes, userinfo,
    # whitespace, fragments, alternate hosts and ambiguous URL normalization.
    return re.fullmatch(r'https://www\.torrentleech\.org/torrent/[1-9][0-9]{0,19}', value) is not None


def parse_listing(body, release_name):
    soup = BeautifulSoup(body, 'html.parser')
    if any(str(tag.get('type', '')).casefold() == 'password' for tag in soup.find_all('input')):
        return _result('login_required')
    headings = soup.select('#torrentnameid, #torrentName')
    # TL appends this separate presentation badge to its h2, while h4 keeps
    # the exact release name. Ignore only the observed badge element/text;
    # never strip words from a release name or accept a mismatching heading.
    for heading in headings:
        for badge in heading.select('span.new.label.labelfreeleech'):
            if badge.get_text(' ', strip=True) == 'FREELEECH':
                badge.decompose()
    names = [node.get('value') if node.name == 'input' else node.get_text(' ', strip=True)
             for node in headings]
    normalize = lambda value: ' '.join(str(value or '').split())
    if not names or any(normalize(name) != normalize(release_name) for name in names):
        return _result('listing_mismatch')
    fields = soup.select('input[name="imdbID"]')
    ids = set(re.findall(r'\btt[0-9]{7,12}\b', str(soup)))
    if (not fields or (len(fields)==1 and fields[0].get('value') in (None,''))) and not ids:
        return _result('listing_id_missing')
    if len(fields) != 1 or not valid_imdb_id(fields[0].get('value')):
        return _result('listing_id_invalid')
    imdb_id = fields[0]['value']
    # Conflicting IMDb links elsewhere in the listing are not silently ignored.
    ids = set(re.findall(r'\btt[0-9]{7,12}\b', str(soup)))
    if ids != {imdb_id}:
        return _result('listing_id_conflict')
    return _result('listing_id_found', imdb_id)


def _backoff(value):
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            seconds = 60
    # Longer server-directed pauses remain honored; malformed values use 60s.
    return max(60, seconds)


def _fetch(url, name, cookies):
    global _NEXT_REQUEST
    with requests.Session() as session:
        session.trust_env = False
        for key, value in cookies.items():
            session.cookies.set(key, value, domain=urlsplit(url).hostname, path='/')
        reserve('listing')
        with session.get(url, allow_redirects=False, timeout=(3, 5), stream=True,
                         headers={'Accept': 'text/html', 'User-Agent': 'movie-intel/1.0'}) as response:
            if response.status_code == 429:
                pause = _backoff(response.headers.get('Retry-After'))
                _NEXT_REQUEST = time.monotonic() + pause
                cooldown('listing', pause)
                return _result('rate_limited')
            if response.status_code in (401,403):
                cooldown('listing',auth=True)
                return _result('listing_auth_failure')
            if response.status_code==404:return _result('listing_not_found')
            if 300<=response.status_code<400:return _result('listing_redirect')
            if response.status_code>=500:return _result('listing_temporary_http')
            if response.status_code != 200:return _result('listing_http_error')
            if 'text/html' not in response.headers.get('Content-Type', '').lower():
                return _result('listing_content_invalid')
            body = bytearray()
            deadline = time.monotonic() + 10
            # Small chunks bound slow trickling between read timeouts.
            for chunk in response.iter_content(chunk_size=1):
                body.extend(chunk)
                if len(body) > MAX_BODY or time.monotonic() > deadline:
                    return _result('listing_limit_exceeded')
            return parse_listing(bytes(body), name)


def lookup_listing(release, indexer):
    """At most one active fetch, bounded TTL cache and a global request interval.

    Every enabled failure is returned explicitly so the caller cannot bypass
    unavailable or contradictory listing evidence with a title-only guess.
    """
    global _NEXT_REQUEST
    if os.environ.get('MOVIE_INTEL_TL_METADATA_ENABLED', '0') != '1':
        return _result('disabled')
    if str(indexer.get('identifier') or indexer.get('name') or '').casefold() != 'torrentleech':
        return _result('unsupported_indexer')
    url, name = release.get('info_url'), release.get('name')
    if not valid_listing_url(url) or not isinstance(name, str) or not name.strip() or len(name) > 4096:
        return _result('listing_reference_invalid')
    if not _LOCK.acquire(blocking=False):
        return _result('lookup_busy')
    try:
        try:
            cookies = cookie_file(os.environ.get('MOVIE_INTEL_TL_COOKIE_FILE'))
        except (OSError, ValueError, TypeError):
            return _result('authentication_unavailable')
        # Cookie rotation invalidates negative cache/session errors immediately.
        key = hashlib.sha256(json.dumps([url, name, cookies], sort_keys=True).encode()).digest()
        now = time.monotonic()
        cached = _CACHE.get(key)
        if cached and cached[0] > now:
            return dict(cached[1])
        if now < _NEXT_REQUEST:
            return _result('rate_limited')
        _NEXT_REQUEST = now + 1
        try:
            result = _fetch(url, name, cookies)
        except (requests.RequestException, ValueError, TypeError):
            result = _result('listing_unavailable')
        ttl = 900 if result.get('imdb_id') else 60
        _CACHE[key] = (time.monotonic() + ttl, dict(result))
        _CACHE.move_to_end(key)
        while len(_CACHE) > 256:
            _CACHE.popitem(last=False)
        return result
    finally:
        _LOCK.release()
