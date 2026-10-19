"""Actor-owned review digest. No research, correction or acquisition capability.

Delivery is at-most-one automatic attempt per material version, except explicit
Telegram 429 rejection. An ambiguous outcome stays uncertain for human review.
"""
from contextlib import contextmanager
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from urllib.error import HTTPError
from identity_triage_store import private_directory, private_path, create_private
from private_text import redact_text

FLAG = 'MOVIE_INTEL_IDENTITY_DIGEST_ENABLED'
REVIEW = {'eligible', 'review_only', 'quarantine', 'unmatched', 'retry_later'}
ROUTES = REVIEW | {'verified', 'routine', 'unassessed', 'existing_seed'}
LOG = logging.getLogger(__name__)


def projection(report, now):
    """Allowlist outbound fields, never forward evidence blobs or source IDs."""
    from identity_triage_intake import REASONS
    if not isinstance(report, dict) or report.get('version') != 1:
        raise ValueError('digest_schema')
    stamp = report.get('generated_at')
    if type(stamp) not in (int, float) or not math.isfinite(stamp) or not now-172800 < stamp <= now+300:
        raise ValueError('digest_stale')
    cases = report.get('cases')
    if not isinstance(cases, list) or len(cases) > 1000:
        raise ValueError('digest_capacity')
    output = []; seen = set()
    for row in cases:
        cid = row['case_id']; version = row['version']
        if not isinstance(cid, str) or not re.fullmatch(r'outcome-[a-f0-9]{64}', cid) or cid in seen:
            raise ValueError('digest_case')
        seen.add(cid)
        if not isinstance(version, str) or not re.fullmatch(r'[a-f0-9]{64}', version):
            raise ValueError('digest_version')
        route = row['route']; reason = row['reason']; title = row['title']; year = row['year']
        if route not in ROUTES or reason not in REASONS or type(year) != int or not 1870 <= year <= 2100:
            raise ValueError('digest_status')
        if not isinstance(title, str) or not 1 <= len(title) <= 256:
            raise ValueError('digest_title')
        title = ' '.join(redact_text(title).split())[:160]
        proposal = row.get('proposal') or {}
        current = proposal.get('current_evidence') is True
        candidates = set()
        if current:
            for item in (proposal.get('search_candidates', []) + (proposal.get('result') or {}).get('candidates', []))[:20]:
                record = item.get('record', {})
                ident = record.get('id'); kind = record.get('type')
                if type(ident) != int or not 0 < ident < 2**63 or kind not in ('movie', 'tv'):
                    raise ValueError('digest_candidate')
                candidates.add((kind, ident))
        candidates = sorted(candidates)[:3]
        status = row.get('research_status', 'not_admitted')
        if status not in {'not_admitted', 'queued', 'researching', 'awaiting_evidence', 'running', 'done', 'leased'}:
            raise ValueError('digest_research_status')
        text = f'{title} ({year})\nStatus: {route}; {reason.replace("_", " ")}. Research: {status.replace("_", " ")}.'
        if candidates:
            text += '\nPossible TMDb matches (unverified): ' + ', '.join(f'{kind} {ident}' for kind, ident in candidates) + '.'
            text += '\nDetails, media type and source crosswalk require review.'
        elif proposal:
            text += '\nResearch evidence available for review' + ('; current proposal.' if current else '; prior proposal is stale.')
        # Include material evidence even when the concise text remains the same.
        stable = {'version': version, 'text': text, 'proposal': proposal}
        key = hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        output.append((cid, key, route, text))
    return output


def read_report(path, now):
    private_path(path.parent, True); private_path(path)
    if path.resolve() != path or path.stat().st_size > 2_097_152:
        raise ValueError('digest_path_size')
    with path.open('rb') as f:
        raw = f.read(2_097_153)
    if len(raw) > 2_097_152:
        raise ValueError('digest_size')
    return projection(json.loads(raw), now)


class Digest:
    def __init__(self, directory):
        self.directory = private_directory(directory)
        self.path = directory / 'deliveries.sqlite3'
        try:
            create_private(self.path)
        except FileExistsError:
            pass
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS delivery (case_id TEXT, version TEXT, state TEXT, due REAL, PRIMARY KEY(case_id,version))')

    @contextmanager
    def connect(self):
        private_path(self.directory, True); private_path(self.path)
        c = sqlite3.connect(self.path, timeout=1)
        c.execute('PRAGMA synchronous=FULL')
        try:
            with c:
                yield c
        finally:
            c.close()

    def tick(self, rows, send, now):
        selected = []
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            for cid, key, route, text in rows:
                prior = c.execute('SELECT 1 FROM delivery WHERE case_id=?', (cid,)).fetchone()
                if route not in REVIEW and not (prior and route in {'verified', 'routine'}):
                    continue
                existing = c.execute('SELECT state,due FROM delivery WHERE case_id=? AND version=?', (cid, key)).fetchone()
                if existing and (existing[0] != 'retry' or existing[1] > now):
                    continue
                c.execute('INSERT OR REPLACE INTO delivery VALUES (?,?,?,?)', (cid, key, 'uncertain', now))
                selected.append((cid, key, text))
                if len(selected) == 4:
                    break
        if not selected:
            return 0
        message = 'Movie identity review\n\n' + '\n\n'.join(x[2] for x in selected)
        message += '\n\nReview required before any correction. No correction or download performed. Reply in the main ChatGPT conversation to review.'
        state = 'sent'; due = now
        try:
            if send(message) != 200:
                raise ValueError('digest_unconfirmed')
        except HTTPError as exc:
            state = 'uncertain'
            if exc.code == 429:
                # Explicit rejection is safe to retry; respect a longer Retry-After.
                try:
                    raw = exc.read(16385)
                    body = json.loads(raw) if raw and len(raw) <= 16384 else {}
                    delay = max(3600, float(exc.headers.get('Retry-After', 3600)),
                                float(body.get('parameters', {}).get('retry_after', 3600)))
                except (ValueError, TypeError, AttributeError, OSError): delay = 86400
                if not math.isfinite(delay): delay = 86400
                state = 'retry'; due = now + delay
        except Exception:
            state = 'uncertain'
        with self.connect() as c:
            c.executemany('UPDATE delivery SET state=?,due=? WHERE case_id=? AND version=?',
                          [(state, due, cid, key) for cid, key, _ in selected])
        LOG.warning('identity_digest delivery=%s cases=%d', state, len(selected))
        return len(selected)

    def summary(self):
        with self.connect() as c:
            return dict(c.execute('SELECT state,count(*) FROM delivery GROUP BY state'))


def start(send):
    if os.environ.get(FLAG, '0') != '1':
        return None
    home = Path.home().resolve()
    report = home / '.local/state/movie-identity-research/review-report.json'
    state = home / '.local/state/movie-identity-digest'
    def run():
        while True:
            try:
                digest = Digest(state)
                digest.tick(read_report(report, time.time()), send, time.time())
                LOG.warning('identity_digest summary %s', json.dumps(digest.summary(), sort_keys=True))
            except Exception:
                LOG.warning('identity_digest check_failed')
            time.sleep(300)
    thread = threading.Thread(target=run, name='identity-digest', daemon=True)
    thread.start()
    return thread
