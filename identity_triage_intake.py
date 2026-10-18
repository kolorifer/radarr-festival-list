"""Strict, capability-free metadata normalization for autobrr v1.88 webhooks."""
from datetime import datetime
import json
import re
import unicodedata
import uuid
from identity_triage_store import digest

MAX_BODY = 65536
OUTCOME_STATUSES = {'imdb_associated', 'verified_tmdb', 'unresolved', 'needs_review', 'legacy_resolved', 'skipped_routine'}
CATEGORIES = {'unknown_movie', 'quality', 'existing', 'not_upgrade', 'other'}
# Fixed codes only. Unknown future resolver reasons collapse to 'other'.
REASONS = {'tmdb_mapping_missing', 'metadata_api_unavailable', 'invalid_metadata', 'non_movie_identity', 'ambiguous_id_mapping', 'identity_conflict', 'invalid_movie_identity', 'metadata_lookup_busy', 'external_id_verified', 'other', 'resolved', 'skipped_routine', 'unmapped_external_id', 'external_id_conflict',
           'local_identity_conflict', 'invalid_external_id', 'title_conflict', 'year_conflict',
           'resolver_error', 'missing', 'ambiguous', 'disabled', 'unavailable', 'verified'}
CONTRADICTIONS = {'missing_crosswalk', 'year_conflict', 'title_conflict', 'runtime_conflict',
                  'director_conflict', 'insufficient_evidence'}


class Reject(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def decode(raw):
    if len(raw) > MAX_BODY:
        raise Reject('oversize')
    try:
        obj = json.loads(raw, object_pairs_hook=unique_object,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError('constant')))
        if not isinstance(obj, dict):
            raise ValueError('object')
        return obj
    except (ValueError, RecursionError, UnicodeError):
        raise Reject('invalid_json') from None


def safe_text(value, limit):
    if not isinstance(value, str) or not 0 < len(value) <= limit:
        raise ValueError('text')
    # Only movie-title/release-name text. URLs, markup, controls, credential syntax
    # and capability-like long opaque strings are not retained even in titles.
    if (any(unicodedata.category(c).startswith('C') for c in value)
            or re.search(r'[<>\\?=@]|[a-z][a-z0-9+.-]*://|magnet:|www\.|\b(?:passkey|token|password|authorization)\s*[:=]|\bBearer\s+\S+|[a-zA-Z0-9_-]{48,}', value, re.I)):
        raise ValueError('unsafe_text')
    if not value.strip():
        raise ValueError('text')
    return value.strip()


def timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('timestamp')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None or not 2000 <= dt.year <= 2100:
        raise ValueError('timestamp')
    return dt.timestamp()


def normalize(payload, sources, channel='release_new'):
    event = 'identity.outcome' if channel == 'outcome' else 'release.new'
    if payload.get('event') != event or payload.get('version') != '1.0':
        raise Reject('unsupported_event')
    data = payload.get('data')
    if not isinstance(data, dict):
        raise Reject('schema')
    release, indexer = data.get('release'), data.get('indexer')
    if not isinstance(release, dict) or not isinstance(indexer, dict):
        raise Reject('schema')
    source = indexer.get('identifier')
    if not isinstance(source, str) or source not in sources or indexer.get('name') != sources[source]:
        raise Reject('source')
    malformed_type = release.get('type') != 'movie'
    if malformed_type and (release.get('type') in ('episode', 'series', 'music', 'book', 'game', 'app')
                           or not ('year' in release and 'title' in release)):
        raise Reject('non_movie')
    # From here, malformed movie-like records are durable quarantine, with no raw text.
    record = {'event_id': '', 'time': None}
    if malformed_type:
        record['reason'] = 'invalid_movie_type'
    try:
        record['event_id'] = str(uuid.UUID(payload.get('id', '')))
    except (ValueError, AttributeError, TypeError):
        record['reason'] = 'invalid_event_id'
    try:
        record['time'] = timestamp(payload.get('timestamp'))
    except (ValueError, TypeError, OverflowError):
        record['reason'] = record.get('reason', 'invalid_timestamp')
    try:
        if release.get('protocol') != 'torrent' or release.get('implementation') not in ('IRC', 'RSS'):
            raise ValueError('source_protocol')
        title = safe_text(release.get('title'), 250)
        name = safe_text(release.get('name'), 512)
        year = release.get('year')
        if type(year) != int or not 1888 <= year <= 2100:
            raise ValueError('year')
        imdb = release.get('meta_imdb')
        imdb = None if imdb in (None, '') else imdb
        tmdb = release.get('meta_tmdb')
        # Zero TMDb is omitted by upstream; explicitly supplied invalid values quarantine.
        if imdb is not None and (not isinstance(imdb, str) or not re.fullmatch(r'tt[0-9]{7,10}', imdb)):
            raise ValueError('film_id')
        if tmdb is not None and (type(tmdb) != int or not 0 < tmdb < 2**31):
            raise ValueError('film_id')
        external = release.get('external_id')
        if external not in (None, '') and (not isinstance(external, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', external)):
            raise ValueError('release_id')
        # No URLs are used or retained. Source's stable torrent ID is hashed; name
        # fallback has explicitly weaker identity and never proves a movie match.
        record['release'] = digest([source, 'torrent', ['external', external] if external else ['name', name]])
        record['metadata'] = {'source': source, 'title': title,
                              'title_key': ''.join(c for c in unicodedata.normalize('NFKC', title).casefold() if c.isalnum()),
                              'year': year, 'name': name, 'imdb': imdb, 'tmdb': tmdb,
                              'release_key_basis': 'external_id' if external else 'name_fallback'}
        if not record['metadata']['title_key']:
            raise ValueError('title')
        if channel == 'outcome':
            o = data.get('outcome')
            if (not isinstance(o, dict) or set(o) != {'category', 'status', 'reason'}
                    or o['category'] not in CATEGORIES or o['status'] not in OUTCOME_STATUSES or o['reason'] not in REASONS):
                raise ValueError('outcome')
            record['outcome'] = dict(o)
        if channel == 'seed':
            s = data.get('seed')
            if (not isinstance(s, dict) or set(s) != {'provenance', 'contradictions'}
                    or not isinstance(s['provenance'], str) or not re.fullmatch('[a-f0-9]{64}', s['provenance'])
                    or not isinstance(s['contradictions'], list) or not 1 <= len(s['contradictions']) <= 6
                    or any(not isinstance(x, str) or x not in CONTRADICTIONS for x in s['contradictions'])):
                raise ValueError('seed')
            record['seed'] = dict(s)
    except (ValueError, TypeError):
        record['reason'] = record.get('reason', 'invalid_movie_metadata')
    if record.get('reason'):
        # No partially parsed title, ID or any raw input is retained in quarantine.
        record = {k: record[k] for k in ('event_id', 'time', 'reason')}
    if not record['event_id']:
        # A fresh opaque ID preserves malformed deliveries without hashing secrets.
        record['event_id'] = str(uuid.uuid4())
    return record
