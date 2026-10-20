"""Explicitly approved reviewed context repairs, bound to private exact provenance.

This is not a general override/crosswalk registry. The fixed title/year changes are
fixed here; owner-only configuration supplies their reviewed IDs and fingerprints.
Returned context must still pass the normal unique external-ID roundtrip checks.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from tmdb_resolver import valid_imdb_id, valid_tmdb_id
from tracker_metadata import valid_listing_url

ENV_NAME = 'MOVIE_INTEL_REVIEWED_CONTEXT_FILE'
# Only these exact observed contexts are approved; punctuation/case variants do
# not expand this exception. IDs and release references remain private.
RULES = {
    'bruce-almiighty-2003': ('Bruce Almiighty', '2003', 'Bruce Almighty', 2003),
    'hamnet-2025': ('Hamnet 2025', '2016', 'Hamnet', 2025),
    'not-not-jazz-2024': ('Medeski Martin Wood Not Not Jazz', '2024', 'Not Not Jazz', 2024),
}


def read_rules(path):
    """Re-read for immediate revocation; never log file contents or exceptions."""
    if not path or not Path(path).is_absolute():
        raise ValueError('invalid reviewed context file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 16384):
            raise ValueError('invalid reviewed context file')
        data = json.loads(stream.read(16385))
    if (not isinstance(data, dict) or set(data) != {'version', 'rules'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['rules'], list) or len(data['rules']) > len(RULES)):
        raise ValueError('invalid reviewed context schema')
    seen = set()
    for row in data['rules']:
        if (not isinstance(row, dict)
                or set(row) != {'rule', 'imdb_id', 'tmdb_id', 'source_sha256', 'evidence_sha256'}
                or not isinstance(row['rule'], str) or row['rule'] not in RULES
                or row['rule'] in seen or not valid_imdb_id(row['imdb_id'])
                or type(row['tmdb_id']) is not int or not valid_tmdb_id(row['tmdb_id'])
                or any(not isinstance(row[key], str) or not re.fullmatch('[0-9a-f]{64}', row[key])
                       for key in ('source_sha256', 'evidence_sha256'))):
            raise ValueError('invalid reviewed context rule')
        seen.add(row['rule'])
    return data['rules']


def source_fingerprint(release, imdb_id):
    """Exact provenance, deliberately excluding mutable acquisition credentials."""
    values = ['torrentleech', release['info_url'], release['name'],
              release['title'], str(release['year']), imdb_id]
    return hashlib.sha256(json.dumps(values, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


def reviewed_context(release, indexer, imdb_id, source):
    """Return context only for a successfully checked exact TorrentLeech listing."""
    if source != 'torrentleech_listing' or not valid_imdb_id(imdb_id):
        return None
    names = [indexer[key] for key in ('identifier', 'name') if indexer.get(key)]
    if not names or any(not isinstance(name, str) or name.casefold() != 'torrentleech' for name in names):
        return None
    if (not valid_listing_url(release.get('info_url'))
            or not isinstance(release.get('name'), str) or not 0 < len(release['name']) <= 4096
            or type(release.get('year')) not in (int, str)):
        return None
    possible = [key for key, rule in RULES.items()
                if (release.get('title'), str(release.get('year'))) == rule[:2]]
    if not possible or not os.environ.get(ENV_NAME):
        return None
    try:
        rows = read_rules(os.environ[ENV_NAME])
    except (OSError, ValueError, TypeError, UnicodeError):
        return None
    fingerprint = source_fingerprint(release, imdb_id)
    for row in rows:
        if (row['rule'] in possible and row['imdb_id'] == imdb_id
                and row['source_sha256'] == fingerprint):
            _, _, title, year = RULES[row['rule']]
            return {'title': title, 'year': year, 'tmdb_id': row['tmdb_id'], 'rule': row['rule']}
    return None
