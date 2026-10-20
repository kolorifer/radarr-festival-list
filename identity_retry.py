"""Actor-owned metadata retries. No notification, approval or acquisition calls.

Only an injected context builder runs. Extra provider requests reserve durable
budget before transport; the original actor's ordinary traffic is unaffected.
"""
import json
import os
from pathlib import Path
import queue
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from identity_outcome_outbox import Outbox
from identity_triage_store import digest
from identity_triage_intake import normalize
from identity_triage_observer import envelope, read_config, _send
from identity_request_guard import guarded

TEMPORARY={'listing_http_error','listing_temporary_http','listing_unavailable','rate_limited',
           'lookup_busy','metadata_api_unavailable','metadata_rate_limited','metadata_lookup_busy','resolver_error',
           'tmdb_mapping_missing'}
_WEEK=7*86400
_DAY=86400
DAILY_TOTAL=60
DAILY_PROVIDER={"listing":20,"tmdb":40}
_QUEUE=queue.Queue(32)
_THREAD=None
_LOCK=threading.Lock()


class RetryBudget(Exception):pass


class RetryStore(Outbox):
    def __init__(self,directory,clock=time.time):
        self.clock=clock
        super().__init__(directory)
        with self.tx() as c:
            c.execute('create table if not exists retry_jobs(version text primary key, source text not null, observed real not null, body text not null, due real not null, expires real not null, state text not null, lease text, until real, reason text not null)')
            c.execute('create table if not exists retry_attempts(id text primary key,version text not null,started real not null,ended real,reason text)')
            c.execute('create table if not exists retry_requests(id integer primary key,attempt text not null,provider text not null,reserved real not null)')
            c.execute('create table if not exists retry_provider(name text primary key,until real not null,auth integer not null)')
            c.execute('create table if not exists retry_policy(name text primary key)')
            # One-time scheduling migration only: never reset requests, attempts,
            # expiry, authentication suspension, completed jobs or active leases.
            if c.execute('insert or ignore into retry_policy values (?)',('daily-v1',)).rowcount:
                now=self.clock()
                rows=c.execute('select version,due from retry_jobs where state="pending" and reason="retry_request_budget" and expires>? order by observed',(now,)).fetchall()
                for index,(version,due) in enumerate(rows):
                    c.execute('update retry_jobs set due=? where version=?',(min(due,now+60+index*60),version))


    def admit(self,item,sources):
        if not isinstance(item,dict) or set(item)-{'observation','listing'}:raise ValueError('retry_shape')
        from tracker_metadata import valid_listing_url
        if 'listing' in item and not valid_listing_url(item['listing']):raise ValueError('retry_listing')
        body=item['observation'];self.validate(body);r=normalize(body,sources,'outcome')
        if r.get('reason'):return 'quarantine'
        version=digest([r['release'],r['metadata']])
        source=r['release'];observed=r['time']
        reason=body['data']['outcome']['reason'];now=self.clock()
        with self.tx() as c:
            if c.execute('select 1 from retry_jobs where source=? and observed>?',(source,observed)).fetchone():return 'stale'
            c.execute('update retry_jobs set state="done",reason="superseded",lease=NULL where source=? and version!=? and observed<=?',(source,version,observed))
            if reason not in TEMPORARY:
                c.execute('update retry_jobs set state="done",reason=?,lease=NULL where version=?',(reason,version));return 'not_retryable'
            if c.execute('select 1 from retry_jobs where version=?',(version,)).fetchone():return 'duplicate'
            if c.execute('select count(*) from retry_jobs').fetchone()[0]>=10000:raise RetryBudget('retry_capacity')
            c.execute('insert into retry_jobs values (?,?,?,?,?,?,"pending",NULL,NULL,?)',(version,source,observed,json.dumps(item),now+900,now+_WEEK,reason))
        return 'admitted'

    def _review(self,c,version,raw,reason):
        event=json.loads(raw)['observation']
        event['id']=str(uuid.uuid4());event['timestamp']=datetime.fromtimestamp(self.clock(),timezone.utc).isoformat()
        event['data']['outcome']={'status':'needs_review','category':'unknown_movie','reason':'retry_exhausted'}
        encoded=self.validate(event)
        c.execute('insert into pending values(?,?,?,0,?)',(event['id'],encoded,self.clock(),self.clock()))
        self.count(c,'persisted')
        c.execute('update retry_jobs set state="review",reason=?,lease=NULL where version=?',(reason,version))

    def lease(self):
        now=self.clock()
        with self.tx() as c:
            for version,raw in c.execute('select version,body from retry_jobs where state in ("pending","leased") and expires<=?',(now,)).fetchall():
                self._review(c,version,raw,'retry_expired')
            rows=c.execute('select version,body from retry_jobs where expires>? and ((state="pending" and due<=?) or (state="leased" and until<=?)) order by due limit 20',(now,now,now)).fetchall()
            for version,raw in rows:
                used=c.execute('select count(*) from retry_attempts where version=? and started>? and not (coalesce(reason,"") in ("retry_request_budget","retry_provider_cooldown") and not exists (select 1 from retry_requests r where r.attempt=retry_attempts.id))',(version,now-86400)).fetchone()[0]
                if used>=3:
                    self._review(c,version,raw,'retry_attempt_limit');continue
                token=uuid.uuid4().hex
                c.execute('insert into retry_attempts values (?,?,?,NULL,NULL)',(token,version,now))
                c.execute('update retry_jobs set state="leased",lease=?,until=? where version=?',(token,now+120,version))
                return {'version':version,'token':token,'item':json.loads(raw),'number':used+1}

    def reserve_request(self,lease,provider):
        if provider not in ('listing','tmdb'):raise RetryBudget('provider_invalid')
        now=self.clock()
        with self.tx() as c:
            job=c.execute('select 1 from retry_jobs where lease=? and until>? and state="leased"',(lease['token'],now)).fetchone()
            if not job:raise RetryBudget('stale_retry')
            total=c.execute('select count(*) from retry_requests where reserved>?',(now-_DAY,)).fetchone()[0]
            used=c.execute('select count(*) from retry_requests where reserved>? and provider=?',(now-_DAY,provider)).fetchone()[0]
            p=c.execute('select until,auth from retry_provider where name=?',(provider,)).fetchone()
            if p and p[1]:raise RetryBudget('retry_provider_auth')
            if p and p[0]>now:raise RetryBudget('retry_provider_cooldown')
            if total>=DAILY_TOTAL or used>=DAILY_PROVIDER[provider]:raise RetryBudget('retry_request_budget')
            c.execute('insert into retry_requests values(NULL,?,?,?)',(lease['token'],provider,now))
            c.execute('insert into retry_provider values(?,?,0) on conflict(name) do update set until=excluded.until',(provider,now+1))

    def cooldown(self,provider,seconds,auth):
        with self.tx() as c:
            c.execute('insert into retry_provider values(?,?,?) on conflict(name) do update set until=max(until,excluded.until),auth=max(auth,excluded.auth)',(provider,self.clock()+max(0,seconds),int(auth)))

    def finish(self,lease,reason,outcome=None):
        encoded=self.validate(outcome) if outcome else None
        with self.tx() as c:
            row=c.execute('select lease,until from retry_jobs where version=?',(lease['version'],)).fetchone()
            if not row or row[0]!=lease['token'] or row[1]<=self.clock():raise RetryBudget('stale_retry')
            temporary=reason in TEMPORARY or reason in ('retry_request_budget','retry_provider_cooldown')
            state='pending' if temporary and lease['number']<3 else 'review' if temporary else 'done'
            if reason=='retry_provider_auth':state='review'
            due=self.clock()+(3600 if lease['number']==1 else 21600)
            if temporary:
                due=max(due,c.execute('select coalesce(max(until),0) from retry_provider').fetchone()[0])
            if encoded:
                c.execute('insert or ignore into pending values(?,?,?,0,?)',(outcome['id'],encoded,self.clock(),self.clock()))
                self.count(c,'persisted')
            c.execute('update retry_jobs set state=?,due=?,lease=NULL,reason=? where version=?',(state,due,reason,lease['version']))
            c.execute('update retry_attempts set ended=?,reason=? where id=?',(self.clock(),reason,lease['token']))

    def defer(self,lease,reason,provider):
        """Budget/cooldown waits are not failed lookups; retain audit history."""
        now=self.clock()
        with self.tx() as c:
            row=c.execute('select lease,until,expires from retry_jobs where version=?',(lease['version'],)).fetchone()
            if not row or row[0]!=lease['token'] or row[1]<=now:raise RetryBudget('stale_retry')
            due=now+1
            for query,args,cap in (
                ('select reserved from retry_requests where reserved>? order by reserved',(now-_DAY,),DAILY_TOTAL),
                ('select reserved from retry_requests where reserved>? and provider=? order by reserved',(now-_DAY,provider),DAILY_PROVIDER[provider])):
                times=[r[0] for r in c.execute(query,args)]
                if len(times)>=cap:due=max(due,times[len(times)-cap]+_DAY+1)
            p=c.execute('select until from retry_provider where name=?',(provider,)).fetchone()
            if p:due=max(due,p[0])
            c.execute('update retry_jobs set state="pending",due=?,lease=NULL,until=NULL,reason=? where version=?',(min(due,row[2]),reason,lease['version']))
            c.execute('update retry_attempts set ended=?,reason=? where id=?',(now,reason,lease['token']))

    def summary(self):
        with self.tx() as c:
            return {'states':dict(c.execute('select state,count(*) from retry_jobs group by state')),
                    'requests_rolling_day':c.execute('select count(*) from retry_requests where reserved>?',(self.clock()-_DAY,)).fetchone()[0],
                    'oldest_pending_age_seconds':max(0,self.clock()-c.execute('select coalesce(min(observed),?) from retry_jobs where state in ("pending","leased")',(self.clock(),)).fetchone()[0]),
                    'request_cap_rolling_day':DAILY_TOTAL,'per_provider_caps':DAILY_PROVIDER,
                    'recoveries':c.execute('select count(*) from retry_attempts where reason="external_id_verified"').fetchone()[0],
                    'reasons':dict(c.execute('select reason,count(*) from retry_jobs group by reason'))}


class Gate:
    def __init__(self,store,lease):self.store=store;self.lease=lease;self.blocked=None;self.provider=None
    def reserve(self,provider):
        self.provider=provider
        time.sleep(1.05)
        try:self.store.reserve_request(self.lease,provider)
        except RetryBudget as exc:self.blocked=str(exc);raise
    def cooldown(self,provider,seconds,auth):self.store.cooldown(provider,seconds,auth)


def run_one(store,resolve):
    lease=store.lease()
    if not lease:return False
    item=lease['item'];event=item['observation'];payload={'event':'action.rejected','data':dict(event['data'])}
    payload['data']['release']=dict(event['data']['release'])
    if item.get('listing'):payload['data']['release']['info_url']=item['listing']
    payload['data']['result']={'rejections':['Unknown Movie']}
    gate=Gate(store,lease)
    with guarded(gate):context=resolve(payload)
    if gate.blocked in ('retry_request_budget','retry_provider_cooldown'):
        store.defer(lease,gate.blocked,gate.provider)
        return True
    if gate.blocked:
        context={'meta':{'identity_status':'needs_review' if lease['number']>=3 else 'unresolved',
                         'identity_reason':'metadata_auth_failure' if gate.blocked=='retry_provider_auth' else 'retry_exhausted' if lease['number']>=3 else 'metadata_api_unavailable'},'category':'unknown_movie'}
    reason=(context.get('identity_observation') or {}).get('reason') or (context.get('meta') or {}).get('identity_reason','other')
    indexer=event['data']['indexer']
    outcome=envelope(payload,context,{indexer['identifier']:indexer['name']})
    outcome['id']=str(uuid.UUID(lease['token']))
    if lease['number']>=3 and (reason in TEMPORARY or gate.blocked):
        outcome['data']['outcome'].update(status='needs_review',reason='retry_exhausted')
    store.finish(lease,gate.blocked or reason,outcome)  # commit outcome and completion atomically
    return True


def submit(payload,context):
    if os.environ.get('MOVIE_INTEL_IDENTITY_RETRY_MODE','off') not in ('shadow','active'):return
    try:
        cfg=read_config(os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG'])
        item={'observation':envelope(payload,context,cfg['sources'])}
        release=(payload.get('data') or {}).get('release') or {}
        from tracker_metadata import valid_listing_url
        if valid_listing_url(release.get('info_url')):item['listing']=release['info_url']
        _QUEUE.put_nowait(item)
    except queue.Full:print('identity_retry queue_full',flush=True)
    except Exception:print('identity_retry admission_failed',flush=True)


def start(resolve):
    global _THREAD
    if os.environ.get('MOVIE_INTEL_IDENTITY_RETRY_MODE','off') not in ('shadow','active'):return
    def work():
        store=None;last=0
        while True:
            try:
                if store is None:store=RetryStore(Path.home().resolve()/'.local/state/movie-identity-retries')
                try:item=_QUEUE.get(timeout=1)
                except queue.Empty:item=None
                if item is not None:
                    try:store.admit(item,read_config(os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG'])['sources'])
                    except Exception:
                        print('identity_retry persistence_failed',flush=True)
                        try:_QUEUE.put_nowait(item)
                        except queue.Full:print('identity_retry queue_full',flush=True)
                    finally:_QUEUE.task_done()
                if os.environ.get('MOVIE_INTEL_IDENTITY_RETRY_MODE')=='active':run_one(store,resolve)
                pending=store.next()
                if pending:
                    key,body,attempts=pending
                    try:
                        _send(read_config(os.environ['MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG']),body);store.ack(key)
                    except Exception:store.failed(key,attempts)
                if time.monotonic()-last>60:
                    print('identity_retry summary '+json.dumps(store.summary(),sort_keys=True),flush=True);last=time.monotonic()
            except Exception:print('identity_retry stopped_safe',flush=True);time.sleep(5)
    with _LOCK:
        if _THREAD is None or not _THREAD.is_alive():
            _THREAD=threading.Thread(target=work,daemon=True,name='identity-metadata-retry');_THREAD.start()
