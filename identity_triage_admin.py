"""Bounded local observation maintenance; never fetches providers or action state."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import uuid

from identity_triage_intake import MAX_BODY, Reject, decode, normalize
from identity_triage_service import read_config
from identity_triage_store import Store, private_path, digest


def retained_envelope(row, sources):
    source = row['indexer']
    # Installed autobrr retains the display name, not always its identifier.
    if source not in sources:
        matches = [k for k, v in sources.items() if v == source]
        if len(matches) != 1:
            raise Reject('source')
        source = matches[0]
    release = {'type': row['type'], 'protocol': row['protocol'], 'implementation': row['implementation'],
               'title': row['title'], 'year': row['year'], 'name': row['torrent_name']}
    if row['torrent_id']:
        release['external_id'] = row['torrent_id']
    return {'version': '1.0', 'event': 'release.new',
            'id': str(uuid.uuid5(uuid.NAMESPACE_URL, 'retained-autobrr:' + str(row['id']) + ':' + digest(release))),
            'timestamp': row['timestamp'],
            'data': {'release': release, 'indexer': {'identifier': source, 'name': sources[source]}}}


def reconcile(store, database, sources, after_id=0, limit=100):
    if not 1 <= limit <= 500 or type(after_id) != int or after_id < 0:
        raise ValueError('bounds')
    path = Path(database).resolve(strict=True)
    c = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=0.25)
    c.row_factory = sqlite3.Row
    try:
        # No raw payload, action status, download/magnet URL or credentials selected.
        rows = c.execute('SELECT id,type,torrent_id,title,year,torrent_name,timestamp,"indexer",protocol,implementation FROM release WHERE id>? ORDER BY id LIMIT ?', (after_id, limit)).fetchall()
    finally:
        c.close()
    results = {}
    for row in rows:
        try:
            result = store.ingest(normalize(retained_envelope(row, sources), sources, 'retained'), 'retained')
        except Reject:
            store.reject('retained')
            result = 'rejected'
        results[result] = results.get(result, 0) + 1
    return {'coverage': 'incomplete_retained_only', 'rows_scanned': len(rows), 'results': results,
            'next_after_id': rows[-1]['id'] if rows else after_id}


def seed(store, path, sources):
    p = private_path(Path(path))
    if p.stat().st_size > MAX_BODY:
        raise ValueError('seed_size')
    document = decode(p.read_bytes())
    if set(document) != {'version', 'cases'} or document['version'] != 1 or not isinstance(document['cases'], list) or len(document['cases']) != 4:
        raise ValueError('four_seed_cases')
    # Validate the entire bundle before first write; a missing case never silently
    # becomes a successful partial import. All statuses are fixed unresolved.
    records = [normalize(item, sources, 'seed') for item in document['cases']]
    if any(r.get('reason') for r in records) or len({r['release'] for r in records}) != 4:
        raise ValueError('seed_evidence_incomplete')
    return [store.ingest(r, 'seed') for r in records]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', required=True)
    p.add_argument('--state', required=True)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('metrics')
    b = sub.add_parser('backup'); b.add_argument('destination')
    s = sub.add_parser('seed'); s.add_argument('private_bundle')
    r = sub.add_parser('reconcile'); r.add_argument('database'); r.add_argument('--after-id', type=int, default=0); r.add_argument('--limit', type=int, default=100)
    v = sub.add_parser('review-occurrence'); v.add_argument('case_id'); v.add_argument('expected_version')
    v.add_argument('--imdb',required=True); v.add_argument('--tmdb',type=int,required=True); v.add_argument('--year',type=int,required=True); v.add_argument('--delivery',type=int,required=True)
    args = p.parse_args(argv)
    try:
        cfg = read_config(args.config)
        store = Store(args.state)
        if args.command == 'metrics':
            result = store.metrics()
        elif args.command == 'backup':
            store.backup(args.destination); result = {'backup': 'ok'}
        elif args.command == 'seed':
            result = {'seed_results': seed(store, args.private_bundle, cfg['sources'])}
        elif args.command == 'review-occurrence':
            from identity_selection import review_occurrence
            with store.connection() as c:
                c.execute('BEGIN IMMEDIATE')
                review_occurrence(c,args.case_id,args.expected_version,args.imdb,args.tmdb,args.year,args.delivery)
                c.commit()
            result = {'reviewed_for_occurrence':True,'identity_verified':False,'download_approved':False}
        else:
            result = reconcile(store, args.database, cfg['sources'], args.after_id, args.limit)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, sqlite3.Error):
        print('triage maintenance_failed')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
