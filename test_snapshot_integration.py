"""Invented snapshot, fake key and fake socket; never contacts a provider."""
import contextlib,hashlib,io,os,time,unittest
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import snapshot_authorization as gate,supervised_authorization as auth,supervised_credit as cmd
from ai_movie_investigator.contracts import decode,digest,encoded,Refusal
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.disclosure import aliases,evidence_alias
from ai_movie_investigator.snapshot_review import build
import test_snapshot_review as sample
import test_standing_credit as standing
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing
from test_responses_compatibility import documented

class IntegrationTests(unittest.TestCase):
 def setUp(self):
  self.f=standing.StandingTests('test_grant_preserves_legacy_hashes_and_default_cap');self.f.setUp();self.addCleanup(self.f.doCleanups);self.f.grant()
  self.root=Path(self.f.f.root);self.state=self.f.state;self.output=self.root/'output';self.output.mkdir(mode=0o700)
  sample_clock=patch.object(sample,'NOW',time.time());sample_clock.start();self.addCleanup(sample_clock.stop)
  snap,src,cat,att=sample.fixture()
  srcj=decode(src);catj=decode(cat);srcj['expires_at']=catj['expires_at']=sample.NOW+600;src=encoded(srcj);cat=encoded(catj)
  att['source_sha256']=hashlib.sha256(src).hexdigest();att['catalogue_sha256']=hashlib.sha256(cat).hexdigest();att['expires_at']=sample.NOW+600
  def pin(name,raw):
   p=self.root/name;p.write_bytes(raw);p.chmod(0o600);return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest())
  self.pin=pin;scope=pin('scope.json',encoded(dict(kind='snapshot_assessment_scope_v1',case_id=sample.CASE,version=sample.VERSION,max_calls=1,disclosure_allowed=True,production_allowed=False)))
  snapshot=pin('snapshot.json',snap);source=pin('source.json',src);catalogue=pin('catalogue.json',cat)
  so=pin('source-original.json',b'{"invented":"source"}');co=pin('catalogue-original.json',b'{"invented":"catalogue"}')
  att['source_original_sha256']=so['sha256'];att['catalogue_original_sha256']=co['sha256']
  local=pin('local.json',encoded(dict(tracker_url='https://example.invalid/listing',release_name='Invented release',nfo_text='Invented NFO')))
  review=pin('review.json',encoded(dict(kind='snapshot_main_review_v1',owner_scope_sha256=scope['sha256'],snapshot_sha256=snapshot['sha256'],source_sha256=source['sha256'],catalogue_sha256=catalogue['sha256'],source_original_sha256=so['sha256'],catalogue_original_sha256=co['sha256'],local_context_sha256=local['sha256'],provenance_reviewed=True)))
  root=History(self.state);events=root.read();st=self.output.stat();self.manifest={'fixture':'a'*64}
  self.record=dict(kind='trusted_main_normalized_snapshot_v1',owner_scope=scope,main_review=review,root_identity=list(root.identity),root_prefix_sha256=digest(events),root_count=len(events),project=self.f.e['project'],account_reference=self.f.e['account_reference'],output_dir=str(self.output),output_identity=[st.st_dev,st.st_ino],snapshot=snapshot,source=source,catalogue=catalogue,source_original=so,catalogue_original=co,local_context=local,attestation=att,runtime_manifest_sha256=digest(self.manifest),issued_at=sample.NOW-1,expires_at=sample.NOW+600)
  self.authority=pin('authority.json',encoded(self.record))
  def fixture_read(path,limit=16384):
   p=Path(path);b=p.read_bytes();assert len(b)<=limit;st=p.stat();return b,(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
  self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
  self.stack.enter_context(patch.object(cmd,'_read_evidence',side_effect=fixture_read))
  self.stack.enter_context(patch('ai_movie_investigator.installation.verify_installation',return_value=self.manifest))
  self.stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('network forbidden')))
 def gate(self):return gate.approved_snapshot_wrapper(self.authority['path'],self.authority['sha256'])
 def reply(self,grant):
  prep=build(gate.active().revalidate());run=grant['run'];v=documented();wire=grant['request']
  v['instructions']=wire['instructions'];v['text']=wire['text'];v['max_output_tokens']=wire['max_output_tokens']
  result=dict(status='supported_candidate',candidate=dict(imdb='tt1234567',tmdb=123),alternatives=[],citations=[dict(evidence_id=evidence_alias(run,'source'),claim='source_identity'),dict(evidence_id=evidence_alias(run,'catalogue'),claim='crosswalk')],rationale='Matching IDs support a proposal.',uncertainty='Edition remains unknown.',next_action='human_review')
  v['output'][-1]['content'][0]['text']=encoded(dict(binding_hash=aliases(run),kind='final',lookups=[],result=result)).decode()
  return encoded(v)
 def test_default_closed_and_forged_receipt_refused(self):
  with self.assertRaisesRegex(Refusal,'snapshot_activation_unissued'):gate.active()
  with self.assertRaisesRegex(Refusal,'snapshot_receipt_unbound'):auth.consume_snapshot_completion({}, {})
 def test_end_to_end_fake_transport_receipt_report_and_replay_refusal(self):
  from ai_movie_investigator import keychain_credential as keychain
  with self.gate(),auth._simulated_captured_io():
   root=History(self.state)
   with root.transaction(write=True) as (events,_):grant=gate.proposal(root,events,self.f.selected.data)
   response=self.reply(grant)
   # Fake transport proof is marked real solely to exercise the private writer.
   consume=auth.consume_snapshot_completion
   def proof(grant,answer):return dict(consume(grant,answer),simulated=False)
   with framing.wire(response),patch.object(auth,'consume_snapshot_completion',side_effect=proof),patch.object(keychain,'_native',return_value=b'sk-SYNTHETIC_FIXTURE') as native,redirect_stdout_silent():
    report=gate.execute(self.state,self.f.selected,self.output)
   self.assertEqual(native.call_count,1)
   self.assertEqual(report['status'],'private_report_written');html=(self.output/'movie-review.html').read_text()
   self.assertIn('Invented release',html);self.assertIn('1 h 35 min 0.000 s',html);self.assertIn('conflicting titles',html)
   with self.assertRaises(Refusal):cmd.run(self.state,self.f.selected,7,historical=True)
   with self.assertRaises(Refusal):gate.authorize(self.state,self.f.selected)
   self.assertEqual(len(History(self.state/'credit').read()),6)
 def test_active_proof_rejects_forgery_and_second_consumption(self):
  from types import SimpleNamespace
  grant={'fixture':'grant'};original={'kind':'invented answer'};forged={'kind':'different answer'}
  session=SimpleNamespace(snapshot_grant=grant,snapshot_receipt=(encoded(original),'a'*64),snapshot_io_marker=None)
  token=auth._ACTIVE.set(session)
  try:
   with self.assertRaisesRegex(Refusal,'snapshot_receipt_unbound'):auth.consume_snapshot_completion(grant,forged)
   self.assertEqual(auth.consume_snapshot_completion(grant,original)['receipt_hash'],'a'*64)
   with self.assertRaisesRegex(Refusal,'snapshot_receipt_unbound'):auth.consume_snapshot_completion(grant,original)
  finally:auth._ACTIVE.reset(token)
 def test_invalid_report_context_refuses_before_allocation(self):
  local=self.pin('bad-local.json',encoded(dict(tracker_url='http://example.invalid/listing',release_name='Invented',nfo_text='')))
  self.record['local_context']=local
  old=decode(Path(self.record['main_review']['path']).read_bytes());old['local_context_sha256']=local['sha256']
  self.record['main_review']=self.pin('bad-review.json',encoded(old));self.authority=self.pin('bad-authority.json',encoded(self.record))
  before=History(self.state).read()
  with patch.object(cmd,'prompt_credential',side_effect=AssertionError('key')),self.assertRaisesRegex(Refusal,'snapshot_report_url'):
   with self.gate():gate.execute(self.state,self.f.selected,self.output)
  self.assertEqual(History(self.state).read(),before);self.assertFalse((self.state/'attempt-7').exists())
 def test_installed_issued_wrapper_uses_one_shot_keychain_boundary(self):
  import json,subprocess,sys
  from ai_movie_investigator.installation import install_runtime
  runtime=self.root/'installed';runtime.mkdir(mode=0o700);install_runtime(Path(__file__).resolve().parent,runtime)
  manifest=json.loads((runtime/'runtime-files.json').read_text());self.manifest.clear();self.manifest.update(manifest)
  self.record['runtime_manifest_sha256']=digest(manifest);self.authority=self.pin('issued-authority.json',encoded(self.record))
  with self.gate():
   root=History(self.state)
   with root.transaction(write=True) as (events,_):grant=gate.proposal(root,events,self.f.selected.data)
   response=self.reply(grant)
  template=Path('automation/snapshot_review_UNISSUED.py').read_text()
  issued=dict(runtime=str(runtime),runtime_files=manifest,python_sha256=hashlib.sha256(Path(sys.executable).resolve(strict=True).read_bytes()).hexdigest(),main_acceptance_path=str(self.root/'acceptance.json'),authority=self.authority,account_evidence=dict(path=str(self.f.selected.path),sha256=self.f.selected.sha256),state=str(self.state),output_dir=str(self.output),root_prefix_sha256=self.record['root_prefix_sha256'],expected_slot=7)
  wrapper=self.root/'issued-wrapper.py';wrapper.write_text(template.replace('ISSUED = None','ISSUED = '+repr(issued),1));wrapper.chmod(0o600)
  self.pin('acceptance.json',encoded(dict(decision='accepted_exact_normalized_snapshot_assessment',wrapper_sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),issued_pins=issued)))
  driver="""import sys,runpy,contextlib,io
from pathlib import Path
sys.path.insert(0,"""+repr(str(runtime))+""")
from ai_movie_investigator import keychain_credential as k,supervised_authorization as a
k._native=lambda project:b'sk-SYNTHETIC_FIXTURE'
consume=a.consume_snapshot_completion
def fixture_proof(grant,answer):return dict(consume(grant,answer),simulated=False)
a.consume_snapshot_completion=fixture_proof
"""
  driver+='selected_raw='+repr(response)+"\nframing='chunked'\n"+framing.wire_code()
  driver+='\nnamespace=runpy.run_path('+repr(str(wrapper))+',run_name="fixture_wrapper")\nsys.argv=['+repr(str(wrapper))+',"--main-accepted-snapshot-review"]\n'
  driver+='with a._simulated_captured_io(),wire_fixture("completed"):\n namespace["main"]()\n'
  path=self.root/'driver.py';path.write_text(driver)
  result=subprocess.run([str(Path(sys.executable).resolve(strict=True)),'-I','-S','-B',str(path)],cwd=runtime,capture_output=True,timeout=60)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
  self.assertIn(b'private_report_written',result.stdout);self.assertTrue((self.output/'movie-review.html').exists())
  self.assertEqual(len(History(self.state/'credit').read()),6)
 def test_replaced_output_refused_before_allocation(self):
  with self.gate():
   old=self.output.with_name('old-output');self.output.rename(old);self.output.mkdir(mode=0o700)
   with self.assertRaisesRegex(Refusal,'snapshot_output_changed'):gate.execute(self.state,self.f.selected,self.output)
   self.assertFalse((self.state/'attempt-7').exists())

def redirect_stdout_silent():return contextlib.redirect_stdout(io.StringIO())
if __name__=='__main__':unittest.main()
