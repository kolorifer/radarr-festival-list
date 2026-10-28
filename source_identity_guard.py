"""Negative corroboration from an exact listing; never selects a movie."""
import re
from torrent_research_evidence import validate, MAX_TEXT


def _duration(value):
    """Parse a single bounded MediaInfo duration, preserving seconds when given."""
    clock = re.match(r'(\d{1,2}):(\d{2}):(\d{2})(?:[.,](\d{1,3}))?(?![\d.,:])', value)
    if clock:
        hours, minutes, seconds, fraction = clock.groups()
        if int(minutes) >= 60 or int(seconds) >= 60:
            return None
        total = int(hours)*60 + int(minutes) + (int(seconds) + float('0.'+(fraction or '0')))/60
        end = clock.end()
    else:
        tokens = re.match(r'(?:\d+\s*(?:min|ms|h|s)\b\s*)+', value, re.I)
        if not tokens:
            return None
        match = re.fullmatch(r'(?:(\d{1,2})\s*h\s*)?(\d{1,4})\s*min\s*'
                             r'(?:(\d{1,2})\s*s\s*)?(?:(\d{1,3})\s*ms\s*)?', tokens[0], re.I)
        if not match:
            return None
        hours, minutes, seconds, milliseconds = match.groups()
        if ((hours and int(minutes) >= 60) or int(seconds or 0) >= 60
                or (milliseconds is not None and seconds is None)):
            return None
        total = int(hours or 0)*60 + int(minutes) + int(seconds or 0)/60 + int(milliseconds or 0)/60000
        end = tokens.end()
    # Multiple durations in one field are not a single-file runtime.
    if re.match(r'\s*(?:/|or|and|,)\s*\d', value[end:], re.I):
        return None
    return total if 0 < total <= 1440 else None


def nfo_runtime(listing):
    """Read one general runtime, excluding video/audio tracks and commentary.

    The tracker adapter has already verified the exact release heading. Only
    recognised General sections are used; absent/ambiguous text adds no evidence.
    """
    try:
        text = validate(listing['torrent_evidence'])['nfo']['text']
    except (KeyError, TypeError, ValueError):
        return None
    if not text or len(text) >= MAX_TEXT:
        return None
    sections = re.split(r'(?:---(?:VIDEO|AUDIO|TEXT)-+|\b(?:Video|Audio|Text)'
                        r'(?:\s*#\d+\s*:|(?: #\d+)? ID\s*:))', text, maxsplit=1, flags=re.I)
    if len(sections) != 2:
        return None
    general = re.split(r'\bGENERAL\b', sections[0], flags=re.I)
    if len(general) != 2:
        return None
    fields = list(re.finditer(r'\b(?:RUNTIME|Duration|Length)\s*[.]*\s*:\s*', general[1], re.I))
    if len(fields) != 1:
        return None
    field = fields[0]
    value = general[1][field.end():]
    if field[0].lower().startswith('length'):
        value = re.sub(r'^\d+(?:[.,]\d+)?\s*[KMGT]?i?B\s+for\s+', '', value, count=1, flags=re.I)
    return _duration(value)


def runtime_conflict(listing, meta):
    duration = nfo_runtime(listing or {})
    runtime = (meta or {}).get('runtime')
    if duration is None or type(runtime) is not int or runtime <= 0:
        return False
    # Preserve minute-precision allowance. The owner-approved wider allowance
    # applies ONLY after the exact listing's IMDb, unique round-trip mapping and
    # title/year checks have succeeded. It never identifies a movie or a cut.
    tolerance = 1
    from tmdb_resolver import valid_imdb_id, valid_tmdb_id
    if (listing.get('source') == 'torrentleech_listing'
            and listing.get('reason') == 'listing_id_found'
            and meta.get('identity_status') == 'verified_tmdb'
            and meta.get('identity_reason') == 'external_id_verified'
            and valid_imdb_id(meta.get('imdb_id'))
            and meta['imdb_id'] == listing.get('imdb_id')
            and valid_tmdb_id(meta.get('tmdb_id'))
            and re.fullmatch(r'[0-9]{4}', str(meta.get('matched_release_year')))):
        tolerance = max(1, min(5, runtime * 0.05))
    return abs(duration-runtime) > tolerance


def current(action, lookup, resolve):
    """Recheck source-owned identities before an acquisition can begin."""
    movie = action.get('movie') or {}
    if movie.get('identity_source') != 'torrentleech_listing':
        return True
    try:
        release = action['release']
        listing = lookup(release, action['indexer'], force_refresh=True)
        if listing.get('reason') != 'listing_id_found' or listing.get('imdb_id') != movie.get('imdb_id'):
            return False
        meta = resolve(release['title'], release['year'], imdb_id=movie['imdb_id'],
                       tmdb_id=movie['tmdb_id'], force_refresh=True,
                       allow_minor_typo=movie.get('identity_title_basis') == 'tracker_minor_typo')
        return (meta.get('identity_status') == 'verified_tmdb'
                and all(meta.get(k) == movie.get(k) for k in ('imdb_id','tmdb_id'))
                and not runtime_conflict(listing, meta))
    except Exception:
        return False
