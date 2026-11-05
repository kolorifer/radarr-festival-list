"""Explicitly selected SQL query core; no transport or source-path authority.

The host adapter enforces fixed source identity, read-only SQLite connections,
no file creation/unlink, safe existing files and bounded operation. Incidental
atime, SQLite read locks and existing SHM bookkeeping are permitted. The exact
observer callback runs in the same confined process and is followed by the
collector recheck. Query-only and the SQL authorizer add restrictions; they do
not themselves establish host confinement or authenticate source bytes.
"""
import hashlib
import json
import math
import re
import sqlite3
from . import source_rows as row_budget
import time
import unicodedata
import uuid

HEX = re.compile(r'[0-9a-f]{64}\Z')
CASE = re.compile(r'outcome-[0-9a-f]{64}\Z')
LIMIT = 32

_READ_COLUMNS = {
    'selection_current': frozenset(('case_key', 'version', 'release', 'observed')),
    'selection_history': frozenset(('version', 'case_key', 'evidence', 'route', 'correlation', 'material')),
    'selection_events': frozenset(('id', 'release', 'evidence', 'observed', 'received', 'outcome')),
    'evidence': frozenset(('id', 'release', 'metadata')),
    'deliveries': frozenset(('ROWID', 'channel', 'event_id', 'signature', 'evidence', 'reason', 'source_time', 'received')),
    'conflicts': frozenset(('channel', 'event_id', 'signature')),
    'selection_reviews': frozenset(('id', 'case_key', 'event', 'delivery', 'reviewed', 'imdb', 'tmdb', 'year')),
}
_REAL_COLUMNS = {'selection_current': {'observed'},
                 'selection_events': {'observed', 'received'},
                 'deliveries': {'source_time', 'received'},
                 'selection_reviews': {'reviewed'}}
_INTEGER_COLUMNS = {'selection_reviews': {'delivery', 'tmdb', 'year'}}


def _schema_snapshot(db):
    """Validate only fixed main-schema table definitions in the current snapshot."""
    names = tuple(sorted(_READ_COLUMNS))
    marks = ','.join('?' for _ in names)
    objects = db.execute('select name,type,sql from main.sqlite_schema where name collate binary in (' + marks + ') order by name collate binary', names).fetchall()
    require(len(objects) == len(names), 'schema_invalid')
    result = []
    for expected, row in zip(names, objects):
        name, kind, definition = tuple(row)
        require(name == expected and kind == 'table' and type(definition) is str and
                re.match(r'\s*create\s+table\b', definition, re.I) is not None, 'schema_invalid')
        # Fixed identifiers only, never supplied by the source or caller.
        columns = db.execute('pragma main.table_xinfo("' + expected + '")').fetchmany(129)
        require(0 < len(columns) <= 128 and all(len(item) == 7 and item[6] == 0 for item in columns), 'schema_invalid')
        present = {item[1] for item in columns}
        require((_READ_COLUMNS[expected] - {'ROWID'}) <= present, 'schema_invalid')
        for item in columns:
            name, decl = item[1], item[2]
            if name not in _READ_COLUMNS[expected] or name == 'ROWID':
                continue
            expected_type = ('REAL' if name in _REAL_COLUMNS.get(expected, ()) else
                             'INTEGER' if name in _INTEGER_COLUMNS.get(expected, ()) else 'TEXT')
            require(type(decl) is str and decl.upper() == expected_type, 'schema_invalid')
        if expected == 'deliveries':
            require(not any(type(item[1]) is str and item[1].lower() in ('rowid', '_rowid_', 'oid')
                            for item in columns), 'schema_invalid')
        result.append((name, definition, tuple(tuple(item) for item in columns)))
    return tuple(result)


def _authorizer(action, arg1, arg2, database, source):
    """Permit only fixed SQL read columns; views and indirect reads fail closed."""
    if source is not None:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and database == 'main' and arg2 in _READ_COLUMNS.get(arg1, ()):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and arg2 == 'max':
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_TRANSACTION and arg1 in ('BEGIN', 'ROLLBACK'):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def validate_selector(selector):
    require(type(selector) is dict and set(selector) == {'case_id', 'version', 'title'}, 'selection_invalid')
    require(type(selector['case_id']) is str and CASE.fullmatch(selector['case_id']) is not None
            and type(selector['version']) is str and HEX.fullmatch(selector['version']) is not None, 'selection_invalid')
    title = selector['title']
    require(type(title) is str and 0 < len(title) <= 200 and title == title.strip()
            and not any(unicodedata.category(ch).startswith('C') for ch in title)
            and re.search(r'[<>\\/?=@]|[a-z][a-z0-9+.-]*://|magnet:|www\.|\b(?:passkey|token|password|authorization)\s*[:=]|\bBearer\s+\S+|[a-zA-Z0-9_-]{48,}', title, re.I) is None,
            'selection_invalid')
    return selector


def _facts(metadata, outcome, selector):
    """Return only validated title/year and separate source ID claims."""
    title = metadata.get('title')
    # Explicit disclosure binding is data; it is never SQL or shell code.
    require(title == selector['title'], 'disclosure_mismatch')
    safe_title = (type(title) is str and
                  0 < len(title) <= 250 and title == title.strip()
                  and not any(unicodedata.category(ch).startswith('C') for ch in title)
                  and re.search(r'[<>\\/?=@]|[a-z][a-z0-9+.-]*://|magnet:|www\.|\b(?:passkey|token|password|authorization)\s*[:=]|\bBearer\s+\S+|[a-zA-Z0-9_-]{48,}', title, re.I) is None)
    year = metadata.get('year')
    require(year is None or type(year) is int and 1888 <= year <= 2100, 'material_invalid')
    values = {}
    for label, value, kind in (
        ('metadata_imdb', metadata.get('imdb'), 'imdb'),
        ('metadata_tmdb', metadata.get('tmdb'), 'tmdb'),
        ('outcome_asserted_imdb', outcome.get('asserted_imdb'), 'imdb'),
        ('outcome_asserted_tmdb', outcome.get('asserted_tmdb'), 'tmdb'),
    ):
        require(value is None or (type(value) is str and re.fullmatch(r'tt[0-9]{7,10}', value) is not None
                if kind == 'imdb' else type(value) is int and 0 < value < 2**31), 'material_invalid')
        values[label] = value
    return {'title': title if safe_title else None,
            'title_status': 'available' if safe_title else ('not_established' if title is None else 'withheld_unsafe'),
            'source_year': year, **values, 'id_values_are_claims': True}


class Refused(Exception):
    def __init__(self, code):
        self.code = code


def require(value, code):
    if not value:
        raise Refused(code)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'invalid_json')
        result[key] = value
    return result


def parse(raw):
    try:
        require(isinstance(raw, str) and len(raw.encode()) <= 262144, 'invalid_json')
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: require(False, 'invalid_json'))
    except (ValueError, TypeError, UnicodeError):
        raise Refused('invalid_json') from None


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False).encode()
    except (ValueError, TypeError, UnicodeError):
        raise Refused('invalid_json') from None


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def valid_time(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 < value < 10**11


def rows(db, sql, args, code):
    found = db.execute(sql, args).fetchmany(LIMIT + 1)
    require(len(found) <= LIMIT, code)
    return found


def current(db, case):
    return rows(db, 'select x.case_key,x.version,x.release,x.observed,h.route,h.correlation,'
        'h.evidence,h.material from main.selection_current x join main.selection_history h '
        'on h.version collate binary=x.version collate binary '
        'and h.case_key collate binary=x.case_key collate binary '
        'where x.case_key collate binary=?', (case,), 'too_many_rows')


def cursor(db, release):
    value = db.execute('select max(d.rowid) from main.deliveries d '
                       'join main.evidence e on e.id collate binary=d.evidence collate binary '
                       'where e.release collate binary=?', (release,)).fetchone()[0]
    require(type(value) is int and value > 0, 'delivery_cursor_unknown')
    return value


def latest(db, release):
    found = rows(db, 'select id,release,evidence,observed,received,outcome from main.selection_events '
                     'where release collate binary=? order by observed desc,id collate binary limit 1', (release,), 'too_many_rows')
    require(len(found) == 1, 'event_missing')
    return found[0]


def collect(collector, probe_observer, selector):
    """Inspect the fixed case and conditionally probe its exact observer event.

    Caller owns the collector and supplies a trusted probe(event_uuid) returning
    exactly ("present" or "absent", observation time). It must independently
    enforce observer access and time bounds. This core enforces neither process
    isolation nor a total external timeout and is not a security boundary.
    """
    db = None
    try:
        validate_selector(selector)
        case_id, version, clock = selector['case_id'], selector['version'], time.time
        require(isinstance(case_id, str) and CASE.fullmatch(case_id) is not None and
                isinstance(version, str) and HEX.fullmatch(version) is not None, 'selection_invalid')
        require(type(collector) is sqlite3.Connection and callable(probe_observer), 'input_invalid')
        db = collector
        require(hasattr(db, 'setlimit') and hasattr(db, 'getlimit') and
                hasattr(sqlite3, 'SQLITE_LIMIT_LENGTH'), 'limits_unavailable')
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1048576)
        require(db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) <= 1048576, 'limits_unavailable')
        deadline = time.monotonic() + 20.0
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 500)
        db.row_factory = row_budget.factory('collector')
        require(all(row[1] in ('main', 'temp') for row in db.execute('pragma database_list')), 'input_invalid')
        db.execute('pragma query_only=on')
        require(db.execute('pragma query_only').fetchone()[0] == 1, 'schema_invalid')
        db.execute('pragma trusted_schema=off')
        trusted = db.execute('pragma trusted_schema').fetchone()
        require(trusted is not None and trusted[0] == 0, 'schema_invalid')
        started = clock(); require(valid_time(started), 'clock_invalid')
        db.execute('begin')
        try:
            schema = _schema_snapshot(db)
            db.set_authorizer(_authorizer)
            selected = current(db, case_id)
            require(len(selected) == 1, 'case_missing')
            row = selected[0]
            require(row['case_key'] == case_id, 'selection_invalid')
            require(row['version'] == version, 'version_changed')
            require(row['release'] == case_id[8:] and HEX.fullmatch(row['release']) is not None and
                    valid_time(row['observed']) and row['observed'] <= started, 'selection_invalid')
            require(row['route'] == 'eligible' and row['correlation'] == 'strong_source_id', 'not_eligible')
            material = parse(row['material'])
            require(type(material) is dict and set(material) in (
                {'metadata','outcome','route','underlying_route','correlation'},
                {'metadata','outcome','route','underlying_route','correlation','occurrence'}), 'material_invalid')
            require(material['route'] == material['underlying_route'] == 'eligible' and
                    material['correlation'] == row['correlation'] and digest([case_id, material]) == version,
                    'material_invalid')
            event = latest(db, row['release'])
            require(isinstance(event['id'], str) and HEX.fullmatch(event['id']) is not None and
                    isinstance(event['evidence'], str) and HEX.fullmatch(event['evidence']) is not None and
                    event['evidence'] == row['evidence'] and valid_time(event['observed']) and
                    valid_time(event['received']) and event['observed'] <= started and event['received'] <= started and
                    row['observed'] == event['observed'], 'event_invalid')
            evidence = rows(db, 'select id,release,metadata from main.evidence where id collate binary=?',
                            (event['evidence'],), 'too_many_rows')
            require(len(evidence) == 1 and evidence[0]['release'] == row['release'], 'evidence_invalid')
            metadata, outcome = parse(evidence[0]['metadata']), parse(event['outcome'])
            require(type(metadata) is dict and type(outcome) is dict and
                    {'category','status','reason'} <= set(outcome) <=
                    {'category','status','reason','asserted_imdb','asserted_tmdb','torrent_evidence'} and
                    material['metadata'] == metadata and
                    material['outcome'] == outcome and outcome.get('status') == 'needs_review' and
                    outcome.get('reason') == 'title_conflict' and
                    outcome.get('category') in ('unknown_movie','other'), 'material_invalid')
            require(digest([row['release'], metadata]) == event['evidence'], 'evidence_invalid')
            require(digest([row['release'], event['evidence'], event['observed'], outcome]) == event['id'],
                    'event_invalid')
            facts = _facts(metadata, outcome, selector)
            concurrent = rows(db, 'select id from main.selection_events where release collate binary=? and observed=? limit 33',
                              (row['release'], event['observed']), 'too_many_rows')
            require(len(concurrent) == 1, 'event_ambiguous')
            deliveries = rows(db, 'select rowid,event_id,signature,received,source_time from main.deliveries '
                "where channel collate binary='outcome' and evidence collate binary=? and source_time=? and reason is null limit 33",
                (event['evidence'], event['observed']), 'too_many_rows')
            require(len(deliveries) == 1, 'delivery_ambiguous')
            delivery = deliveries[0]
            try:
                event_uuid = str(uuid.UUID(delivery['event_id']))
            except (ValueError, TypeError, AttributeError):
                raise Refused('event_invalid') from None
            require(event_uuid == delivery['event_id'] and type(delivery['rowid']) is int and
                    delivery['rowid'] > 0 and valid_time(delivery['received']) and delivery['received'] <= started and
                    delivery['received'] == event['received'] and valid_time(delivery['source_time']) and
                    delivery['source_time'] == event['observed'], 'event_invalid')
            conflicts = rows(db, "select signature from main.conflicts where channel collate binary='outcome' and event_id collate binary=? limit 33",
                             (event_uuid,), 'too_many_rows')
            require(not conflicts, 'delivery_conflict')
            signature = digest(dict(event_id=event_uuid, release=row['release'], metadata=metadata, outcome=outcome))
            require(delivery['signature'] == signature, 'delivery_signature_mismatch')
            review_cursor = cursor(db, row['release'])
            review_rows = rows(db, 'select id,event,delivery,reviewed,imdb,tmdb,year from main.selection_reviews where case_key collate binary=? order by event collate binary,delivery limit 33',
                               (case_id,), 'too_many_rows')
            require(all(isinstance(r['event'], str) and HEX.fullmatch(r['event']) is not None and
                        type(r['delivery']) is int and r['delivery'] > 0 and
                        isinstance(r['id'], str) and r['id'] == digest([case_id, r['event'], r['delivery']]) and
                        valid_time(r['reviewed']) and r['reviewed'] <= clock() and
                        isinstance(r['imdb'], str) and re.fullmatch(r'tt[0-9]{7,10}', r['imdb']) is not None and
                        type(r['tmdb']) is int and 0 < r['tmdb'] < 2**31 and
                        type(r['year']) is int and 1888 <= r['year'] <= 2100 for r in review_rows), 'review_invalid')
            require((not review_rows and 'occurrence' not in material) or
                    (bool(review_rows) and material.get('occurrence') == digest([event['id'], review_cursor])),
                    'material_invalid')
            require(not any(r['event'] == event['id'] and r['delivery'] == review_cursor for r in review_rows),
                    'already_reviewed')
            current_event = event['id']
            selected_record = tuple(row)
            selected_reviews = [tuple(r) for r in review_rows]
            observed_at = clock(); require(valid_time(observed_at) and observed_at >= started, 'clock_invalid')
            require(time.monotonic() <= deadline, 'deadline_exceeded')
            result = {'status':'ok', 'case_id':case_id, 'selection_version':version,
                      'route':'eligible', 'correlation':'strong_source_id', 'reason':'title_conflict',
                      'selection_event_digest':current_event, 'event_uuid':event_uuid,
                      'outcome_delivery_rowid':delivery['rowid'], 'review_cursor':review_cursor,
                      'event_observed_at':event['observed'], 'collector_observation_started_at':started,
                      'collector_observed_at':observed_at,
                      'historical_review_count':len(review_rows), 'decision_history':'incomplete_unknown',
                      'selection_reviews':[dict(r) for r in review_rows],
                      'facts':facts,
                      'normalized_signature':'source_side_match_only', 'captured_bytes':'not_established',
                      'evidence_freshness':'not_established'}
        finally:
            db.rollback()
        spool_started = clock(); require(valid_time(spool_started) and spool_started >= observed_at, 'clock_invalid')
        require(time.monotonic() <= deadline, 'deadline_exceeded')
        observation = probe_observer(event_uuid)
        spool_finished = clock(); require(valid_time(spool_finished) and spool_finished >= spool_started, 'clock_invalid')
        require(type(observation) is tuple and len(observation) == 2 and
                observation[0] in ('present', 'absent') and type(observation[0]) is str and
                valid_time(observation[1]) and spool_started <= observation[1] <= spool_finished, 'observer_invalid')
        pending, spool_at = observation
        require(time.monotonic() <= deadline, 'deadline_exceeded')
        recheck_started = clock(); require(valid_time(recheck_started) and recheck_started >= spool_finished, 'clock_invalid')
        db.execute('begin')
        try:
            # Permit only fixed SQLite schema introspection in this new snapshot.
            # Keep the restrictive authorizer active throughout the observer call.
            db.set_authorizer(None)
            require(_schema_snapshot(db) == schema, 'schema_changed')
            db.set_authorizer(_authorizer)
            again = current(db, case_id)
            latest_reviews = rows(db, 'select id,event,delivery,reviewed,imdb,tmdb,year from main.selection_reviews where case_key collate binary=? order by event collate binary,delivery limit 33',
                                  (case_id,), 'too_many_rows')
            again_event = latest(db, row['release'])
            again_evidence = rows(db, 'select id,release,metadata from main.evidence where id collate binary=?',
                                  (event['evidence'],), 'too_many_rows')
            again_deliveries = rows(db, 'select rowid,event_id,signature,received,source_time from main.deliveries '
                "where channel collate binary='outcome' and evidence collate binary=? and source_time=? and reason is null limit 33",
                (event['evidence'], event['observed']), 'too_many_rows')
            again_conflicts = rows(db, "select signature from main.conflicts where channel collate binary='outcome' and event_id collate binary=? limit 33",
                                   (event_uuid,), 'too_many_rows')
            again_concurrent = rows(db, 'select id from main.selection_events where release collate binary=? and observed=? limit 33',
                                    (row['release'], event['observed']), 'too_many_rows')
            require(len(again) == 1 and tuple(again[0]) == selected_record and
                    [tuple(r) for r in latest_reviews] == selected_reviews and
                    tuple(again_event) == tuple(event) and [tuple(r) for r in again_evidence] == [tuple(r) for r in evidence] and
                    [tuple(r) for r in again_deliveries] == [tuple(r) for r in deliveries] and not again_conflicts and
                    [tuple(r) for r in again_concurrent] == [tuple(r) for r in concurrent] and
                    again[0]['version'] == version and again[0]['route'] == 'eligible' and
                    again[0]['correlation'] == 'strong_source_id' and
                    cursor(db, row['release']) == review_cursor, 'case_changed')
            rechecked_at = clock(); require(valid_time(rechecked_at) and rechecked_at >= recheck_started, 'clock_invalid')
            require(time.monotonic() <= deadline, 'deadline_exceeded')
        finally:
            db.rollback()
        result.update(observer_pending=pending, spool_observation_started_at=spool_started,
                      spool_observed_at=spool_at, spool_observation_finished_at=spool_finished,
                      collector_recheck_started_at=recheck_started, collector_rechecked_at=rechecked_at,
                      cross_store_atomic=False, intervening_changes='not_excluded')
        return result
    except Refused as exc:
        return {'status':'refused', 'code':exc.code}
    except Exception:
        return {'status':'refused', 'code':'query_failed'}
    finally:
        if db is not None:
            try:
                db.set_progress_handler(None, 0)
            except Exception:
                pass
            try:
                db.set_authorizer(None)
            except Exception:
                pass
