"""Passive bounded shadow pilot. Reads research DBs; writes only its own report.

No provider clients, credentials, actor imports, queue updates or notifications.
Research projections do not retain sufficient provenance for automatic acceptance;
missing checks are reported honestly, never inferred from a research proposal.
"""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from .scorer import evaluate, Policy

MAX_ROWS = 1000
MAX_BYTES = 262144


def adapt(proposal):
    f = proposal['original_facts']
    source = dict(title=f['title'], year=f['year'], imdb=f.get('imdb'),
                  runtime=f.get('runtime'), language=None, checked_listing=False,
                  nfo_bound=False, conflicting_evidence=None)
    candidates = {}
    # Keep every retrieved movie, including rivals the worker did not detail.
    for e in proposal.get('evidence', []):
        if e.get('result', {}).get('reason') != 'ok':
            continue
        data = e['result'].get('data') or {}
        records = ([data] if e['method'] == 'details' else
                   data.get('movies', []) if e['method'] == 'find' else
                   data.get('results', []) if e['method'] == 'movie_search' else [])
        for r in records:
            if r.get('type') != 'movie':
                continue
            ident = r['id']
            if ident in candidates and e['method'] != 'details':
                continue
            titles = list(dict.fromkeys(x for x in [r.get('title'), r.get('original_title')]
                                         + r.get('aliases', []) + r.get('translations', []) if x))[:100]
            dates = [r.get('date')] + r.get('dates', [])
            years = sorted({int(d[:4]) for d in dates if isinstance(d, str) and d[:4].isdigit()})
            imdb = r.get('imdb')
            verified = any(x.get('method') == 'find' and x.get('query') == imdb
                           and x.get('result', {}).get('reason') == 'ok'
                           and [v.get('id') for v in (x['result'].get('data') or {}).get('movies', [])] == [ident]
                           and not (x['result'].get('data') or {}).get('tv')
                           and not (x['result'].get('data') or {}).get('tv_other')
                           for x in proposal.get('evidence', [])) if imdb else False
            candidates[ident] = dict(id=ident, titles=titles, years=years,
                                    runtime=r.get('runtime') or None,
                                    language=r.get('original_language'), imdb=imdb,
                                    media_type='movie', crosswalk_verified=verified)
    return dict(source=source, candidates=list(candidates.values()), candidate_set_complete=False)


def observe(proposal):
    case = adapt(proposal)
    result = evaluate(case)
    top = result['ranked'][0] if result['ranked'] else None
    # Arithmetic-only comparison is explicitly separate from a guarded decision.
    return dict(title=case['source']['title'], year=case['source']['year'],
                research_reason=proposal.get('reason'),
                arithmetic_pass=bool(top and top['score'] >= Policy().threshold and result['margin'] >= Policy().margin),
                evidence_gaps=['exact_listing_binding_not_retained', 'candidate_pagination_not_retained',
                               'source_audio_language_not_projected', 'nfo_filename_binding_not_retained'],
                **result)


def scan(databases, started, until, now=None):
    now = time.time() if now is None else now
    if not started < until <= started + 7 * 86400:
        raise ValueError('pilot_window')
    if now >= until:
        return dict(mode='shadow_only', expired=True, started=started, until=until, rows=[])
    rows = []; total = 0; seen = set()
    for path in databases:
        path = Path(path).resolve(strict=True)
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as conn:
            conn.execute('PRAGMA query_only=ON')
            total += conn.execute('select count(*) from proposals').fetchone()[0]
            remaining = MAX_ROWS - len(rows)
            query = '''select p.version,p.created,p.result,e.case_id from proposals p
                       join evidence e on e.version=p.version order by p.created desc limit ?'''
            for version, created, raw, case_id in conn.execute(query, (remaining,)):
                key = hashlib.sha256((path.name + ':' + version + ':' + raw).encode()).hexdigest()
                if key in seen:
                    continue
                seen.add(key)
                base = dict(key=key, case_id=case_id, version=version, observed=created,
                            cohort='new_during_pilot' if created >= started else 'historical_baseline')
                try:
                    if len(raw.encode()) > MAX_BYTES:
                        raise ValueError('record_size')
                    base.update(observe(json.loads(raw)))
                except (ValueError, TypeError, KeyError, AttributeError):
                    base.update(decision='unscorable', reasons=['invalid_or_unsupported_evidence'])
                rows.append(base)
    return dict(mode='shadow_only', expired=False, started=started, until=until,
                generated=now, input_proposals=total, recorded=len(rows),
                capacity_reached=total > MAX_ROWS,
                new_results=sum(x['cohort']=='new_during_pilot' for x in rows),
                would_identify=sum(x['decision']=='would_identify' for x in rows),
                arithmetic_pass=sum(x.get('arithmetic_pass', False) for x in rows), rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', action='append', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--started', type=float, required=True)
    parser.add_argument('--until', type=float, required=True)
    args = parser.parse_args()
    if time.time() >= args.until:
        return  # Stop processing after seven days; preserve the last results.
    # Runtime guard: even accidental future network imports cannot connect.
    import sys
    def audit(event, arguments):
        if event.startswith('socket.'):
            raise PermissionError('shadow_network_forbidden')
    sys.addaudithook(audit)
    result = scan(args.database, args.started, args.until)
    output = Path(args.output).absolute()
    if output.resolve() in [Path(p).resolve() for p in args.database] or output.is_symlink():
        raise ValueError('output_must_be_separate')
    os.umask(0o077)
    temporary = output.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
