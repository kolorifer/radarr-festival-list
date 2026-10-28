"""Negative corroboration from an exact listing; never selects a movie."""
import re
from torrent_research_evidence import validate, MAX_TEXT


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
    sections = re.split(r'(?:---VIDEO-+|\bVideo(?: #\d+)? ID\s*:)', text, maxsplit=1, flags=re.I)
    if len(sections) != 2 or not re.search(r'\bGENERAL\b', sections[0], re.I):
        return None
    values = re.findall(r'\b(?:RUNTIME|Duration)\s*[.]*\s*:\s*(?:(\d{1,2})\s*h\s*)?(\d{1,3})\s*min\b', sections[0], re.I)
    if len(values) != 1:
        return None
    hours, minutes = values[0]
    if hours and int(minutes) >= 60:
        return None
    duration = int(hours or 0)*60 + int(minutes)
    return duration if 0 < duration <= 1440 else None


def runtime_conflict(listing, meta):
    duration = nfo_runtime(listing or {})
    runtime = (meta or {}).get('runtime')
    # Both sources expose whole minutes. Adjacent minute values cannot establish
    # a contradiction because one source may truncate and the other round up.
    # This is a veto only: agreement never establishes or changes an identity.
    return (duration is not None and type(runtime) is int and runtime > 0
            and abs(duration-runtime) > 1)


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
