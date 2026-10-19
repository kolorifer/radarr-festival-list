"""Separate private, append-only research evidence; never opens the Stage1 inbox.

A singleton pilot ledger caps all invocations together. Request reservations commit
before transport; a crash can waste a reservation but cannot refund or exceed it.
"""
from contextlib import contextmanager
import json
import sqlite3
import time
import uuid

from identity_triage_store import create_private, digest, private_directory, private_path

STATES = ('queued', 'leased', 'retry_wait', 'awaiting_evidence')
ELIGIBLE = {'seed_missing_crosswalk', 'explicit_unresolved', 'identifier_conflict', 'verified_resolver_unresolved'}


class Stop(Exception):
    pass


class ResearchStore:
    filename = 'research.sqlite3'
    def __init__(self, directory, clock=time.time):
        self.directory = private_directory(directory)
        self.path = self.directory / self.filename
        self.clock = clock
        try:
            create_private(self.path)
        except FileExistsError:
            pass
        with self.tx() as c:
            version = c.execute('pragma user_version').fetchone()[0]
            if version not in (0, 1):
                raise ValueError('research_schema')
            if not version:
                for sql in (
                    'CREATE TABLE pilot (id INTEGER PRIMARY KEY CHECK(id=1), active_run TEXT, until REAL NOT NULL, closed INTEGER NOT NULL DEFAULT 0)',
                    'INSERT INTO pilot VALUES (1,NULL,0,0)',
                    'CREATE TABLE admissions (case_id TEXT PRIMARY KEY, seed INTEGER NOT NULL CHECK(seed IN (0,1)))',
                    'CREATE TABLE evidence (version TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES admissions, material TEXT NOT NULL, observed REAL NOT NULL)',
                    "CREATE TABLE jobs (case_id TEXT PRIMARY KEY REFERENCES admissions, version TEXT NOT NULL REFERENCES evidence, status TEXT NOT NULL CHECK(status IN ('queued','leased','retry_wait','awaiting_evidence')), due REAL NOT NULL, lease TEXT, until REAL, failures INTEGER NOT NULL DEFAULT 0)",
                    'CREATE TABLE runs (id TEXT PRIMARY KEY, started REAL NOT NULL, deadline REAL NOT NULL, cases INTEGER NOT NULL DEFAULT 0, ended REAL)',
                    'CREATE TABLE attempts (id TEXT PRIMARY KEY, run TEXT NOT NULL REFERENCES runs, version TEXT NOT NULL REFERENCES evidence, started REAL NOT NULL, ended REAL, result TEXT)',
                    'CREATE TABLE requests (id INTEGER PRIMARY KEY, run TEXT NOT NULL REFERENCES runs, attempt TEXT NOT NULL REFERENCES attempts, provider TEXT NOT NULL CHECK(provider="tmdb"), request_key TEXT NOT NULL, reserved REAL NOT NULL, result TEXT)',
                    'CREATE TABLE provider (id TEXT PRIMARY KEY CHECK(id="tmdb"), not_before REAL NOT NULL, suspended INTEGER NOT NULL DEFAULT 0)',
                    'INSERT INTO provider VALUES ("tmdb",0,0)',
                    'CREATE TABLE cache (key TEXT PRIMARY KEY, expires REAL NOT NULL, result TEXT NOT NULL)',
                    'CREATE TABLE proposals (attempt TEXT PRIMARY KEY REFERENCES attempts, version TEXT NOT NULL REFERENCES evidence, created REAL NOT NULL, status TEXT NOT NULL CHECK(status="needs_review"), result TEXT NOT NULL)',
                ):
                    c.execute(sql)
                c.execute('pragma user_version=1')

    def check(self):
        private_path(self.directory, True)
        for suffix in ('', '-wal', '-shm', '-journal'):
            p = self.path.with_name(self.path.name + suffix)
            try:
                private_path(p)
            except FileNotFoundError:
                if not suffix:
                    raise

    @contextmanager
    def tx(self):
        self.check()
        c = sqlite3.connect(self.path.as_uri()+'?mode=rw', uri=True, timeout=1, isolation_level=None)
        c.row_factory = sqlite3.Row
        try:
            c.execute('pragma foreign_keys=ON')
            c.execute('pragma journal_mode=WAL')
            c.execute('pragma synchronous=FULL')
            c.execute('BEGIN IMMEDIATE')
            yield c
            c.commit()
        finally:
            c.close()

    def admit(self, item):
        # Validator belongs to the ingestion API, not just the command-line caller.
        from identity_research_provider import validate_case
        item = validate_case(item)
        material = {k:v for k,v in item.items() if k != 'observed_at'}
        version = digest(material)
        with self.tx() as c:
            old = c.execute('select seed from admissions where case_id=?',(item['case_id'],)).fetchone()
            if old and old['seed'] != item['seed']:
                raise ValueError('seed_changed')
            if not old:
                count = c.execute('select count(*) from admissions where seed=?',(item['seed'],)).fetchone()[0]
                if count >= (4 if item['seed'] else 10):
                    raise Stop('case_budget')
                c.execute('insert into admissions values (?,?)',(item['case_id'],item['seed']))
            if c.execute('select 1 from evidence where version=?',(version,)).fetchone():
                return 'duplicate'
            c.execute('insert into evidence values (?,?,?,?)',(version,item['case_id'],json.dumps(material,sort_keys=True),item['observed_at']))
            c.execute('insert into jobs values (?,?,"queued",?,NULL,NULL,0) ON CONFLICT(case_id) DO UPDATE SET version=excluded.version,status="queued",due=excluded.due,lease=NULL,until=NULL,failures=0', (item['case_id'],version,self.clock()))
        return 'admitted'

    def start(self):
        now = self.clock(); run = uuid.uuid4().hex
        with self.tx() as c:
            p = c.execute('select * from pilot').fetchone()
            if p['closed'] or p['until'] > now:
                raise Stop('pilot_closed_or_busy')
            if c.execute('select count(*) from requests').fetchone()[0] >= 100:
                raise Stop('pilot_request_budget')
            c.execute('insert into runs values (?,?,?,0,NULL)',(run,now,now+540))
            c.execute('update pilot set active_run=?,until=?',(run,now+600))
        return run

    def _run(self,c,run):
        r = c.execute('select * from runs where id=?',(run,)).fetchone()
        p = c.execute('select * from pilot').fetchone()
        if not r or r['ended'] is not None or r['deadline'] <= self.clock() or p['closed'] or p['active_run'] != run:
            raise Stop('run_inactive')
        return r

    def lease(self,run):
        now = self.clock()
        with self.tx() as c:
            r = self._run(c,run)
            if r['cases'] >= 10:
                raise Stop('run_case_budget')
            row = c.execute('select j.*,e.material from jobs j join evidence e on e.version=j.version join admissions a on a.case_id=j.case_id where (j.status!="leased" AND j.due<=?) OR (j.status="leased" AND j.until<=?) order by a.seed DESC,j.due,j.case_id limit 1',(now,now)).fetchone()
            if not row:
                return None
            token = uuid.uuid4().hex
            c.execute('update jobs set status="leased",lease=?,until=? where case_id=?',(token,now+600,row['case_id']))
            c.execute('update runs set cases=cases+1 where id=?',(run,))
            c.execute('insert into attempts values (?,?,?,?,NULL,NULL)',(token,run,row['version'],now))
            return dict(row)|{'token':token,'item':json.loads(row['material'])}

    def reserve(self,run,lease,key):
        now = self.clock()
        with self.tx() as c:
            self._run(c,run)
            j = c.execute('select * from jobs where lease=?',(lease,)).fetchone()
            a = c.execute('select run from attempts where id=?',(lease,)).fetchone()
            if not j or j['until'] <= now or not a or a['run'] != run:
                raise Stop('stale_lease')
            p = c.execute('select * from provider').fetchone()
            if p['suspended']:
                raise Stop('provider_suspended')
            cached = c.execute('select result from cache where key=? and expires>?',(key,now)).fetchone()
            if cached:
                return None,json.loads(cached['result'])
            if p['not_before'] > now:
                raise Stop('provider_cooldown')
            total = c.execute('select count(*) from requests').fetchone()[0]
            used = c.execute('select count(*) from requests where run=?',(run,)).fetchone()[0]
            if total >= 100 or used >= 50:
                raise Stop('request_budget')
            cursor = c.execute('insert into requests values (NULL,?,?,"tmdb",?,?,NULL)',(run,lease,key,now))
            c.execute('update provider set not_before=?',(now+1,))
            return cursor.lastrowid,None

    def record(self,request,key,result):
        now = self.clock(); reason=result['reason']
        with self.tx() as c:
            row=c.execute('select * from requests where id=?',(request,)).fetchone()
            if not row or row['request_key'] != key or row['result'] is not None:
                raise Stop('request_finalized')
            c.execute('update requests set result=? where id=?',(reason,request))
            if reason == 'auth_failure':
                c.execute('update provider set suspended=1')
            elif reason == 'rate_limited':
                c.execute('update provider set not_before=max(not_before,?)',(now+max(900,result.get('retry_after',0)),))
            elif reason in ('ok','not_found','redirect_denied'):
                c.execute('insert or replace into cache values (?,?,?)',(key,now+86400,json.dumps(result,sort_keys=True)))

    def finish(self,lease,result):
        now=self.clock()
        with self.tx() as c:
            a=c.execute('select * from attempts where id=?',(lease['token'],)).fetchone()
            if a and a['ended'] is not None:
                return 'duplicate'
            j=c.execute('select * from jobs where case_id=?',(lease['case_id'],)).fetchone()
            if not j or j['lease'] != lease['token'] or j['version'] != lease['version'] or j['until']<=now:
                raise Stop('stale_lease')
            reason=result['reason']; transient=reason in {'transport_failure','http_failure','rate_limited','auth_failure','malformed_response','response_too_large','provider_cooldown','provider_suspended','request_budget','run_inactive'}
            failures=j['failures']+1
            delay=retry_delay(reason,failures,lease['version'],result.get('retry_after',0))
            c.execute('insert into proposals values (?,?,?,"needs_review",?)',(lease['token'],lease['version'],now,json.dumps(result,sort_keys=True)))
            c.execute('update attempts set ended=?,result=? where id=?',(now,reason,lease['token']))
            c.execute('update jobs set status=?,due=?,lease=NULL,until=NULL,failures=? where case_id=?',('retry_wait' if transient else 'awaiting_evidence',now+delay,failures,lease['case_id']))
        return 'completed'

    def end(self,run,close=False):
        with self.tx() as c:
            c.execute('update runs set ended=? where id=?',(self.clock(),run))
            c.execute('update pilot set until=0,active_run=NULL,closed=max(closed,?) where active_run=?',(int(close),run))

    def close_pilot(self):
        with self.tx() as c:
            c.execute('update pilot set closed=1')

    def summary(self):
        with self.tx() as c:
            return {'admissions':c.execute('select count(*) from admissions').fetchone()[0],
                    'requests_reserved':c.execute('select count(*) from requests').fetchone()[0],
                    'requests_completed':c.execute('select count(*) from requests where result is not null').fetchone()[0],
                    'request_cap':100,'remaining':100-c.execute('select count(*) from requests').fetchone()[0],
                    'runs':c.execute('select count(*) from runs').fetchone()[0],
                    'attempts':c.execute('select count(*) from attempts').fetchone()[0],
                    'proposals':c.execute('select count(*) from proposals').fetchone()[0],
                    'states':dict(c.execute('select status,count(*) from jobs group by status')),
                    'reasons':dict(c.execute('select result,count(*) from attempts where ended is not null group by result')),
                    'closed':bool(c.execute('select closed from pilot').fetchone()[0])}


def retry_delay(reason, failures, material, retry_after=0):
    if reason in ('missing_crosswalk','no_supported_candidate','candidate_review','tv_only','identifier_conflict','context_conflict','not_found','redirect_denied'):
        base=7*86400 if failures==1 else 30*86400
    else:
        base=(900,3600,21600,86400)[min(max(failures-1,0),3)]
    # Stable positive jitter makes frozen replay deterministic and never shortens Retry-After.
    jitter=int(digest([material,failures])[:8],16)%max(1,base//10)
    return max(base+jitter,retry_after)
