"""Explicit audit mode through real capture/store and connected parsing, invented I/O only."""
import copy,hashlib,json,time,unittest,uuid
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
import test_identity_capture as capfixture
import test_captured_activation as activation
import test_captured_generation as generation
from identity_triage_intake import normalize
import identity_triage_capture as cap
from ai_movie_investigator import new_case as n,contracts as k,supervised_authorization as auth,installation
from ai_movie_investigator.replay import synthetic_case,owner_decision,NOW
from ai_movie_investigator.history import History

FILTER=dict(mode='first_verified_identity_check',category='unknown_movie',status='verified_tmdb',reason='external_id_verified')

class CaptureAudit(unittest.TestCase):
 def fixture(self):
  f=capfixture.CaptureTests('test_raw_native_receipt_and_default_health');f.setUp();self.addCleanup(f.doCleanups);return f
 def test_exact_audit_capture_and_single_lifetime(self):
  f=self.fixture();f.arm(filter=FILTER);e=f.outcome();e['data']['outcome']={k:v for k,v in FILTER.items() if k!='mode'}
  response,raw=f.request(e);self.assertIn(b'200 OK',response)
  self.assertEqual((f.store.directory/cap.BODY).read_bytes(),raw)
  receipt=(f.store.directory/cap.RECEIPT).read_bytes();self.assertTrue(f.server.capture.burned)
  e['id']=str(uuid.uuid4());f.request(e);self.assertEqual((f.store.directory/cap.RECEIPT).read_bytes(),receipt)
  with f.store.connection(True) as c:self.assertEqual(c.execute('select route from selection_history').fetchone()[0],'verified')
 def test_wrong_triples_and_old_modes_never_capture(self):
  for field,value in [('category','existing'),('status','legacy_resolved'),('reason','resolved'),('mode','first_matching')]:
   with self.subTest(field=field):
    f=self.fixture();flt=dict(FILTER);flt[field]=value;f.arm(filter=flt)
    e=f.outcome();e['data']['outcome']={k:v for k,v in FILTER.items() if k!='mode'};f.request(e)
    self.assertFalse((f.store.directory/cap.BODY).exists());self.assertFalse(f.server.capture.burned)
 def test_valid_grant_wrong_outcome_triples_refuse(self):
  for field,value in [('category','existing'),('status','legacy_resolved'),('reason','resolved')]:
   with self.subTest(field=field):
    f=self.fixture();f.arm(filter=FILTER);e=f.outcome()
    e['data']['outcome']={k:v for k,v in FILTER.items() if k!='mode'};e['data']['outcome'][field]=value
    f.request(e);self.assertFalse((f.store.directory/cap.BODY).exists());self.assertFalse(f.server.capture.burned)
 def test_mismatch_source_and_name_fallback_refuse(self):
  for change in ('source','external_id'):
   with self.subTest(change=change):
    f=self.fixture();f.arm(filter=FILTER,**({'source':'different'} if change=='source' else {}))
    e=f.outcome();e['data']['outcome']={k:v for k,v in FILTER.items() if k!='mode'}
    if change=='external_id':e['data']['release'].pop('external_id')
    f.request(e);self.assertFalse((f.store.directory/cap.BODY).exists())
 def test_reservation_failure_burns_audit(self):
  f=self.fixture();f.arm(filter=FILTER);e=f.outcome();e['data']['outcome']={k:v for k,v in FILTER.items() if k!='mode'}
  with patch.object(cap,'write_at',side_effect=OSError('invented')):f.request(e)
  self.assertTrue(f.server.capture.burned);f.request(e);self.assertFalse((f.store.directory/cap.BODY).exists())

class AdmissionAudit(unittest.TestCase):
 def packet(self,kind=None):
  raw,b,e=synthetic_case(165);raw['data']['outcome']={k:v for k,v in FILTER.items() if k!='mode'}
  decisions=[owner_decision(b,kind,evidence=e,chosen=kind=='confirmed_identity')] if kind else []
  return k.captured_outcome(k.encoded(raw),sources={'synthetic':'Synthetic Index'},binding=b,evidence=e,decisions=decisions,trusted_issuers=['synthetic_owner'])
 def test_audit_refusals_are_finite_and_sanitized(self):
  from ai_movie_investigator import supervised_credit as credit
  for reason in ('verified_identity_check_scope','assessment_purpose','verified_capture_grant','verified_capture_qualification'):
   self.assertEqual(credit.safe_reason(k.Refusal(reason)),reason)
   self.assertEqual(credit.refusal_category(k.Refusal(reason)),'captured_refused')
  self.assertEqual(credit.safe_reason(k.Refusal('PRIVATE_UNKNOWN')),'unexpected_exception')
 def test_explicit_mode_only_preserves_facts(self):
  p=self.packet();before=copy.deepcopy(p)
  self.assertEqual(k.reconcile(p,NOW)['admission'],'intentionally_skipped')
  with self.assertRaises(k.Refusal):n.admitted(p,p['binding'],NOW)
  self.assertEqual(n.admitted(p,p['binding'],NOW,purpose=k.VERIFIED_IDENTITY_CHECK)['admission'],'eligible');self.assertEqual(p,before)
 def test_owner_skip_completed_and_remembered_identity_stay_closed(self):
  for kind in ('intentionally_skipped','completed_occurrence','confirmed_identity'):
   with self.subTest(kind=kind):
    p=self.packet(kind)
    with self.assertRaises(k.Refusal):n.admitted(p,p['binding'],NOW,purpose=k.VERIFIED_IDENTITY_CHECK)
 def test_conflicting_owner_decisions_and_clock(self):
  p=self.packet('confirmed_identity');other=copy.deepcopy(p['decisions'][0]);other['id']='other';other['chosen_target']={'imdb':'tt9000128','tmdb':9000128};p['decisions'].append(other)
  self.assertEqual(k.reconcile_verified_identity_check(p,NOW)['disposition'],'conflicting_owner_decisions')
  p=self.packet();p['event']['observed_at']=NOW+301
  self.assertEqual(k.reconcile_verified_identity_check(p,NOW)['disposition'],'outcome_clock_unverified')

class ConnectedAudit(unittest.TestCase):
 def setUp(self):
  # Produce real native raw-body/receipt from the invented Handler and SQLite.
  f=capfixture.CaptureTests('test_raw_native_receipt_and_default_health');f.setUp();self.addCleanup(f.doCleanups)
  raw,b,e=synthetic_case(165);raw['timestamp']=datetime.now(timezone.utc).isoformat()
  raw['data']['outcome']={k:v for k,v in FILTER.items() if k!='mode'}
  f.cfg['sources']={'synthetic':'Synthetic Index'};f.save()
  release=copy.deepcopy(raw);release['event']='release.new';release['id']=str(uuid.uuid4());del release['data']['outcome']
  if getattr(self,'support','strong_source_id')=='strong_source_id':
   f.store.ingest(normalize(release,f.cfg['sources']),'release_new')
  f.arm(source='synthetic',filter=FILTER);response,self.body=f.request(raw);self.assertIn(b'200 OK',response)
  self.receipt=json.loads((f.store.directory/cap.RECEIPT).read_bytes());self.grant=(f.store.directory/cap.GRANT).read_bytes()
  r=self.receipt;b=dict(source=r['source'],case_id=r['case_id'],version=r['case_version'],occurrence=dict(event_id=r['event_id'],delivery_id=r['delivery_rowid']))
  for row in e:row['scope']=copy.deepcopy(b)
  original_prepare=n.prepare;original_capture=k.captured_outcome
  # Fixture assembly adapts only invented input; no admission/activation gate patch.
  with patch.object(generation,'synthetic_case',return_value=(raw,b,e)),patch.object(activation,'synthetic_case',return_value=(raw,b,e)),patch.object(generation,'captured_outcome',side_effect=lambda ignored,**kwargs:original_capture(self.body,qualification=self.receipt['capture_qualification'],**kwargs)),patch.object(n,'prepare',side_effect=lambda *args,**kwargs:original_prepare(*args,purpose=k.VERIFIED_IDENTITY_CHECK,**kwargs)):
   self.a=activation.Activation('test_exact_context_receipt_report_and_reset_without_gate_patch');self.a.setUp();self.addCleanup(self.a.doCleanups)
  self.a.record.update(kind='trusted_wrapper_verified_identity_check_v1',assessment_purpose=k.VERIFIED_IDENTITY_CHECK)
  for name,data in [('body',self.body),('receipt',k.encoded(self.receipt)),('capture_grant',self.grant)]:
   path=self.a.root/(name+'.json');path.write_bytes(data);path.chmod(0o600)
   self.a.record[name]=dict(path=str(path),sha256=hashlib.sha256(data).hexdigest())
  self.a.write_record()
 def test_native_capture_to_bound_response_and_private_report(self):
  with self.a.context(),auth._simulated_captured_io():
   self.a.f.authorize();self.assertEqual(self.a.f.run_case()['status'],'completed')
   with self.assertRaises(k.Refusal):self.a.f.run_case()
  report=self.a.f.case.read()[-1]['report'];receipt=History(self.a.f.f.state/'attempt-7').read()[-1]
  self.assertEqual(report['receipt_hash'],k.digest(receipt));self.assertEqual(report['assessment_purpose'],k.VERIFIED_IDENTITY_CHECK)
  self.assertEqual(report['producer_assertion']['status'],'verified_tmdb');self.assertFalse(report['producer_assertion']['independently_approved'])
  self.assertEqual(report['capture_qualification'],self.receipt['capture_qualification'])
  self.assertEqual(self.a.f.case.read()[1]['request']['input']['qualifications']['capture_source_support'],self.receipt['capture_qualification'])
  self.assertFalse(report['draft']['sent']);self.assertTrue(report['connected_transport_invoked']);self.assertFalse(report['generation_invoked'])
  self.assertNotIn('Source conflict:',json.dumps(report));self.assertEqual(self.a.f.packet['facts']['route'],'verified')
 def test_wrong_purpose_and_grant_refuse_before_credit(self):
  self.a.record['assessment_purpose']='wrong';self.a.write_record()
  with self.assertRaises(k.Refusal):
   with self.a.context():pass
  self.a.record['assessment_purpose']=k.VERIFIED_IDENTITY_CHECK
  p=Path(self.a.record['capture_grant']['path']);p.write_bytes(b'changed');self.a.write_record()
  with self.assertRaises(k.Refusal):
   with self.a.context():pass
 def test_receipt_grant_hash_and_source_mismatch_refuse(self):
  original=copy.deepcopy(self.receipt)
  for field,value in [('grant_sha256','0'*64),('source','different')]:
   with self.subTest(field=field):
    r=copy.deepcopy(original);r[field]=value
    p=Path(self.a.record['receipt']['path']);p.write_bytes(k.encoded(r));self.a.record['receipt']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();self.a.write_record()
    before=History(self.a.f.f.state).read()
    with self.assertRaises(k.Refusal):
     with self.a.context():pass
    self.assertEqual(History(self.a.f.f.state).read(),before)
 def test_prepared_purpose_swap_refuses_before_debit(self):
  before=History(self.a.f.f.state).read()
  with self.a.context(),auth._simulated_captured_io():
   original=n._prepared_locked
   def changed(*args):
    p,packet,body,rec=original(*args);p=copy.deepcopy(p);p.pop('assessment_purpose');return p,packet,body,rec
   with patch.object(n,'_prepared_locked',side_effect=changed):
    with self.assertRaises(k.Refusal):self.a.f.authorize()
  self.assertEqual(History(self.a.f.f.state).read(),before)
 def test_old_wrapper_cannot_authorize_audit(self):
  self.a.record['kind']='trusted_wrapper_one_captured_case_v1';del self.a.record['assessment_purpose'];del self.a.record['capture_grant'];self.a.write_record()
  with self.assertRaises(k.Refusal):
   with self.a.context():pass
 def test_changed_body_or_request_refuse(self):
  with self.a.context(),auth._simulated_captured_io():
   self.a.f.authorize();Path(self.a.record['body']['path']).write_bytes(b'changed')
   with self.assertRaises(k.Refusal):self.a.f.run_case()
 def test_installed_audit_runtime_connected_wire(self):
  activation.Activation.test_installed_wrapper_uses_real_bounded_module_with_fake_keychain_wire(self.a)
  report=self.a.f.case.read()[-1]['report']
  self.assertEqual(report['assessment_purpose'],k.VERIFIED_IDENTITY_CHECK)
  self.assertFalse(report['draft']['sent'])
 def test_uncertain_audit_transport_no_retry(self):
  activation.Activation.test_uncertain_transport_does_not_allow_retry_or_supplied_completion(self.a)
 def test_installed_nonempty_closure(self):
  target=self.a.root/'audit-runtime';target.mkdir(mode=0o700)
  manifest=installation.install_runtime(Path(__file__).resolve().parent,target)
  manifest=json.loads((target/'runtime-files.json').read_bytes())
  self.assertEqual(len(manifest),42)
  for name in ('ai_movie_investigator/new_case.py','ai_movie_investigator/contracts.py'):
   self.assertEqual((target/name).read_bytes(),(Path(__file__).parent/name).read_bytes())

if __name__=='__main__':unittest.main()


class ConnectedOutcomeOnly(ConnectedAudit):
 support="outcome_only"

class OutcomeOnlyAdmission(unittest.TestCase):
 def fixture(self):
  f=capfixture.CaptureTests('test_raw_native_receipt_and_default_health');f.setUp();self.addCleanup(f.doCleanups)
  f.cfg['source_mode']='selected_only';f.save();f.arm(filter=FILTER)
  e=f.outcome();e['data']['release']['external_id']='new-audit-release';e['data']['outcome']={k:v for k,v in FILTER.items() if k!='mode'}
  return f,e
 def test_outcome_first_later_selected_duplicate_and_new_delivery_do_not_replay(self):
  from test_identity_selected import selected
  import identity_triage_service as service
  f,e=self.fixture();response,raw=f.request(e);self.assertIn(b'200 OK',response)
  receipt=(f.store.directory/cap.RECEIPT).read_bytes();r=json.loads(receipt)
  self.assertEqual(r['capture_qualification'],dict(scope='retained_collector_observations_at_capture',correlation='outcome_only',source_support='no_prior_supporting_observation'))
  p=selected(external_id='new-audit-release');body=json.dumps(p).encode()
  request=(f"POST /v1/selected HTTP/1.0\r\nX-Identity-Intake-Key: {f.cfg['release_key']}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n").encode()+body
  sock=capfixture.FakeSocket(request);service.Handler(sock,('127.0.0.1',1),f.server);self.assertIn(b'200 OK',sock.output)
  f.request(e);e['id']=str(uuid.uuid4());f.request(e)
  self.assertEqual((f.store.directory/cap.RECEIPT).read_bytes(),receipt);self.assertEqual((f.store.directory/cap.BODY).read_bytes(),raw)
 def test_conflicting_asserted_identity_and_wrong_route_refuse(self):
  for change in ('conflict','route','fallback'):
   with self.subTest(change=change):
    f,e=self.fixture()
    if change=='conflict':e['data']['outcome']['asserted_imdb']='tt7654321'
    elif change=='route':e['data']['outcome']['category']='existing'
    else:e['data']['release'].pop('external_id')
    f.request(e);self.assertFalse((f.store.directory/cap.BODY).exists());self.assertFalse(f.server.capture.burned)
 def test_qualification_cannot_be_forged_or_added_to_generic_packet(self):
  raw,b,e=synthetic_case(165);raw['data']['outcome']={k:v for k,v in FILTER.items() if k!='mode'}
  good=dict(scope='retained_collector_observations_at_capture',correlation='outcome_only',source_support='no_prior_supporting_observation')
  for qualification in (dict(good,source_support='prior_supporting_observation_correlated'),{x:y for x,y in good.items() if x!='scope'}):
   with self.subTest(qualification=qualification),self.assertRaises(k.Refusal):
    k.captured_outcome(k.encoded(raw),sources={'synthetic':'Synthetic Index'},binding=b,evidence=e,decisions=[],qualification=qualification)
  raw['data']['outcome'].update(status='unresolved',reason='no_exact_match')
  with self.assertRaises(k.Refusal):
   k.captured_outcome(k.encoded(raw),sources={'synthetic':'Synthetic Index'},binding=b,evidence=e,decisions=[],qualification=good)
