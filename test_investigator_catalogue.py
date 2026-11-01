"""Task6 fixtures are invented data; all socket/DNS calls are forbidden."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import copy
from dataclasses import replace
from fractions import Fraction
import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from ai_movie_investigator.catalogue_replay import fixture_rows, run_catalogue_synthetic, setup_case
from ai_movie_investigator.contracts import Refusal, decode, digest, encoded, legacy_snapshot
from ai_movie_investigator.controller import INSTRUCTIONS, RetainedTools, investigate, output_schema
from ai_movie_investigator.history import FILENAME, History
from ai_movie_investigator.installation import RUNTIME_FILES, install_runtime
from ai_movie_investigator.pilot import build_plan, readable_plan, validate_pilot
from ai_movie_investigator.replay import NOW, packet_for, simulated_replies
from ai_movie_investigator.research import (FIXTURE_TOKEN, FixtureConnection, OfflineResearch,
    SyntheticResearch, material_for, select_plan, validate_plan)
from ai_movie_investigator.responses_http import HTTPResult, MAX_RESPONSE
from ai_movie_investigator.responses_protocol import parse_response
from ai_movie_investigator.responses_replay import simulated_response, simulated_transport
from ai_movie_investigator.responses_transport import ResponsesTransport
from ai_movie_investigator.spending import COUNTER, POLICY, PRICING, SimulatedSpending, rational
from identity_recurring_store import RecurringStore
from identity_research_provider import Provider
from identity_research_store import Stop

ROOT = Path(__file__).resolve().parent


def prompt_for(packet, now=NOW):
    from ai_movie_investigator.contracts import reconcile
    return dict(protocol='retained-investigator-v1', binding_hash=digest(packet['binding']),
                binding=packet['binding'], facts=packet['facts'], reconciliation=reconcile(packet, now),
                evidence_index=[{k: r[k] for k in ('id', 'kind', 'observed_at', 'expires_at')}
                                for r in RetainedTools(packet, now).rows.values()],
                query_results=[], instruction=INSTRUCTIONS)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='SIMULATED-task6-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.socket = patch('socket.socket', side_effect=AssertionError('live socket forbidden')).start()
        self.dns = patch('socket.getaddrinfo', side_effect=AssertionError('live DNS forbidden')).start()
        self.addCleanup(patch.stopall)

    def case(self):
        directory = self.root / ('case-' + str(len(list(self.root.iterdir()))))
        directory.mkdir(mode=0o700)
        return setup_case(directory)

    def broker(self, case, rows=None):
        h, store, clock, original, job, plan = case
        return OfflineResearch(enabled=True, history=h, store=store,
            connection=FixtureConnection(rows if rows is not None else fixture_rows()),
            authorization=SyntheticResearch(digest(original), digest(plan)), monotonic=clock)

    def test_nonempty_catalogue_to_responses_private_result_daily_and_pilot(self):
        demo = run_catalogue_synthetic(self.root)
        self.assertEqual(demo['result']['status'], 'supported_candidate')
        self.assertEqual(demo['result']['model_calls'], 2)
        self.assertFalse(demo['result']['production_identity_verified'])
        self.assertFalse(demo['result']['download_consent'])
        self.assertEqual(len(demo['connection'].requests), 2)
        self.assertEqual(len(demo['transport'].http.requests), 2)
        self.assertEqual(demo['store'].summary()['requests_rolling_week'], 2)
        self.assertEqual(demo['store'].summary()['requests_unknown'], 0)
        self.assertEqual(demo['skipped']['status'], 'intentionally_skipped')
        self.assertEqual(demo['conflict']['status'], 'unresolved')
        self.assertTrue(demo['conflict']['reconciliation']['conflicting_ids'])
        self.assertEqual(demo['revoked'], 'research_plan_revoked')
        self.assertEqual(demo['revoked_requests'], 0)
        events = demo['history'].read()
        self.assertEqual(sum(e['type'] == 'spending_reserved' for e in events), 2)
        self.assertEqual(sum(e['type'] == 'spending_settled' for e in events), 2)
        for index, e in enumerate(events):
            if e['type'] == 'spending_settled':
                self.assertTrue(any(r['type'] == 'spending_reserved' and
                    r['local_request_id'] == e['local_request_id'] for r in events[:index]))
        self.assertIn('2 SIMULATED GETs through shared ledger', demo['review']['text'])
        self.assertIn('SIMULATED spending', demo['review']['text'])
        self.assertIn('Real readiness: blocked', demo['plan_text'])
        self.assertFalse(demo['plan']['real_readiness'])
        self.assertEqual(demo['plan']['request_policy'], POLICY)
        self.assertNotIn(FIXTURE_TOKEN, encoded(events).decode())
        for receipt in demo['receipts']:
            self.assertNotEqual(receipt['provenance']['source_version'], receipt['provenance']['material_version'])
        self.socket.assert_not_called()
        self.dns.assert_not_called()

    def test_disabled_import_startup_and_false_real_authorizers_do_no_io(self):
        with patch.object(Path, 'read_text', side_effect=AssertionError('source/config read')):
            importlib.import_module('ai_movie_investigator.research')
            importlib.import_module('ai_movie_investigator.pilot')
            self.assertEqual(OfflineResearch().preflight(), 'research_disabled')
            for grant in (True, None, {'verified': True}, SyntheticResearch('a'*64, 'b'*64)):
                broker = OfflineResearch(enabled=True, authorization=grant, connection=Mock())
                self.assertIn('unimplemented', broker.preflight())
                with self.assertRaisesRegex(Refusal, 'unimplemented'):
                    broker.run('unknown', {})
            class Forged(FixtureConnection):
                pass
            self.assertIn('unimplemented', OfflineResearch(enabled=True,
                authorization=SyntheticResearch('a'*64, 'b'*64), connection=Forged(fixture_rows())).preflight())
            self.assertIn('unimplemented', ResponsesTransport(enabled=True, authorization=True).preflight())
        self.socket.assert_not_called()
        self.dns.assert_not_called()

    def test_changed_source_case_version_event_delivery_plan_and_material_rejected(self):
        for field in ('source', 'case_id', 'version', 'event', 'delivery', 'plan', 'material', 'source_clock'):
            with self.subTest(field=field):
                case = self.case()
                _, store, _, original, job, plan = case
                broker = self.broker(case)
                changed = copy.deepcopy(plan)
                if field in ('source', 'case_id', 'version'):
                    changed['binding'][field] = ('synthetic2' if field == 'source' else
                        'outcome-' + 'a'*64 if field == 'case_id' else 'a'*64)
                elif field in ('event', 'delivery'):
                    changed['binding']['occurrence'][field + '_id'] = 'changed'
                elif field == 'plan':
                    changed['operations'].reverse()
                elif field == 'source_clock':
                    changed['source_observed_at'] = NOW
                else:
                    changed['material']['facts']['year'] = 2025
                with self.assertRaises((Refusal, ValueError)):
                    broker.run(job, changed)
                self.assertFalse(broker.connection.requests)
                self.assertEqual(store.summary()['requests_rolling_week'], 0)
                with self.assertRaises((Refusal, ValueError)):
                    validate_plan(changed, original)

    def test_unselected_queries_detail_ids_imdb_arbitrary_urls_and_forward_dependencies(self):
        _, _, _, original, _, _ = self.case()
        for op in (dict(kind='movie_search', value='Another title'), dict(kind='tv_search', value='https://invalid'),
                   dict(kind='details', value=1), dict(kind='find', value='tt9000128'),
                   dict(kind='url', value='https://api.themoviedb.org'),
                   dict(kind='details', value=dict(from_step=0, id=9000127)),
                   dict(kind='movie_search', value='Synthetic Harbor?api_key=private')):
            with self.subTest(operation=op), self.assertRaises((Refusal, ValueError)):
                select_plan(original, [op], issued_at=NOW, expires_at=NOW+120)
        with self.assertRaisesRegex(Refusal, 'operation_limit'):
            select_plan(original, [dict(kind='movie_search', value='Synthetic Harbor')]*6,
                        issued_at=NOW, expires_at=NOW+120)

    def test_detail_must_be_in_earlier_bound_movie_result(self):
        case = self.case()
        rows = fixture_rows()
        rows[0]['body']['results'][0]['id'] = 9000128
        broker = self.broker(case, rows)
        with self.assertRaisesRegex(Refusal, 'detail_not_returned'):
            broker.run(case[4], case[5])
        self.assertEqual(len(broker.connection.requests), 1)
        self.assertEqual(case[1].summary()['requests_rolling_week'], 1)

    def test_cross_occurrence_evidence_cannot_select_catalogue_ids(self):
        case=self.case()
        packet=copy.deepcopy(case[3])
        foreign=copy.deepcopy(packet['evidence'][0])
        foreign['id']='foreign'
        foreign['scope']['occurrence']['delivery_id']=999
        foreign['candidate']=dict(imdb='tt9000999',tmdb=9000999)
        packet['evidence'].append(foreign)
        for op in (dict(kind='details',value=9000999),dict(kind='find',value='tt9000999')):
            with self.assertRaisesRegex(Refusal,'not_selected'):
                select_plan(packet,[op],issued_at=NOW,expires_at=NOW+120)

    def test_conflicting_catalogue_ids_are_retained_without_identity_or_consent(self):
        case=self.case()
        rows=fixture_rows()
        rows[1]['body']['external_ids']['imdb_id']='tt9000999'
        new_job,packet,_=self.broker(case,rows).run(case[4],case[5])
        self.assertEqual(packet['evidence'][-1]['candidate']['imdb'],'tt9000999')
        replies=simulated_replies(packet)
        replies[-1]['result']['citations'][0]['evidence_id']='research-1'
        t=simulated_transport(packet,responses=[simulated_response(r,n) for n,r in enumerate(replies,1)])
        t.clock=case[2]
        result=investigate(case[0],new_job,'SIMULATED-catalogue-conflict',t,monotonic=case[2])
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['reason'],'unsupported_candidate')
        self.assertFalse(result['production_identity_verified'])
        self.assertFalse(result['download_consent'])

    def test_selected_find_and_tv_search_use_existing_provider_projection(self):
        for kind, value, body in (
            ('find', 'tt9000127', dict(movie_results=[dict(id=9000127, title='Synthetic Harbor')])),
            ('tv_search', 'Synthetic Harbor', dict(page=1, results=[dict(id=9000127, name='Synthetic Harbor')]))):
            case = list(self.case())
            case[5] = select_plan(case[3], [dict(kind=kind, value=value)], issued_at=NOW, expires_at=NOW+120)
            broker = self.broker(case, [dict(kind=kind, value=value, body=body, status=200, fault=None)])
            _, enriched, receipts = broker.run(case[4], case[5])
            self.assertEqual(receipts[0]['kind'], kind)
            self.assertIsNone(enriched['evidence'][-1]['candidate'])
            self.assertNotIn('source_identity', enriched['evidence'][-1]['claims'])

    def test_original_event_hash_and_clocks_preserved_and_catalogue_claims_narrow(self):
        case = self.case()
        _, enriched, _ = self.broker(case).run(case[4], case[5])
        for key in ('binding', 'event', 'original_hash', 'hash_basis', 'facts', 'decisions'):
            self.assertEqual(enriched[key], case[3][key])
        for row in enriched['evidence'][1:]:
            self.assertEqual(row['scope'], case[3]['binding'])
            self.assertEqual(row['image_references'], 0)
            self.assertFalse(set(row['claims']) & {'source_identity', 'runtime', 'edition'})

    def test_shared_cache_requires_exact_own_occurrence_plan_provenance(self):
        case = list(self.case())
        first = case[5]['operations'][0]
        case[5] = select_plan(case[3], [first, first, dict(kind='details', value=dict(from_step=0,id=9000127))],
                              issued_at=NOW, expires_at=NOW+120)
        broker = self.broker(case)
        _, _, receipts = broker.run(case[4], case[5])
        self.assertEqual(len(broker.connection.requests), 2)
        self.assertEqual(len(receipts), 3)
        self.assertIsNotNone(receipts[1]['provenance']['cache_of'])
        self.assertIsNone(receipts[1]['provenance']['request'])
        self.assertEqual(case[1].summary()['requests_rolling_week'], 2)
        case = self.case()
        with case[1].tx() as c:
            c.execute('insert into cache values(?,?,?)', (digest(['movie_search', 'Synthetic Harbor']), NOW+86400,
                encoded(dict(reason='ok', observed_at=NOW, expires_at=NOW+86400,data={})).decode()))
        broker = self.broker(case)
        with self.assertRaisesRegex(Refusal, 'cache_unbound'):
            broker.run(case[4], case[5])
        self.assertFalse(broker.connection.requests)

    def test_stale_expired_future_or_missing_expiry_catalogue_cannot_be_used(self):
        real_get = Provider.get
        for change in (dict(observed_at=NOW+100), dict(expires_at=NOW), dict(expires_at=None)):
            case = self.case()
            broker = self.broker(case)
            def changed(provider, *args):
                result = real_get(provider, *args)
                return dict(result, **change)
            with patch.object(Provider, 'get', changed), self.assertRaises((Refusal, ValueError, TypeError)):
                broker.run(case[4], case[5])
            self.assertEqual(len(broker.connection.requests), 1)
            self.assertFalse(any(e['type'] == 'research_complete' for e in case[0].read()))

    def test_expired_cache_does_not_refund_or_hide_a_new_get(self):
        case = self.case()
        with case[1].tx() as c:
            c.execute('insert into cache values(?,?,?)', (digest(['movie_search', 'Synthetic Harbor']), NOW,
                       encoded(dict(reason='ok', observed_at=NOW-86400, expires_at=NOW,data={})).decode()))
        broker = self.broker(case)
        broker.run(case[4], case[5])
        self.assertEqual(len(broker.connection.requests), 2)
        self.assertEqual(case[1].summary()['requests_rolling_week'], 2)

    def test_unsafe_body_credential_echo_redirect_failures_auth_and_rate_limits(self):
        for kind in ('unsafe', 'echo', 'escaped_echo', 'malformed', 'redirect', 'auth', 'rate', 'timeout'):
            with self.subTest(kind=kind):
                case = self.case()
                rows = fixture_rows()
                if kind == 'unsafe':
                    rows[0]['body']['results'][0]['title'] = 'Bearer PRIVATE_SENTINEL'
                elif kind == 'echo': rows[0]['body'] = dict(echo=FIXTURE_TOKEN)
                elif kind == 'escaped_echo':
                    rows[0]['body']['results'][0]['title'] = FIXTURE_TOKEN
                    rows[0]['body'] = encoded(rows[0]['body']).replace(b'SIMULATED', b'\\u0053IMULATED')
                elif kind == 'malformed': rows[0]['body'] = b'{'
                elif kind == 'redirect': rows[0]['status'] = 302
                elif kind == 'auth': rows[0]['status'] = 401
                elif kind == 'rate': rows[0]['status'] = 429
                else: rows[0]['fault'] = 'send_timeout'
                broker = self.broker(case, rows)
                with self.assertRaises(Refusal): broker.run(case[4], case[5])
                self.assertEqual(len(broker.connection.requests), 1)
                self.assertEqual(case[1].summary()['requests_rolling_week'], 1)
                self.assertEqual(case[1].summary()['provider_suspended'], kind == 'auth')
                with case[1].tx() as c:
                    stored = str([tuple(row) for row in c.execute('select * from cache')])
                    cooldown = c.execute('select not_before from provider').fetchone()[0]
                self.assertNotIn('PRIVATE_SENTINEL', stored + encoded(case[0].read()).decode())
                self.assertNotIn(FIXTURE_TOKEN, stored)
                if kind == 'rate': self.assertGreaterEqual(cooldown, NOW+900)

    def test_shared_cooldown_suspension_weekly_cases_requests_and_per_version_cap(self):
        for gate in ('cooldown', 'suspension', 'weekly_cases', 'weekly_requests', 'per_version'):
            with self.subTest(gate=gate):
                case = self.case()
                h, store, clock, _, job, plan = case
                if gate in ('cooldown', 'suspension'):
                    with store.tx() as c:
                        c.execute('update provider set not_before=?,suspended=?',
                                  (NOW+100 if gate == 'cooldown' else 0, int(gate == 'suspension')))
                elif gate == 'weekly_cases':
                    run = store.start()
                    with store.tx() as c:
                        for n in range(5):
                            c.execute('insert into attempts values(?,?,?,?,NULL,NULL)',
                                      ('old-'+str(n), run, plan['provider_version'], NOW))
                    store.end(run)
                else:
                    actual_lease = store.lease
                    def filled(run):
                        lease = actual_lease(run)
                        with store.tx() as c:
                            for n in range(25 if gate == 'weekly_requests' else 5):
                                c.execute('insert into requests values(NULL,?, ?,"tmdb",?,?,NULL)',
                                          (run, lease['token'], digest(['old',n]), NOW))
                        return lease
                    patcher = patch.object(store, 'lease', side_effect=filled)
                    patcher.start()
                    self.addCleanup(patcher.stop)
                broker = self.broker(case)
                with self.assertRaises(Stop) as exc: broker.run(job, plan)
                self.assertIn(str(exc.exception), ('provider_cooldown','provider_suspended','weekly_case_budget',
                                                   'weekly_request_budget','case_request_budget'))
                self.assertFalse(broker.connection.requests)

    def test_skipped_retired_superseded_and_future_source_do_zero_research(self):
        for mode in ('skipped','retired','superseded','future'):
            case = list(self.case())
            h, store, clock, original, job, plan = case
            if mode == 'skipped':
                p = packet_for(999, 'intentionally_skipped')
                case[3] = p
                case[4] = h.intake(p)[0]
                case[5] = select_plan(p, [dict(kind='movie_search',value='Synthetic Harbor')],
                                      issued_at=NOW,expires_at=NOW+120)
            elif mode == 'retired':
                with h.transaction(write=True) as (_, append):
                    append(dict(type='research_revoked',at=clock(),job=job,plan_hash=digest(plan)))
            elif mode == 'superseded':
                changed = copy.deepcopy(original)
                changed['binding']['version'] = 'b'*64
                h.intake(changed)
            else:
                clock.value = NOW-7200
            broker = self.broker(case)
            with self.assertRaises(Refusal): broker.run(case[4],case[5])
            self.assertFalse(broker.connection.requests)
            self.assertEqual(store.summary()['requests_rolling_week'],0)

    def test_ledger_material_correspondence_cannot_use_equal_version_or_title(self):
        for mode in ('material','version','retired'):
            case = self.case()
            with case[1].tx() as c:
                if mode == 'material':
                    material = copy.deepcopy(case[5]['material'])
                    material['facts']['year'] = 2025
                    c.execute('update evidence set material=?',(encoded(material).decode(),))
                elif mode == 'version':
                    c.execute('update jobs set status="awaiting_evidence"')
                else: c.execute('delete from jobs')
            broker = self.broker(case)
            with self.assertRaisesRegex(Refusal,'ledger_material_unbound'):
                broker.run(case[4],case[5])
            self.assertFalse(broker.connection.requests)

    def test_interruptions_at_reserve_send_and_record_remain_consumed_after_reopen(self):
        for where in ('reserve','send','record'):
            case = self.case()
            rows = fixture_rows()
            broker = self.broker(case, rows)
            if where == 'reserve':
                reserve = case[1].reserve
                def fail(*args):
                    reserve(*args)
                    raise KeyboardInterrupt()
                patched = patch.object(case[1], 'reserve', side_effect=fail)
            elif where == 'record': patched = patch.object(case[1], 'record', side_effect=KeyboardInterrupt())
            else:
                rows[0]['fault'] = 'send_interrupt'
                broker = self.broker(case, rows)
                patched = nullcontext()
            with patched, self.assertRaises(KeyboardInterrupt): broker.run(case[4],case[5])
            self.assertEqual(case[1].summary()['requests_unknown'],1)
            self.assertEqual(len(broker.connection.requests),0 if where == 'reserve' else 1)
            reopened = list(case)
            reopened[0] = History(case[0].directory,clock=case[2])
            reopened[1] = RecurringStore(case[1].directory,clock=case[2])
            fresh = self.broker(reopened)
            with self.assertRaisesRegex(Refusal,'attempt_consumed'): fresh.run(case[4],case[5])
            self.assertFalse(fresh.connection.requests)

    def test_no_replay_after_success_or_duplicate_request_record(self):
        case = self.case()
        _, _, receipts = self.broker(case).run(case[4],case[5])
        with self.assertRaises((Refusal,Stop)): self.broker(case).run(case[4],case[5])
        receipt=receipts[0]
        with self.assertRaisesRegex(Stop,'finalized'):
            case[1].record(receipt['provenance']['request'],receipt['key'],receipt['result'])

    def test_concurrent_research_selection_consumes_only_one_shared_attempt(self):
        case=self.case()
        # Provider's main-thread signal timer is disabled ONLY for this
        # synthetic threaded reservation race; the finite wire cannot do I/O.
        def attempt(_):
            broker=self.broker(case)
            try:broker.run(case[4],case[5])
            except (Refusal,Stop):pass
            return len(broker.connection.requests)
        with patch('identity_research_provider.request_deadline',side_effect=lambda:nullcontext()):
            with ThreadPoolExecutor(max_workers=2) as pool:
                sent=list(pool.map(attempt,(1,2)))
        self.assertEqual(sum(sent),2)
        self.assertEqual(case[1].summary()['cases_rolling_week'],1)
        self.assertEqual(case[1].summary()['requests_rolling_week'],2)

    def test_source_expiry_and_decision_expiry_stop_research_before_next_send(self):
        for mode in ('source_expired','source_future','decision_expiry'):
            case=list(self.case())
            h,store,clock,packet,_,_=case
            if mode=='source_expired':clock.value=packet['evidence'][0]['expires_at']+1
            elif mode=='source_future':clock.value=packet['evidence'][0]['observed_at']-1
            else:
                from ai_movie_investigator.replay import owner_decision
                decision=owner_decision(packet['binding'],'technical_gap',evidence=packet['evidence'])
                decision['expires_at']=NOW+1.5
                packet['decisions']=[decision]
            case[4]=h.intake(packet)[0]
            store.admit(material_for(packet))
            case[5]=select_plan(packet,[dict(kind='movie_search',value='Synthetic Harbor'),
                dict(kind='details',value=dict(from_step=0,id=9000127))],
                issued_at=clock(),expires_at=clock()+120)
            broker=self.broker(case)
            with self.assertRaisesRegex(Refusal,'freshness_unverified|decision_applicability_changed'):
                broker.run(case[4],case[5])
            self.assertEqual(len(broker.connection.requests),1 if mode=='decision_expiry' else 0)

    def test_missing_crosswalk_progresses_to_durable_unresolved_simulated_result(self):
        case=self.case()
        rows=fixture_rows()
        rows[1]['body']['external_ids']={}
        new_job,packet,_=self.broker(case,rows).run(case[4],case[5])
        replies=simulated_replies(packet,status='unresolved')
        replies[-1]['result']['citations']=[dict(evidence_id='research-1',claim='title')]
        spending=SimulatedSpending(case[0],binding=packet['binding'],ceiling=[1,1],expires_at=NOW+120)
        t=simulated_transport(packet,spending=spending,
            responses=[simulated_response(r,n) for n,r in enumerate(replies,1)])
        t.clock=case[2]
        result=investigate(case[0],new_job,'SIMULATED-unresolved',t,monotonic=case[2])
        self.assertEqual(result['status'],'unresolved')
        self.assertIsNone(result['model_result']['candidate'])
        self.assertEqual(len(t.http.requests),2)

    def test_late_response_or_wall_rollback_cannot_extend_research(self):
        actual_get=Provider.get
        for mode in ('late','rollback'):
            case=self.case()
            tick=[NOW]
            broker=self.broker(case)
            broker.monotonic=lambda:tick[0]
            def delayed(provider,*args):
                result=actual_get(provider,*args)
                tick[0]=NOW+61
                case[2].value=NOW+61 if mode=='late' else NOW-50
                return result
            with patch.object(Provider,'get',delayed), self.assertRaisesRegex(Refusal,'deadline|clock'):
                broker.run(case[4],case[5])
            self.assertEqual(len(broker.connection.requests),1)
            self.assertFalse(any(e['type']=='research_complete' for e in case[0].read()))

    def test_history_and_ledger_symlink_permissions_and_path_replacement_fail(self):
        for mode in ('history_mode','ledger_mode','ledger_symlink','history_replaced','ledger_replaced'):
            case=self.case()
            h,store,_,_,job,plan=case
            broker=self.broker(case)
            if mode=='history_mode':
                h.directory.chmod(0o755)
            elif mode=='ledger_mode': store.path.chmod(0o644)
            elif mode=='ledger_symlink':
                saved=store.path.with_name('saved.sqlite3')
                store.path.rename(saved)
                store.path.symlink_to(saved)
            elif mode=='history_replaced':
                h.read()  # no file creation beyond existing synthetic intake
                saved=h.directory.with_name('saved-history')
                h.directory.rename(saved)
                h.directory.mkdir(mode=0o700)
            else:
                reserve=store.reserve
                def replace_after(*args):
                    answer=reserve(*args)
                    saved=store.path.with_name('saved.sqlite3')
                    store.path.rename(saved)
                    store.path.write_bytes(saved.read_bytes())
                    store.path.chmod(0o600)
                    return answer
                patcher=patch.object(store,'reserve',side_effect=replace_after)
                patcher.start()
                self.addCleanup(patcher.stop)
            with self.assertRaises((Refusal,ValueError,OSError)): broker.run(job,plan)
            self.assertLessEqual(len(broker.connection.requests),1)
            if mode=='ledger_replaced':
                # Refusal must cover cleanup too, not just the GET/record path.
                with store.tx() as c:
                    self.assertIsNotNone(c.execute('select active_run from pilot').fetchone()[0])
                    self.assertIsNone(c.execute('select ended from runs').fetchone()[0])

    def test_pilot_exact_payload_pins_missing_grants_and_mutation_rejection(self):
        case=self.case()
        h,_,_,original,job,plan=case
        pilot=build_plan(h,original,plan,selected_job=job,provenance='synthetic',ceiling=None,expires_at=NOW+120)
        self.assertEqual(validate_pilot(pilot,h,original),'blocked_for_real_execution')
        self.assertFalse(pilot['real_readiness'])
        self.assertIsNone(pilot['real_owner_ceiling'])
        self.assertIn('no_selected_simulated_ceiling',pilot['missing_live_facts'])
        self.assertIn('current_shared_model_quota_telemetry',pilot['missing_live_facts'])
        self.assertEqual(pilot['selected_payload_hash'],digest(pilot['selected_redacted_model_payload']))
        self.assertIn('not a hard real spending cap',readable_plan(pilot))
        for key,value in (('real_readiness',True),('input_hash','a'*64),('missing_live_facts',[]),
                          ('output_binding','b'*64),('request_policy',{})):
            changed=dict(pilot,**{key:value})
            with self.assertRaises(Refusal): validate_pilot(changed,h,original)
        case[2].advance(1)
        with self.assertRaisesRegex(Refusal,'changed_or_stale'):validate_pilot(pilot,h,original)

    def test_unbound_historical_plan_is_assessed_blocked_never_runnable(self):
        h,_,_,p,_,_=self.case()
        historical=legacy_snapshot(dict(case_id=p['binding']['case_id'],version=p['binding']['version'],
            observed_at=NOW-10,first_observed_at=NOW-20,title='Synthetic Harbor',year=2026,route='eligible',
            reason='no_exact_match',correlation='strong_source_id',original_type='movie',
            source_identity=dict(imdb=None,tmdb=None,asserted_imdb=None,asserted_tmdb=None)),
            source='synthetic',evidence=[],decisions=[])
        job=h.intake(historical)[0]
        selected=select_plan(historical,[dict(kind='movie_search',value='Synthetic Harbor')],
                             issued_at=NOW,expires_at=NOW+120)
        plan=build_plan(h,historical,selected,selected_job=job,provenance='historical_unverified',
                        ceiling=None,expires_at=NOW+120)
        self.assertIn('historical_occurrence_and_source_currentness_unknown',plan['missing_live_facts'])
        self.assertIn('selected_case_ineligible',plan['missing_live_facts'])
        self.assertEqual(validate_pilot(plan,h,historical),'blocked_for_real_execution')
        self.assertIsNone(plan['binding']['occurrence'])


class SpendingTests(unittest.TestCase):
    setUp = OfflineTests.setUp
    case = OfflineTests.case
    def spending_case(self, ceiling=None):
        h,_,clock,_,_,_=self.case()
        packet=packet_for(12766)
        budget=SimulatedSpending(h,binding=packet['binding'],ceiling=[1,1] if ceiling is None else ceiling,
                                 expires_at=NOW+120)
        t=simulated_transport(packet,spending=budget)
        return h,clock,packet,budget,t

    def prepare(self,t,p):
        raw=encoded(prompt_for(p))
        reservation=t.prepare(raw,schema=output_schema())
        return raw,reservation

    def test_exact_rational_worst_case_complete_input_before_fake_send(self):
        h,_,p,budget,t=self.spending_case()
        raw,reservation=self.prepare(t,p)
        self.assertFalse(t.http.requests)
        row=[e for e in h.read() if e['type']=='spending_reserved'][0]
        self.assertEqual(row['tokens'],len(t.pending[0]))
        expected=row['tokens']*Fraction(8,1000000)+4096*Fraction(20,1000000)
        self.assertEqual(rational(row['cost']),expected)
        t.complete(raw,schema=output_schema(),timeout=25)
        settled=[e for e in h.read() if e['type']=='spending_settled'][0]
        self.assertEqual(rational(settled['cost']),Fraction(10800,1000000))
        self.assertEqual(settled['request_hash'],reservation['request_hash'])

    def test_ceiling_counter_and_rate_policy_unknown_injection_never_send(self):
        h,_,p,b,t=self.spending_case([1,1000000])
        with self.assertRaisesRegex(Refusal,'spending_ceiling'):self.prepare(t,p)
        self.assertFalse(t.http.requests)
        for key,value in (('counter','unknown'),('pricing',{}),('policy',{})):
            _,_,p,b,t=self.spending_case()
            b.spec[key]=value
            with self.assertRaisesRegex(Refusal,'policy_unknown'):self.prepare(t,p)
            self.assertFalse(t.http.requests)
        self.assertIn('implementation_unknown',simulated_transport(p,spending=lambda:0).preflight())
        with self.assertRaises(TypeError):SimulatedSpending(h,binding=p['binding'],ceiling=[1,1],expires_at=NOW+120,counter=lambda:0)

    def test_restart_unknown_charge_cannot_rename_budget_refund_or_authorize_send(self):
        h,clock,p,b,t=self.spending_case()
        raw,reservation=self.prepare(t,p)
        reopened=History(h.directory,clock=clock)
        b2=SimulatedSpending(reopened,binding=p['binding'],ceiling=[1,1],expires_at=NOW+120)
        t2=simulated_transport(p,spending=b2)
        with self.assertRaisesRegex(Refusal,'previous_charge_unknown'):self.prepare(t2,p)
        self.assertFalse(t2.http.requests)
        with self.assertRaisesRegex(Refusal,'budget_changed'):
            SimulatedSpending(reopened,binding=p['binding'],ceiling=[2,1],expires_at=NOW+120)
        self.assertEqual(sum(e['type']=='spending_reserved' for e in reopened.read()),1)

    def test_concurrent_reservations_cannot_double_spend(self):
        h,clock,p,b,t=self.spending_case()
        def attempt(n):
            other=SimulatedSpending(History(h.directory,clock=clock),binding=p['binding'],ceiling=[1,1],expires_at=NOW+120)
            candidate=simulated_transport(p,spending=other)
            try:self.prepare(candidate,p)
            except Refusal:return False
            return True
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(attempt,(1,2))),1)
        self.assertEqual(sum(e['type']=='spending_reserved' for e in h.read()),1)

    def test_invalid_missing_usage_policy_or_cost_partition_never_refunds(self):
        for mode in ('missing','overflow','write_partition','ttl','tier','cache_missing','diagnostics','input_overspend'):
            with self.subTest(mode=mode):
                h,_,p,b,t=self.spending_case()
                response=simulated_response(simulated_replies(p)[0],1)
                body=decode(response.body,MAX_RESPONSE)
                if mode=='missing': del body['usage']['input_tokens_details']['cached_tokens']
                elif mode=='overflow': body['usage']['input_tokens_details'].update(cached_tokens=1200,cache_write_tokens=1)
                elif mode=='write_partition': body['usage']['input_tokens_details']['cache_write_tokens_details']['ttl_12h_tokens']=1
                elif mode=='ttl':body['prompt_cache_options']={'ttl':'12h'}
                elif mode=='tier':body['service_tier']='auto'
                elif mode=='cache_missing':del body['prompt_cache_options']
                elif mode=='diagnostics':body['prompt_cache_diagnostics']={}
                else:body['usage'].update(input_tokens=65536,total_tokens=65836)
                t.http.responses=[replace(response,body=encoded(body))]
                raw,_=self.prepare(t,p)
                with self.assertRaises(Refusal):t.complete(raw,schema=output_schema(),timeout=25)
                self.assertFalse(any(e['type']=='spending_settled' for e in h.read()))
                fresh=simulated_transport(p,spending=b)
                with self.assertRaisesRegex(Refusal,'previous_charge_unknown'):self.prepare(fresh,p)
                self.assertFalse(fresh.http.requests)

    def test_cache_read_write_and_reasoning_are_not_double_counted(self):
        h,_,p,b,t=self.spending_case()
        response=simulated_response(simulated_replies(p)[0],1)
        body=decode(response.body,MAX_RESPONSE)
        body['usage']['input_tokens_details'].update(cached_tokens=400,cache_write_tokens=500,
            cache_write_tokens_details=dict(ttl_30m_tokens=500,ttl_12h_tokens=0))
        t.http.responses=[replace(response,body=encoded(body))]
        raw,_=self.prepare(t,p)
        t.complete(raw,schema=output_schema(),timeout=25)
        settled=[e for e in h.read() if e['type']=='spending_settled'][0]
        self.assertEqual(rational(settled['cost']),Fraction(300*4+400*2+500*8+300*20,1000000))
        self.assertEqual(settled['usage']['output_tokens_details']['reasoning_tokens'],50)

    def test_json_escaped_response_identity_echo_cannot_settle_or_enter_history(self):
        from ai_movie_investigator.responses_http import SYNTHETIC_CREDENTIAL
        h,_,p,b,t=self.spending_case()
        response=simulated_response(simulated_replies(p)[0],1)
        body=decode(response.body,MAX_RESPONSE)
        body['id']=SYNTHETIC_CREDENTIAL
        escaped=encoded(body).replace(b'SIMULATED-NOT-A-KEY',b'\\u0053IMULATED-NOT-A-KEY')
        self.assertNotIn(SYNTHETIC_CREDENTIAL.encode(),escaped)
        t.http.responses=[replace(response,body=escaped)]
        raw,_=self.prepare(t,p)
        with self.assertRaisesRegex(Refusal,'credential_echo_refused'):
            t.complete(raw,schema=output_schema(),timeout=25)
        self.assertFalse(any(e['type']=='spending_settled' for e in h.read()))
        self.assertNotIn(SYNTHETIC_CREDENTIAL,encoded(h.read()).decode())

    def test_duplicate_response_receipt_request_and_wrong_binding_fail(self):
        h,_,p,b,t=self.spending_case()
        raw,reservation=self.prepare(t,p)
        t.complete(raw,schema=output_schema(),timeout=25)
        with self.assertRaisesRegex(Refusal,'settlement_sequence'):
            b.settle(reservation,t.completion_accounting())
        fresh=simulated_transport(p,spending=b)
        with self.assertRaisesRegex(Refusal,'request_consumed'):self.prepare(fresh,p)
        changed=dict(p['binding'],version='b'*64)
        with self.assertRaisesRegex(Refusal,'case_changed'):
            b.reserve(t.http.requests[0]['body'],reservation,changed)
        self.assertEqual(sum(e['type']=='spending_settled' for e in h.read()),1)

    def test_missing_or_uncertain_completion_and_interrupt_stay_reserved(self):
        for failure in (HTTPResult(500,b'private error'),TimeoutError(),KeyboardInterrupt()):
            h,_,p,b,t=self.spending_case()
            t.http.responses=[failure]
            raw,_=self.prepare(t,p)
            with self.assertRaises((Refusal,KeyboardInterrupt)):
                t.complete(raw,schema=output_schema(),timeout=25)
            self.assertEqual(sum(e['type']=='spending_reserved' for e in h.read()),1)
            self.assertFalse(any(e['type']=='spending_settled' for e in h.read()))

    def test_second_request_exceeding_remaining_ceiling_stops_before_fake_send(self):
        h,_,clock,_,_,_=self.case()
        p=packet_for(12767)
        unpriced=simulated_transport(p)
        body=unpriced._body(encoded(prompt_for(p)),output_schema())
        ceiling=len(body)*Fraction(8,1000000)+4096*Fraction(20,1000000)
        b=SimulatedSpending(h,binding=p['binding'],ceiling=[ceiling.numerator,ceiling.denominator],expires_at=NOW+120)
        t=simulated_transport(p,spending=b)
        job=h.intake(p)[0]
        result=investigate(h,job,'SIMULATED-stop-spend',t)
        self.assertEqual(result['reason'],'spending_ceiling')
        self.assertEqual(len(t.http.requests),1)
        self.assertEqual(sum(e['type']=='spending_reserved' for e in h.read()),1)
        self.assertEqual(sum(e['type']=='spending_settled' for e in h.read()),1)

    def test_send_reservation_is_one_use_and_must_precede_settlement(self):
        h,_,p,b,t=self.spending_case()
        raw,reservation=self.prepare(t,p)
        body=t.pending[0]
        b.before_send(body,reservation)
        with self.assertRaisesRegex(Refusal,'send_consumed'):b.before_send(body,reservation)
        with self.assertRaisesRegex(Refusal,'send_consumed'):t.complete(raw,schema=output_schema(),timeout=25)
        self.assertFalse(t.http.requests)

    def test_late_model_response_expiry_and_wall_rollback_never_settle(self):
        for mode in ('late','rollback','expiry'):
            h,clock,p,b,t=self.spending_case()
            raw,_=self.prepare(t,p)
            if mode=='late':
                ticks=iter([0,0,0,26])
                t.monotonic=lambda:next(ticks)
            else:
                # The transport clock stays authorized so the durable spending
                # clock independently refuses settlement after restart/drift.
                clock.value=NOW-1 if mode=='rollback' else NOW+121
            with self.assertRaises(Refusal): t.complete(raw,schema=output_schema(),timeout=25)
            self.assertFalse(any(e['type']=='spending_settled' for e in h.read()))
            self.assertEqual(len(t.http.requests),1 if mode=='late' else 0)

    def test_spending_history_symlink_permissions_incomplete_tail_and_replacement(self):
        for mode in ('symlink','permissions','tail','replacement'):
            h,_,p,b,t=self.spending_case()
            path=h.directory/FILENAME
            if mode=='symlink':
                saved=path.with_name('saved.jsonl')
                path.rename(saved)
                path.symlink_to(saved)
            elif mode=='permissions':path.chmod(0o644)
            elif mode=='tail':
                with path.open('ab') as stream:stream.write(b'{')
            else:
                h.directory.rename(h.directory.with_name('saved-history'))
                h.directory.mkdir(mode=0o700)
            with self.assertRaises((Refusal,OSError)):self.prepare(t,p)
            self.assertFalse(t.http.requests)


class CatalogueInstalledTests(unittest.TestCase):
    def test_installed_nonempty_workflow_and_every_individually_removed_dependency(self):
        script='''
import pathlib,sys,tempfile,socket,ssl
sys.path.insert(0,sys.argv[1])
socket.socket=lambda *a,**k: (_ for _ in ()).throw(AssertionError('live socket'))
socket.getaddrinfo=lambda *a,**k: (_ for _ in ()).throw(AssertionError('live DNS'))
from ai_movie_investigator.installation import verify_installation
verify_installation(sys.argv[1])
from ai_movie_investigator.catalogue_replay import run_catalogue_synthetic
with tempfile.TemporaryDirectory() as tmp:
 d=run_catalogue_synthetic(pathlib.Path(tmp).resolve())
 assert d['result']['status']=='supported_candidate'
 assert len(d['connection'].requests)==2 and len(d['transport'].http.requests)==2
 assert d['store'].summary()['requests_rolling_week']==2
 assert len([e for e in d['history'].read() if e['type']=='spending_settled'])==2
 assert not d['plan']['real_readiness'] and d['revoked_requests']==0
 assert '2 SIMULATED GETs' in d['review']['text']
installed=pathlib.Path(sys.argv[1])
for name,module in list(sys.modules.items()):
 if name.startswith('ai_movie_investigator') or name.startswith('identity_') or name=='torrent_research_evidence':
  assert pathlib.Path(module.__file__).is_relative_to(installed), name
print('INSTALLED_CATALOGUE_PASS')
'''
        with tempfile.TemporaryDirectory(prefix='SIMULATED-task6-install-') as tmp:
            base=Path(tmp).resolve()
            destination=base/'installed'
            destination.mkdir(mode=0o700)
            manifest=install_runtime(ROOT,destination)
            self.assertEqual(set(manifest),set(RUNTIME_FILES))
            def execute():
                return subprocess.run([sys.executable,'-I','-B','-S','-c',script,str(destination)],
                    cwd=base,env={'PATH':os.environ.get('PATH','')},capture_output=True,text=True,timeout=30)
            result=execute()
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('INSTALLED_CATALOGUE_PASS',result.stdout)
            for name in RUNTIME_FILES:
                path=destination/name
                body=path.read_bytes()
                path.unlink()
                result=execute()
                self.assertNotEqual(result.returncode,0,'missing dependency accepted: '+name)
                self.assertNotIn('INSTALLED_CATALOGUE_PASS',result.stdout)
                path.write_bytes(body)
            for name in ('identity_research_provider.py','ai_movie_investigator/research.py'):
                path=destination/name
                body=path.read_bytes()
                path.write_bytes(body+b'\n# drift\n')
                self.assertNotEqual(execute().returncode,0)
                path.write_bytes(body)


if __name__=='__main__':
    unittest.main()
