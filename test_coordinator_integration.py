"""Synthetic offline boundary tests; no host state, network or execution claims."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import io
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from automation import coordinator as c
from automation import coordinator_io as files
from automation import coordinator_sources as sources
from automation import coordinator_parent as parent
from automation import coordinator_outbox as outbox
from automation import coordinator_integration as cli
from automation import github_worker as worker
from automation.supervisor_policy import PRIVATE_REPOSITORY, PolicyError
from identity_investigation_report import write_report
from identity_triage_store import digest as producer_digest
from test_coordinator import NOW, HEAD, snapshot, movies
from test_identity_research import case as research_case

CANARY = 'SYNTHETIC_PRIVATE_TEXT_PATH_AUTHORIZATION_CAPABILITY'


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(files.encode(value))
    return path


def pair(root):
    """Use the actual review-report writer with an isolated in-memory store."""
    export, _ = movies()
    row = export['cases'][0]
    row['route'] = 'eligible'
    item = research_case(seed=False)
    item.update(case_id=row['case_id'], observed_at=row['observed_at'])
    item['facts'].update(title=row['title'], year=row['year'], tmdb=123)
    item['provenance'][0].update(digest=row['version'], observed_at=row['observed_at'])
    export['items'] = [item]
    version = producer_digest({k: v for k, v in item.items() if k != 'observed_at'})
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript('CREATE TABLE evidence(case_id,version); CREATE TABLE proposals(created,result,version); CREATE TABLE jobs(case_id,status,version);')
    for idx, row in enumerate(export['cases']):
        ver = version if idx == 0 else 'd' * 64
        db.execute('INSERT INTO evidence VALUES (?,?)', (row['case_id'], ver))
        db.execute('INSERT INTO proposals VALUES (?,?,?)', (NOW - 10, json.dumps({
            'candidates': [{'record': {'id': 321, 'type': 'movie'}}],
            'evidence': [{'method': 'details', 'query': 321, 'result': {'reason': 'ok',
                           'data': {'private': CANARY}}}]}), ver))
        db.execute('INSERT INTO jobs VALUES (?,?,?)', (row['case_id'], 'awaiting_evidence', ver))
    class Store:
        @contextmanager
        def tx(self):
            yield db
        def summary(self):
            return {'requests': 0}
    try:
        write_report(root, export, Store())
        report = json.loads((root / 'review-report.json').read_text())
    finally:
        db.close()
    return export, report


def parent_fixture(root, issue=113):
    """Actual parent writers, with all external methods replaced by inert stubs."""
    runner = worker.Runner.__new__(worker.Runner)
    runner.args = SimpleNamespace(github_repo=c.REPOSITORY, issue=issue)
    runner.state_dir = root / str(issue)
    runner.state_dir.mkdir(parents=True)
    runner.state = {'consumed': [1], 'notifications': {'raw': CANARY}}
    worker.save(runner.state_dir / 'state.json', runner.state)
    runner.claimed_task = 1
    runner.execution_commit = HEAD
    runner.execution_checkout = None
    runner.runner_revision = HEAD
    runner.execution_outcome = None
    runner.branch = f'automation/issue-{issue}-worker'
    runner.verification = dict.fromkeys(('inputs_verified', 'inputs_unchanged', 'public_checkout_unchanged', 'artifact_readback'), False)
    runner.artifact_reference = None
    runner.post = lambda _: None
    runner.record_outcome(1, child_process='exited', worker_state='READY_FOR_REVIEW', code_publication='completed')
    with runner.heartbeat(1):
        pass
    runner.terminal({'body': 'synthetic task'}, 1, 'READY_FOR_REVIEW', 'OK')
    return runner


def intent(issue=113, task=1):
    return {'identity': {'repository': c.REPOSITORY, 'issue': issue, 'task': task},
            'destination': {'repository': PRIVATE_REPOSITORY, 'path': 'operations/synthetic-report.json',
                            'expected_blob': 'absent'}}


def parallel_poll(state, result):
    # Spawned process, independent interpreter and fcntl acquisition.
    report = c.findings(snapshot(), NOW)
    value = outbox.poll(Path(state), lambda: report)
    result.put((value['changed'], value['pending_outbox'][0]['id']))


def synthetic_stage(root):
    export, report = pair(root)
    contents = {'engineering': snapshot(), 'investigations': export, 'research_report': report}
    entries = []
    for source in sources.SOURCES:
        content = contents.get(source)
        name = source + '.json' if content is not None else None
        if name:
            put(root, name, content)
        entries.append({'id': source, 'path': name,
                        'sha256': files.digest(files.encode(content)) if name else None,
                        'revision': HEAD if source == 'engineering' else None,
                        'generated_at': NOW if source in ('investigations', 'research_report') else None,
                        'observed_at': NOW if source == 'engineering' else None,
                        'collected_at': NOW, 'max_age_seconds': sources.MAX_AGE[source]})
    value = {'version': 1, 'repository': c.REPOSITORY, 'sources': entries}
    put(root, 'manifest.json', value)
    return value


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.staged = self.root / 'staged'
        self.staged.mkdir(mode=0o700)
        self.state = self.root / 'state.json'
        self.report = c.findings(snapshot(), NOW)

    def staged_pair(self):
        return synthetic_stage(self.staged)

    def update_source(self, manifest, source, change):
        entry = next(e for e in manifest['sources'] if e['id'] == source)
        value = files.read_json(self.staged, entry['path'])
        change(value)
        raw = files.encode(value)
        (self.staged / entry['path']).write_bytes(raw)
        entry['sha256'] = files.digest(raw)
        put(self.staged, 'manifest.json', manifest)


class SourceTests(Base):
    def test_actual_producer_pair_complete_set_eligible_retained_and_coverage(self):
        self.staged_pair()
        report = sources.observations(self.staged, 'manifest.json', NOW)
        movie = report['movies']
        self.assertEqual(movie['status'], 'partial')
        self.assertEqual(movie['coverage'], 'incomplete_upstream')
        self.assertEqual(len(movie['known_cases']), 2)
        self.assertEqual(movie['known_cases'], files.read_json(self.staged, 'investigations.json')['cases'])
        self.assertEqual(movie['upstream_coverage'], files.read_json(self.staged, 'investigations.json')['coverage'])
        self.assertEqual(len(movie['eligible_cases']), 1)
        occurrences = movie['groups'][0]['occurrences']
        self.assertEqual([r['evidence'] for r in occurrences], ['fresh', 'retained'])
        self.assertTrue(all(r['acquisition_approval'] == 'unknown' for r in occurrences))
        self.assertEqual(report['sources']['research_report']['status'], 'available')
        self.assertEqual(report['quality']['status'], 'unavailable')
        self.assertFalse(report['quality']['review_completed'])
        self.assertNotIn(CANARY, json.dumps(report))

    def test_mismatched_ids_base_fields_occurrence_versions_and_coverage(self):
        for change in (lambda r: r['cases'].pop(),
                       lambda r: r['cases'][0].update(year=2001),
                       lambda r: r['cases'][0].update(version='f'*64),
                       lambda r: r['coverage'].update(source_releases_observed=100),
                       lambda r: r['cases'][0]['proposal'].update(evidence_version='f'*64),
                       lambda r: r['versions'].update({'outcome-'+'a'*64: 'f'*64}),
                       lambda r: r['changed_cases'].clear() or r['changed_cases'].append({'case_id': 'wrong'})):
            with self.subTest(change=change):
                manifest = self.staged_pair()
                self.update_source(manifest, 'research_report', change)
                result = sources.observations(self.staged, 'manifest.json', NOW)
                self.assertEqual(result['sources']['research_report']['status'], 'inconsistent')
                self.assertEqual(result['movies']['status'], 'partial')
                self.assertEqual(len(result['movies']['known_cases']), 2)
                self.assertEqual(len(result['goals']), 1)

    def test_base_mismatch_with_valid_report_hash_still_rejected(self):
        manifest = self.staged_pair()
        def change(report):
            report['cases'][0]['year'] += 1
            row = report['cases'][0]
            report['versions'][row['case_id']] = producer_digest({k: v for k, v in row.items() if k != 'observed_at'})
            report['changed_cases'] = deepcopy(report['cases'])
        self.update_source(manifest, 'research_report', change)
        self.assertEqual(sources.observations(self.staged, 'manifest.json', NOW)['movies']['reason'], 'incompatible_report')

    def test_exact_hour_48hour_and_future_boundaries(self):
        for source, delta, expected in (('investigations', -3600, 'stale'),
                                        ('research_report', -172800, 'stale'),
                                        ('investigations', 301, 'inconsistent'),
                                        ('research_report', 301, 'inconsistent')):
            with self.subTest(source=source, delta=delta):
                manifest = self.staged_pair()
                self.update_source(manifest, source, lambda r: r.update(generated_at=NOW+delta))
                next(e for e in manifest['sources'] if e['id'] == source)['generated_at'] = NOW + delta
                put(self.staged, 'manifest.json', manifest)
                result = sources.observations(self.staged, 'manifest.json', NOW)
                self.assertEqual(result['sources'][source]['status'], expected)
                self.assertEqual(len(result['goals']), 1)

    def test_five_minute_future_skew_accepted(self):
        manifest = self.staged_pair()
        self.update_source(manifest, 'investigations', lambda r: r.update(generated_at=NOW+300))
        next(e for e in manifest['sources'] if e['id'] == 'investigations')['generated_at'] = NOW+300
        put(self.staged, 'manifest.json', manifest)
        self.assertEqual(sources.observations(self.staged, 'manifest.json', NOW)['sources']['investigations']['status'], 'available')

    def test_old_proposal_is_retained_future_proposal_rejected(self):
        for delta, expected in ((-172800, 'available'), (301, 'inconsistent')):
            manifest = self.staged_pair()
            def change(report):
                report['cases'][0]['proposal']['created_at'] = NOW + delta
                row = report['cases'][0]
                report['versions'][row['case_id']] = producer_digest({k: v for k, v in row.items() if k != 'observed_at'})
                report['changed_cases'] = deepcopy(report['cases'])
            self.update_source(manifest, 'research_report', change)
            result = sources.observations(self.staged, 'manifest.json', NOW)
            self.assertEqual(result['sources']['research_report']['status'], expected)
            if delta < 0:
                self.assertEqual(result['movies']['groups'][0]['occurrences'][0]['evidence'], 'retained')

    def test_missing_report_does_not_claim_successful_empty_review(self):
        manifest = self.staged_pair()
        (self.staged / 'research_report.json').unlink()
        result = sources.observations(self.staged, 'manifest.json', NOW)
        self.assertEqual(result['movies']['status'], 'partial')
        self.assertFalse(result['movies']['review_completed'])
        self.assertEqual(len(result['movies']['known_cases']), 2)
        self.assertEqual(len(result['goals']), 1)

    def test_every_route_survives_complete_known_set(self):
        manifest = self.staged_pair()
        self.update_source(manifest, 'investigations', lambda r: r['cases'][1].update(route='verified'))
        # Incompatible report is still not allowed to erase known cases.
        result = sources.observations(self.staged, 'manifest.json', NOW)
        self.assertEqual(result['movies']['known_cases'][1]['route'], 'verified')

    def test_missing_eligible_subset_cannot_pass(self):
        manifest = self.staged_pair()
        self.update_source(manifest, 'investigations', lambda r: r['items'].clear())
        result = sources.observations(self.staged, 'manifest.json', NOW)
        self.assertEqual(result['sources']['investigations']['status'], 'inconsistent')
        self.assertEqual(result['movies']['status'], 'unavailable')

    def test_hash_revision_time_conflicts_are_isolated(self):
        for field, value in (('sha256', 'f'*64), ('revision', 'f'*40), ('observed_at', NOW-1)):
            manifest = self.staged_pair()
            manifest['sources'][0][field] = value
            put(self.staged, 'manifest.json', manifest)
            result = sources.observations(self.staged, 'manifest.json', NOW)
            self.assertEqual(result['sources']['engineering']['status'], 'inconsistent')
            self.assertEqual(len(result['movies']['known_cases']), 2)

    def test_read_time_does_not_refresh_source_and_unknown_stays_unknown(self):
        self.staged_pair()
        first = sources.observations(self.staged, 'manifest.json', NOW)
        second = sources.observations(self.staged, 'manifest.json', NOW+1)
        self.assertEqual(c.material_value(first), c.material_value(second))
        self.assertIsNone(first['sources']['investigations']['revision'])
        self.assertEqual(sources.observations(self.staged, 'manifest.json', NOW+3600)['sources']['investigations']['status'], 'stale')

    def test_availability_is_material(self):
        self.staged_pair()
        state, _ = c.reconcile_report(sources.observations(self.staged, 'manifest.json', NOW), c.empty_state())
        (self.staged / 'research_report.json').unlink()
        _, result = c.reconcile_report(sources.observations(self.staged, 'manifest.json', NOW), state)
        self.assertTrue(result['changed'])
        self.assertIn('sources', result['changed_sections'])

    def test_duplicate_keys_nonfinite_and_oversize_files_rejected_without_echo(self):
        manifest = self.staged_pair()
        entry = manifest['sources'][0]
        for raw in (b'{"private":"'+CANARY.encode()+b'","private":0}', b'{"x":NaN}', b'{"x":1e999}',
                    b' '*(c.MAX_BYTES+1)):
            (self.staged / entry['path']).write_bytes(raw)
            entry['sha256'] = files.digest(raw)
            put(self.staged, 'manifest.json', manifest)
            result = sources.observations(self.staged, 'manifest.json', NOW)
            self.assertEqual(result['sources']['engineering']['status'], 'inconsistent')
            self.assertNotIn(CANARY, json.dumps(result))
            self.assertEqual(len(result['movies']['known_cases']), 2)

    def test_manifest_explicit_expected_duplicate_identity_traversal_and_symlink(self):
        original = self.staged_pair()
        for edit in (lambda m: m['sources'].pop(),
                     lambda m: m['sources'][1].update(id='engineering'),
                     lambda m: m['sources'][1].update(path='engineering.json'),
                     lambda m: m['sources'][0].update(path='../outside.json'),
                     lambda m: m['sources'][0].update(path='/private/input.json'),
                     lambda m: m['sources'][0].update(path='sub/./x.json')):
            manifest = deepcopy(original); edit(manifest)
            put(self.staged, 'manifest.json', manifest)
            with self.assertRaises(ValueError):
                sources.observations(self.staged, 'manifest.json', NOW)
        put(self.staged, 'manifest.json', original)
        target = self.staged / 'engineering.json'
        target.unlink(); target.symlink_to(self.staged / 'investigations.json')
        self.assertEqual(sources.observations(self.staged, 'manifest.json', NOW)['sources']['engineering']['status'], 'inconsistent')

    def test_no_symlink_ancestor_fifo_directory_or_root(self):
        target = put(self.root, 'elsewhere/input.json', {})
        (self.staged / 'sub').symlink_to(target.parent, target_is_directory=True)
        (self.root / 'linked').symlink_to(self.staged, target_is_directory=True)
        for root, name in ((self.staged, 'sub/input.json'), (self.root/'linked', 'sub/input.json'),
                           (self.root, 'elsewhere')):
            with self.subTest(root=root, name=name), self.assertRaises((OSError, ValueError)):
                files.read_bytes(root, name)
        os.mkfifo(self.staged / 'pipe')
        with self.assertRaises(ValueError):
            files.read_bytes(self.staged, 'pipe')

    def test_quality_source_cannot_promote_synthetic_records_or_coerce_unknown(self):
        manifest = self.staged_pair()
        entry = manifest['sources'][-1]
        value = {'records': [], 'identity_verified': None, 'acquisition_approved': None}
        put(self.staged, 'quality.json', value)
        entry.update(path='quality.json', sha256=files.digest(files.encode(value)))
        put(self.staged, 'manifest.json', manifest)
        result = sources.observations(self.staged, 'manifest.json', NOW)
        self.assertEqual(result['sources']['quality_release']['status'], 'unavailable')
        self.assertEqual(result['quality']['identity_approval'], 'unknown')

    def test_invalid_report_without_snapshot_is_rejected(self):
        manifest = self.staged_pair()
        (self.staged/'investigations.json').unlink()
        self.update_source(manifest, 'research_report', lambda r: r.update(version=999))
        result = sources.observations(self.staged, 'manifest.json', NOW)
        self.assertEqual(result['sources']['research_report']['status'], 'inconsistent')
        self.assertEqual(result['movies']['status'], 'unavailable')


class ParentTests(Base):
    def test_actual_writers_project_read_only_no_private_text_and_unknown_liveness(self):
        parent_fixture(self.root)
        paths = list((self.root/'113').iterdir())
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
        result = parent.export_parent(self.root, 113, [1], NOW)
        parent.validate_export(result)
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['writer_liveness'], 'unknown')
        self.assertIsNone(result['event_at'])
        execution = result['records']['execution-1']['value']
        self.assertEqual(execution['code_publication'], 'completed')
        self.assertIsNone(execution['event_at'])
        self.assertEqual(result['records']['state']['value']['consumed'], [1])
        self.assertNotIn(CANARY, json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths})
        self.assertEqual({p.name for p in paths}, {p.name for p in (self.root/'113').iterdir()})

    def test_other_issue_task_one_cannot_supply_this_issue(self):
        parent_fixture(self.root, 86)
        result = parent.export_parent(self.root, 113, [1], NOW)
        self.assertEqual(result['status'], 'partial')
        self.assertIsNone(result['records']['state']['value'])
        self.assertIsNone(result['records']['terminal-1']['value'])
        s = snapshot()
        s['local']['issue'] = 86
        with self.assertRaisesRegex(ValueError, 'local_issue'):
            c.render_task(s, 'synthetic-support', 2, 'owner', NOW)
        s['local'].pop('issue')
        s['github']['comments']['86'] = {'status': 'complete', 'items': []}
        with self.assertRaisesRegex(ValueError, 'local_issue'):
            c.render_task(s, 'synthetic-support', 2, 'owner', NOW)

    def test_conflicting_identity_and_terminal_records_stay_inconsistent(self):
        parent_fixture(self.root)
        path = self.root/'113/terminal-1.json'
        original = json.loads(path.read_text())
        for change in (lambda v: v['identity'].update(issue=86),
                       lambda v: v['identity'].update(task=2),
                       lambda v: v['identity'].update(repository='other/repo'),
                       lambda v: v.update(state='FAILED', code='EXECUTION_FAILED', next_action='inspect_local')):
            value = deepcopy(original); change(value); put(self.root, '113/terminal-1.json', value)
            result = parent.export_parent(self.root, 113, [1], NOW)
            self.assertEqual(result['status'], 'inconsistent')
            self.assertEqual(result['writer_liveness'], 'unknown')

    def test_active_heartbeat_and_running_execution_are_not_liveness(self):
        runner = parent_fixture(self.root)
        runner.record_outcome(1, child_process='running')
        put(self.root, '113/heartbeat.json', {'task': 1, 'pid': os.getpid(), 'updated_at': NOW, 'active': True})
        result = parent.export_parent(self.root, 113, [1], NOW)
        self.assertEqual(result['writer_liveness'], 'unknown')
        self.assertEqual(result['records']['heartbeat']['value']['writer_liveness'], 'unknown')

    def test_selected_tasks_only_and_parent_file_failures(self):
        parent_fixture(self.root)
        put(self.root, '113/execution-2.json', {'private': CANARY})
        result = parent.export_parent(self.root, 113, [1], NOW)
        self.assertNotIn('execution-2', result['records'])
        path = self.root/'113/execution-1.json'
        path.unlink(); path.symlink_to(self.root/'113/terminal-1.json')
        result = parent.export_parent(self.root, 113, [1], NOW)
        self.assertEqual(result['records']['execution-1']['status'], 'inconsistent')
        for tasks in ([], [1, 1], list(range(1, 10)), [True]):
            with self.assertRaises(ValueError):
                parent.export_parent(self.root, 113, tasks, NOW)

    def test_parent_projection_staged_without_manufacturing_event_time(self):
        manifest = self.staged_pair()
        parent_fixture(self.root)
        value = parent.export_parent(self.root, 113, [1], NOW)
        put(self.staged, 'parent.json', value)
        entry = next(e for e in manifest['sources'] if e['id'] == 'parent_status')
        entry.update(path='parent.json', sha256=files.digest(files.encode(value)))
        put(self.staged, 'manifest.json', manifest)
        result = sources.observations(self.staged, 'manifest.json', NOW)
        self.assertEqual(result['parent']['issue'], 113)
        self.assertIsNone(result['sources']['parent_status']['observed_at'])
        self.assertEqual(result['sources']['parent_status']['collected_at'], NOW)
        self.assertEqual(result['parent']['writer_liveness'], 'unknown')

    def test_projection_cannot_hide_conflicts_or_missing_consumption(self):
        parent_fixture(self.root)
        result = parent.export_parent(self.root, 113, [1], NOW)
        result['records']['state']['value']['consumed'] = []
        with self.assertRaisesRegex(ValueError, 'status_conflict'):
            parent.validate_export(result)
        put(self.root, '113/state.json', {'consumed': []})
        self.assertEqual(parent.export_parent(self.root, 113, [1], NOW)['status'], 'inconsistent')


class OutboxTests(Base):
    def prepare(self):
        result = outbox.poll(self.state, lambda: self.report, intent())
        return result['pending_outbox'][0]

    def receipt(self, item):
        runner = parent_fixture(self.root)
        value = json.loads((runner.state_dir/'terminal-1.json').read_text())
        value['verification']['artifact_readback'] = True
        content = item['payload'].encode()
        blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        value['artifacts'] = [{'repository': PRIVATE_REPOSITORY, 'path': intent()['destination']['path'],
                               'blob': blob, 'sha256': item['sha256']}]
        (self.staged/'artifact.json').write_bytes(item['payload'].encode())
        put(self.root, '113/terminal-1.json', value)
        return value

    def reconcile(self, item, receipt):
        put(self.root, '113/terminal-1.json', receipt)
        return outbox.reconcile_publication(self.state, item['id'], self.root, 113, 1,
                    files.digest(files.encode(receipt)), self.staged, 'artifact.json')

    def test_crash_after_durable_preparation_before_stdout_and_restart(self):
        # Crash the public CLI at emission, after its durable save.
        path = put(self.root, 'snapshot.json', snapshot())
        with patch('builtins.print', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                c.main(['report', '--snapshot', str(path), '--state', str(self.state)])
        first = outbox.view(self.state)
        self.assertEqual(len(first), 1)
        child = subprocess.run([sys.executable, '-m', 'automation.coordinator', 'report',
                                '--snapshot', str(path), '--state', str(self.state)],
                               check=True, capture_output=True, text=True)
        replay = json.loads(child.stdout)
        self.assertFalse(replay['changed'])
        self.assertIsNone(replay['report'])
        self.assertEqual(first, outbox.view(self.state))
        self.assertEqual(first[0]['id'], replay['pending_outbox'][0]['id'])
        self.assertEqual(first[0]['sha256'], replay['pending_outbox'][0]['sha256'])
        self.assertNotIn('payload', replay['pending_outbox'][0])
        self.assertEqual(len(outbox.read_state(self.state)['outbox']), 1)

    def test_unchanged_replay_has_same_id_bytes_hash_and_no_publication_attempt(self):
        first = self.prepare()
        again = outbox.poll(self.state, lambda: self.report, intent())
        self.assertFalse(again['changed'])
        self.assertEqual(again['pending_outbox'], [first])
        self.assertEqual(first['sha256'], files.digest(first['payload'].encode()))
        self.assertEqual(first['publication']['status'], 'pending')
        self.assertEqual(first['recipient_delivery'], 'not_configured')

    def test_concurrent_independent_processes_prepare_once(self):
        context = multiprocessing.get_context('spawn')
        results = context.Queue()
        children = [context.Process(target=parallel_poll, args=(str(self.state), results)) for _ in range(2)]
        for child in children:
            child.start()
        for child in children:
            child.join(20)
            self.assertEqual(child.exitcode, 0)
        received = [results.get(timeout=5) for _ in children]
        self.assertEqual(sum(changed for changed, _ in received), 1)
        self.assertEqual(len({identity for _, identity in received}), 1)
        self.assertEqual(len(outbox.view(self.state)), 1)
        results.close()

    def test_read_reconcile_entire_transaction_is_locked(self):
        with ThreadPoolExecutor(2) as pool:
            values = list(pool.map(lambda _: outbox.poll(self.state, lambda: self.report), range(2)))
        self.assertEqual(sum(v['changed'] for v in values), 1)
        self.assertEqual(values[0]['pending_outbox'], values[1]['pending_outbox'])

    def test_atomic_failure_keeps_prior_state_and_reports_recoverable(self):
        first = self.prepare()
        before = self.state.read_bytes()
        report = deepcopy(self.report); report['revision'] = 'f'*40
        with patch.object(c.os, 'replace', side_effect=OSError(CANARY)):
            with self.assertRaises(OSError):
                outbox.poll(self.state, lambda: report)
        self.assertEqual(self.state.read_bytes(), before)
        self.assertEqual(outbox.view(self.state), [first])
        self.assertTrue(outbox.poll(self.state, lambda: report)['changed'])

    def test_exhaustion_does_not_evict_or_commit_suppressing_material(self):
        first = self.prepare()
        before = self.state.read_bytes()
        report = deepcopy(self.report); report['revision'] = 'f'*40
        with patch.object(outbox, 'MAX_REPORTS', 1):
            result = outbox.poll(self.state, lambda: report)
        self.assertTrue(result['backpressure'])
        self.assertTrue(result['material_change_pending'])
        self.assertEqual(result['reason'], 'outbox_full')
        self.assertEqual(result['pending_outbox'], [first])
        self.assertEqual(self.state.read_bytes(), before)
        self.assertTrue(outbox.poll(self.state, lambda: report)['changed'])

    def test_payload_and_state_byte_backpressure_preserve_pending(self):
        first = self.prepare()
        before = self.state.read_bytes()
        report = deepcopy(self.report); report['revision'] = 'f'*40
        with patch.object(outbox, 'MAX_PAYLOAD', len(first['payload'].encode())):
            # Larger report is refused before any state transition.
            large = deepcopy(report); large['documentation'].append({'id': 'synthetic', 'finding': 'x'*10000})
            result = outbox.poll(self.state, lambda: large)
            self.assertEqual(result['reason'], 'report_too_large')
        with patch.object(outbox, 'MAX_STATE', len(before)+20):
            result = outbox.poll(self.state, lambda: report)
            self.assertEqual(result['reason'], 'outbox_bytes_full')
        self.assertEqual(self.state.read_bytes(), before)

    def test_legacy_migration_reprepares_without_delivered_or_reviewed_upgrade(self):
        old, _ = c.reconcile(snapshot(), c.empty_state(), NOW)
        put(self.root, self.state.name, old)
        result = outbox.poll(self.state, lambda: self.report)
        self.assertTrue(result['changed'])
        state = outbox.read_state(self.state)
        self.assertEqual(state['migration'], 'v1_reprepared_unacknowledged')
        item = state['outbox'][0]
        self.assertEqual(item['publication']['status'], 'pending')
        self.assertEqual(item['recipient_delivery'], 'not_configured')
        self.assertEqual(state['reconciliation']['work'], old['work'])

    def test_payload_corruption_is_rejected_and_not_silently_reprepared(self):
        self.prepare()
        state = json.loads(self.state.read_text())
        state['outbox'][0]['payload'] += CANARY
        put(self.root, self.state.name, state)
        with self.assertRaises(ValueError):
            outbox.poll(self.state, lambda: self.report)

    def test_suppressing_state_without_payload_is_rejected(self):
        self.prepare()
        state = json.loads(self.state.read_text())
        state['outbox'].clear()
        put(self.root, self.state.name, state)
        with self.assertRaisesRegex(ValueError, 'payload_missing'):
            outbox.poll(self.state, lambda: self.report)

    def test_exact_recovery_bytes_and_divergent_destination_refused(self):
        item = self.prepare()
        path = self.staged/'recovered.json'
        self.assertEqual(cli.recover(self.state, item['id'], path), item['sha256'])
        self.assertEqual(path.read_bytes(), item['payload'].encode())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(cli.recover(self.state, item['id'], path), item['sha256'])
        path.write_bytes(b'different')
        with self.assertRaises(ValueError):
            cli.recover(self.state, item['id'], path)

    def test_uncertain_attempt_restart_never_resends_and_receipt_does_not_ack_recipient(self):
        item = self.prepare()
        uncertain = outbox.publication_uncertain(self.state, item['id'])
        self.assertEqual(uncertain[0]['publication']['status'], 'uncertain')
        self.assertEqual(outbox.publication_uncertain(self.state, item['id']), uncertain)
        replay = outbox.poll(self.state, lambda: self.report)
        self.assertFalse(replay['changed'])
        self.assertEqual(replay['pending_outbox'], uncertain)
        receipt = self.receipt(item)
        verified = self.reconcile(item, receipt)
        self.assertEqual(verified[0]['publication']['status'], 'verified')
        self.assertEqual(verified[0]['recipient_delivery'], 'not_configured')
        self.assertEqual(self.reconcile(item, receipt), verified)
        self.assertFalse(outbox.poll(self.state, lambda: self.report)['changed'])

    def test_wrong_missing_conflicting_receipts_never_acknowledge(self):
        item = self.prepare()
        original = self.receipt(item)
        for change in (lambda r: r['identity'].update(issue=86),
                       lambda r: r['identity'].update(task=2),
                       lambda r: r['identity'].update(repository='other/repo'),
                       lambda r: r['verification'].update(artifact_readback=False),
                       lambda r: r['artifacts'].clear(),
                       lambda r: r['artifacts'][0].update(sha256='f'*64),
                       lambda r: r['artifacts'][0].update(blob='f'*40),
                       lambda r: r['artifacts'][0].update(path='operations/wrong.json'),
                       lambda r: r['artifacts'][0].update(repository='other/private'),
                       lambda r: r.update(extra=CANARY)):
            with self.subTest(change=change):
                receipt = deepcopy(original); change(receipt)
                with self.assertRaises((ValueError, PolicyError)):
                    self.reconcile(item, receipt)
                self.assertEqual(outbox.view(self.state)[0]['publication']['status'], 'pending')
        put(self.root, '113/terminal-1.json', original)
        with self.assertRaises(ValueError):
            outbox.reconcile_publication(self.state, item['id'], self.root, 113, 1,
                                        'f'*64, self.staged, 'artifact.json')
        (self.root/'113/terminal-1.json').unlink()
        with self.assertRaises(FileNotFoundError):
            outbox.reconcile_publication(self.state, item['id'], self.root, 113, 1,
                                        'f'*64, self.staged, 'artifact.json')
        self.assertEqual(outbox.view(self.state)[0]['publication']['status'], 'pending')

    def test_wrong_readback_bytes_and_untrusted_child_flags_do_not_ack(self):
        item = self.prepare()
        receipt = self.receipt(item)
        # A child result isn't a parent receipt and cannot manufacture delivery.
        with self.assertRaises((ValueError, PolicyError)):
            self.reconcile(item, {'state': 'READY_FOR_REVIEW', 'artifact_readback': True})
        (self.staged/'artifact.json').write_bytes(b'wrong content')
        with self.assertRaises(ValueError):
            self.reconcile(item, receipt)
        self.assertEqual(outbox.view(self.state)[0]['publication']['status'], 'pending')

    def test_ambiguous_failed_receipt_keeps_uncertain_until_exact_readback(self):
        item = self.prepare()
        receipt = self.receipt(item)
        outbox.publication_uncertain(self.state, item['id'])
        receipt.update(state='FAILED', code='ARTIFACT_PUBLICATION_FAILED', next_action='reconcile_private')
        receipt['verification']['artifact_readback'] = False
        receipt['artifacts'] = []
        with self.assertRaises(ValueError):
            self.reconcile(item, receipt)
        self.assertEqual(outbox.view(self.state)[0]['publication']['status'], 'uncertain')

    def test_verified_publication_does_not_depend_on_public_result_success(self):
        item = self.prepare()
        receipt = self.receipt(item)
        receipt.update(state='FAILED', code='RESULT_PUBLICATION_FAILED', next_action='reconcile_private')
        result = self.reconcile(item, receipt)
        self.assertEqual(result[0]['publication']['status'], 'verified')
        self.assertEqual(result[0]['recipient_delivery'], 'not_configured')

    def test_conflicting_later_receipt_cannot_overwrite_verified_evidence(self):
        item = self.prepare()
        receipt = self.receipt(item)
        self.reconcile(item, receipt)
        before = self.state.read_bytes()
        receipt['artifacts'][0]['blob'] = 'f'*40
        with self.assertRaises(ValueError):
            self.reconcile(item, receipt)
        self.assertEqual(self.state.read_bytes(), before)

    def test_unconfigured_publication_has_no_implicit_destination_or_sender(self):
        result = outbox.poll(self.state, lambda: self.report)
        item = result['pending_outbox'][0]
        self.assertIsNone(item['publication']['intent'])
        with self.assertRaises(ValueError):
            outbox.publication_uncertain(self.state, item['id'])

    def test_cli_fixed_public_projection_and_fixed_errors(self):
        self.staged_pair()
        with patch.object(cli.time, 'time', return_value=NOW), redirect_stdout(io.StringIO()) as capture:
            self.assertEqual(cli.main(['report', '--root', str(self.staged), '--state', str(self.state)]), 0)
        public = capture.getvalue()
        for marker in (CANARY, str(self.root), 'AUTHORIZATION', 'destination', 'payload'):
            self.assertNotIn(marker, public)
        self.assertEqual(len(json.loads(public)['pending_reports']), 1)
        (self.staged/'manifest.json').write_text('{"private":"'+CANARY+'","private":0}')
        with redirect_stdout(io.StringIO()) as capture:
            self.assertEqual(cli.main(['report', '--root', str(self.staged), '--state', str(self.state)]), 1)
        self.assertEqual(json.loads(capture.getvalue()), {'state': 'NEEDS_USER', 'reason': 'invalid_or_unavailable_input'})

    def test_foundation_cli_cannot_print_staged_private_pending_payload(self):
        self.staged_pair()
        outbox.poll(self.state, lambda: sources.observations(self.staged, 'manifest.json', NOW))
        self.assertIn('Synthetic Movie', outbox.view(self.state)[0]['payload'])
        with patch.object(c.time, 'time', return_value=NOW), redirect_stdout(io.StringIO()) as capture:
            self.assertEqual(c.main(['report', '--snapshot', str(self.staged/'engineering.json'),
                                     '--state', str(self.state)]), 0)
        self.assertNotIn('Synthetic Movie', capture.getvalue())
        self.assertTrue(all('payload' not in item for item in json.loads(capture.getvalue())['pending_outbox']))


if __name__ == '__main__':
    unittest.main()
