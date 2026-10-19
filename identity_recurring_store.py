"""New, independent rolling budget epoch. Never opens or resets the old pilot.

Each material version is researched once, including interrupted/failed attempts.
Unknown requests count. Only materially new evidence can enqueue it again.
"""
import json
import uuid
from identity_research_store import ResearchStore, Stop
from identity_research_provider import validate_case
from identity_triage_store import digest

WEEK=7*86400

class RecurringStore(ResearchStore):
    filename='recurring-v1.sqlite3'

    def admit(self,item):
        item=validate_case(item)
        if item['seed']:raise ValueError('historical_seed_not_reimported')
        material={k:v for k,v in item.items() if k!='observed_at'}
        # A repeated observation is freshness, not newly discovered evidence.
        material['provenance']=[{**p,'observed_at':1} for p in item['provenance']]
        version=digest(material)
        with self.tx() as c:
            if c.execute('select 1 from evidence where version=?',(version,)).fetchone():return 'duplicate'
            if c.execute('select count(*) from evidence').fetchone()[0]>=10000:raise Stop('epoch_capacity')
            c.execute('insert or ignore into admissions values (?,0)',(item['case_id'],))
            c.execute('insert into evidence values(?,?,?,?)',(version,item['case_id'],json.dumps(material,sort_keys=True),item['observed_at']))
            c.execute('insert into jobs values(?,?,"queued",?,NULL,NULL,0) on conflict(case_id) do update set version=excluded.version,status="queued",due=excluded.due,lease=NULL,until=NULL,failures=0',(item['case_id'],version,self.clock()))
        return 'admitted'

    def reconcile(self,items):
        """Complete authenticated snapshot retires cases that are no longer eligible."""
        current={x['case_id'] for x in items}
        with self.tx() as c:
            for row in c.execute('select case_id from jobs where status="queued"').fetchall():
                if row['case_id'] not in current:
                    c.execute('update jobs set status="awaiting_evidence" where case_id=?',(row['case_id'],))

    def start(self):
        now=self.clock();run=uuid.uuid4().hex
        with self.tx() as c:
            p=c.execute('select * from pilot').fetchone()
            if p['closed'] or p['until']>now:raise Stop('epoch_closed_or_busy')
            c.execute('insert into runs values(?,?,?,0,NULL)',(run,now,now+540))
            c.execute('update pilot set active_run=?,until=?',(run,now+600))
        return run

    def lease(self,run):
        now=self.clock()
        with self.tx() as c:
            self._run(c,run)
            # An interrupted attempt has an unknown outcome; do not rerun it.
            c.execute('update jobs set status="awaiting_evidence",lease=NULL where status="leased" and until<=?',(now,))
            if c.execute('select count(*) from attempts where started>?',(now-WEEK,)).fetchone()[0]>=5:raise Stop('weekly_case_budget')
            if c.execute('select count(*) from requests where reserved>?',(now-WEEK,)).fetchone()[0]>=25:raise Stop('weekly_request_budget')
            p=c.execute('select * from provider').fetchone()
            if p['suspended']:raise Stop('provider_suspended')
            if p['not_before']>now:raise Stop('provider_cooldown')
            row=c.execute('select j.*,e.material from jobs j join evidence e on e.version=j.version where j.status="queued" and j.due<=? order by j.due,j.case_id limit 1',(now,)).fetchone()
            if not row:return None
            token=uuid.uuid4().hex
            c.execute('update jobs set status="leased",lease=?,until=? where case_id=?',(token,now+600,row['case_id']))
            c.execute('update runs set cases=cases+1 where id=?',(run,))
            c.execute('insert into attempts values(?,?,?,?,NULL,NULL)',(token,run,row['version'],now))
            return dict(row)|{'token':token,'item':json.loads(row['material'])}

    def reserve(self,run,lease,key):
        now=self.clock()
        with self.tx() as c:
            self._run(c,run)
            j=c.execute('select * from jobs where lease=? and status="leased"',(lease,)).fetchone()
            a=c.execute('select run from attempts where id=?',(lease,)).fetchone()
            if not j or j['until']<=now or not a or a['run']!=run:raise Stop('stale_lease')
            p=c.execute('select * from provider').fetchone()
            if p['suspended']:raise Stop('provider_suspended')
            cached=c.execute('select result from cache where key=? and expires>?',(key,now)).fetchone()
            if cached:return None,json.loads(cached['result'])
            if p['not_before']>now:raise Stop('provider_cooldown')
            if c.execute('select count(*) from requests where reserved>?',(now-WEEK,)).fetchone()[0]>=25:raise Stop('weekly_request_budget')
            if c.execute('select count(*) from requests r join attempts a on a.id=r.attempt where a.version=?',(j['version'],)).fetchone()[0]>=5:raise Stop('case_request_budget')
            cursor=c.execute('insert into requests values(NULL,?,?,"tmdb",?,?,NULL)',(run,lease,key,now))
            c.execute('update provider set not_before=?',(now+1,))
            return cursor.lastrowid,None

    def finish(self,lease,result):
        # Preserve proposal/history but disable the pilot's automatic same-version retry.
        status=super().finish(lease,result)
        with self.tx() as c:
            c.execute('update jobs set status="awaiting_evidence" where case_id=? and version=? and status!="leased"',(lease['case_id'],lease['version']))
        return status

    def summary(self):
        with self.tx() as c:
            return {'epoch':'recurring-v1','weekly_case_cap':5,'weekly_request_cap':25,'per_version_request_cap':5,
                    'cases_rolling_week':c.execute('select count(*) from attempts where started>?',(self.clock()-WEEK,)).fetchone()[0],
                    'requests_rolling_week':c.execute('select count(*) from requests where reserved>?',(self.clock()-WEEK,)).fetchone()[0],
                    'requests_unknown':c.execute('select count(*) from requests where result is null').fetchone()[0],
                    'states':dict(c.execute('select status,count(*) from jobs group by status')),
                    'proposals':c.execute('select count(*) from proposals').fetchone()[0],
                    'provider_suspended':bool(c.execute('select suspended from provider').fetchone()[0])}
