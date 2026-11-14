"""Invented fresh film-scope successor; fake transport and credential only."""
import copy
import hashlib
import io
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from ai_movie_investigator import snapshot_authorization as gate, snapshot_review as review
from ai_movie_investigator import supervised_authorization as auth, supervised_credit as credit
from ai_movie_investigator.contracts import decode, digest, encoded, Refusal
from ai_movie_investigator.history import History
from ai_movie_investigator.disclosure import aliases, evidence_alias
import test_snapshot_reassessment as prior
import test_supervised_diagnostics as diagnostics
import test_supervised_envelope as framing


class FilmIntegrationTests(unittest.TestCase):
 def setUp(self):
  self.r=prior.ReassessmentTests('test_distinct_new_result_preserves_prior_and_refuses_another');self.r.setUp();self.addCleanup(self.r.doCleanups)
  self.f=self.r.f;self.root=self.r.root;self.credit=self.r.credit
  with self.f.gate(),auth._simulated_captured_io():
   gate.authorize(self.f.state,self.f.f.selected)
   grant=self.root.read()[-2]['historical'];response=self.f.reply(grant)
   consume=auth.consume_snapshot_completion
   def proof(grant,answer):return dict(consume(grant,answer),simulated=False)
   with patch.object(auth,'consume_snapshot_completion',side_effect=proof),diagnostics.DiagnosticTests().inputs(),framing.wire(response),redirect_stdout(io.StringIO()):
    self.assertEqual(credit.run(self.f.state,self.f.f.selected,9,historical=True)['status'],'completed')
  events=self.root.read();start=next(r for r in events if r.get('type')=='supervised_standing_attempt_started' and r.get('slot')==9)
  completed=next(r for r in events if r.get('type')=='supervised_completed' and r.get('slot')==9)
  rows=History(self.f.state/'attempt-9').read();credit_rows=self.credit.read()
  record=copy.deepcopy(self.f.record);record.pop('reassessment')
  att=copy.deepcopy(record['attestation']);now=time.time()
  snapshot=decode(Path(record['snapshot']['path']).read_bytes(),1048576);snapshot['generated_at']=now-1
  source=decode(Path(record['source']['path']).read_bytes());source['observed_at']=now-2
  catalogue=decode(Path(record['catalogue']['path']).read_bytes());catalogue['observed_at']=now-2
  for name,obj in (('snapshot',snapshot),('source',source),('catalogue',catalogue)):
   record[name]=self.f.pin('fresh-'+name+'.json',encoded(obj));att[name+'_sha256']=record[name]['sha256']
  att['observed_at']=now-0.5;record['attestation']=att
  p=review.projection(encoded(snapshot),record['snapshot']['sha256'],att['case_id'],att['version'],encoded(source),encoded(catalogue),att,now=now)
  proof=dict(kind='snapshot_film_scope_reassessment_v1',prior_slot=9,prior_start_sha256=digest(start),prior_grant_sha256=digest(grant),prior_completion_sha256=digest(completed),prior_report_sha256=digest(completed['historical_report']),prior_retained_reply_sha256=digest(completed['answer']),prior_attempt_sha256=digest(rows),prior_receipt_sha256=digest(rows[-1]),prior_credit_sha256=digest(credit_rows),prior_credit_count=len(credit_rows),prior_request_sha256=digest(grant['request']),root_prefix_sha256=digest(events),new_request_sha256=digest(review.build_film_scope(p)['request']),prior_status=completed['answer']['result']['status'],prior_candidate=completed['answer']['result']['candidate'],prior_rationale_status=completed['historical_report']['prose_handling']['rationale']['status'],reviewed=True)
  record.update(root_prefix_sha256=digest(events),root_count=len(events),film_reassessment=proof)
  output=self.f.root/'film-output';output.mkdir(mode=0o700);st=output.stat();record.update(output_dir=str(output),output_identity=[st.st_dev,st.st_ino]);self.f.output=output
  scope=self.f.pin('film-scope.json',encoded(dict(kind='snapshot_film_scope_v1',case_id=att['case_id'],version=att['version'],max_calls=1,disclosure_allowed=True,production_allowed=False,prior_slot=9)));record['owner_scope']=scope
  main=decode(Path(record['main_review']['path']).read_bytes());main.pop('reassessment_sha256');main.update(owner_scope_sha256=scope['sha256'],snapshot_sha256=record['snapshot']['sha256'],source_sha256=record['source']['sha256'],catalogue_sha256=record['catalogue']['sha256'],film_reassessment_sha256=digest(proof))
  record['main_review']=self.f.pin('film-review.json',encoded(main));self.f.record=record;self.f.authority=self.f.pin('film-authority.json',encoded(record));self.p=p

 def test_one_fresh_successor_and_replay_refusal(self):
  with self.f.gate(),auth._simulated_captured_io():
   self.assertEqual(gate.authorize(self.f.state,self.f.f.selected)['slot'],10)
   with self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)

 def test_wrong_prior_receipt_refuses_before_reservation(self):
  with self.f.gate():
   with self.root.transaction(write=True) as (events,_):
    grant=gate.proposal(self.root,events,self.f.f.selected.data);grant['film_reassessment']['prior_receipt_sha256']='f'*64
    with self.assertRaises(Refusal):gate.validate_film_reassessment(self.root,events,grant,creating=True)
  self.assertFalse((self.f.state/'attempt-10').exists())

 def test_stale_clocks_changed_identity_and_prior_grant_refused(self):
  with self.f.gate() as held:
   with self.root.transaction(write=True) as (events,_):
    grant=gate.proposal(self.root,events,self.f.f.selected.data)
    old=self.r.c.p
    for label in ('snapshot','listing','catalogue','identity'):
     p=copy.deepcopy(self.p)
     if label=='snapshot':p['generated_at']=old['generated_at']
     elif label=='listing':p['listing']['observed_at']=old['listing']['observed_at']
     elif label=='catalogue':p['catalogue']['observed_at']=old['catalogue']['observed_at']
     else:p['source_identifiers']['asserted_tmdb']=999
     with self.subTest(label=label),patch.object(held,'revalidate',return_value=p),self.assertRaises(Refusal):
      gate.validate_film_reassessment(self.root,events,grant,creating=True)
    changed=copy.deepcopy(grant);changed['case']['version']='f'*64
    with self.assertRaises(Refusal):gate.validate_film_reassessment(self.root,events,changed,creating=True)
    changed=copy.deepcopy(grant);changed['film_reassessment']['prior_rationale_status']='withheld'
    with self.assertRaises(Refusal):gate.validate_film_reassessment(self.root,events,changed,creating=True)
    changed_events=copy.deepcopy(events)
    next(x for x in changed_events if x.get('type')=='supervised_standing_attempt_started' and x.get('slot')==9)['historical']['projection_sha256']='f'*64
    with patch.object(self.root,'require_write_transaction'),self.assertRaises(Refusal):
     gate.validate_film_reassessment(self.root,changed_events,grant,creating=True)
  self.assertFalse((self.f.state/'attempt-10').exists())

 def response(self,grant):
  response=decode(self.f.reply(grant),65536);answer=decode(response['output'][-1]['content'][0]['text'])
  run=grant['run'];refs=[evidence_alias(run,'source'),evidence_alias(run,'catalogue')]
  def f(aspect,disposition,source_field,catalogue_field,explanation):
   return dict(aspect=aspect,disposition=disposition,source_field=source_field,catalogue_field=catalogue_field,explanation=explanation,evidence=refs[:])
  answer['film_findings']=[f('title','supports','title','title','The titles match.'),
   f('year','supports','year','festival_years','The festival year matches.'),
   f('people','supports','cast','cast','A cast member matches.'),
   f('runtime_description','conflicts','description_runtime_minutes','runtime_minutes','Listing and catalogue duration differ.'),
   f('runtime_nfo','reconciled','nfo_runtime_milliseconds','runtime_minutes','The uploader video duration differs.'),
   f('ids','supports','imdb','imdb','The listed identifiers match.')]
  answer['film_blockers']=[]
  response['output'][-1]['content'][0]['text']=encoded(answer).decode()
  return encoded(response)

 def test_fake_wire_receipt_report_and_no_second_child(self):
  from ai_movie_investigator import keychain_credential
  with self.f.gate(),auth._simulated_captured_io():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,self.f.f.selected.data)
   response=self.response(grant);consume=auth.consume_snapshot_completion
   def proof(grant,answer):return dict(consume(grant,answer),simulated=False)
   with framing.wire(response),patch.object(auth,'consume_snapshot_completion',side_effect=proof),patch.object(keychain_credential,'_native',return_value=b'sk-SYNTHETIC_FIXTURE'),redirect_stdout(io.StringIO()):
    self.assertEqual(gate.execute(self.f.state,self.f.f.selected,self.f.output)['status'],'private_report_written')
   html=(self.f.output/'movie-review.html').read_text()
   self.assertIn('Film identity findings',html);self.assertIn('model interpretations',html)
   self.assertIn('Listing and catalogue duration differ.',html)
   with self.assertRaises(Refusal):gate.authorize(self.f.state,self.f.f.selected)

 def test_installed_fake_keychain_and_wire(self):
  import json,os,shutil,subprocess,sys,sysconfig
  from ai_movie_investigator.installation import install_runtime
  f=self.f;runtime=f.root/'installed-film';runtime.mkdir(mode=0o700)
  install_runtime(Path(__file__).resolve().parent,runtime)
  manifest=json.loads((runtime/'runtime-files.json').read_text());f.manifest.clear();f.manifest.update(manifest)
  f.record['runtime_manifest_sha256']=digest(manifest);f.authority=f.pin('film-installed-authority.json',encoded(f.record))
  with f.gate():
   with self.root.transaction(write=True) as (events,_):grant=gate.proposal(self.root,events,f.f.selected.data)
   response=self.response(grant)
  template=Path('automation/snapshot_review_UNISSUED.py').read_text()
  interpreter=Path(sys.executable).resolve(strict=True);child_env=os.environ.copy()
  if sys.platform.startswith('linux'):
   interpreter=f.root/'fixture-film-python';shutil.copyfile(Path(sys.executable).resolve(strict=True),interpreter);interpreter.chmod(0o700)
   library_dir=sysconfig.get_config_var('LIBDIR')
   if library_dir:child_env['LD_LIBRARY_PATH']=library_dir
  issued=dict(runtime=str(runtime),runtime_files=manifest,python_sha256=hashlib.sha256(interpreter.read_bytes()).hexdigest(),main_acceptance_path=str(f.root/'film-acceptance.json'),authority=f.authority,account_evidence=dict(path=str(f.f.selected.path),sha256=f.f.selected.sha256),state=str(f.state),output_dir=str(f.output),root_prefix_sha256=f.record['root_prefix_sha256'],expected_slot=10)
  wrapper=f.root/'issued-film-wrapper.py';wrapper.write_text(template.replace('ISSUED = None','ISSUED = '+repr(issued),1));wrapper.chmod(0o600)
  f.pin('film-acceptance.json',encoded(dict(decision='accepted_exact_normalized_snapshot_assessment',wrapper_sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),issued_pins=issued)))
  driver="""import sys,runpy,os,errno
from pathlib import Path
if sys.platform.startswith('linux'):
 def fixture_absent_acl(*args,**kwargs):raise OSError(errno.ENODATA,'fixture absent ACL')
 os.getxattr=fixture_absent_acl
 print('LINUX_FIXTURE_ACL_SIMULATED')
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
  path=f.root/'film-driver.py';path.write_text(driver)
  result=subprocess.run([str(interpreter),'-I','-S','-B',str(path)],cwd=runtime,env=child_env,capture_output=True,timeout=60)
  self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
  self.assertIn(b'private_report_written',result.stdout)
  html=(f.output/'movie-review.html').read_text();self.assertIn('Film identity findings',html)
