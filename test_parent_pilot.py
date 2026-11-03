"""Task8: invented data, finite external systems and local fixture processes only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ai_movie_investigator.contracts import Refusal, decode, digest, encoded, reconcile
from ai_movie_investigator.disclosure import aliases, evidence_alias
from ai_movie_investigator.history import FILENAME, History
from ai_movie_investigator.installation import RUNTIME_FILES, install_runtime
from ai_movie_investigator.parent_pilot import (FixtureModelSite, FixtureParent, FixturePermit,
    SingleResponsesTransport, run_pilot, storage_identity)
from ai_movie_investigator.pilot_fixture import make_fixture
from ai_movie_investigator.replay import NOW, packet_for
from ai_movie_investigator.research import material_for, provider_material
from ai_movie_investigator.responses_http import FixedResponsesHTTP, HTTPResult
from ai_movie_investigator.responses_replay import simulated_response
from ai_movie_investigator.weekly_ledger import ExistingWeeklyLedger, PROFILE
from identity_recurring_store import RecurringStore
from identity_research_store import Stop

ROOT = Path(__file__).resolve().parent


def reselect(parent, change):
    """New original FAKE owner selection, never a self-authenticating live grant."""
    s = decode(parent.blob, 131072)
    change(s)
    parent.blob = encoded(s)
    sha = hashlib.sha256(parent.blob).hexdigest()
    oid = hashlib.sha1(b'blob '+str(len(parent.blob)).encode()+b'\0'+parent.blob).hexdigest()
    parent.owner_event.update(blob_sha256=sha, blob_oid=oid, command='investigate-one '+sha)
    parent.repository_record.update(blob_sha256=sha,blob_oid=oid,bytes=len(parent.blob))
    return s


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='SIMULATED-task8-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.socket = patch('socket.socket', side_effect=AssertionError('network forbidden')).start()
        self.dns = patch('socket.getaddrinfo', side_effect=AssertionError('DNS forbidden')).start()
        self.addCleanup(patch.stopall)

    def fixture(self, **kwargs):
        path = self.root / ('fixture-'+str(len(list(self.root.iterdir()))))
        path.mkdir(mode=0o700)
        return make_fixture(path, **kwargs)

    def run_pilot(self, p):
        return run_pilot(p, command=p.owner_event['command'], enabled=True)

    def no_effects(self, p):
        self.assertEqual(p.catalogue.requests, [])
        self.assertEqual(p.counter.requests, [])
        self.assertEqual(p.model.requests, [])
        self.assertFalse(p.control.read())

    def result(self, p):
        return [e for e in p.history.read() if e['type']=='result'][-1]

    def response(self, p, mutate):
        body = decode(p.model.response.body, 32768)
        mutate(body)
        p.model.response = HTTPResult(200, encoded(body), p.model.response.request_id)

    def answer(self, p, mutate):
        def change(body):
            item = body['output'][-1]['content'][0]
            reply = decode(item['text'])
            mutate(reply)
            item['text'] = encoded(reply).decode()
        self.response(p, change)

    def test_fixed_entrypoint_nonempty_cited_durable_and_disabled_default(self):
        p = self.fixture()
        with self.assertRaisesRegex(Refusal,'pilot_disabled'):
            run_pilot(p,command=p.owner_event['command'])
        self.no_effects(p)
        record = self.run_pilot(p)
        result = self.result(p)
        self.assertEqual(result['status'],'supported_candidate')
        self.assertEqual(result['model_calls'],1)
        self.assertEqual(len(p.catalogue.requests),2)
        self.assertEqual(len(p.counter.requests),1)
        self.assertEqual(len(p.model.requests),1)
        self.assertEqual({c['evidence_id'] for c in result['model_result']['citations']},{'source-1','research-1'})
        self.assertEqual(record['result_hash'],digest(result))
        self.assertEqual(record['review_hash'],digest(record['review']))
        terminal = p.control.read()[-1]
        self.assertEqual(terminal['archive_hash'],digest(record))
        self.assertEqual(record['archive_identity'],storage_identity(p.history))
        self.assertEqual(p.history.read()[-1],record)
        self.assertFalse(record['real_ready'] or record['download_consent'] or record['production_identity_verified'])
        self.assertIn('SIMULATED',record['review']['text'])
        self.assertIn('one generation',record['review']['text'])
        self.assertIn('scope_changed_or_unbound',record['review']['text'])
        self.assertIn('revoked',record['review']['text'])
        self.assertFalse(record['review']['sent'] or record['review']['archived'])
        self.socket.assert_not_called(); self.dns.assert_not_called()

    def test_independently_ingested_native_torrent_and_provenance_are_preserved(self):
        p = self.fixture()
        s = decode(p.blob,131072)
        original = p.history.read()[0]['packet']
        native = p.occurrence_record['native_item']
        self.assertNotEqual(provider_material(native),provider_material(material_for(original)))
        self.assertIn('torrent_evidence',native['facts'])
        self.assertEqual(native['provenance'][0]['digest'],original['original_hash'])
        with ExistingWeeklyLedger(p.ledger_directory,clock=p.clock,profile=PROFILE).tx() as c:
            material = json.loads(c.execute('select material from evidence').fetchone()[0])
        self.assertEqual(material,provider_material(native))
        self.run_pilot(p)
        started = next(e for e in p.history.read() if e['type']=='research_started')
        self.assertEqual(started['plan']['material'],material)
        self.assertEqual(started['provider_version'],digest(material))
        self.assertNotEqual(started['provider_version'],original['binding']['version'])
        self.assertEqual(s['research_plan']['native_item'],native)

    def test_flags_subclasses_and_real_boundaries_cannot_grant_live_capability(self):
        for parent in (None,True,{},object()):
            with self.assertRaisesRegex(Refusal,'real_parent_verifier_unimplemented'):
                run_pilot(parent,enabled=True,command='invented')
        p = self.fixture()
        class Forged(FixtureParent): pass
        p.__class__ = Forged
        with self.assertRaisesRegex(Refusal,'real_parent_verifier_unimplemented'): self.run_pilot(p)
        with self.assertRaisesRegex(Refusal,'real_authorization_unimplemented'):
            FixedResponsesHTTP().post(b'{}',credential=True,project='proj_fake',timeout=1,
                                      authorization=FixturePermit('proj_fake','fake','a'*64,'local-fake'))
        self.socket.assert_not_called(); self.dns.assert_not_called()

    def test_owner_authentication_exact_original_command_and_repository_bytes(self):
        for mode in ('issuer','edited','conflict','repo','issue','command','commit','tree','path','mode','regular','oid','sha','bytes','blob'):
            with self.subTest(mode=mode):
                p = self.fixture()
                if mode=='issuer': p.owner_event['issuer']='foreign'
                elif mode=='edited': p.owner_event['edited']=True
                elif mode=='conflict': p.owner_event['conflicting_selection']=True
                elif mode in ('repo','issue','commit','tree','path'):
                    p.repository_record[mode]='foreign'
                elif mode=='command': p.owner_event['command']+=' '
                elif mode=='mode': p.repository_record['mode']='120000'
                elif mode=='regular': p.repository_record['regular']=False
                elif mode=='oid': p.repository_record['blob_oid']='a'*40
                elif mode=='sha': p.repository_record['blob_sha256']='a'*64
                elif mode=='bytes': p.repository_record['bytes']+=1
                else: p.blob+=b' '
                with self.assertRaises(Refusal): self.run_pilot(p)
                self.no_effects(p)

    def test_independent_event_delivery_release_collector_and_native_receipts_required(self):
        for key in ('event_sha256','event_id','delivery_id','collector_version','source','release_case','delivered','native_item_hash'):
            with self.subTest(key=key):
                p = self.fixture()
                p.occurrence_record['delivery_receipt'][key] = False if key=='delivered' else 'foreign'
                with self.assertRaises(Refusal): self.run_pilot(p)
                self.no_effects(p)
        for mode in ('bytes','native_delivery','native_version','native_material','decisions','eligible'):
            p = self.fixture()
            o = p.occurrence_record
            if mode=='bytes': o['original_hex']=(bytes.fromhex(o['original_hex'])+b' ').hex()
            elif mode=='native_delivery': o['native_receipt']['delivery_id']='foreign'
            elif mode=='native_version': o['native_receipt']['collector_version']='f'*64
            elif mode=='native_material': o['native_item']['facts']['torrent_evidence']['unavailable_images']=1
            elif mode=='decisions': o['decisions']=[]
            else: o['eligible_unresolved_jobs']=[]
            with self.assertRaises(Refusal): self.run_pilot(p)
            self.no_effects(p)

    def test_same_original_bytes_different_caller_delivery_label_cannot_rebind(self):
        p = self.fixture()
        old = p.history.read()[0]['packet']
        changed = copy.deepcopy(old)
        changed['binding']['occurrence']['delivery_id']='caller-selected-delivery'
        for row in changed['evidence']: row['scope']=copy.deepcopy(changed['binding'])
        new_job,_=p.history.intake(changed)
        reselect(p,lambda s:s.update(job=new_job))
        # Even allowlisting a nominated hash does not replace the independent receipt.
        p.occurrence_record['eligible_unresolved_jobs']=[new_job]
        p.occurrence_record['packet_hash']=new_job
        with self.assertRaisesRegex(Refusal,'independent_delivery_binding'): self.run_pilot(p)
        self.no_effects(p)

    def test_stale_selection_storage_and_code_change_before_effects(self):
        for mode in ('expiry','history','control','ledger','code'):
            p=self.fixture()
            if mode=='expiry': p.clock.advance(60);p.clock.advance(60)
            elif mode=='code': reselect(p,lambda s:s['reviewed_code'].update({'identity_recurring_store.py':'f'*64}))
            else:
                reselect(p,lambda s:s['storage'][mode]['file'].__setitem__(1,0))
            with self.assertRaises(Refusal): self.run_pilot(p)
            self.no_effects(p)

    def test_site_facts_and_unknown_profile_are_separate_from_selection(self):
        for key in ('profile','namespace','project','model','quote','storage'):
            p=self.fixture()
            p.site_record[key] = 'unknown'
            with self.assertRaisesRegex(Refusal,'site_facts_unverified'): self.run_pilot(p)
            self.no_effects(p)
        p=self.fixture()
        p.site_record['profile']='installed-daily-profile-UNKNOWN'
        reselect(p,lambda s:s.update(site_facts=copy.deepcopy(p.site_record)))
        with self.assertRaisesRegex(Refusal,'site_facts_unverified'): self.run_pilot(p)
        self.no_effects(p)

    def test_ledger_adapter_never_creates_migrates_admits_or_reconciles(self):
        missing=self.root/'missing-ledger';missing.mkdir(mode=0o700)
        with self.assertRaises(FileNotFoundError): ExistingWeeklyLedger(missing,clock=lambda:NOW,profile=PROFILE)
        self.assertEqual(list(missing.iterdir()),[])
        p=self.fixture()
        ledger=ExistingWeeklyLedger(p.ledger_directory,clock=p.clock,profile=PROFILE)
        for method in (lambda:ledger.admit(p.occurrence_record['native_item']),lambda:ledger.reconcile([])):
            with self.assertRaisesRegex(Refusal,'existing_ledger_only'): method()
        with ledger.tx() as c:c.execute('pragma user_version=2')
        with self.assertRaisesRegex(Refusal,'schema_unknown'):
            ExistingWeeklyLedger(p.ledger_directory,clock=p.clock,profile=PROFILE)
        with ledger.tx() as c:self.assertEqual(c.execute('pragma user_version').fetchone()[0],2)
        self.assertEqual(p.catalogue.requests,[])

    def test_ledger_schema_extension_and_material_drift_refuse(self):
        for mode in ('schema','material','version','torrent','provenance'):
            p=self.fixture()
            ledger=ExistingWeeklyLedger(p.ledger_directory,clock=p.clock,profile=PROFILE)
            with ledger.tx() as c:
                if mode=='schema':c.execute('create table unexpected(x integer)')
                else:
                    row=c.execute('select material from evidence').fetchone()
                    data=json.loads(row[0])
                    if mode=='material':data['facts']['year']=2025
                    elif mode=='torrent':data['facts'].pop('torrent_evidence')
                    elif mode=='provenance':data['provenance'][0]['digest']='a'*64
                    else:c.execute('update jobs set status="awaiting_evidence"')
                    c.execute('update evidence set material=?',(encoded(data).decode(),))
            with self.assertRaises(Refusal): self.run_pilot(p)
            self.assertFalse(p.catalogue.requests or p.counter.requests or p.model.requests)

    def test_atomic_selected_oldest_mismatch_consumes_no_foreign_attempt_or_housekeeping(self):
        p=self.fixture()
        ledger=RecurringStore(p.ledger_directory,clock=p.clock)
        native=copy.deepcopy(p.occurrence_record['native_item']);native['case_id']='outcome-'+'0'*64
        ledger.admit(native)
        with ledger.tx() as c:
            c.execute('update jobs set due=? where case_id=?',(NOW-1,native['case_id']))
            before=[tuple(r) for r in c.execute('select * from jobs order by case_id')]
        run=ledger.start()
        plan=decode(p.blob,131072)['research_plan']
        with self.assertRaisesRegex(Stop,'selected_oldest_job_changed'):
            ledger.lease(run,selected=dict(case_id=plan['binding']['case_id'],version=plan['provider_version'],material=plan['material']))
        with ledger.tx() as c:
            self.assertEqual(c.execute('select count(*) from attempts').fetchone()[0],0)
            self.assertEqual([tuple(r) for r in c.execute('select * from jobs order by case_id')],before)
            self.assertEqual(c.execute('select cases from runs where id=?',(run,)).fetchone()[0],0)
        ledger.end(run)

    def test_queue_changes_between_diagnostic_and_lease_do_not_consume_foreign_job(self):
        p=self.fixture()
        start=ExistingWeeklyLedger.start
        def race(store):
            run=start(store)
            native=copy.deepcopy(p.occurrence_record['native_item']);native['case_id']='outcome-'+'0'*64
            other=RecurringStore(p.ledger_directory,clock=p.clock);other.admit(native)
            with other.tx() as c:c.execute('update jobs set due=? where case_id=?',(NOW-1,native['case_id']))
            return run
        with patch.object(ExistingWeeklyLedger,'start',race):
            with self.assertRaisesRegex(Refusal,'shared_ledger_refused'):self.run_pilot(p)
        with RecurringStore(p.ledger_directory,clock=p.clock).tx() as c:
            self.assertEqual(c.execute('select count(*) from attempts').fetchone()[0],0)
            self.assertTrue(all(r[0]=='queued' for r in c.execute('select status from jobs')))
        self.assertFalse(p.catalogue.requests or p.model.requests)

    def test_selected_attempt_is_once_even_after_interruption_and_not_reset(self):
        p=self.fixture();ledger=RecurringStore(p.ledger_directory,clock=p.clock)
        plan=decode(p.blob,131072)['research_plan'];run=ledger.start()
        lease=ledger.lease(run,selected=dict(case_id=plan['binding']['case_id'],version=plan['provider_version'],material=plan['material']))
        with ledger.tx() as c:
            c.execute('update jobs set status="queued",until=?,lease=?',(NOW-1,lease['token']))
            before=[tuple(r) for r in c.execute('select * from jobs')]
        with self.assertRaisesRegex(Stop,'selected_version_consumed'):
            ledger.lease(run,selected=dict(case_id=plan['binding']['case_id'],version=plan['provider_version'],material=plan['material']))
        with ledger.tx() as c:
            self.assertEqual([tuple(r) for r in c.execute('select * from jobs')],before)
            self.assertEqual(c.execute('select count(*) from attempts').fetchone()[0],1)
        ledger.end(run)

    def test_selected_lease_does_not_housekeep_an_expired_foreign_attempt(self):
        p=self.fixture();ledger=RecurringStore(p.ledger_directory,clock=p.clock)
        native=copy.deepcopy(p.occurrence_record['native_item']);native['case_id']='outcome-'+'0'*64
        ledger.admit(native)
        with ledger.tx() as c:
            version=c.execute('select version from jobs where case_id=?',(native['case_id'],)).fetchone()[0]
            c.execute('insert into runs values(?,?,?,1,?)',('interrupted-run',NOW-700,NOW-160,NOW-100))
            c.execute('insert into attempts values(?,?,?,?,NULL,NULL)',('interrupted-attempt','interrupted-run',version,NOW-700))
            c.execute('update jobs set status="leased",lease=?,until=? where case_id=?',
                      ('interrupted-attempt',NOW-1,native['case_id']))
            before=tuple(c.execute('select * from jobs where case_id=?',(native['case_id'],)).fetchone())
        run=ledger.start();plan=decode(p.blob,131072)['research_plan']
        lease=ledger.lease(run,selected=dict(case_id=plan['binding']['case_id'],version=plan['provider_version'],material=plan['material']))
        self.assertEqual(lease['case_id'],plan['binding']['case_id'])
        with ledger.tx() as c:
            self.assertEqual(tuple(c.execute('select * from jobs where case_id=?',(native['case_id'],)).fetchone()),before)
            self.assertIsNone(c.execute('select ended from attempts where id="interrupted-attempt"').fetchone()[0])
        ledger.end(run)

    def test_single_request_projection_has_only_approved_facts_and_run_aliases(self):
        p=self.fixture(); captured=[]
        post=FixtureModelSite.post
        def inspect(site,body,**kwargs):captured.append(body);return post(site,body,**kwargs)
        with patch.object(FixtureModelSite,'post',inspect):self.run_pilot(p)
        s=decode(p.blob,131072);body=decode(captured[0],65536)
        data=decode(body['input'][0]['content'][0]['text'],65536)
        self.assertEqual(set(data),{'protocol','binding_hash','facts','conflicting_ids','evidence'})
        self.assertEqual(data['binding_hash'],aliases(s['run']))
        self.assertEqual(body['tools'],[]);self.assertEqual(body['service_tier'],'default')
        self.assertEqual(digest(body),s['preview_hash'])
        self.assertEqual(p.counter.requests[0]['request_hash'],digest(body))
        for value in (s['job'],p.occurrence_record['delivery_receipt']['event_id'],
            p.occurrence_record['delivery_receipt']['collector_version'],s['owner'],s['decision_hash'],
            p.occurrence_record['native_item']['case_id'],p.occurrence_record['evidence'][0]['text'],
            'source-1','research-1','torrent_evidence','provenance','decisions','delivery_id'):
            self.assertNotIn(value,captured[0].decode())
        self.assertEqual(data['evidence'][1]['candidate'],{'imdb':'tt9000127','tmdb':9000127})
        self.assertIn('contradiction',data['facts'])
        self.assertEqual(p.model.requests[0]['permit'].project,s['project'])

    def test_foreign_unreturned_original_and_cross_run_aliases_rejected(self):
        for alias in ('source-1','research-0',evidence_alias('different-run','source-1'),'evidence-foreign'):
            p=self.fixture()
            self.answer(p,lambda reply:reply['result']['citations'][0].update(evidence_id=alias))
            self.run_pilot(p)
            self.assertEqual(self.result(p)['status'],'blocked')
            self.assertEqual(self.result(p)['reason'],'pilot_citation_alias_unknown')
            self.assertEqual(len(p.model.requests),1)
        p=self.fixture();self.answer(p,lambda reply:reply.update(binding_hash=aliases('different-run')))
        self.run_pilot(p);self.assertEqual(self.result(p)['reason'],'pilot_run_alias_changed')

    def test_undisclosed_new_catalogue_facts_and_unapproved_source_block_before_count(self):
        for mode in ('runtime','title','source'):
            p=self.fixture()
            if mode=='source':reselect(p,lambda s:s['disclosure']['rows']['source-1'].update(original_hash='a'*64))
            else:
                row=p.catalogue.rows[1];body=decode(row['body'],1048576)
                body[mode]=92 if mode=='runtime' else 'Changed synthetic title';row['body']=encoded(body)
            self.run_pilot(p)
            self.assertEqual(self.result(p)['status'],'blocked')
            self.assertFalse(p.counter.requests or p.model.requests)

    def test_evidence_selection_ambiguous_missing_stale_and_foreign_block_before_model(self):
        for mode in ('duplicate','missing','foreign','six','stale'):
            p=self.fixture()
            if mode=='stale':
                # Expire only source evidence after valid research; no refresh.
                pre=SingleResponsesTransport.prepare
                def expire(t,*a,**kw):p.clock.advance(60);p.clock.advance(60);return pre(t,*a,**kw)
                ctx=patch.object(SingleResponsesTransport,'prepare',expire)
            else:
                ids={'duplicate':['source-1','source-1'],'missing':['research-0'],
                     'foreign':['foreign-source'],'six':['a','b','c','d','e','f']}[mode]
                reselect(p,lambda s:s.update(evidence_ids=ids))
                from contextlib import nullcontext
                ctx=nullcontext()
            with ctx:
                if mode=='stale':
                    with self.assertRaisesRegex(Refusal,'expired'):self.run_pilot(p)
                else:self.run_pilot(p)
            self.assertFalse(p.model.requests)

    def test_one_generation_forbids_model_lookup_or_tool_request(self):
        p=self.fixture()
        self.answer(p,lambda reply:reply.update(kind='lookup',result=None,lookups=[]))
        self.run_pilot(p)
        self.assertEqual(self.result(p)['status'],'blocked')
        self.assertEqual(self.result(p)['reason'],'pilot_one_generation_required')
        self.assertEqual(len(p.model.requests),1)

    def test_conflicting_case_remains_unresolved_and_cannot_be_promoted(self):
        for status in ('unresolved','supported_candidate'):
            p=self.fixture(conflict=True,status=status)
            record=self.run_pilot(p);result=self.result(p)
            self.assertTrue(result['reconciliation']['conflicting_ids'])
            self.assertEqual(result['status'],'unresolved' if status=='unresolved' else 'blocked')
            self.assertEqual(len(p.model.requests),1)
            self.assertFalse(record['production_identity_verified'] or record['download_consent'])

    def test_skip_completed_and_revocation_history_cannot_be_omitted(self):
        for mode in ('skip','review','omitted'):
            p=self.fixture();old=p.history.read()[0]['packet'];new=copy.deepcopy(old)
            if mode=='skip':new['decisions'][0].update(revoked_at=None,revision=3)
            elif mode=='review':new['decisions'][1].update(scope=copy.deepcopy(new['binding']),revision=2)
            else:new['decisions']=[]
            if mode in ('skip','omitted'):
                with self.assertRaisesRegex(Refusal,'rollback|omitted'):p.history.intake(new)
            else:
                job,_=p.history.intake(new);reselect(p,lambda s:s.update(job=job))
                with self.assertRaises(Refusal):self.run_pilot(p)
                self.no_effects(p)

    def test_retirement_before_research_after_response_and_before_final_commit(self):
        for when in ('before','after_response','final'):
            p=self.fixture();s=decode(p.blob,131072)
            def retire():
                with p.history.transaction(write=True) as (_,append):
                    append(dict(type='research_revoked',at=p.clock(),job=s['job'],plan_hash=digest(s['research_plan'])))
            if when=='before':
                retire()
                with self.assertRaisesRegex(Refusal,'research_plan_revoked'):self.run_pilot(p)
                self.no_effects(p)
                continue
            if when=='after_response':
                post=FixtureModelSite.post
                def retired(site,*a,**kw):
                    response=post(site,*a,**kw);retire();return response
                ctx=patch.object(FixtureModelSite,'post',retired)
            else:
                record=History.record
                def retired(h,event,**kw):
                    if event['type']=='result' and event.get('model_result'):retire()
                    return record(h,event,**kw)
                ctx=patch.object(History,'record',retired)
            with ctx:
                with self.assertRaisesRegex(Refusal,'research_plan_revoked'):self.run_pilot(p)
            self.assertFalse(any(e['type']=='result' and e['status']=='supported_candidate' for e in p.history.read()))
            self.assertEqual(len(p.model.requests),1)
            self.assertTrue(any(e['type']=='pilot_model_settled' for e in p.control.read()))
            with self.assertRaisesRegex(Refusal,'revoked|superseded'):self.run_pilot(p)
            self.assertEqual(len(p.model.requests),1)

    def test_retirement_during_research_prevents_next_get(self):
        p=self.fixture();s=decode(p.blob,131072)
        from ai_movie_investigator.research import FixtureConnection
        get=FixtureConnection.getresponse
        def retire(connection):
            response=get(connection)
            with p.history.transaction(write=True) as (_,append):
                append(dict(type='research_revoked',at=p.clock(),job=s['job'],plan_hash=digest(s['research_plan'])))
            return response
        with patch.object(FixtureConnection,'getresponse',retire):
            with self.assertRaisesRegex(Refusal,'research_plan_revoked'):self.run_pilot(p)
        self.assertEqual(len(p.catalogue.requests),1)
        self.assertFalse(p.model.requests)

    def test_owner_selection_and_independent_receipt_changes_during_research_stop_effects(self):
        from ai_movie_investigator.research import FixtureConnection
        for mode in ('owner','receipt','site'):
            p=self.fixture();get=FixtureConnection.getresponse
            def changed(connection):
                response=get(connection)
                if mode=='owner':p.owner_event['edited']=True
                elif mode=='receipt':p.occurrence_record['delivery_receipt']['delivery_id']='foreign'
                else:p.site_record['namespace']='foreign'
                return response
            with patch.object(FixtureConnection,'getresponse',changed):
                with self.assertRaises(Refusal):self.run_pilot(p)
            self.assertEqual(len(p.catalogue.requests),1)
            self.assertFalse(p.counter.requests or p.model.requests)

    def test_invalid_review_destination_fails_before_research(self):
        for field,value in (('review_date','invalid'),('timezone','Invented-Unknown-Zone')):
            p=self.fixture();reselect(p,lambda s:s.update({field:value}))
            with self.assertRaises(Refusal):self.run_pilot(p)
            self.no_effects(p)

    def test_quote_coverage_prices_ceiling_and_full_body_fail_before_affected_request(self):
        for mode in ('coverage','ancillary','currency','policy','body','count_fee','absent_ceiling','ceiling'):
            p=self.fixture()
            def change(s):
                q=s['quote']
                if mode=='coverage':q['coverage']='partial-input-only'
                elif mode=='ancillary':q['ancillary']='unknown'
                elif mode=='currency':q['currency']='unknown'
                elif mode=='policy':q['policy']['service_tier']='priority'
                elif mode=='body':q['request_hash']='f'*64
                elif mode=='count_fee':q['count_maximum_fee']=[2,1]
                elif mode=='absent_ceiling':s['ceiling']=None
                else:s['ceiling']=[1,10000000]
                s['site_facts']['quote']=copy.deepcopy(q)
                p.site_record=copy.deepcopy(s['site_facts'])
            reselect(p,change)
            self.run_pilot(p)
            self.assertEqual(self.result(p)['status'],'blocked')
            self.assertFalse(p.counter.requests or p.model.requests)

    def test_count_known_unknown_wrong_project_run_coverage_and_fee(self):
        for mode in ('known','project','run','coverage','request_hash','fee'):
            p=self.fixture()
            p.counter.receipt[mode]=False if mode=='known' else [2,1] if mode=='fee' else 'foreign'
            self.run_pilot(p)
            self.assertEqual(self.result(p)['status'],'blocked')
            self.assertEqual(len(p.counter.requests),1)
            self.assertFalse(p.model.requests)
            events=p.control.read()
            self.assertEqual(sum(e['type']=='pilot_count_reserved' for e in events),1)
            self.assertFalse(any(e['type']=='pilot_count_settled' for e in events))

    def test_model_ceiling_after_exact_count_holds_count_maximum_no_generation(self):
        p=self.fixture();reselect(p,lambda s:s.update(ceiling=[1,1000]))
        self.run_pilot(p)
        self.assertEqual(self.result(p)['reason'],'pilot_model_ceiling')
        self.assertEqual(len(p.counter.requests),1);self.assertFalse(p.model.requests)
        self.assertTrue(any(e['type']=='pilot_count_reserved' for e in p.control.read()))

    def test_model_receipt_unknown_identity_or_invalid_usage_holds_maximum(self):
        for mode in ('known','request_id','response_id','usage','partitions'):
            p=self.fixture()
            if mode in ('known','request_id','response_id'):
                p.model.receipt[mode]=False if mode=='known' else 'foreign'
            elif mode=='usage':self.response(p,lambda b:b['usage'].update(total_tokens=1))
            else:self.response(p,lambda b:b['usage']['input_tokens_details'].update(cached_tokens=1200,cache_write_tokens=1))
            self.run_pilot(p)
            self.assertEqual(self.result(p)['status'],'blocked')
            events=p.control.read()
            self.assertTrue(any(e['type']=='pilot_model_reserved' for e in events))
            self.assertFalse(any(e['type']=='pilot_model_settled' for e in events))
            self.assertEqual(len(p.model.requests),1)

    def test_timeout_and_interruption_preserve_unknown_reservation_no_replay(self):
        for failure in (TimeoutError(),KeyboardInterrupt()):
            p=self.fixture();p.model.response=failure
            if isinstance(failure,KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):self.run_pilot(p)
            else:self.run_pilot(p)
            events=p.control.read()
            self.assertTrue(any(e['type']=='pilot_model_sent' for e in events))
            self.assertFalse(any(e['type']=='pilot_model_settled' for e in events))
            with self.assertRaises(Refusal):self.run_pilot(p)
            self.assertEqual(len(p.model.requests),1)

    def test_second_history_cannot_multiply_parent_claim_or_budget(self):
        p=self.fixture();self.run_pilot(p)
        other=self.fixture()
        h=other.history
        h.clock=p.clock
        p.history=h
        with self.assertRaisesRegex(Refusal,'storage_changed'):self.run_pilot(p)
        # Even an original new fixture selection for that history cannot create
        # a second claim in the already selected canonical project/run store.
        reselect(p,lambda s:s['storage'].update(history=storage_identity(h)))
        with self.assertRaisesRegex(Refusal,'already_consumed'):self.run_pilot(p)
        self.assertEqual(sum(e['type']=='pilot_claim' for e in p.control.read()),1)
        self.assertEqual(sum(e['type']=='pilot_model_reserved' for e in p.control.read()),1)

    def test_fixture_data_cannot_enroll_existing_journal_or_ledger_roots(self):
        from ai_movie_investigator.parent_pilot import ledger_identity
        for kind in ('control','history','ledger'):
            p=self.fixture()
            unknown=self.root/('unenrolled-'+kind);unknown.mkdir(mode=0o700)
            if kind=='ledger':
                # An independently existing synthetic DB with the right schema
                # is still not an enrolled fixture; do not even inspect rows.
                store=RecurringStore(unknown,clock=p.clock)
                store.admit(p.occurrence_record['native_item'])
                p.ledger_directory=unknown
                reselect(p,lambda s:s['storage'].update(ledger=ledger_identity(unknown)))
            else:
                h=History(unknown,clock=p.clock)
                with h.transaction(write=True):pass
                if kind=='history':h.intake(p.history.read()[0]['packet'])
                setattr(p,kind,h)
                def selected(s):
                    s['storage'][kind]=storage_identity(h)
                    if kind=='control':
                        s['site_facts']['storage']=storage_identity(h)
                        p.site_record=copy.deepcopy(s['site_facts'])
                reselect(p,selected)
            with patch.object(History,'read',side_effect=AssertionError('existing journal read')):
                with self.assertRaisesRegex(Refusal,'fixture_storage_unregistered'):self.run_pilot(p)
            self.assertFalse(p.catalogue.requests or p.counter.requests or p.model.requests)

    def test_renaming_run_ceiling_namespace_and_reset_control_is_not_authority(self):
        p=self.fixture();self.run_pilot(p)
        for mode in ('run','ceiling','namespace'):
            reselect(p,lambda s:s.update({mode:[2,1] if mode=='ceiling' else 'changed'}))
            with self.assertRaises(Refusal):self.run_pilot(p)
        new=self.root/'new-control';new.mkdir(mode=0o700)
        p.control=History(new,clock=p.clock)
        with p.control.transaction(write=True):pass
        reselect(p,lambda s:s['storage'].update(control=storage_identity(p.control)))
        with self.assertRaisesRegex(Refusal,'site_facts_unverified|fixture_storage_unregistered'):self.run_pilot(p)
        self.assertFalse(p.control.read())

    @unittest.skipUnless(hasattr(os,'fork'),'local POSIX fixture process boundary')
    def test_concurrent_fixture_processes_share_one_canonical_claim_and_generation(self):
        p=self.fixture()
        children=[]
        for _ in range(2):
            child=os.fork()
            if child==0:
                try:self.run_pilot(p)
                except Refusal:os._exit(20)
                except BaseException:os._exit(21)
                os._exit(0)
            children.append(child)
        statuses=[os.waitpid(child,0)[1] for child in children]
        self.assertEqual(sorted(os.waitstatus_to_exitcode(s) for s in statuses),[0,20])
        events=p.control.read()
        for kind in ('pilot_claim','pilot_count_reserved','pilot_model_reserved','pilot_model_sent','pilot_model_settled'):
            self.assertEqual(sum(e['type']==kind for e in events),1)
        self.assertEqual(sum(e['type']=='result' for e in p.history.read()),1)

    @unittest.skipUnless(hasattr(os,'fork'),'local POSIX fixture process boundary')
    def test_parent_or_reply_loss_at_real_fixture_process_boundary_has_no_recovery_get(self):
        for phase in ('provider','model'):
            p=self.fixture()
            child=os.fork()
            if child==0:
                if phase=='provider':
                    from ai_movie_investigator.research import FixtureConnection
                    FixtureConnection.getresponse=lambda _:os._exit(74)
                else:FixtureModelSite.post=lambda *a,**kw:os._exit(75)
                try:self.run_pilot(p)
                except BaseException:os._exit(76)
                os._exit(77)
            _,status=os.waitpid(child,0)
            self.assertEqual(os.waitstatus_to_exitcode(status),74 if phase=='provider' else 75)
            events=p.control.read()
            self.assertEqual(sum(e['type']=='pilot_claim' for e in events),1)
            if phase=='model':
                self.assertEqual(sum(e['type']=='pilot_model_sent' for e in events),1)
                self.assertFalse(any(e['type']=='pilot_model_settled' for e in events))
            ledger=ExistingWeeklyLedger(p.ledger_directory,clock=p.clock,profile=PROFILE)
            before=ledger.summary()
            with self.assertRaises(Refusal):self.run_pilot(p)
            self.assertEqual(ledger.summary(),before)
            self.assertFalse(p.catalogue.requests or p.model.requests)
            if phase=='provider':self.assertEqual(before['requests_unknown'],1)


class InstalledPilotTests(unittest.TestCase):
    def test_installed_only_nonempty_path_and_every_missing_or_altered_dependency(self):
        with tempfile.TemporaryDirectory(prefix='SIMULATED-installed-task8-') as d:
            root=Path(d).resolve();installed=root/'runtime';installed.mkdir(mode=0o700)
            install_runtime(ROOT,installed)
            script=r'''
import sys, socket, ssl, tempfile
from pathlib import Path
sys.path.insert(0,sys.argv[1])
socket.socket=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('network forbidden'))
socket.getaddrinfo=socket.socket
from ai_movie_investigator.installation import verify_installation
verify_installation(Path(sys.argv[1]))
from ai_movie_investigator.parent_pilot import run_pilot
from ai_movie_investigator.pilot_fixture import make_fixture
with tempfile.TemporaryDirectory(prefix='SIMULATED-installed-pilot-') as d:
 p=make_fixture(Path(d))
 record=run_pilot(p,command=p.owner_event['command'],enabled=True)
 assert record['review']['changed_result_ids']
 assert len(p.model.requests)==1 and len(p.catalogue.requests)==2
 assert record['real_ready'] is False
 assert 'supported_candidate' in record['review']['text']
for name,module in list(sys.modules.items()):
 path=getattr(module,'__file__',None)
 if name.startswith('ai_movie_investigator') or name.startswith('identity_') or name=='torrent_research_evidence':
  assert path and Path(path).resolve().is_relative_to(Path(sys.argv[1]))
print('SIMULATED installed fixed pilot: nonempty, one generation, no real identification')
'''
            command=[sys.executable,'-I','-B','-S','-c',script,str(installed)]
            env={'PATH':os.environ.get('PATH','/usr/bin:/bin')}
            result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('nonempty',result.stdout)
            for name in RUNTIME_FILES:
                path=installed/name;body=path.read_bytes()
                for mode in ('removed','altered'):
                    with self.subTest(name=name,mode=mode):
                        if mode=='removed':path.unlink()
                        else:path.write_bytes(body+b'\n# synthetic alteration\n')
                        try:
                            result=subprocess.run(command,cwd=root,env=env,capture_output=True,timeout=10)
                            self.assertNotEqual(result.returncode,0)
                        finally:
                            path.write_bytes(body);path.chmod(0o600)
