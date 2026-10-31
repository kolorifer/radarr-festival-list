"""Synthetic retained issue122 recovery and truly isolated selective-package tests."""
import argparse
import base64
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from automation import coordinator_runtime as r
from automation import coordinator_recovery as recovery
from automation import coordinator_owner as owner
from automation import coordinator_cycles as cycles
from automation import coordinator_exports as exports
from automation import coordinator_io as io
from automation import coordinator_storage as storage
from automation import coordinator_transport as transport
from automation.supervisor_policy import PolicyError, PRIVATE_REPOSITORY
from test_coordinator_runtime import FakeParent, CODE, NOW, CANARY, blob, stamp
from test_coordinator import snapshot, HEAD
from test_coordinator_cycles import Crash

LEGACY = tuple(p for p in r.MANIFEST if p not in (
    'identity_research_store.py', 'torrent_research_evidence.py', 'automation/coordinator_recovery.py'))


def synthetic_pair(_):
    """Pure static exports; no producer or database operation to build fixtures."""
    from test_coordinator import movies
    movie, _ = movies()
    row = movie['cases'][0]
    row['route'] = 'eligible'
    item = dict(case_id=row['case_id'], seed=False, eligibility='explicit_unresolved',
                facts=dict(title=row['title'], year=row['year'], imdb='tt1234567', tmdb=123,
                           variants=[row['title']], contradictions=['missing_crosswalk'], director=None, runtime=None),
                provenance=[dict(source='stage1_outcome', digest=row['version'], observed_at=row['observed_at'])],
                historical_candidates=[], observed_at=row['observed_at'])
    movie['items'] = [item]
    rows = [dict(case, research_status='awaiting_evidence', proposal=None,
                 proposed_fix='Synthetic offline review only.') for case in movie['cases']]
    # Honest independent-report compatibility failure, as in the retained pilot.
    rows[0]['proposal'] = dict(current_evidence=True, evidence_version='0'*64,
                               created_at=NOW-10, search_candidates=[], result=dict(candidates=[], evidence=[]))
    from identity_triage_store import digest
    versions = {row['case_id']: digest({k:v for k,v in row.items() if k!='observed_at'}) for row in rows}
    report = dict(version=1, generated_at=NOW, coverage=deepcopy(movie['coverage']),
                  oldest_unresolved_age_seconds=100, budget={'requests':0}, cases=rows,
                  changed_cases=deepcopy(rows), versions=versions, telegram_digest_enabled=False,
                  review_controls_enabled=False, unassessed_policy='Synthetic incomplete coverage.',
                  historical_seeds='Retained synthetic evidence only.')
    return movie, report


class RecoveryTests(unittest.TestCase):
    def boundary(self):
        from test_coordinator_runtime import RuntimeTests
        f = RuntimeTests()
        with patch('test_coordinator_runtime.pair', side_effect=synthetic_pair), \
                patch('sqlite3.connect', side_effect=AssertionError('fixture database forbidden')):
            f.setUp()
        self.addCleanup(f.doCleanups)
        engineering = io.encode(snapshot())
        manifest = cycles.empty_manifest()
        for entry in manifest['sources']:
            if entry['id'] == 'engineering':
                entry.update(path='engineering.json', sha256=io.digest(engineering), revision=HEAD,
                             observed_at=NOW, collected_at=NOW)
        manifest = io.encode(manifest)
        f.req['evidence_manifest_sha256'] = io.digest(manifest)
        f.value['independent'] = dict(manifest=f.runner.pin('selected/manifest.json', manifest),
                                    engineering=f.runner.pin('selected/engineering.json', engineering), parent_status=None)
        # Nonempty actual validator input with optional function-local dependency.
        movie = io.decode(f.originals[owner.FIXED_PATHS[0]])
        evidence = {'version': 1, 'description': {'text': 'Synthetic description',
                    'digest': io.digest(b'Synthetic description')},
                    'nfo': {'text': '', 'digest': io.digest(b'')}, 'images': [],
                    'unavailable_images': 0, 'truncated': False}
        movie['items'][0]['facts']['torrent_evidence'] = evidence
        f.originals[owner.FIXED_PATHS[0]] = (json.dumps(movie, indent=2)+'\n').encode()
        f.value['code_sha256'] = {p: f.value['code_sha256'][p] for p in LEGACY}
        with patch.object(r, 'MANIFEST', LEGACY):
            f.start()
            with patch('identity_research_handoff.validate_snapshot', side_effect=Crash):
                with self.assertRaises(Crash): f.poll()
        self.assertEqual(f.runner.journal()['status'], 'preparation_uncertain')
        self.assertEqual(owner.inspect(f.req)['status'], 'collecting')
        # Original reader did install originals, but no collection/report exists.
        self.assertTrue((Path(f.req['cycle_root'])/'staging/movie/investigations.json').exists())
        original_api = f.runner.api
        def api(endpoint, **data):
            if endpoint == f'repos/{r.REPOSITORY}/git/commits/' + 'e'*40:
                return {'sha': 'e'*40, 'tree': {'sha': 'f'*40}}
            if endpoint == f'repos/{r.REPOSITORY}/git/ref/heads/automation/reporting-operation-issue-122-phase-1':
                return {'ref': r.CLAIM, 'object': {'sha': 'b'*40}}
            return original_api(endpoint, **data)
        api_patch = patch.object(f.runner, 'api', side_effect=api)
        api_patch.start(); self.addCleanup(api_patch.stop)
        f.runner.runner_revision = 'd'*40
        rt = types.SimpleNamespace(req=f.req, runner=f.runner, evidence_root=f.enclosing/'finite-phase-1')
        checkpoint, _ = recovery.capture(rt)
        f.recovery_value = dict(version=1, phase=r.PHASE, operation='partial-1',
                                original_selection=f.selection, original_start=r.origin(f.runner.messages[0], 'owner'),
                                request_sha256=r.c.fingerprint(f.req), checkpoint=checkpoint,
                                code=dict(reviewed_revision='e'*40, deployed_revision='d'*40,
                                          code_sha256={p: io.digest((CODE/p).read_bytes()) for p in r.MANIFEST}))
        return f

    def select(self, f, change=None):
        if change: change(f.recovery_value)
        f.recovery_pin = f.runner.pin('selected/recovery.json', io.encode(f.recovery_value))
        return f.command('recover', recovery=f.recovery_pin)

    def command(self, f, action):
        return f.command(action, recovery=f.recovery_pin)

    def forbidden(self):
        stack = ExitStack()
        for module, name in ((transport, 'acquire'), (owner, 'reserve'), (owner, 'seal'),
                             (r.Runtime, 'credentials'), (r, 'independent_evidence'),
                             (exports, 'stage_exports')):
            stack.enter_context(patch.object(module, name, side_effect=AssertionError('forbidden recovery edge: ' + name)))
        stack.enter_context(patch('sqlite3.connect', side_effect=AssertionError('database forbidden')))
        stack.enter_context(patch('socket.socket', side_effect=AssertionError('network forbidden')))
        stack.enter_context(patch('identity_research_provider.Provider', side_effect=AssertionError('provider forbidden')))
        return stack

    def ack(self, f, change=None):
        j = f.runner.journal()
        # Explicit separate recipient selection after reading the actual payload.
        payload = r.io.decode(f.runner.remote_file)
        self.assertEqual(payload['observed_at'], NOW)
        ack = dict(version=1, phase=r.PHASE, operation='partial-1', selection=f.selection,
                   binding=j['attempt'], recipient_chat=f.value['recipient_chat'],
                   ingestion_reference='separate-synthetic-chat-ingestion', observed_at=NOW,
                   publication=j['publication'], recovery=f.recovery_pin)
        if change: change(ack)
        return f.command('ack', recovery=f.recovery_pin,
                         acknowledgement=f.runner.pin('selected/recovery-ack.json', io.encode(ack)))

    def test_complete_ordinary_poll_recovery_distinct_ack_archive_preserves_originals(self):
        f = self.boundary(); original = f.runner.journal()
        originals = {p: (Path(f.req['intake_root'])/p).read_bytes() for p in owner.FIXED_PATHS}
        seal_path = Path(f.req['base'])/('seal-'+r.c.fingerprint(f.req)+'.json')
        seal = seal_path.read_bytes()
        self.select(f)
        with self.forbidden():
            f.poll()
            self.assertEqual(f.runner.journal()['status'], 'published')
            report = io.decode(f.runner.remote_file)
            self.assertEqual(report['observed_at'], NOW)
            self.assertEqual(report['report']['movies']['status'], 'unavailable')
            self.assertEqual(report['report']['sources']['engineering']['status'], 'available')
            self.assertEqual(owner.inspect(f.req)['collection'], 'interrupted')
            self.assertFalse(owner.inspect(f.req)['archived'])
            with patch.object(r, 'fetch', side_effect=AssertionError('inert recovery must be quiet')):
                f.poll()
            self.ack(f); f.poll()
            self.assertTrue(owner.inspect(f.req)['archived'])
            with patch.object(r, 'fetch', side_effect=AssertionError('archive must be quiet')):
                f.poll()
        self.assertEqual(f.runner.journal()['request'], original['request'])
        self.assertEqual(f.runner.journal()['selection'], original['selection'])
        self.assertEqual(f.runner.journal()['start'], original['start'])
        self.assertEqual(seal_path.read_bytes(), seal)
        self.assertEqual(originals, {p: (Path(f.req['intake_root'])/p).read_bytes() for p in owner.FIXED_PATHS})
        retained = io.decode((f.enclosing/'finite-phase-1'/recovery.RETAINED).read_bytes())
        self.assertEqual(io.decode(base64.b64decode(retained['parent/journal'])), original)
        self.assertEqual((f.runner.claims, f.runner.acquisitions, f.runner.puts), (1, 1, 1))

    def test_later_recovery_uses_original_observation_clock_and_never_refreshes(self):
        f = self.boundary()
        comment = self.select(f)
        comment['created_at'] = comment['updated_at'] = stamp(NOW + 7200)
        before = {p: (Path(f.req['intake_root'])/p).read_bytes() for p in owner.FIXED_PATHS}
        with patch.object(r.time, 'time', return_value=NOW + 7200), self.forbidden():
            f.poll()
            self.assertEqual(io.decode(f.runner.remote_file)['observed_at'], NOW)
            ack = self.ack(f, lambda a: a.update(observed_at=NOW+7200))
            ack['created_at'] = ack['updated_at'] = stamp(NOW+7200)
            f.poll()
        self.assertTrue(owner.inspect(f.req)['archived'])
        self.assertEqual(before, {p: (Path(f.req['intake_root'])/p).read_bytes() for p in owner.FIXED_PATHS})
        self.assertEqual((f.runner.claims, f.runner.acquisitions, f.runner.puts), (1,1,1))

    def test_recovery_lost_put_is_readback_only_and_ack_carries_transition(self):
        f=self.boundary(); self.select(f); f.runner.put_error=True
        with self.forbidden():
            with self.assertRaises(PolicyError): f.poll()
            f.poll()
            self.command(f, 'reconcile'); f.poll()
            self.ack(f, lambda a: a.update(recovery=dict(f.recovery_pin, sha256='0'*64)))
            before=f.runner.journal()
            with self.assertRaises(PolicyError): f.poll()
            self.assertEqual(f.runner.journal(), before)
            f.runner.messages.pop()
            self.ack(f); f.poll()
        self.assertEqual(f.runner.puts, 1)
        self.assertTrue(owner.inspect(f.req)['archived'])

    def test_prepare_and_completed_handoff_interruptions_require_fresh_continuation(self):
        for point in ('before-prepare', 'after-prepare', 'after-handoff', 'before-publish', 'before-binding'):
            with self.subTest(point=point):
                f=self.boundary(); self.select(f)
                if point in ('before-prepare', 'after-prepare'):
                    module, name = owner, 'prepare'
                elif point == 'after-handoff':
                    module, name = owner, 'handoff'
                else:
                    module, name = r.Runtime, 'publish' if point == 'before-publish' else 'persist'
                original = getattr(module, name)
                def interrupted(*a, **k):
                    if point in ('before-prepare', 'before-publish'):
                        raise Crash()
                    if point == 'before-binding' and k.get('status') == 'handoff_ready':
                        raise Crash()
                    result = original(*a, **k)
                    if point in ('after-prepare', 'after-handoff'):
                        raise Crash()
                    return result
                with self.forbidden():
                    with patch.object(module, name, side_effect=interrupted, autospec=module is r.Runtime):
                        with self.assertRaises(Crash): f.poll()
                    with patch.object(r,'fetch',side_effect=AssertionError('consumed continuation is quiet')): f.poll()
                    self.command(f,'continue'); f.poll()
                    self.assertEqual(f.runner.journal()['status'],'published')
                    self.ack(f); f.poll()
                self.assertEqual((f.runner.claims,f.runner.acquisitions,f.runner.puts),(1,1,1))
                f.doCleanups()

    def test_unexposed_handoff_does_not_gain_another_handoff(self):
        f=self.boundary(); self.select(f)
        original=cycles.handoff
        def lost(*a,**k):
            original(*a,**k); raise Crash()
        with self.forbidden():
            with patch.object(cycles,'handoff',side_effect=lost):
                with self.assertRaises(Crash): f.poll()
            self.command(f,'continue')
            with patch.object(owner,'handoff',side_effect=AssertionError('no second handoff')):
                with self.assertRaises(PolicyError): f.poll()
            with patch.object(r,'fetch',side_effect=AssertionError('failed continuation quiet')): f.poll()
        self.assertEqual(f.runner.puts,0)

    def test_initial_tampered_boundaries_are_read_only_and_consumed_commands_quiet(self):
        for problem in ('checkpoint','type','original-start','state','seal','independent','mode','symlink','receipt','output','report','clock','claim','code','pin','owner','edited'):
            with self.subTest(problem=problem):
                f=self.boundary()
                change=None
                if problem=='checkpoint': change=lambda v:v['checkpoint']['files']['stage/independent.json'].update(sha256='0'*64)
                if problem=='type': change=lambda v:v['checkpoint']['files']['stage/independent.json']['metadata'].__setitem__(-1, True)
                if problem=='original-start': change=lambda v:v['original_start'].update(id=True)
                if problem=='clock': change=lambda v:v.update(request_sha256='0'*64)
                if problem=='code': change=lambda v:v['code']['code_sha256'].update({'automation/coordinator_runtime.py':'0'*64})
                self.select(f,change)
                if problem in ('state','report'):
                    p=Path(f.req['cycle_root'])/'state.json'; value=io.decode(p.read_bytes())
                    if problem=='state': value['collecting']=None
                    else: value['baseline']='0'*64
                    p.write_bytes(io.encode(value))
                if problem=='seal': (Path(f.req['intake_root'])/owner.FIXED_PATHS[0]).write_bytes(b'changed')
                p=Path(f.req['cycle_root'])/'staging/independent.json'
                if problem=='independent': p.write_bytes(b'{}')
                if problem=='mode': p.chmod(0o644)
                if problem=='symlink': p.rename(p.with_suffix('.saved'));p.symlink_to(p.with_suffix('.saved'))
                if problem=='receipt':
                    p=Path(f.req['receipt_root'])/'recipient.json';p.write_bytes(b'{}');p.chmod(0o600)
                if problem=='output':
                    p=Path(f.req['parent_output']);p.write_bytes(b'{}');p.chmod(0o600)
                if problem=='claim':
                    original=f.runner.api
                    def bad(endpoint,**data):
                        value=original(endpoint,**data)
                        if '/git/ref/' in endpoint:value['object']['sha']='0'*40
                        return value
                    self.enter_patch(patch.object(f.runner,'api',side_effect=bad))
                if problem=='pin': f.runner.messages[-1]['body']=f.runner.messages[-1]['body'].replace(f.recovery_pin['sha256'],'0'*64)
                if problem=='owner': f.runner.messages[-1]['user']['login']='worker'
                if problem=='edited': f.runner.messages[-1]['updated_at']=stamp(NOW+1)
                before={str(p):p.read_bytes() for p in f.enclosing.rglob('*') if p.is_file()}
                with self.forbidden():
                    if problem=='owner': f.poll()
                    else:
                        with self.assertRaises((PolicyError, ValueError)):f.poll()
                self.assertEqual(before,{str(p):p.read_bytes() for p in f.enclosing.rglob('*') if p.is_file()})
                self.assertEqual(f.runner.puts,0)
                if problem not in ('owner','edited'):
                    with patch.object(r,'fetch',side_effect=AssertionError('refused command quiet')):f.poll()
                # Release patches for each temporary fixture before next iteration.
                f.doCleanups()

    def enter_patch(self, item):
        result=item.start();self.addCleanup(item.stop);return result

    def test_publication_import_and_archive_interruptions_use_retained_authorization(self):
        for point in ('observation', 'publication-import', 'recipient-import', 'archive'):
            with self.subTest(point=point):
                f=self.boundary();self.select(f)
                with self.forbidden():
                    if point in ('observation','publication-import'):
                        original=r.Runtime.install_receipt if point=='observation' else owner.receipt
                        def interrupted(*a,**k):
                            if point=='observation': raise Crash()
                            result=original(*a,**k); raise Crash()
                        module,name=(r.Runtime,'install_receipt') if point=='observation' else (owner,'receipt')
                        with patch.object(module,name,side_effect=interrupted,autospec=module is r.Runtime):
                            with self.assertRaises(Crash): f.poll()
                        self.command(f,'reconcile');f.poll()
                    else:
                        f.poll()
                    self.ack(f)
                    if point in ('recipient-import','archive'):
                        original=owner.receipt if point=='recipient-import' else owner.archive
                        def interrupted(*a,**k):
                            result=original(*a,**k);raise Crash()
                        with patch.object(owner,'receipt' if point=='recipient-import' else 'archive',side_effect=interrupted):
                            with self.assertRaises(Crash):f.poll()
                    f.poll()
                self.assertTrue(owner.inspect(f.req)['archived'])
                self.assertEqual(f.runner.puts,1)
                f.doCleanups()

    def test_inert_recovery_does_not_starve_other_issue_and_done_stops(self):
        f=self.boundary();self.select(f)
        with self.forbidden():f.poll()
        with patch.object(r,'fetch',side_effect=AssertionError('inert recovery private fetch')):
            self.assertIsNone(f.runner.eligible(f.runner.issue,'owner'))
        # Use the actual discovery poll with a different eligible engineering issue.
        f.runner.discovery=True
        other=dict(f.runner.issue,number=120,url=f'https://api.github.com/repos/{r.REPOSITORY}/issues/120')
        from test_github_worker import TASK
        messages=deepcopy(f.runner.messages)
        original_comments=f.runner.comments
        with patch.object(f.runner,'gh',return_value=json.dumps([[f.runner.issue,other]])), \
                patch.object(f.runner,'comments',side_effect=lambda: messages if f.runner.args.issue==122 else [dict(id=900,user={'login':'owner'},body=TASK)]), \
                patch.object(f.runner,'run_selected',return_value=None) as engineering, \
                patch.object(r,'fetch',side_effect=AssertionError('inert recovery private fetch')):
            f.poll()
            self.assertEqual(engineering.call_count,1)
        f.runner.discovery=False;f.runner.args.issue=122;f.runner.select_issue(122)
        f.runner.comment({},body='STATE: DONE')
        with patch.object(r,'fetch',side_effect=AssertionError('DONE private fetch')):f.poll()

    def test_isolated_selective_package_nonempty_validation_and_complete_recovery(self):
        f=self.boundary();self.select(f)
        bundle=f.root/'installed'
        bundle.mkdir(mode=0o700)
        for name in r.MANIFEST:
            path=bundle/name;path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(CODE/name,path)
        # Only declared runtime files, without test modules or the full checkout.
        config=dict(root=str(f.root),home=str(f.home),dispatch=str(f.runner.dispatch_dir),
                    enclosing=str(f.enclosing),req=f.req,value=f.value,selection=f.selection,
                    recovery=f.recovery_pin,messages=f.runner.messages,registry={key:[path,base64.b64encode(raw).decode()] for key,(path,raw) in f.runner.registry.items()})
        conf=f.root/'isolated-fixture.json';conf.write_bytes(io.encode(config));conf.chmod(0o600)
        harness = '''
import argparse, base64, contextlib, datetime as dt, hashlib, json, os
from copy import deepcopy
from pathlib import Path
import socket, sqlite3, stat, subprocess, sys, types
from unittest.mock import patch
CODE=Path(sys.argv[1]); sys.path.insert(0,str(CODE))
from automation import github_worker as worker
from automation import coordinator_runtime as r
from automation import coordinator_transport as t
from automation import coordinator_storage as storage
from automation import coordinator_owner as owner
from automation import coordinator_cycles as cycles
from automation import coordinator_exports as exports
from automation import coordinator_io as io
from automation.supervisor_policy import PRIVATE_REPOSITORY
CANARY='SYNTHETIC_PRIVATE_NO_PUBLIC_OUTPUT'
NOW=1800000000
'''+inspect.getsource(blob)+'\n'+inspect.getsource(stamp)+'\n'+inspect.getsource(FakeParent)+'''
v=io.decode(Path(sys.argv[2]).read_bytes())
root=Path(v['root']);home=Path(v['home'])
p=FakeParent.__new__(FakeParent)
p.repo=CODE
p.args=argparse.Namespace(repo=CODE,github_repo=r.REPOSITORY,issue=122,dry_run=False,once=True,interval=60,base='main')
p.dispatch_dir=Path(v['dispatch']);p.runner_revision='d'*40;p.discovery=False
p.global_lock_fd=p.lock_fd=None;p.probe_file=p.dispatch_dir/'quota-refresh.json'
p.select_issue(122)
p.issue=dict(number=122,state='open',user={'login':'owner'},url=f'https://api.github.com/repos/{r.REPOSITORY}/issues/122')
p.messages=v['messages'];p.registry={key:(path,base64.b64decode(raw)) for key,(path,raw) in v['registry'].items()};p.events=[]
p.puts=0;p.claims=1;p.acquisitions=1;p.private=True
p.claim_error=p.put_error=p.readback_error=False;p.current_commit=p.remote_file=None
original_api=p.api
def api(endpoint,**data):
    if endpoint==f'repos/{r.REPOSITORY}/git/commits/'+'e'*40:return dict(sha='e'*40,tree=dict(sha='f'*40))
    if endpoint==f'repos/{r.REPOSITORY}/git/ref/heads/automation/reporting-operation-issue-122-phase-1':return dict(ref=r.CLAIM,object=dict(sha='b'*40))
    if endpoint.endswith('/git/refs'):raise AssertionError('new claim forbidden')
    return original_api(endpoint,**data)
p.api=api
original_stat,original_fstat=os.stat,os.fstat
ancestors={(x.stat().st_dev,x.stat().st_ino) for x in root.parents}
def safe(s):
    if (s.st_dev,s.st_ino) in ancestors:
        values=list(s);values[0]&=~0o022;values[4]=0;return os.stat_result(values)
    return s
# Read audit also rejects any accidental full-checkout/test-source fallback.
stdlib=Path(os.__file__).parent
allowed=(root,stdlib)
def audit(event,args):
    if event.startswith(('socket.','subprocess.','sqlite3.')):raise AssertionError('forbidden isolated edge')
    if event=='open' and isinstance(args[0],str) and os.path.isabs(args[0]):
        path=Path(args[0])
        if not (any(path==base or base in path.parents for base in allowed)
                or (path in root.parents and args[2] & os.O_DIRECTORY)):
            raise AssertionError('isolated file outside declared bundle/fixture/stdlib')
sys.addaudithook(audit)
with contextlib.ExitStack() as stack:
    stack.enter_context(patch.object(storage.os,'stat',side_effect=lambda *a,**k:safe(original_stat(*a,**k))))
    stack.enter_context(patch.object(storage.os,'fstat',side_effect=lambda *a,**k:safe(original_fstat(*a,**k))))
    stack.enter_context(patch.object(storage.pwd,'getpwuid',return_value=types.SimpleNamespace(pw_dir=str(home))))
    stack.enter_context(patch.object(storage,'acl_identity',return_value='synthetic-acl'))
    stack.enter_context(patch.object(r.time,'time',return_value=NOW))
    from identity_research_handoff import validate_snapshot
    raw=io.read_bytes(Path(v['req']['intake_root']),owner.FIXED_PATHS[0],exports.LIMIT)
    movie=io.decode(raw)
    assert movie['items'] and 'torrent_evidence' in movie['items'][0]['facts']
    if sys.argv[3]=='validate':
        validate_snapshot(movie,NOW)
        print('validator-ok')
        raise SystemExit(0)
    # Original-byte offline stage in a fresh disposable local fixture, first.
    staged=root/'isolated-reader'
    result=exports.stage_exports(Path(v['req']['intake_root']),staged,NOW)
    assert result['sources']['research_report']['status']=='inconsistent'
    assert (staged/'investigations.json').read_bytes()==raw
    assert result['sources']['investigations']['status']=='available'
    for module,name in ((t,'acquire'),(owner,'reserve'),(owner,'seal'),(r.Runtime,'credentials'),(r,'independent_evidence'),(exports,'stage_exports')):
        stack.enter_context(patch.object(module,name,side_effect=AssertionError('forbidden recovery edge')))
    with worker.lock(p.dispatch_dir/'dispatcher.lock') as p.global_lock_fd:p.poll()
    assert p.journal()['status']=='published'
    payload=io.decode(p.remote_file)
    assert payload['observed_at']==NOW
    assert payload['report']['movies']['status']=='unavailable'
    assert payload['report']['sources']['engineering']['status']=='available'
    j=p.journal()
    ack=dict(version=1,phase=r.PHASE,operation='partial-1',selection=v['selection'],binding=j['attempt'],recipient_chat=v['value']['recipient_chat'],ingestion_reference='separate-isolated-recipient-ingestion',observed_at=NOW,publication=j['publication'],recovery=v['recovery'])
    selected=p.pin('selected/isolated-ack.json',io.encode(ack))
    p.comment(dict(action='ack',phase=r.PHASE,selection=v['selection'],recovery=v['recovery'],acknowledgement=selected))
    with worker.lock(p.dispatch_dir/'dispatcher.lock') as p.global_lock_fd:p.poll()
    assert p.journal()['status']=='archived' and owner.inspect(v['req'])['archived']
    assert (p.claims,p.acquisitions,p.puts)==(1,1,1)
    with patch.object(r,'fetch',side_effect=AssertionError('completed polling must be quiet')):
        with worker.lock(p.dispatch_dir/'dispatcher.lock') as p.global_lock_fd:p.poll()
print('isolated-recovery-archive-ok')
'''
        # -S removes site packages too; only stdlib and declared installed bundle.
        command=[sys.executable,'-I','-B','-S','-c',harness,str(bundle),str(conf),'validate']
        for missing in ('identity_research_store.py','torrent_research_evidence.py'):
            path=bundle/missing;path.rename(path.with_suffix('.withheld'))
            result=subprocess.run(command,cwd=f.root,env={'PATH':os.defpath},capture_output=True,text=True,timeout=90)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('ModuleNotFoundError',result.stderr)
            self.assertIn(missing[:-3],result.stderr)
            path.with_suffix('.withheld').rename(path)
        result=subprocess.run(command,cwd=f.root,env={'PATH':os.defpath},capture_output=True,text=True,timeout=90)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('validator-ok',result.stdout)
        command[-1]='recover'
        result=subprocess.run(command,cwd=f.root,env={'PATH':os.defpath},capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('isolated-recovery-archive-ok',result.stdout)
