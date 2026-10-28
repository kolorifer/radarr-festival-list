#!/usr/bin/env python3
"""Manual research validation. Offline by default; never emits rating/count values.

MDBList has NO live adapter: its response contract and downstream rights are
unverified. Synthetic envelopes below are our proposed private observation schema,
not asserted MDBList fields. No scoring, private config discovery or persistence.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import re
import time
import zlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parent
IMDB_URL = 'https://datasets.imdbws.com/title.ratings.tsv.gz'
BASELINE = '489ce4e3e005dbb15fadebf8ac27e6c181cf3a98'
ATTRIBUTION = 'Information courtesy of IMDb (https://www.imdb.com). Used with permission.'
MAX_COMPRESSED = 64 * 1024 * 1024
MAX_DECOMPRESSED = 256 * 1024 * 1024
MAX_SECONDS = 90
EXPECTED_IDS = (
    'tt14905854', 'tt28607951', 'tt8999762', 'tt17526714',
    'tt27714581', 'tt36491653', 'tt29271639', 'tt38991615',
)


class InvalidObservation(ValueError):
    """Fixed diagnostics only: never include input values, responses or URLs."""


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def parse_time(value):
    if not isinstance(value, str):
        raise InvalidObservation('invalid_time')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise InvalidObservation('invalid_time') from None
    if parsed.tzinfo is None:
        raise InvalidObservation('invalid_time')
    return parsed.astimezone(timezone.utc)


def cohort():
    manifest = json.loads((ROOT / 'cohort.json').read_text())
    rows = manifest['films']
    if tuple(r['imdb_id'] for r in rows) != EXPECTED_IDS:
        raise InvalidObservation('cohort_mismatch')
    if len({r['tmdb_id'] for r in rows}) != len(rows):
        raise InvalidObservation('ambiguous_identity')
    return {r['imdb_id']: r for r in rows}


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise InvalidObservation('invalid_number')
    if isinstance(value, str) and not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', value):
        raise InvalidObservation('invalid_number')
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise InvalidObservation('invalid_number') from None
    if not math.isfinite(result):
        raise InvalidObservation('invalid_number')
    return result


def integer_count(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r'[0-9]+', value):
        return int(value)
    raise InvalidObservation('invalid_count')


def validate_observation(row, expected, requested_at):
    """Validate one same-response pair in OUR schema; no merging partial records.

    Returns internal private values. Callers must publish aggregate_gate only.
    Unknown count precision/meaning and source measurement time stay unknown.
    """
    if not isinstance(row, dict):
        raise InvalidObservation('invalid_record')
    if row.get('imdb_id') != expected['imdb_id']:
        raise InvalidObservation('wrong_identity')
    if type(row.get('tmdb_id')) is not int or row['tmdb_id'] != expected['tmdb_id']:
        raise InvalidObservation('wrong_identity')
    source = row.get('source')
    if source not in ('imdb', 'letterboxd'):
        raise InvalidObservation('unsupported_source')
    result = {'source': source, 'imdb_id': expected['imdb_id'],
              'requested_at': requested_at, 'measurement_at': row.get('measurement_at'),
              'rating': None, 'count': None, 'flags': []}
    request_time = parse_time(requested_at)
    measured = result['measurement_at']
    if measured is None:
        result['flags'].append('measurement_time_unknown')
    else:
        measured = parse_time(measured)
        if measured > request_time:
            raise InvalidObservation('future_measurement')
        if (request_time - measured).total_seconds() >= 30 * 86400:
            result['flags'].append('measurement_at_least_30_days_old')
    rating, count = row.get('rating'), row.get('count')
    # Null / IMDb TSV missing sentinel are missing, not numerical zeros.
    missing_rating = rating is None or rating == '\\N'
    missing_count = count is None or count == '\\N'
    if not missing_rating:
        result['rating'] = number(rating)
        low, high = (1, 10) if source == 'imdb' else (0.5, 5)
        if not low <= result['rating'] <= high:
            raise InvalidObservation('rating_out_of_range')
    if not missing_count:
        result['count'] = integer_count(count)
    if missing_rating or missing_count:
        result['flags'].append('pair_missing')
    if result['count'] == 0:
        result['flags'].append('zero_ratings')
        if not missing_rating:
            raise InvalidObservation('rating_without_votes')
    if row.get('count_semantics') != 'ratings':
        result['flags'].append('count_semantics_unverified')
    if row.get('count_precision') != 'exact_integer':
        result['flags'].append('count_precision_unverified')
    if row.get('rating_semantics') != 'source_weighted_average':
        result['flags'].append('rating_semantics_unverified')
    result['eligible_pair'] = not any(f != 'measurement_time_unknown' and
                                      f != 'measurement_at_least_30_days_old'
                                      for f in result['flags'])
    return result


def aggregate_gate(observations):
    """Allowlisted public view: no film identities, raw data or exception text."""
    return {
        'observations_checked': len(observations),
        'valid_pairs': sum(o['eligible_pair'] for o in observations),
        'missing_pairs': sum('pair_missing' in o['flags'] for o in observations),
        'unknown_measurement_times': sum('measurement_time_unknown' in o['flags']
                                         for o in observations),
        'old_measurement_times': sum('measurement_at_least_30_days_old' in o['flags']
                                     for o in observations),
        'semantics_or_precision_unverified': sum(any('unverified' in f for f in o['flags'])
                                                 for o in observations),
    }


def retry_after_seconds(value, now):
    if value is None:
        return None
    try:
        if re.fullmatch(r'[0-9]{1,8}', str(value)):
            return int(value)
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            return None
        return max(0, math.ceil((dt - parse_time(now)).total_seconds()))
    except (ValueError, TypeError, OverflowError):
        return None


class SyntheticTrial:
    """OFFLINE injected-transport rehearsal, deliberately no HTTP implementation.

    At most eight exact-ID film GETs, at most ten operations, or lower account
    allowance. Stop on any failure or 429; never sleep/retry or force refresh.
    A later authenticated adapter needs permission + a reviewed response schema.
    """
    def run(self, transport, allowance, requested_at):
        if type(allowance) is not int or allowance < 0:
            raise InvalidObservation('invalid_allowance')
        limit = min(10, allowance, len(EXPECTED_IDS))
        observations = []
        attempts = 0
        reason = 'complete' if limit == len(EXPECTED_IDS) else 'allowance_exhausted'
        retry_after = None
        remaining_budget = limit
        for expected in list(cohort().values())[:limit]:
            if remaining_budget == 0:
                reason = 'allowance_exhausted'
                break
            attempts += 1
            remaining_budget -= 1
            try:
                response = transport(expected['imdb_id'])
                status = response['status']
                headers = response.get('headers', {})
                if status != 200:
                    reason = {401: 'auth_failure', 403: 'auth_failure',
                              429: 'rate_limited'}.get(status, 'http_failure')
                    retry_after = retry_after_seconds(headers.get('Retry-After'), requested_at)
                    break
                rows = response['observations']
                if (not isinstance(rows, list) or len(rows) != 2 or
                        not all(isinstance(r, dict) for r in rows)):
                    raise InvalidObservation('ambiguous_pair')
                if {r.get('source') for r in rows} != {'imdb', 'letterboxd'}:
                    raise InvalidObservation('ambiguous_pair')
                validated = [validate_observation(r, expected, requested_at) for r in rows]
                observations.extend(validated)
                remaining = headers.get('X-RateLimit-Remaining')
                if remaining is not None:
                    remaining_budget = min(remaining_budget, integer_count(remaining))
                    if remaining_budget == 0:
                        reason = 'allowance_exhausted'
                        break
            except TimeoutError:
                reason = 'timeout'
                break
            except (InvalidObservation, KeyError, TypeError, ValueError, OSError):
                reason = 'invalid_or_unavailable_response'
                break
        return {'mode': 'synthetic_offline', 'attempts': attempts, 'stop_reason': reason,
                'retry_after_seconds': retry_after, 'aggregate': aggregate_gate(observations)}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_bounded(response, clock=time.monotonic):
    start = clock()
    chunks, size = [], 0
    while True:
        if clock() - start >= MAX_SECONDS:
            raise InvalidObservation('time_bound_exceeded')
        chunk = response.read(min(65536, MAX_COMPRESSED + 1 - size))
        if not chunk:
            return b''.join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size > MAX_COMPRESSED:
            raise InvalidObservation('compressed_bound_exceeded')


def extract_imdb(blob, requested_at):
    """Parse in memory only; scan whole dataset to detect duplicate exact IDs."""
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
        decoded = gz.read(MAX_DECOMPRESSED + 1)
    if len(decoded) > MAX_DECOMPRESSED:
        raise InvalidObservation('decompressed_bound_exceeded')
    reader = csv.DictReader(io.StringIO(decoded.decode('utf-8')), delimiter='\t')
    if reader.fieldnames != ['tconst', 'averageRating', 'numVotes']:
        raise InvalidObservation('schema_mismatch')
    wanted, found = cohort(), {}
    for row in reader:
        identity = row['tconst']
        if identity not in wanted:
            continue
        if identity in found:
            raise InvalidObservation('duplicate_identity')
        if None in row:
            raise InvalidObservation('schema_mismatch')
        proposed = dict(wanted[identity], source='imdb', rating=row['averageRating'],
                        count=row['numVotes'], count_semantics='ratings',
                        count_precision='exact_integer',
                        rating_semantics='source_weighted_average', measurement_at=None)
        found[identity] = validate_observation(proposed, wanted[identity], requested_at)
    return {'sample_size': len(wanted), 'exact_ids_present': len(found),
            'exact_ids_absent': len(wanted) - len(found),
            'aggregate': aggregate_gate(list(found.values()))}


def safe_http_date(value):
    try:
        date = parsedate_to_datetime(value)
        return date.astimezone(timezone.utc).isoformat() if date.tzinfo else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def imdb_personal_check():
    """ONE unauthenticated official dataset GET; no disk storage, retries or logging."""
    report = {'provider': 'imdb_official_dataset', 'status': 'UNAVAILABLE',
              'url': IMDB_URL, 'requested_at': utc_now(), 'retrieved_at': None,
              'attribution': ATTRIBUTION, 'per_film_measurement_time': 'not_provided',
              'storage': 'memory_only_no_raw_output', 'attempts': 1}
    try:
        request = Request(IMDB_URL, headers={'User-Agent': 'LiveScoreSourceValidation/1.0',
                                             'Accept-Encoding': 'identity'})
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            if response.status != 200:
                raise InvalidObservation('http_failure')
            blob = read_bounded(response)
            report['retrieved_at'] = utc_now()
            # Version tokens must have a narrow public-safe representation.
            etag = response.headers.get('ETag', '')
            report['dataset_version'] = etag if re.fullmatch(r'[W/"a-fA-F0-9-]{1,160}', etag) else None
            report['dataset_last_modified'] = safe_http_date(response.headers.get('Last-Modified'))
        sample = extract_imdb(blob, report['requested_at'])
        report.update(status='CHECKED', compressed_sha256=hashlib.sha256(blob).hexdigest(),
                      compressed_bytes=len(blob), schema=['tconst', 'averageRating', 'numVotes'],
                      sample=sample)
    except HTTPError as error:
        report.update(reason='http_failure', http_status=error.code,
                      retry_after_seconds=retry_after_seconds(error.headers.get('Retry-After'),
                                                             report['requested_at']))
        error.close()
    except (TimeoutError, URLError, OSError, EOFError, UnicodeError, ValueError, HTTPException,
            csv.Error, zlib.error):
        # Do not print exceptions, headers, response bodies or partial observations.
        report['reason'] = 'bounded_read_or_schema_unavailable'
    return report


def offline_check():
    fixtures = json.loads((ROOT / 'fixtures' / 'synthetic.json').read_text())
    expected = cohort()[EXPECTED_IDS[0]]
    checked = [validate_observation(row, expected, fixtures['requested_at'])
               for row in fixtures['observations']]
    return {'mode': 'synthetic_offline', 'baseline_commit': BASELINE,
            'cohort_size': len(cohort()), 'aggregate': aggregate_gate(checked),
            'authenticated_mdblist': 'NOT_RUN', 'network_requests': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imdb-personal-check', action='store_true',
                        help='opt in to ONE bounded official IMDb dataset GET, in memory')
    parser.add_argument('--accept-imdb-conditions', action='store_true',
                        help='acknowledge current IMDb terms and personal noncommercial scope')
    args = parser.parse_args(argv)
    if args.imdb_personal_check != args.accept_imdb_conditions:
        parser.error('both explicit IMDb opt-in and conditions acknowledgment are required')
    result = imdb_personal_check() if args.imdb_personal_check else offline_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get('status') != 'UNAVAILABLE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
