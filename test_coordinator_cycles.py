"""Reproducible synthetic cycle rehearsal. No external calls or private inputs."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from copy import deepcopy
import io as streams
import json
import errno
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from automation import coordinator_cycles as cycles
from automation import coordinator_io as io
from automation import coordinator_exports as exports
from automation import coordinator_parent as parent
from automation import coordinator_outbox as legacy
from automation import coordinator_sources as sources
from automation.supervisor_policy import PRIVATE_REPOSITORY
from test_coordinator import NOW, HEAD, snapshot
from test_coordinator_integration import pair, put, parent_fixture

DEST = {'repository': PRIVATE_REPOSITORY, 'path': 'operations/synthetic-cycle.json'}


class Crash(BaseException):
    pass


class CycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.base.chmod(0o700)
        self.source = self.base / 'source'
        self.source.mkdir(mode=0o700)
        export, report = pair(self.source)
        for s, content in zip(exports.EXPORTS, (export, report)):
            put(self.source, exports.EXPORTS[s], content)
        self.evidence = self.base / 'evidence'
        self.evidence.mkdir(mode=0o700)
        worker = self.base / 'synthetic-journals'
        worker.mkdir(mode=0o700)
        parent_fixture(worker)
        contents = {'engineering': snapshot(), 'parent_status': parent.export_parent(worker, 113, [1], NOW)}
        manifest = cycles.empty_manifest()
        for e in manifest['sources']:
            if e['id'] in contents:
                raw = io.encode(contents[e['id']])
                e.update(path=e['id'] + '.json', sha256=io.digest(raw), collected_at=NOW)
                if e['id'] == 'engineering':
                    e.update(observed_at=NOW, revision=HEAD)
                (self.evidence / e['path']).write_bytes(raw)
                (self.evidence / e['path']).chmod(0o600)
        put(self.evidence, 'manifest.json', manifest).chmod(0o600)
        self.root = self.base / 'cycles'
        self.inbox = self.base / 'owner-selected'
        self.inbox.mkdir(mode=0o700)

    def run_cycle(self, cid='cycle-1', now=NOW, **kw):
        args = dict(root=self.root, runtime='synthetic-runtime', owner='synthetic-owner',
                    cycle_id=cid, now=now, source_root=self.source,
                    intended_destination=DEST, recipient='original-supervisor', evidence_root=self.evidence)
        args.update(kw)
        return cycles.cycle(**args)

    def state(self):
        return io.decode((self.root / 'state.json').read_bytes())

    def record(self, rid, where='active'):
        return io.decode((self.root / where / (rid + '.json')).read_bytes())

    def handoff(self, rid):
        return cycles.handoff(self.root, 'synthetic-runtime', 'synthetic-owner', rid)

    def stage_receipt(self, rid, kind, modify=None, name=None):
        state = self.state()
        record = self.record(rid, state['reports'][rid]['location'])
        receipt = {'version': 1, 'kind': kind, 'owner': 'synthetic-owner',
                   'issuer': 'synthetic-owner' if kind == 'publication' else 'original-supervisor',
                   'binding': deepcopy(record['attempt']), 'observed_at': NOW + 100,
                   'reference': 'synthetic-owner-readback'}
        if modify:
            modify(receipt)
        name = name or kind
        put(self.inbox, name + '.json', receipt).chmod(0o600)
        payload = self.inbox / (name + '.payload')
        payload.write_bytes(record['payload'].encode())
        payload.chmod(0o600)
        return name

    def receipt(self, rid, kind, **kw):
        name = self.stage_receipt(rid, kind, **kw)
        return self.import_receipt(rid, kind, name)

    def import_receipt(self, rid, kind, name):
        return cycles.import_receipt(self.root, 'synthetic-runtime', 'synthetic-owner', rid,
                                     kind, self.inbox, name)

    def archive(self, rid):
        return cycles.archive(self.root, 'synthetic-runtime', 'synthetic-owner', rid)

    def complete(self, result):
        rid = result['report_id']
        self.handoff(rid)
        self.receipt(rid, 'publication')
        self.receipt(rid, 'recipient')
        return self.archive(rid)

    def update_engineering(self, number):
        value = snapshot()
        # Use a known validated material field rather than relying on free prose.
        value['github']['revision'] = format(number + 1, '040x')
        value['github']['branches']['items'][0]['commit']['sha'] = value['github']['revision']
        raw = io.encode(value)
        path = self.evidence / 'engineering.json'
        path.write_bytes(raw)
        manifest = io.decode((self.evidence / 'manifest.json').read_bytes())
        e = next(e for e in manifest['sources'] if e['id'] == 'engineering')
        e.update(sha256=io.digest(raw), revision=value['github']['revision'])
        put(self.evidence, 'manifest.json', manifest).chmod(0o600)

    def tree_bytes(self, root):
        return {str(p.relative_to(root)): p.read_bytes() if p.is_file() else None
                for p in root.rglob('*')}

    def test_source_and_evidence_aliases_reject_before_writes(self):
        for field, target in (('source_root', self.source), ('evidence_root', self.evidence)):
            alias = self.base / (field + '-alias')
            alias.symlink_to(target, target_is_directory=True)
            for existing in (False, True):
                with self.subTest(field=field, existing=existing):
                    self.root = target / ('existing' if existing else 'new-state')
                    if existing:
                        with cycles.store(self.root, 'synthetic-runtime', 'synthetic-owner') as (_, fd, _, state):
                            cycles.save(fd, state)
                    before = self.tree_bytes(self.base)
                    with self.assertRaises((ValueError, OSError)):
                        self.run_cycle(**{field: alias})
                    self.assertEqual(self.tree_bytes(self.base), before)

    def test_missing_source_spelling_cannot_alias_prospective_state(self):
        # Do not guess a filesystem's case/normalization rules for absent names.
        for field in ('source_root', 'evidence_root'):
            with self.subTest(field=field):
                root = self.base / 'prospective-state'
                protected = self.base / 'PROSPECTIVE-STATE' / 'missing'
                before = self.tree_bytes(self.base)
                with self.assertRaises(ValueError):
                    self.run_cycle(root=root, **{field: protected})
                self.assertEqual(self.tree_bytes(self.base), before)

    def test_initial_and_later_separation_errors_fail_closed(self):
        self.run_cycle()
        for existing in (False, True):
            root = self.root if existing else self.base / 'new-state'
            for guard in (('_outside_source', 'disjoint') if existing else ('_outside_source',)):
                target = exports if guard == '_outside_source' else cycles
                with self.subTest(existing=existing, guard=guard):
                    before = self.tree_bytes(self.base)
                    with patch.object(target, guard, side_effect=OSError(errno.EIO, 'synthetic guard')):
                        with self.assertRaises(OSError):
                            self.run_cycle('guard-failure', root=root)
                    self.assertEqual(self.tree_bytes(self.base), before)

    def test_source_identity_guard_eio_is_not_unavailability(self):
        self.run_cycle()
        source_identity = self.source.stat()
        real_outside, real_disjoint = exports._outside_source, cycles.disjoint
        for guard, real in (('_outside_source', real_outside), ('disjoint', real_disjoint)):
            target = exports if guard == '_outside_source' else cycles
            def faulty(a, b):
                if os.path.samestat(os.fstat(b), source_identity):
                    raise OSError(errno.EIO, 'synthetic source identity guard')
                return real(a, b)
            with self.subTest(guard=guard):
                before = self.tree_bytes(self.base)
                with patch.object(target, guard, side_effect=faulty):
                    with self.assertRaises(OSError):
                        self.run_cycle('source-guard-error')
                self.assertEqual(self.tree_bytes(self.base), before)

    def test_empty_evidence_rejected_before_archive(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid); self.receipt(rid, 'publication'); self.receipt(rid, 'recipient')
        path = self.root / 'active' / (rid + '.json')
        record = self.record(rid)
        self.assertTrue(record['evidence'])
        record['evidence'] = {}
        path.write_bytes(io.encode(record))
        before = self.tree_bytes(self.root)
        with self.assertRaises(ValueError):
            self.archive(rid)
        self.assertEqual(self.tree_bytes(self.root), before)

    def test_changed_original_copies_rejected_before_archive(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid); self.receipt(rid, 'publication'); self.receipt(rid, 'recipient')
        path = self.root / 'active' / (rid + '.json')
        record = self.record(rid)
        for name in ('investigations.json', 'reader/investigations.json'):
            record['evidence'][name] = cycles.pack(cycles.unpack(record['evidence'][name]) + b' ')
        path.write_bytes(io.encode(record))
        before = self.tree_bytes(self.root)
        with self.assertRaises(ValueError):
            self.archive(rid)
        self.assertEqual(self.tree_bytes(self.root), before)

    def test_prewrite_ancestor_open_stat_errors_close_only_owned_descriptors(self):
        self.run_cycle()
        real_open, real_stat, real_fstat = os.open, os.stat, os.fstat
        caller = real_open(self.source, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, caller)
        def descriptors():
            result = set()
            for fd in range(256):
                try:
                    real_fstat(fd)
                    result.add(fd)
                except OSError:
                    pass
            return result
        source_identity = real_fstat(caller)
        for existing in (False, True):
            for operation in ('ancestor_open', 'source_open', 'source_stat', 'source_fstat'):
                with self.subTest(existing=existing, operation=operation):
                    def faulty_open(name, *args, **kw):
                        if name == ('..' if operation == 'ancestor_open' else 'source'):
                            raise OSError(errno.EIO, 'synthetic open')
                        return real_open(name, *args, **kw)
                    def faulty_stat(name, *args, **kw):
                        if name == 'source':
                            raise OSError(errno.EIO, 'synthetic stat')
                        return real_stat(name, *args, **kw)
                    def faulty_fstat(fd):
                        info = real_fstat(fd)
                        if os.path.samestat(info, source_identity):
                            raise OSError(errno.EIO, 'synthetic fstat')
                        return info
                    field = 'open' if operation.endswith('open') else ('stat' if operation == 'source_stat' else 'fstat')
                    fault = faulty_open if field == 'open' else (faulty_stat if field == 'stat' else faulty_fstat)
                    before, owned = self.tree_bytes(self.base), descriptors()
                    with patch.object(cycles.os, field, side_effect=fault):
                        with self.assertRaises(OSError):
                            self.run_cycle('prewrite-failure', root=self.root if existing else self.base / 'new-state')
                    self.assertEqual(self.tree_bytes(self.base), before)
                    self.assertEqual(descriptors(), owned)
                    self.assertTrue(os.path.samestat(real_fstat(caller), source_identity))

    def test_safe_missing_and_inaccessible_inputs_preserve_partial_findings(self):
        real = exports.files.read_from_directory
        def denied(fd, name, *args, **kw):
            if name == 'incoming/snapshot.json':
                raise PermissionError(errno.EACCES, 'synthetic input')
            return real(fd, name, *args, **kw)
        for mode in ('missing-root', 'inaccessible-file'):
            with self.subTest(mode=mode):
                self.root = self.base / mode
                with patch.object(exports.files, 'read_from_directory', side_effect=denied):
                    result = self.run_cycle(source_root=self.source / 'missing' if mode == 'missing-root' else self.source)
                report = io.decode(self.record(result['report_id'])['payload'].encode())['report']
                self.assertTrue(report['goals'])
                self.assertEqual(report['sources']['engineering']['status'], 'available')
                self.assertNotEqual(report['movies']['reason'], 'incomplete_upstream')

    def test_evidence_corruption_rejected_at_every_record_entry_point(self):
        rid = self.run_cycle()['report_id']
        initial = self.record(rid)
        self.handoff(rid)
        publication = self.stage_receipt(rid, 'publication')
        recipient = self.stage_receipt(rid, 'recipient')
        self.import_receipt(rid, 'publication', publication)
        self.import_receipt(rid, 'recipient', recipient)
        complete = self.record(rid)
        state_initial = self.state()
        path = self.root / 'active' / (rid + '.json')
        def corrupt(value, mode):
            evidence = value['evidence']
            if mode == 'missing-map':
                del value['evidence']
            elif mode == 'empty':
                evidence.clear()
            elif mode == 'removed':
                del evidence['investigations.json']
            elif mode == 'substituted':
                evidence['substitute.json'] = evidence.pop('investigations.json')
            elif mode == 'extra':
                evidence['extra.json'] = cycles.pack(b'extra')
            elif mode == 'binding':
                payload = io.decode(value['payload'].encode())
                payload['evidence_binding'] = cycles.evidence_binding({})
                value['payload'] = io.encode(payload).decode()
                value['sha256'] = io.digest(value['payload'].encode())
            else:
                name = 'combined-manifest.json' if mode == 'manifest' else 'investigations.json'
                evidence[name] = cycles.pack(cycles.unpack(evidence[name]) + b' ')
        for mode in ('missing-map', 'empty', 'removed', 'substituted', 'extra', 'bytes', 'manifest', 'binding'):
            for operation in ('handoff', 'publication', 'recipient', 'archive', 'replay'):
                with self.subTest(mode=mode, operation=operation):
                    value = deepcopy(initial if operation == 'handoff' else complete)
                    corrupt(value, mode)
                    path.write_bytes(io.encode(value))
                    before = self.tree_bytes(self.root)
                    with self.assertRaises(sources.FAILURES):
                        if operation == 'handoff':
                            self.handoff(rid)
                        elif operation == 'archive':
                            self.archive(rid)
                        elif operation == 'replay':
                            self.run_cycle()
                        else:
                            self.import_receipt(rid, operation, publication if operation == 'publication' else recipient)
                    self.assertEqual(self.tree_bytes(self.root), before)
                    self.assertEqual(self.state(), state_initial)
        path.write_bytes(io.encode(complete))
        self.assertTrue(self.archive(rid)['archived'])
        archived = self.root / 'archive' / path.name
        valid = archived.read_bytes()
        # Even after the archive reference commit, reject corruption before the
        # duplicate active/handoff originals can be reclaimed.
        path.write_bytes(io.encode(complete)); path.chmod(0o600)
        value = self.record(rid, 'archive')
        value['evidence'] = {}
        archived.write_bytes(io.encode(value))
        before = self.tree_bytes(self.root)
        with self.assertRaises(ValueError):
            self.archive(rid)
        self.assertEqual(self.tree_bytes(self.root), before)
        archived.write_bytes(valid)
        self.assertTrue(self.archive(rid)['archived'])
        self.assertEqual(archived.read_bytes(), valid)

    def test_checkpoint_corruption_never_rebaselines_or_rereads(self):
        for phase in ('independent', 'collection'):
            for mode in ('missing', 'bytes', 'manifest', 'binding', 'unanchored'):
                with self.subTest(phase=phase, mode=mode):
                    self.root = self.base / (phase + '-' + mode)
                    if phase == 'independent':
                        with patch.object(exports, 'stage_exports', side_effect=Crash()):
                            with self.assertRaises(Crash):
                                self.run_cycle()
                    else:
                        real = cycles.write
                        def fail_record(fd, name, raw, replace=False):
                            if len(name) == 69:
                                raise Crash()
                            return real(fd, name, raw, replace)
                        with patch.object(cycles, 'write', side_effect=fail_record):
                            with self.assertRaises(Crash):
                                self.run_cycle()
                    path = self.root / 'staging' / (phase + '.json')
                    if mode == 'missing':
                        path.unlink()
                    elif mode in ('bytes', 'manifest'):
                        value = io.decode(path.read_bytes())
                        name = 'independent-manifest.json' if phase == 'independent' else 'combined-manifest.json'
                        if mode == 'bytes':
                            value['evidence'] = {}
                        else:
                            value['evidence'][name] = cycles.pack(b'{}')
                        # Updating a mutable local checksum must not grant trust.
                        if phase == 'collection':
                            value['evidence_binding'] = cycles.evidence_binding(value['evidence'])
                        path.write_bytes(io.encode(value))
                    else:
                        state = self.state()
                        state['cycles']['cycle-1']['checkpoints'][phase] = None if mode == 'unanchored' else 'a'*64
                        (self.root / 'state.json').write_bytes(io.encode(state))
                    before = self.tree_bytes(self.root)
                    with patch.object(exports, 'stage_exports', side_effect=AssertionError('reread')):
                        with self.assertRaises(ValueError):
                            self.run_cycle()
                    self.assertEqual(self.tree_bytes(self.root), before)

    def test_actual_hash_mismatch_evidence_archives_and_replays(self):
        original = (self.evidence / 'engineering.json').read_bytes() + b' '
        (self.evidence / 'engineering.json').write_bytes(original)
        result = self.run_cycle()
        rid = result['report_id']
        record = self.record(rid)
        payload = io.decode(record['payload'].encode())
        source = payload['report']['sources']['engineering']
        self.assertEqual(source['status'], 'inconsistent')
        self.assertTrue(any(d['stage'] == 'identity' and d['reason'] == 'hash_mismatch'
                            for d in source['diagnostics']))
        bound = payload['evidence_binding']['engineering.json']
        self.assertEqual(bound, {'sha256': io.digest(original), 'size': len(original)})
        self.assertNotEqual(bound['sha256'], next(e['sha256'] for e in io.decode(
            cycles.unpack(record['evidence']['independent-manifest.json']))['sources'] if e['id'] == 'engineering'))
        self.complete(result)
        archived = self.record(rid, 'archive')
        self.assertEqual(cycles.unpack(archived['evidence']['engineering.json']), original)
        before = self.tree_bytes(self.root)
        self.assertFalse(self.handoff(rid)['may_attempt'])
        self.receipt(rid, 'publication'); self.receipt(rid, 'recipient'); self.archive(rid)
        self.assertEqual(self.run_cycle()['report_id'], rid)
        self.assertEqual(self.tree_bytes(self.root), before)

    def test_cycle_v1_rejected_without_mutation_legacy_v2_unchanged(self):
        rid = self.run_cycle()['report_id']
        for name in ('identity.json', 'state.json'):
            path = self.root / name
            value = io.decode(path.read_bytes())
            value['version'] = 1
            path.write_bytes(io.encode(value))
        before = self.tree_bytes(self.root)
        args = ['--root', str(self.root), '--runtime', 'synthetic-runtime', '--owner', 'synthetic-owner', '--id', rid]
        for command in ('handoff', 'archive'):
            with redirect_stdout(streams.StringIO()) as captured:
                self.assertEqual(cycles.main([command] + args), 1)
            self.assertEqual(json.loads(captured.getvalue()),
                             {'state': 'NEEDS_USER', 'reason': 'invalid_or_unavailable_input'})
            self.assertEqual(self.tree_bytes(self.root), before)
        with self.assertRaises(ValueError):
            self.run_cycle()
        self.assertEqual(self.tree_bytes(self.root), before)

    def test_actual_reader_and_independent_sources_originals_survive_archive(self):
        originals = {p: ((self.source / p).stat().st_mtime_ns, (self.source / p).read_bytes())
                     for p in exports.EXPORTS.values()}
        result = self.run_cycle()
        self.assertTrue(result['changed'])
        rid = result['report_id']
        record = self.record(rid)
        report = io.decode(record['payload'].encode())['report']
        self.assertEqual(report['movies']['reason'], 'incomplete_upstream')
        self.assertEqual(report['sources']['engineering']['status'], 'available')
        self.assertEqual(report['sources']['parent_status']['status'], 'available')
        self.assertTrue(report['goals'])
        self.assertEqual(report['quality']['reason'], 'passive_export_missing')
        self.assertTrue(any(b'SYNTHETIC_PRIVATE' in cycles.unpack(raw)
                            for raw in record['evidence'].values()))
        for source, path in exports.EXPORTS.items():
            self.assertEqual(cycles.unpack(record['evidence'][source + '.json']), originals[path][1])
            self.assertEqual(cycles.unpack(record['evidence']['reader/' + source + '.json']), originals[path][1])
        self.assertNotIn('SYNTHETIC_PRIVATE', io.encode(result).decode())
        archived = self.complete(result)
        self.assertTrue(archived['archived'])
        retained = self.record(rid, 'archive')
        self.assertEqual(retained['payload'], record['payload'])
        self.assertEqual(retained['evidence'], record['evidence'])
        self.assertEqual(list((self.root / 'active').iterdir()), [])
        self.assertEqual(list((self.root / 'handoff').iterdir()), [])
        self.assertEqual(list((self.root / 'staging').iterdir()), [])
        for path, before in originals.items():
            self.assertEqual(((self.source / path).stat().st_mtime_ns, (self.source / path).read_bytes()), before)
        for path in self.root.rglob('*'):
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            if path.is_file():
                self.assertEqual(path.stat().st_nlink, 1)

    def test_same_cycle_never_recollects_conflicts_reject(self):
        first = self.run_cycle()
        self.source.rename(self.base / 'moved')
        with patch.object(exports, 'stage_exports', side_effect=AssertionError('reread')):
            self.assertEqual(first, self.run_cycle())
        for kw in ({'now': NOW + 1}, {'recipient': 'different'}, {'source_root': self.base / 'other'},
                   {'intended_destination': {**DEST, 'path': 'operations/other.json'}}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.run_cycle(**kw)

    def test_simultaneous_callers_share_one_acquisition(self):
        # Initialize the root so the test focuses on the collection lock.
        with cycles.store(self.root, 'synthetic-runtime', 'synthetic-owner'):
            pass
        real = exports.stage_exports
        with patch.object(exports, 'stage_exports', wraps=real) as collect:
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: self.run_cycle(), range(4)))
        self.assertTrue(all(r == results[0] for r in results))
        self.assertEqual(collect.call_count, 1)
        self.assertEqual(len(list((self.root / 'active').iterdir())), 1)

    def test_source_failures_keep_independent_findings(self):
        for idx, mode in enumerate(('missing', 'stale', 'conflict', 'partial', 'root', 'symlink', 'hardlink')):
            with self.subTest(mode=mode):
                self.root = self.base / ('cycles-' + mode)
                source = self.base / ('source-' + mode)
                source.mkdir(mode=0o700)
                export, report = pair(source)
                if mode == 'stale':
                    export['generated_at'] = NOW - 3600
                if mode == 'conflict':
                    report['cases'] = []
                    report['versions'] = {}
                    report['changed_cases'] = []
                for s, content in zip(exports.EXPORTS, (export, report)):
                    put(source, exports.EXPORTS[s], content)
                if mode == 'missing':
                    (source / 'incoming/snapshot.json').unlink()
                if mode == 'partial':
                    (source / 'review-report.json').unlink()
                if mode == 'root':
                    source = source / 'missing'
                if mode == 'symlink':
                    alias = self.base / 'source-alias'
                    alias.symlink_to(source, target_is_directory=True)
                    source = alias
                if mode == 'hardlink':
                    os.link(source / 'review-report.json', self.base / 'hardlink')
                if mode == 'symlink':
                    before = self.tree_bytes(self.base)
                    with self.assertRaises((ValueError, OSError)):
                        self.run_cycle('failure-' + mode, source_root=source)
                    self.assertEqual(self.tree_bytes(self.base), before)
                    continue
                result = self.run_cycle('failure-' + mode, source_root=source)
                record = self.record(result['report_id'])
                report = io.decode(record['payload'].encode())['report']
                self.assertTrue(report['goals'])
                self.assertEqual(report['sources']['engineering']['status'], 'available')
                self.assertNotEqual(report['movies']['reason'], 'incomplete_upstream')

    def test_optional_evidence_absent_and_invalid(self):
        first = self.run_cycle(evidence_root=None)
        report = io.decode(self.record(first['report_id'])['payload'].encode())['report']
        self.assertEqual(report['parent']['status'], 'unavailable')
        self.assertEqual(report['goals'], [])
        self.assertEqual(report['movies']['reason'], 'incomplete_upstream')
        (self.evidence / 'manifest.json').write_bytes(b'{}')
        self.assertFalse(self.run_cycle('missing-optional')['changed'])

    def test_quiet_refresh_current_clock_and_staging_bounded(self):
        first = self.run_cycle()
        raw = (self.root / 'active' / (first['report_id'] + '.json')).read_bytes()
        for idx in range(35):
            export = io.decode((self.source / 'incoming/snapshot.json').read_bytes())
            report = io.decode((self.source / 'review-report.json').read_bytes())
            export['generated_at'] = NOW + idx + 1
            report['generated_at'] = NOW + idx + 1
            put(self.source, 'incoming/snapshot.json', export)
            put(self.source, 'review-report.json', report)
            result = self.run_cycle('quiet-' + str(idx), now=NOW + idx + 1)
            self.assertFalse(result['changed'])
            self.assertEqual(list((self.root / 'staging').iterdir()), [])
        self.assertEqual((self.root / 'active' / (first['report_id'] + '.json')).read_bytes(), raw)
        self.assertEqual(io.decode((self.root / 'current.json').read_bytes())['observed_at'], NOW + 35)
        self.assertEqual(len(list((self.root / 'active').iterdir())), 1)
        self.assertEqual(len(self.state()['cycles']), 36)

    def test_many_failed_quiet_polls_and_count_backpressure(self):
        missing = self.base / 'missing'
        before = self.tree_bytes(self.base)
        with self.assertRaises(ValueError):
            self.run_cycle(source_root=missing)
        self.assertEqual(self.tree_bytes(self.base), before)
        # An existing state identity proves that this missing sibling cannot
        # alias it; preserve the original failed/quiet-poll and capacity checks.
        with cycles.store(self.root, 'synthetic-runtime', 'synthetic-owner') as (_, fd, _, state):
            cycles.save(fd, state)
        self.run_cycle(source_root=missing)
        for idx in range(25):
            self.assertFalse(self.run_cycle('failed-' + str(idx), source_root=missing)['changed'])
            self.assertEqual(list((self.root / 'staging').iterdir()), [])
        with patch.object(cycles, 'MAX_CYCLES', len(self.state()['cycles'])):
            self.assertTrue(self.run_cycle('exhausted', source_root=missing)['backpressure'])
        self.assertNotIn('exhausted', self.state()['cycles'])

    def test_more_than_twenty_archives_baseline_survives_restart(self):
        for idx in range(25):
            self.update_engineering(idx)
            result = self.run_cycle('material-' + str(idx))
            self.assertTrue(result['changed'])
            self.complete(result)
            self.assertFalse(self.run_cycle('quiet-' + str(idx))['changed'])
        self.assertEqual(len(list((self.root / 'archive').iterdir())), 25)
        self.assertEqual(list((self.root / 'active').iterdir()), [])
        self.assertEqual(len(self.state()['reports']), 25)
        self.assertFalse(self.run_cycle('restart-quiet')['changed'])

    def test_material_transition_and_pending_backpressure(self):
        first = self.run_cycle()
        (self.source / 'review-report.json').unlink()
        transition = self.run_cycle('transition')
        self.assertTrue(transition['changed'])
        self.assertFalse(self.run_cycle('transition-quiet')['changed'])
        self.assertNotEqual(first['report_id'], transition['report_id'])
        with patch.object(cycles, 'MAX_ACTIVE', 2):
            self.assertTrue(self.run_cycle('full')['backpressure'])
        self.assertEqual(len(list((self.root / 'active').iterdir())), 2)
        with self.assertRaises(ValueError):
            self.archive(first['report_id'])

    def test_attempt_is_uncertain_single_opportunity_and_no_auto_resend(self):
        rid = self.run_cycle()['report_id']
        self.assertTrue(self.handoff(rid)['may_attempt'])
        self.assertFalse(self.handoff(rid)['may_attempt'])
        self.assertEqual(self.run_cycle()['publication'], 'uncertain')
        self.assertEqual((self.root / 'handoff' / (rid + '.json')).read_bytes(), self.record(rid)['payload'].encode())
        self.assertEqual(len(list((self.root / 'handoff').iterdir())), 1)

    def test_publication_recipient_separate_exact_replays_conflict(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid)
        self.assertEqual(self.receipt(rid, 'publication')['recipient'], 'pending')
        self.assertEqual(self.receipt(rid, 'publication')['publication'], 'verified')
        with self.assertRaises(ValueError):
            self.archive(rid)
        acknowledged = self.receipt(rid, 'recipient')
        self.assertEqual(acknowledged['recipient'], 'acknowledged')
        self.assertEqual(acknowledged['publication'], 'verified')
        with self.assertRaises(ValueError):
            self.receipt(rid, 'recipient', modify=lambda r: r.update(reference='different'))
        self.assertTrue(self.archive(rid)['archived'])
        self.assertTrue(self.archive(rid)['archived'])
        self.assertTrue(self.receipt(rid, 'publication')['archived'])
        self.assertFalse(self.handoff(rid)['may_attempt'])
        self.assertEqual(list((self.root / 'handoff').iterdir()), [])

    def test_recipient_first_never_proves_publication(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid)
        result = self.receipt(rid, 'recipient')
        self.assertEqual(result['publication'], 'uncertain')
        with self.assertRaises(ValueError):
            self.archive(rid)

    def test_mismatched_unbound_and_untrusted_context_receipts(self):
        rid = self.run_cycle()['report_id']
        put(self.inbox, 'unbound.json', {'success': True}).chmod(0o600)
        with self.assertRaises(ValueError):
            self.import_receipt(rid, 'publication', 'unbound')
        self.handoff(rid)
        changes = [lambda r: r.update(owner='another-owner'),
                   lambda r: r.update(issuer='wrong-issuer'),
                   lambda r: r.update(success=True),
                   lambda r: r.update(kind='recipient'),
                   lambda r: r['binding'].update(runtime='another-runtime'),
                   lambda r: r['binding'].update(cycle='another-cycle'),
                   lambda r: r['binding'].update(report='f'*64),
                   lambda r: r['binding'].update(attempt='f'*64),
                   lambda r: r['binding'].update(payload_sha256='f'*64),
                   lambda r: r['binding'].update(recipient='someone'),
                   lambda r: r['binding']['destination'].update(path='operations/other.json'),
                   lambda r: r.update(observed_at=NOW-1)]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.receipt(rid, 'publication', modify=change)
        name = self.stage_receipt(rid, 'publication')
        (self.inbox / (name + '.payload')).write_bytes(b'successful-looking')
        with self.assertRaises(ValueError):
            self.import_receipt(rid, 'publication', name)
        self.inbox.chmod(0o755)
        with self.assertRaises(ValueError):
            self.import_receipt(rid, 'publication', name)
        self.assertEqual(self.run_cycle()['publication'], 'uncertain')

    def test_interrupted_before_collection_never_rereads_new_sources(self):
        with patch.object(cycles, 'collect', side_effect=Crash()):
            with self.assertRaises(Crash):
                self.run_cycle()
        self.assertTrue(self.run_cycle('other')['backpressure'])
        with patch.object(exports, 'stage_exports', side_effect=AssertionError('reread')):
            result = self.run_cycle()
        self.assertEqual(result['collection'], 'interrupted')
        report = io.decode(self.record(result['report_id'])['payload'].encode())['report']
        self.assertEqual(report['movies']['status'], 'unavailable')
        self.assertEqual(report['goals'], [])
        self.assertEqual(list((self.root / 'staging').iterdir()), [])
        self.assertTrue(self.run_cycle('fresh')['changed'])

    def test_interrupted_movie_reader_preserves_checkpointed_independent_findings(self):
        with patch.object(exports, 'stage_exports', side_effect=Crash()):
            with self.assertRaises(Crash):
                self.run_cycle()
        with patch.object(exports, 'stage_exports', side_effect=AssertionError('reread')):
            result = self.run_cycle()
        report = io.decode(self.record(result['report_id'])['payload'].encode())['report']
        self.assertTrue(report['goals'])
        self.assertEqual(result['collection'], 'interrupted')
        self.assertEqual(report['movies']['status'], 'unavailable')

    def test_complete_collection_checkpoint_reused_after_failed_record_write(self):
        real = cycles.write
        def fail(fd, name, raw, replace=False):
            if len(name) == 69:
                raise Crash()
            return real(fd, name, raw, replace)
        with patch.object(cycles, 'write', side_effect=fail):
            with self.assertRaises(Crash):
                self.run_cycle()
        self.source.rename(self.base / 'moved')
        with patch.object(exports, 'stage_exports', side_effect=AssertionError('reread')):
            result = self.run_cycle()
        self.assertEqual(result['collection'], 'collected')
        self.assertEqual(len(list((self.root / 'active').iterdir())), 1)

    def test_outcome_commit_before_cleanup_replays_without_duplicate(self):
        with patch.object(cycles, 'cleanup_stage', side_effect=Crash()):
            with self.assertRaises(Crash):
                self.run_cycle()
        rid = self.state()['cycles']['cycle-1']['report']
        with patch.object(exports, 'stage_exports', side_effect=AssertionError('reread')):
            self.assertEqual(self.run_cycle()['report_id'], rid)
        self.assertEqual(list((self.root / 'staging').iterdir()), [])

    def test_attempt_checkpoint_failure_never_grants_second_write(self):
        rid = self.run_cycle()['report_id']
        with patch.object(cycles, 'save', side_effect=Crash()):
            with self.assertRaises(Crash):
                self.handoff(rid)
        self.assertFalse(self.handoff(rid)['may_attempt'])
        self.assertEqual(self.run_cycle()['publication'], 'uncertain')

    def test_receipt_commit_failure_recovers_without_losing_evidence(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid)
        name = self.stage_receipt(rid, 'publication')
        with patch.object(cycles, 'save', side_effect=Crash()):
            with self.assertRaises(Crash):
                self.import_receipt(rid, 'publication', name)
        self.assertEqual(self.import_receipt(rid, 'publication', name)['publication'], 'verified')

    def test_archive_existing_copy_active_present_and_state_commit_crashes(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid); self.receipt(rid, 'publication'); self.receipt(rid, 'recipient')
        with patch.object(cycles, 'save', side_effect=Crash()):
            with self.assertRaises(Crash):
                self.archive(rid)
        self.assertTrue((self.root / 'archive' / (rid + '.json')).exists())
        self.assertTrue((self.root / 'active' / (rid + '.json')).exists())
        self.assertTrue(self.archive(rid)['archived'])
        self.assertFalse((self.root / 'active' / (rid + '.json')).exists())

    def test_archive_after_state_commit_cleanup_crash_recovery(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid); self.receipt(rid, 'publication'); self.receipt(rid, 'recipient')
        real = cycles.os.unlink
        def fail(name, **kw):
            if name == rid + '.json':
                raise Crash()
            return real(name, **kw)
        with patch.object(cycles.os, 'unlink', side_effect=fail):
            with self.assertRaises(Crash):
                self.archive(rid)
        self.assertEqual(self.state()['reports'][rid]['location'], 'archive')
        self.assertTrue(self.archive(rid)['archived'])
        self.assertEqual(list((self.root / 'active').iterdir()), [])

    def test_archive_conflict_and_capacity_preserve_active_bytes(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid); self.receipt(rid, 'publication'); self.receipt(rid, 'recipient')
        original = (self.root / 'active' / (rid + '.json')).read_bytes()
        for limit in ('MAX_ARCHIVE', 'MAX_ARCHIVE_BYTES'):
            with self.subTest(limit=limit), patch.object(cycles, limit, 0):
                self.assertTrue(self.archive(rid)['backpressure'])
            self.assertEqual((self.root / 'active' / (rid + '.json')).read_bytes(), original)
        conflict = self.root / 'archive' / (rid + '.json')
        conflict.write_bytes(b'conflict'); conflict.chmod(0o600)
        with self.assertRaises(ValueError):
            self.archive(rid)
        self.assertEqual(conflict.read_bytes(), b'conflict')
        self.assertEqual((self.root / 'active' / (rid + '.json')).read_bytes(), original)

    def test_legacy_state_never_touched_and_unowned_root_rejected(self):
        old = self.base / 'legacy-state.json'
        legacy.poll(old, lambda: sources.observations(self.evidence, 'manifest.json', NOW))
        before = old.read_bytes()
        fixture = Path('tests/fixtures/coordinator-pending-v2-task1.json').read_bytes()
        retained = self.base / 'retained-v2.json'
        retained.write_bytes(fixture)
        self.run_cycle()
        legacy.view(retained)
        self.assertEqual(retained.read_bytes(), fixture)
        self.assertEqual(old.read_bytes(), before)
        unowned = self.base / 'unowned'
        unowned.mkdir(mode=0o700)
        marker = unowned / 'state.json'
        marker.write_bytes(before)
        with self.assertRaises((ValueError, OSError)):
            self.run_cycle(root=unowned)
        self.assertEqual(set(p.name for p in unowned.iterdir()), {'state.json'})
        self.assertEqual(marker.read_bytes(), before)

    def test_root_aliases_collisions_and_unsafe_paths(self):
        alias = self.base / 'source-alias'
        alias.symlink_to(self.source, target_is_directory=True)
        checkout = Path(__file__).resolve().parent
        for root in (self.source, self.source / 'new', alias / 'new', checkout / 'cycle-output',
                     self.evidence / 'new', '//' + str(self.base / 'double').lstrip('/'),
                     str(self.base) + '/../escape'):
            with self.subTest(root=root), self.assertRaises((ValueError, OSError)):
                self.run_cycle(root=root)
        self.assertFalse((self.source / 'new').exists())
        self.assertFalse((checkout / 'cycle-output').exists())
        self.base.chmod(0o755)
        with self.assertRaises(ValueError):
            self.run_cycle()

    def test_owned_hardlink_and_symlink_refused(self):
        rid = self.run_cycle()['report_id']
        record = self.root / 'active' / (rid + '.json')
        other = self.base / 'linked'
        os.link(record, other)
        with self.assertRaises(ValueError):
            self.handoff(rid)
        other.unlink()
        original = record.read_bytes()
        record.unlink(); record.symlink_to(other)
        other.write_bytes(original)
        with self.assertRaises(OSError):
            self.handoff(rid)
        self.assertEqual(other.read_bytes(), original)

    def test_injected_collection_io_failures_yield_fixed_unavailable(self):
        for idx, operation in enumerate(('open', 'stat', 'write', 'fsync')):
            # Failure scoped to actual reader; cycle-owned state is still writable.
            with self.subTest(operation=operation):
                if operation == 'stat':
                    target, field = exports.os, 'fstat'
                elif operation == 'write':
                    target, field = exports, '_write_new'
                else:
                    target, field = exports.os, operation
                def fail_reader(*args, **kwargs):
                    raise OSError('SYNTHETIC_PRIVATE_EXCEPTION')
                real_stage = exports.stage_exports
                def faulty(*args, **kwargs):
                    with patch.object(target, field, side_effect=fail_reader):
                        return real_stage(*args, **kwargs)
                with patch.object(exports, 'stage_exports', side_effect=faulty):
                    result = self.run_cycle('io-' + operation)
                self.assertEqual(result['collection'], 'movie_unavailable')
                self.assertNotIn('SYNTHETIC_PRIVATE', io.encode(result).decode())
                self.assertEqual(list((self.root / 'staging').iterdir()), [])

    def test_public_cli_end_to_end_fixed_projection(self):
        command = [sys.executable, '-m', 'automation.coordinator_cycles', 'cycle',
                   '--root', str(self.root), '--runtime', 'synthetic-runtime', '--owner', 'synthetic-owner',
                   '--cycle-id', 'cli', '--now', str(NOW), '--source-root', str(self.source),
                   '--evidence-root', str(self.evidence), '--destination-repository', PRIVATE_REPOSITORY,
                   '--destination-path', DEST['path'], '--recipient', 'original-supervisor']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertTrue(value['changed'])
        self.assertNotIn(str(self.base), result.stdout)
        self.assertNotIn('SYNTHETIC_PRIVATE', result.stdout)
        self.assertEqual(subprocess.run(command, capture_output=True, text=True).stdout, result.stdout)

    def test_cli_runtime_errors_hide_private_values(self):
        args = ['handoff', '--root', str(self.root), '--runtime', 'synthetic-runtime',
                '--owner', 'synthetic-owner', '--id', 'SYNTHETIC_PRIVATE_INVALID']
        self.run_cycle()
        with redirect_stdout(streams.StringIO()) as captured:
            self.assertEqual(cycles.main(args), 1)
        self.assertEqual(json.loads(captured.getvalue()),
                         {'state': 'NEEDS_USER', 'reason': 'invalid_or_unavailable_input'})
        run = subprocess.run([sys.executable, '-m', 'automation.coordinator_cycles', 'private-invalid'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertNotIn('private-invalid', run.stdout + run.stderr)

    def test_collection_capacity_keeps_independent_findings(self):
        # Exercise composition's movie staging budget, separate from reader caps.
        with patch.object(cycles, 'MAX_EVIDENCE', 70000):
            result = self.run_cycle()
        report = io.decode(self.record(result['report_id'])['payload'].encode())['report']
        self.assertTrue(report['goals'])
        self.assertEqual(result['collection'], 'movie_unavailable')
        self.assertEqual(report['movies']['status'], 'unavailable')

    def test_state_byte_backpressure_precedes_collection(self):
        self.run_cycle()
        original = (self.root / 'state.json').read_bytes()
        with patch.object(cycles, 'MAX_STATE', len(original) + 1000):
            with patch.object(exports, 'stage_exports', side_effect=AssertionError('must not read')):
                self.assertTrue(self.run_cycle('state-full')['backpressure'])
        self.assertEqual((self.root / 'state.json').read_bytes(), original)

    def test_payload_and_active_byte_backpressure_are_durable(self):
        for field in ('MAX_PAYLOAD', 'MAX_ACTIVE_BYTES'):
            self.root = self.base / field
            with patch.object(cycles, field, 1024):
                result = self.run_cycle()
            self.assertTrue(result['backpressure'])
            self.assertFalse(result['changed'])
            self.assertIsNone(self.state()['baseline'])
            self.assertEqual(list((self.root / 'staging').iterdir()), [])
            self.assertTrue(self.run_cycle()['backpressure'])
            self.assertTrue(self.run_cycle('fresh')['changed'])

    def test_invalid_independent_source_does_not_erase_other_sources(self):
        for source, other in (('engineering', 'parent_status'), ('parent_status', 'engineering')):
            self.root = self.base / ('invalid-' + source)
            path = self.evidence / (source + '.json')
            original = path.read_bytes()
            path.write_bytes(b'{}')
            result = self.run_cycle()
            report = io.decode(self.record(result['report_id'])['payload'].encode())['report']
            self.assertEqual(report['sources'][source]['status'], 'inconsistent')
            self.assertEqual(report['sources'][other]['status'], 'available')
            self.assertEqual(report['movies']['reason'], 'incomplete_upstream')
            path.write_bytes(original)

    def test_research_report_freshness_never_uses_collection_clock(self):
        value = io.decode((self.source / 'review-report.json').read_bytes())
        value['generated_at'] = NOW - 172800
        put(self.source, 'review-report.json', value)
        result = self.run_cycle()
        report = io.decode(self.record(result['report_id'])['payload'].encode())['report']
        self.assertEqual(report['sources']['research_report']['status'], 'stale')
        self.assertEqual(report['sources']['research_report']['generated_at'], NOW - 172800)
        self.assertTrue(report['goals'])

    def test_archive_recovers_at_each_fsync_boundary(self):
        # file install, archive dir, verification file/dir, state file/dir,
        # active unlink dir, handoff unlink dir: all durable boundaries.
        for boundary in range(1, 9):
            with self.subTest(boundary=boundary):
                self.root = self.base / ('fsync-' + str(boundary))
                rid = self.run_cycle()['report_id']
                self.handoff(rid); self.receipt(rid, 'publication'); self.receipt(rid, 'recipient')
                original = self.record(rid)
                real = cycles.os.fsync
                calls = []
                def fail(fd):
                    calls.append(fd)
                    if len(calls) == boundary:
                        raise OSError('synthetic fsync boundary')
                    return real(fd)
                with patch.object(cycles.os, 'fsync', side_effect=fail):
                    with self.assertRaises(OSError):
                        self.archive(rid)
                self.assertGreaterEqual(len(calls), boundary)
                self.assertTrue(self.archive(rid)['archived'])
                archived = self.record(rid, 'archive')
                self.assertEqual(archived, original)
                self.assertEqual(list((self.root / 'active').iterdir()), [])
                self.assertEqual(list((self.root / 'handoff').iterdir()), [])

    def test_archive_fsync_failure_retains_original_and_recovers(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid); self.receipt(rid, 'publication'); self.receipt(rid, 'recipient')
        original = (self.root / 'active' / (rid + '.json')).read_bytes()
        with patch.object(cycles.os, 'fsync', side_effect=OSError('synthetic fsync failure')):
            with self.assertRaises(OSError):
                self.archive(rid)
        self.assertEqual((self.root / 'active' / (rid + '.json')).read_bytes(), original)
        self.assertTrue(self.archive(rid)['archived'])

    def test_archive_verification_failure_retains_original(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid); self.receipt(rid, 'publication'); self.receipt(rid, 'recipient')
        real = cycles.read
        def mismatch(fd, name, limit=cycles.MAX_RECORD):
            raw = real(fd, name, limit)
            if name == rid + '.json' and (self.root / 'archive' / name).exists():
                return b'wrong bytes'
            return raw
        with patch.object(cycles, 'read', side_effect=mismatch):
            with self.assertRaises(ValueError):
                self.archive(rid)
        self.assertEqual(self.state()['reports'][rid]['location'], 'active')
        self.assertTrue((self.root / 'active' / (rid + '.json')).exists())
        self.assertTrue(self.archive(rid)['archived'])

    def test_create_only_handoff_collision_retains_uncertain_attempt(self):
        rid = self.run_cycle()['report_id']
        path = self.root / 'handoff' / (rid + '.json')
        path.write_bytes(b'foreign content'); path.chmod(0o600)
        with self.assertRaises(ValueError):
            self.handoff(rid)
        self.assertEqual(path.read_bytes(), b'foreign content')
        self.assertEqual(self.run_cycle()['publication'], 'uncertain')
        self.assertIsNotNone(self.record(rid)['attempt'])

    def test_temporary_link_recovery_at_archive_install_boundary(self):
        rid = self.run_cycle()['report_id']
        self.handoff(rid); self.receipt(rid, 'publication'); self.receipt(rid, 'recipient')
        raw = (self.root / 'active' / (rid + '.json')).read_bytes()
        temporary = self.root / 'archive/.write'
        temporary.write_bytes(raw); temporary.chmod(0o600)
        os.link(temporary, self.root / 'archive' / (rid + '.json'))
        self.assertTrue(self.archive(rid)['archived'])
        self.assertFalse(temporary.exists())
        self.assertEqual((self.root / 'archive' / (rid + '.json')).stat().st_nlink, 1)

    def test_reader_temporary_link_recovery_after_interruption(self):
        real = exports.stage_exports
        def interrupt(*args):
            real(*args)
            movie = self.root / 'staging/movie'
            os.link(movie / 'investigations.json', movie / ('.export-' + 'a'*32))
            raise Crash()
        with patch.object(exports, 'stage_exports', side_effect=interrupt):
            with self.assertRaises(Crash):
                self.run_cycle()
        result = self.run_cycle()
        self.assertEqual(result['collection'], 'interrupted')
        self.assertEqual(list((self.root / 'staging').iterdir()), [])

    def test_no_descriptor_leaks_on_owned_open_stat_write_failures(self):
        # Count descriptor ownership using dup probes (portable beyond /proc).
        self.run_cycle()
        def descriptors():
            count = 0
            for fd in range(256):
                try:
                    os.fstat(fd)
                    count += 1
                except OSError:
                    pass
            return count
        before = descriptors()
        for field in ('open', 'fstat', 'fsync'):
            with patch.object(cycles.os, field, side_effect=OSError('synthetic failure')):
                with self.assertRaises(OSError):
                    self.run_cycle('error-' + field)
            self.assertEqual(descriptors(), before)
        with patch.object(cycles, 'write', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                self.run_cycle('error-write')
        self.assertEqual(descriptors(), before)

    def test_cli_all_lifecycle_commands_with_fake_owner_adapter(self):
        result = self.run_cycle()
        rid = result['report_id']
        common = ['--root', str(self.root), '--runtime', 'synthetic-runtime',
                  '--owner', 'synthetic-owner', '--id', rid]
        def invoke(command, extra=()):
            with redirect_stdout(streams.StringIO()) as captured:
                self.assertEqual(cycles.main([command] + common + list(extra)), 0)
            value = json.loads(captured.getvalue())
            self.assertNotIn(str(self.base), captured.getvalue())
            self.assertNotIn('SYNTHETIC_PRIVATE', captured.getvalue())
            return value
        self.assertTrue(invoke('handoff')['may_attempt'])
        self.assertFalse(invoke('handoff')['may_attempt'])
        for kind in ('publication', 'recipient'):
            name = self.stage_receipt(rid, kind)
            invoke('receipt', ['--kind', kind, '--owner-evidence-root', str(self.inbox),
                               '--evidence-id', name])
        self.assertTrue(invoke('archive')['archived'])


if __name__ == '__main__':
    unittest.main()
