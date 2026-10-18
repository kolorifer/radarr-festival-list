"""Synthetic-only Stage2 gates; external transport is always fake in this suite."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from identity_research_store import ResearchStore, Stop, retry_delay
from identity_research_provider import Provider, projection, route, validate_case, retry_after
from identity_triage_worker import investigate, read_config, read_manifest
from identity_triage_store import Store, digest
from identity_triage_service import storage_reason
from identity_triage_intake import normalize
from test_identity_triage import payload


def case(i=1,seed=True):
    return {'case_id':'synthetic-'+str(i),'seed':seed,'eligibility':'seed_missing_crosswalk' if seed else 'explicit_unresolved',
            'facts':{'title':'Synthetic Movie','year':2025,'imdb':'tt1234567','tmdb':None,
                     'variants':['Synthetic Movie'],'contradictions':['missing_crosswalk'],'director':None,'runtime':None},
            'provenance':[{'source':'stage1_seed' if seed else 'stage1_outcome','digest':'a'*64,'observed_at':1000}],
            'historical_candidates':[],'observed_at':1000}


def movie(i=123,title='Synthetic Movie',date='2025-01-01',imdb=None):
    return {'id':i,'title':title,'original_title':title,'release_date':date,'runtime':100,
            'external_ids':{'imdb_id':imdb},'credits':{'crew':[]},'alternative_titles':{'titles':[]},
            'translations':{'translations':[]},'release_dates':{'results':[]}}


class Response:
    def __init__(self,data=None,status=200,headers=None):
        self.status=status;self.headers={'Content-Type':'application/json'}| (headers or {})
        self.body=io.BytesIO(json.dumps(data).encode())
    def getheader(self,key,default=None):return self.headers.get(key,default)
    def read(self,n):return self.body.read(n)


class Transport:
    def __init__(self,responses):self.responses=iter(responses);self.calls=[];self.closed=False
    def request(self,*args,**kwargs):self.calls.append((args,kwargs))
    def getresponse(self):
        r=next(self.responses)
        if isinstance(r,Exception):raise r
        return r
    def close(self):self.closed=True


class Base(unittest.TestCase):
    def setUp(self):
        previous_umask=os.umask(0o077);self.addCleanup(os.umask,previous_umask)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.now=10000
        self.store=ResearchStore(self.root/'research',clock=lambda:self.now)
    def ready(self,item=None):
        self.store.admit(item or case());run=self.store.start();return run,self.store.lease(run)
    def provider(self,run,responses):
        t=Transport(responses)
        def advance(n):self.now+=n
        return Provider(self.store,run,t,'synthetic-token-'+'x'*20,clock=lambda:self.now,sleep=advance),t
    def sql(self,q):
        with self.store.tx() as c:return [tuple(r) for r in c.execute(q)]


class StoreTests(Base):
    def test_schema_idempotence_and_separate_stage1(self):
        stage=Store(self.root/'stage1')
        before=stage.path.read_bytes()
        ResearchStore(self.store.directory)
        self.assertEqual(before,stage.path.read_bytes())
        with stage.connection() as c:
            with self.assertRaises(sqlite3.IntegrityError):c.execute('insert into cases values ("x","x","queued",1)')
        self.assertEqual(self.sql('pragma user_version'),[(1,)])
        with self.store.tx() as c:c.execute('pragma user_version=2')
        with self.assertRaises(ValueError):ResearchStore(self.store.directory)

    def test_material_dedup_and_new_evidence_reopens_without_rewriting(self):
        item=case();self.assertEqual(self.store.admit(item),'admitted');item['observed_at']+=1
        self.assertEqual(self.store.admit(item),'duplicate')
        run=self.store.start();lease=self.store.lease(run)
        self.store.finish(lease,{'reason':'missing_crosswalk'})
        self.assertEqual(self.store.finish(lease,{'reason':'missing_crosswalk'}),'duplicate')
        item['facts']['year']=2024;self.store.admit(item)
        self.assertEqual(self.sql('select count(*) from evidence'),[(2,)])
        self.assertEqual(self.sql('select status from jobs'),[('queued',)])
        self.assertEqual(self.sql('select count(*) from proposals'),[(1,)])

    def test_old_evidence_does_not_revert_latest_or_reopen(self):
        item=case();self.store.admit(item);new=deepcopy(item);new['facts']['year']=2024
        self.store.admit(new);version=self.sql('select version from jobs')
        self.store.admit(item);self.assertEqual(version,self.sql('select version from jobs'))

    def test_case_caps_and_duplicate_does_not_consume(self):
        for i in range(4):self.store.admit(case(i))
        with self.assertRaises(Stop):self.store.admit(case(5))
        for i in range(10):self.store.admit(case(i+10,False))
        with self.assertRaises(Stop):self.store.admit(case(99,False))
        self.assertEqual(self.store.admit(case(0)),'duplicate')
        self.assertEqual(self.store.summary()['admissions'],14)

    def test_crash_expiry_fencing_and_single_run(self):
        run,lease=self.ready()
        with self.assertRaises(Stop):self.store.start()
        self.now+=601;run2=self.store.start();lease2=self.store.lease(run2)
        self.assertNotEqual(lease['token'],lease2['token'])
        with self.assertRaises(Stop):self.store.finish(lease,{'reason':'missing_crosswalk'})
        self.store.finish(lease2,{'reason':'missing_crosswalk'})

    def test_new_evidence_fences_old_worker(self):
        run,lease=self.ready();new=case();new['facts']['year']=2024;self.store.admit(new)
        with self.assertRaises(Stop):self.store.reserve(run,lease['token'],'key')
        with self.assertRaises(Stop):self.store.finish(lease,{'reason':'missing_crosswalk'})

    def test_hard_request_budget_survives_restarts_and_crashed_reservations(self):
        run,lease=self.ready()
        for i in range(50):self.now+=2;self.store.reserve(run,lease['token'],str(i))
        with self.assertRaises(Stop):self.store.reserve(run,lease['token'],'overflow')
        self.store.end(run);self.now+=601
        self.store=ResearchStore(self.store.directory,clock=lambda:self.now)
        run=self.store.start();lease=self.store.lease(run)
        for i in range(50):self.now+=2;self.store.reserve(run,lease['token'],'second'+str(i))
        self.store.end(run)
        with self.assertRaises(Stop):self.store.start()
        self.assertEqual(self.store.summary()['requests_reserved'],100)
        self.assertEqual(self.store.summary()['requests_completed'],0)

    def test_run_case_cap(self):
        for i in range(4):self.store.admit(case(i))
        for i in range(10):self.store.admit(case(i+10,False))
        run=self.store.start()
        for _ in range(10):self.store.finish(self.store.lease(run),{'reason':'missing_crosswalk'})
        with self.assertRaises(Stop):self.store.lease(run)

    def test_request_cooldown_cache_and_auth_are_persistent(self):
        run,lease=self.ready();req,_=self.store.reserve(run,lease['token'],'key')
        with self.assertRaises(Stop):self.store.reserve(run,lease['token'],'other')
        self.store.record(req,'key',{'reason':'ok','data':{}})
        self.assertEqual(self.store.reserve(run,lease['token'],'key'),(None,{'reason':'ok','data':{}}))
        self.now+=86401
        # Expiry also expires the run: it cannot be used to bypass any other gate.
        with self.assertRaises(Stop):self.store.reserve(run,lease['token'],'key')

    def test_private_permissions_symlink_and_busy(self):
        self.store.path.chmod(0o644)
        with self.assertRaises(ValueError):self.store.summary()
        self.store.path.chmod(0o600)
        with self.store.tx() as c:
            with self.assertRaises(sqlite3.OperationalError):self.store.admit(case())
        self.assertEqual(self.store.summary()['admissions'],0)
        self.store.path.rename(self.root/'elsewhere');self.store.path.symlink_to(self.root/'elsewhere')
        with self.assertRaises(ValueError):ResearchStore(self.store.directory)

    def test_full_disk_reservation_failure_prevents_transport(self):
        run,lease=self.ready();p,t=self.provider(run,[])
        with patch.object(self.store,'reserve',side_effect=sqlite3.OperationalError('disk full')):
            with self.assertRaises(sqlite3.OperationalError):p.get(lease,'find','tt1234567')
        self.assertEqual(t.calls,[])

    def test_closed_pilot_cannot_restart(self):
        run,_=self.ready();self.store.end(run,close=True)
        with self.assertRaises(Stop):self.store.start()
        self.assertTrue(self.store.summary()['closed'])

    def test_concurrent_dedup(self):
        with ThreadPoolExecutor(max_workers=4) as p:results=list(p.map(lambda _:self.store.admit(case()),range(20)))
        self.assertEqual(results.count('admitted'),1)
        self.assertEqual(self.store.summary()['admissions'],1)


class ProviderTests(Base):
    def test_get_only_fixed_routes_and_no_arbitrary_urls(self):
        for kind,value in [('url','https://evil.invalid'),('details',True),('find','tt1'),('movie_search','https://evil.invalid'),('movie_search','<script>')]:
            with self.assertRaises(ValueError):route(kind,value)
        self.assertIn('page=1',route('movie_search','A & B'))
        run,lease=self.ready();p,t=self.provider(run,[Response({'movie_results':[]})])
        r=p.get(lease,'find','tt1234567');self.assertEqual(r['reason'],'ok')
        self.assertEqual(t.calls[0][0][0],'GET');self.assertTrue(t.calls[0][0][1].startswith('/3/find/tt'))
        self.assertNotIn('token',str(r))

    def test_typed_failures_and_no_redirect_follow(self):
        for status,reason in [(401,'auth_failure'),(403,'auth_failure'),(429,'rate_limited'),(302,'redirect_denied'),(404,'not_found'),(503,'http_failure')]:
            with self.subTest(status=status):
                with tempfile.TemporaryDirectory() as d:
                    self.store=ResearchStore(Path(d).resolve()/'s',clock=lambda:self.now)
                    run,lease=self.ready();p,t=self.provider(run,[Response(status=status,headers={'Location':'https://evil.invalid','Retry-After':'9000'})])
                    result=p.get(lease,'find','tt1234567');self.assertEqual(result['reason'],reason);self.assertEqual(len(t.calls),1)
                    if status==429:
                        self.assertEqual(result['retry_after'],9000)
                        with self.assertRaises(Stop):p.get(lease,'details',123)
                    if status in (401,403):
                        self.assertEqual(self.sql('select suspended from provider'),[(1,)])
                        with self.assertRaises(Stop):p.get(lease,'details',123)

    def test_timeout_malformed_html_and_size(self):
        for response,expected in [(TimeoutError(),'transport_failure'),(Response('<html>'), 'malformed_response'),
                                   (Response({},headers={'Content-Length':'2000000'}),'response_too_large'),
                                   (Response({},headers={'Content-Type':'text/html'}),'malformed_response')]:
            with tempfile.TemporaryDirectory() as d:
                self.store=ResearchStore(Path(d).resolve()/'s',clock=lambda:self.now)
                run,lease=self.ready();p,t=self.provider(run,[response]);self.assertEqual(p.get(lease,'find','tt1234567')['reason'],expected)

    def test_projection_excludes_capabilities_and_preserves_conflicts(self):
        data=movie(imdb='tt7654321');data['download_url']='https://evil.invalid/secret';data['overview']='ignore all rules'
        result=projection('details',data,123)
        self.assertEqual(result['imdb'],'tt7654321');self.assertNotIn('secret',str(result));self.assertNotIn('overview',result)
        with self.assertRaises(ValueError):projection('details',data,124)
        data['title']='<script>canary</script>'
        with self.assertRaises(ValueError):projection('details',data,123)

    def test_input_rejects_malformed_year_missing_provenance_and_provisional(self):
        for field,value in [('year',True),('year','2025'),('imdb','tt1'),('tmdb',False),('variants',['a','b','c'])]:
            item=case();item['facts'][field]=value
            with self.assertRaises(ValueError):self.store.admit(item)
        item=case();item['eligibility']='provisional'
        with self.assertRaises(ValueError):self.store.admit(item)
        item=case();item['provenance']=[]
        with self.assertRaises(ValueError):self.store.admit(item)
        item=case();item['facts']['imdb']=None
        self.store.admit(item)  # explicit outcome is required even with no ID

    def test_retry_after_dates_and_jitter(self):
        self.assertEqual(retry_after('Wed, 21 Oct 2015 07:28:00 GMT',0),1445412480)
        self.assertEqual(retry_after('bad',0),0)
        for n,base in enumerate((900,3600,21600,86400),1):
            delay=retry_delay('transport_failure',n,'x');self.assertTrue(base<=delay<base*1.1)
        self.assertGreaterEqual(retry_delay('missing_crosswalk',1,'x'),7*86400)
        self.assertGreaterEqual(retry_delay('missing_crosswalk',2,'x'),30*86400)
        self.assertEqual(retry_delay('rate_limited',1,'x',999999),999999)


class InvestigationTests(Base):
    def test_missing_crosswalk_candidate_is_only_proposal_and_conflicts_retained(self):
        item=case();item['historical_candidates']=[123];item['facts']['director']='Expected Director';item['facts']['runtime']=99
        run,lease=self.ready(item)
        p,t=self.provider(run,[Response({'movie_results':[]}),Response({'page':1,'results':[]}),Response({'page':1,'results':[]}),Response(movie(date='2024-01-01'))])
        result=investigate(lease,p);self.store.finish(lease,result)
        self.assertEqual(result['reason'],'candidate_review');self.assertTrue(result['missing_crosswalk']);self.assertFalse(result['runtime_correction'])
        self.assertEqual(set(result['candidates'][0]['contradictions']),{'missing_crosswalk','year_conflict','runtime_conflict'})
        self.assertEqual(result['candidates'][0]['support_gaps'],['director_missing'])
        self.assertEqual(self.sql('select status from proposals'),[('needs_review',)])
        self.assertEqual(self.sql('select status from jobs'),[('awaiting_evidence',)])

    def test_tv_only_is_not_movie_or_catalog_absence(self):
        run,lease=self.ready();p,t=self.provider(run,[Response({'movie_results':[],'tv_results':[{'id':123,'name':'Synthetic Movie','first_air_date':'2025-01-01'}]}),Response({'page':1,'results':[]}),Response({'page':1,'results':[]})])
        r=investigate(lease,p);self.assertEqual(r['reason'],'tv_only');self.assertFalse(r['catalog_absence_proven']);self.assertEqual(r['candidates'],[])

    def test_ambiguous_remake_candidates_never_popularity_choice(self):
        item=case();item['facts']['variants']=['Synthetic Movie','Evidenced Alias']
        rows=[movie(i) for i in range(1,6)]
        run,lease=self.ready(item)
        responses=[Response({'movie_results':[]}),Response({'page':1,'results':rows}),Response({'page':1,'results':[]}),Response({'page':1,'results':[]}),Response({'page':1,'results':[]})]+[Response(movie(i,date='1999-01-01')) for i in range(1,4)]
        p,t=self.provider(run,responses);r=investigate(lease,p)
        self.assertEqual(len(r['candidates']),3);self.assertTrue(r['detail_limit_reached']);self.assertEqual(len(t.calls),8)
        self.assertTrue(all('year_conflict' in c['contradictions'] for c in r['candidates']))

    def test_conflicting_id_and_multiple_crosswalks_block_resolution(self):
        run,lease=self.ready();p,t=self.provider(run,[Response({'movie_results':[movie(1),movie(2)]}),Response(movie(1,imdb='tt7654321')),Response(movie(2,imdb='tt1234567'))])
        r=investigate(lease,p);self.assertEqual(r['reason'],'identifier_conflict');self.assertFalse(r['runtime_correction']);self.assertEqual(len(t.calls),3)

    def test_unrelated_search_results_do_not_become_candidates(self):
        run,lease=self.ready();p,t=self.provider(run,[Response({'movie_results':[]}),Response({'page':1,'results':[movie(title='Nearby Popular Movie')]}),Response({'page':1,'results':[]})])
        r=investigate(lease,p);self.assertEqual(r['reason'],'missing_crosswalk');self.assertEqual(r['candidates'],[])

    def test_disabled_config_manifest_and_quarantine(self):
        config=self.root/'config.json';config.write_text('{"enabled":false,"tmdb_token":""}');config.chmod(0o600)
        self.assertFalse(read_config(config)['enabled'])
        manifest=self.root/'input.json';manifest.write_text(json.dumps([case()]));manifest.chmod(0o600)
        self.assertEqual(len(read_manifest(manifest)),1)
        manifest.write_text(json.dumps([case()]*15))
        with self.assertRaises(ValueError):read_manifest(manifest)


class StageA(unittest.TestCase):
    def setUp(self):
        previous_umask=os.umask(0o077);self.addCleanup(os.umask,previous_umask)

    def test_fixed_storage_reason_codes_never_emit_error_text(self):
        for code,expected in [(sqlite3.SQLITE_BUSY,'sqlite_busy'),(sqlite3.SQLITE_FULL,'sqlite_full'),(sqlite3.SQLITE_IOERR,'sqlite_io')]:
            exc=sqlite3.OperationalError('SECRET_PAYLOAD');exc.sqlite_errorcode=code
            self.assertEqual(storage_reason(exc),expected)
        self.assertEqual(storage_reason(PermissionError(13,'SECRET')),'permission')
        self.assertEqual(storage_reason(ValueError('SECRET')),'validation')

    def test_bounded_concurrent_import_live_metrics_recovers_without_partial_ack(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d).resolve()/'state');records=[]
            for n in range(80):
                channel='retained' if n%2 else 'release_new'
                records.append((normalize(payload(external_id=str(n)),{'example':'Example'},channel),channel))
            def ingest(pair):
                try:return s.ingest(*pair)
                except sqlite3.OperationalError as exc:
                    self.assertEqual(getattr(exc,'sqlite_errorcode',0)&255,sqlite3.SQLITE_BUSY)
                    return 'busy'
            with ThreadPoolExecutor(max_workers=6) as pool:
                jobs=[pool.submit(ingest,pair) for pair in records]
                metrics=[pool.submit(s.metrics) for _ in range(20)]
                results=[f.result() for f in jobs]
                for f in metrics:
                    try:f.result()
                    except sqlite3.OperationalError as exc:self.assertEqual(getattr(exc,'sqlite_errorcode',0)&255,sqlite3.SQLITE_BUSY)
            for pair,result in zip(records,results):
                self.assertEqual(s.ingest(*pair),'accepted' if result=='busy' else 'duplicate_event')
            self.assertEqual(s.metrics()['distinct_releases'],80)
            with s.connection() as c:self.assertEqual(c.execute('pragma quick_check').fetchone()[0],'ok')

class BoundaryTests(unittest.TestCase):
    def test_fixed_connection_never_reconnects(self):
        from identity_research_sandbox import FixedConnection
        with self.assertRaises(PermissionError):FixedConnection('api.themoviedb.org').connect()

    def test_no_unconfined_or_disabled_activation(self):
        import subprocess,sys
        with tempfile.TemporaryDirectory() as home:
            result=subprocess.run([sys.executable,'identity_triage_worker.py'],env=dict(os.environ,HOME=home),capture_output=True,text=True,timeout=15)
        self.assertNotIn('sandbox_verified',result.stdout)
        self.assertNotIn('Traceback',result.stderr)
        unit=Path('deploy/identity-research.service').read_text()
        self.assertIn('TimeoutStartSec=600',unit);self.assertIn('env -i',unit)
        self.assertNotIn('[Install]',unit);self.assertNotIn('Restart=',unit)

    def test_actual_kernel_network_denial_in_child(self):
        import subprocess,sys
        if sys.platform!='linux':self.skipTest('Linux seccomp required; real installed proof is separate')
        code='''import socket,os
from identity_research_sandbox import deny_syscalls
from identity_triage_sandbox import deny_check
# Standard libseccomp applies to this disposable process only.
deny_syscalls()
for family,kind in ((socket.AF_INET,socket.SOCK_STREAM),(socket.AF_INET6,socket.SOCK_STREAM),(socket.AF_INET,socket.SOCK_DGRAM),(socket.AF_UNIX,socket.SOCK_STREAM)):
 deny_check(lambda family=family,kind=kind:socket.socket(family,kind))
deny_check(lambda:os.chmod('.',0o755))
print('seccomp_denials_passed')
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'seccomp_denials_passed')

    def test_strict_json_duplicate_constant_and_credentials(self):
        from identity_research_provider import strict_json
        for body in ('{"id":1,"id":2}','{"id":NaN}'):
            with self.assertRaises(ValueError):strict_json(body)

class AdditionalGates(Base):
    def test_real_sqlite_full_reservation_rollback(self):
        from contextlib import contextmanager
        run,lease=self.ready();original=self.store.tx
        @contextmanager
        def limited():
            with original() as c:
                pages=c.execute('pragma page_count').fetchone()[0]
                c.execute('pragma max_page_count='+str(pages))
                yield c
        with patch.object(self.store,'tx',limited):
            with self.assertRaises(sqlite3.OperationalError) as raised:
                self.store.reserve(run,lease['token'],'x'*1_000_000)
        self.assertEqual(raised.exception.sqlite_errorcode&255,sqlite3.SQLITE_FULL)
        self.assertEqual(self.store.summary()['requests_reserved'],0)

    def test_response_absolute_deadline_and_secret_echo(self):
        import signal,time
        original=signal.setitimer
        def timer(which,seconds,interval=0):return original(which,0.03 if seconds==10 else seconds,interval)
        response=Response({})
        response.read=lambda n:time.sleep(0.2)
        run,lease=self.ready();p,t=self.provider(run,[response])
        with patch('identity_research_provider.signal.setitimer',side_effect=timer):
            self.assertEqual(p.get(lease,'find','tt1234567')['reason'],'transport_failure')
        p,t=self.provider(run,[Response({'echo':'synthetic-token-'+'x'*20})])
        result=p.get(lease,'find','tt1234567')
        self.assertEqual(result['reason'],'malformed_response')
        self.assertNotIn('synthetic-token',str(result))

    def test_cache_expiry_requires_new_reserved_request_and_closed_run_stops(self):
        run,lease=self.ready();p,t=self.provider(run,[Response({'movie_results':[]})])
        p.get(lease,'find','tt1234567')
        self.store.end(run);self.now+=86401
        run=self.store.start();lease=self.store.lease(run);p,t=self.provider(run,[Response({'movie_results':[]})])
        p.get(lease,'find','tt1234567')
        self.assertEqual(self.store.summary()['requests_reserved'],2)
        self.store.close_pilot()
        with self.assertRaises(Stop):p.get(lease,'details',123)


class EvidenceDistinctions(Base):
    def test_source_flags_and_missing_context_are_not_new_contradictions(self):
        item=case();item['historical_candidates']=[123]
        item['facts'].update(director='Expected',runtime=100,contradictions=['missing_crosswalk','runtime_conflict'])
        run,lease=self.ready(item);data=movie(date='',imdb='tt1234567');data['runtime']=0
        p,t=self.provider(run,[Response({'movie_results':[movie()]}),Response(data)])
        r=investigate(lease,p);c=r['candidates'][0]
        self.assertEqual(c['contradictions'],[])
        self.assertEqual(set(c['support_gaps']),{'director_missing','runtime_missing','release_date_missing'})
        self.assertEqual(c['source_contradictions'],['missing_crosswalk','runtime_conflict'])
        self.assertFalse(r['runtime_correction'])

    def test_different_director_is_actual_conflict_and_alias_does_not_erase_source_title(self):
        item=case();item['facts'].update(title='Original Source Title',director='Expected')
        run,lease=self.ready(item);data=movie(imdb='tt1234567');data['credits']['crew']=[{'job':'Director','name':'Different'}]
        p,t=self.provider(run,[Response({'movie_results':[movie()]}),Response(data)])
        candidate=investigate(lease,p)['candidates'][0]
        self.assertEqual(set(candidate['contradictions']),{'director_conflict','title_conflict'})
        self.assertEqual(candidate['support_gaps'],[])
