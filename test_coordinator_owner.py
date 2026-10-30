"""Synthetic owner commissioning only. No operational authentication or transport."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from automation import coordinator_owner as owner
from automation import coordinator_cycles as cycles
from automation import coordinator_io as io
from automation import coordinator_exports as exports
from automation import coordinator_parent as parent
from automation import coordinator_sources as sources
from test_coordinator import NOW, HEAD, snapshot
from test_coordinator_cycles import DEST, Crash
from test_coordinator_integration import pair, parent_fixture, put


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.base.chmod(0o700)
        self.producer = self.base / 'synthetic-producer'
        self.producer.mkdir(mode=0o700)
        self.movie, self.review = pair(self.producer)
        self.originals = {path: (json.dumps(v, indent=2) + '\n\n').encode()
                          for path, v in zip(owner.FIXED_PATHS, (self.movie, self.review))}
        self.independent = None
        (self.base / 'parent-staging').mkdir(mode=0o700)
        self.req = self.request()

    def request(self, cid='cycle-1', now=NOW, pin=None):
        root = self.base / 'owner'
        return owner.request(root, 'synthetic-runtime', 'synthetic-owner', cid, now,
                             root / ('intake-' + cid), root / 'cycles', root / ('evidence-' + cid),
                             root / ('receipts-' + cid), self.base / 'parent-staging' / ('parent-' + cid + '.json'),
                             'synthetic-fixed-exports', '/synthetic/canonical-source', DEST,
                             'original-supervisor', evidence_manifest_sha256=pin)

    def stage(self, req=None, originals=None):
        req = req or self.req
        for relative, raw in (self.originals if originals is None else originals).items():
            path = Path(req['intake_root']) / relative
            path.write_bytes(raw)
            path.chmod(0o600)
        if self.independent is not None:
            for name, raw in self.independent.items():
                path = Path(req['evidence_root']) / name
                path.write_bytes(raw)
                path.chmod(0o600)

    def setup_independent(self):
        journals = self.base / 'fake-journals'
        parent_fixture(journals, issue=119)
        contents = dict(engineering=snapshot(), parent_status=parent.export_parent(journals, 119, [1], NOW))
        manifest = cycles.empty_manifest()
        self.independent = {}
        for e in manifest['sources']:
            if e['id'] not in contents:
                continue
            raw = io.encode(contents[e['id']])
            self.independent[e['id'] + '.json'] = raw
            e.update(path=e['id'] + '.json', sha256=io.digest(raw), collected_at=NOW)
            if e['id'] == 'engineering':
                e.update(revision=HEAD, observed_at=NOW)
        self.independent['manifest.json'] = io.encode(manifest)
        self.req = self.request(pin=io.digest(self.independent['manifest.json']))

    def prepared(self, originals=None):
        owner.reserve(self.req)
        self.stage(originals=originals)
        owner.seal(self.req)
        return owner.prepare(self.req)

    def record(self, result=None):
        result = result or owner.inspect(self.req)
        state = io.decode((Path(self.req['cycle_root']) / 'state.json').read_bytes())
        where = state['reports'][result['report_id']]['location']
        return io.decode((Path(self.req['cycle_root']) / where / (result['report_id'] + '.json')).read_bytes())

    def receipt(self, kind, mutate=None, payload=None):
        rec = self.record()
        value = dict(version=1, kind=kind, owner=self.req['owner'],
                     issuer=self.req['owner'] if kind == 'publication' else self.req['recipient'],
                     binding=deepcopy(rec['attempt']), observed_at=NOW + 100,
                     reference='fake-independent-' + kind)
        if mutate:
            mutate(value)
        path = put(Path(self.req['receipt_root']), kind + '.json', value)
        path.chmod(0o600)
        if kind == 'publication':
            path = Path(self.req['receipt_root']) / 'publication.payload'
            path.write_bytes(rec['payload'].encode() if payload is None else payload)
            path.chmod(0o600)

    def complete(self):
        self.prepared()
        owner.handoff(self.req)
        for kind in ('publication', 'recipient'):
            self.receipt(kind)
            owner.receipt(self.req, kind, kind)
        return owner.archive(self.req)

    def tree(self):
        return {str(p.relative_to(self.base)): (p.read_bytes() if p.is_file() and not p.is_symlink()
                                               else str(p.readlink()) if p.is_symlink() else None)
                for p in self.base.rglob('*')}

    def test_fake_transport_sees_durable_intent_before_original_byte_staging(self):
        seen = []
        def fake_transport(grant):
            self.assertTrue(grant['acquisition_grant'])
            path = Path(self.req['base']) / owner.intent_name(self.req)
            with path.open('rb') as stream:
                seen.append(io.decode(stream.read()))
            self.assertEqual(seen[0]['request'], self.req)
            self.assertEqual(seen[0]['sha256'], grant['intent_sha256'])
            self.stage()
        fake_transport(owner.reserve(self.req))
        self.assertEqual(len(seen), 1)
        owner.seal(self.req)
        result = owner.prepare(self.req)
        record = self.record(result)
        for source, path in exports.EXPORTS.items():
            self.assertEqual(cycles.unpack(record['evidence'][source + '.json']), self.originals[path])
        report = io.decode(record['payload'].encode())['report']
        self.assertEqual(report['movies']['reason'], 'incomplete_upstream')
        self.assertEqual(report['quality']['reason'], 'passive_export_missing')

    def test_exact_restart_replay_and_changed_request_fail_closed(self):
        first = owner.reserve(self.req)
        original = self.tree()
        replay = owner.reserve(deepcopy(self.req))
        self.assertFalse(replay['acquisition_grant'])
        self.assertEqual(first['intent_sha256'], replay['intent_sha256'])
        self.assertEqual(self.tree(), original)
        for field, value in (('now', NOW+1), ('recipient', 'another-supervisor'),
                             ('selector', 'another-source'), ('source_path', '/different/source'),
                             ('destination', dict(repository=DEST['repository'], path='operations/other.json'))):
            req = deepcopy(self.req)
            req[field] = value
            with self.subTest(field=field), self.assertRaises((ValueError, OSError)):
                owner.reserve(req)
            self.assertEqual(self.tree(), original)

    def test_concurrent_initialization_one_grant_at_most(self):
        def attempt(_):
            try:
                return owner.reserve(self.req)['acquisition_grant']
            except (ValueError, OSError):
                return False
        with ThreadPoolExecutor(max_workers=5) as pool:
            grants = list(pool.map(attempt, range(5)))
        self.assertEqual(sum(grants), 1)
        self.assertFalse(owner.reserve(self.req)['acquisition_grant'])

    def test_nonblocking_owner_lock(self):
        owner.reserve(self.req)
        with owner.owner_store(self.req):
            with self.assertRaisesRegex(owner.OwnerFailure, 'owner_busy'):
                owner.inspect(self.req)

    def test_canonical_case_normalization_overlap_rejected_before_writes(self):
        for field, value in (('base', '//' + str(self.base).lstrip('/') + '/owner'),
                             ('intake_root', str(self.base / 'owner/INTAKE')),
                             ('intake_root', str(self.base / 'owner/intaké')),
                             ('intake_root', str(self.base / 'owner/intake/../escape')),
                             ('intake_root', str(self.base / 'owner/cycles')),
                             ('evidence_root', str(self.base / 'owner/intake-cycle-1/sub')),
                             ('receipt_root', str(self.base / 'outside'))):
            req = deepcopy(self.req)
            req[field] = value
            before = self.tree()
            with self.subTest(field=field, value=value), self.assertRaises((ValueError, OSError)):
                owner.reserve(req)
            self.assertEqual(self.tree(), before)

    def test_symlink_parent_and_final_aliases_never_followed(self):
        alias = self.base / 'alias'
        alias.symlink_to(self.base, target_is_directory=True)
        req = deepcopy(self.req)
        for field in ('base',) + owner.ROOT_FIELDS + ('parent_output',):
            req[field] = req[field].replace(str(self.base), str(alias), 1)
        before = self.tree()
        with self.assertRaises((ValueError, OSError)):
            owner.reserve(req)
        self.assertEqual(self.tree(), before)
        alias.unlink()
        (self.base / 'owner').symlink_to(self.producer, target_is_directory=True)
        before = self.tree()
        with self.assertRaises((ValueError, OSError)):
            owner.reserve(self.req)
        self.assertEqual(self.tree(), before)

    def test_missing_parent_and_inaccessible_separation_guards_before_write(self):
        req = deepcopy(self.req)
        for field in ('base',) + owner.ROOT_FIELDS + ('parent_output',):
            req[field] = req[field].replace('/owner', '/missing/owner')
        before = self.tree()
        with self.assertRaises((ValueError, OSError)):
            owner.reserve(req)
        self.assertEqual(self.tree(), before)
        with patch.object(exports, '_outside_source', side_effect=OSError('synthetic guard')):
            with self.assertRaises(OSError):
                owner.reserve(self.req)
        self.assertEqual(self.tree(), before)

    def test_existing_unowned_base_and_partial_initialization_no_adoption(self):
        (self.base / 'owner').mkdir(mode=0o700)
        before = self.tree()
        with self.assertRaises((ValueError, OSError)):
            owner.reserve(self.req)
        self.assertEqual(self.tree(), before)

    def test_interrupted_initialization_unanchored_bytes_preserved(self):
        real = exports._write_new
        def crash(fd, name, raw):
            if name.startswith('intent-'):
                raise Crash()
            return real(fd, name, raw)
        with patch.object(exports, '_write_new', side_effect=crash):
            with self.assertRaises(Crash):
                owner.reserve(self.req)
        before = self.tree()
        with self.assertRaisesRegex(ValueError, 'owner_unanchored'):
            owner.reserve(self.req)
        self.assertEqual(self.tree(), before)

    def test_lost_reservation_return_burns_acquisition_grant(self):
        real = exports._write_new
        def crash(fd, name, raw):
            result = real(fd, name, raw)
            if name.startswith('intent-'):
                raise Crash()
            return result
        with patch.object(exports, '_write_new', side_effect=crash):
            with self.assertRaises(Crash):
                owner.reserve(self.req)
        self.assertFalse(owner.reserve(self.req)['acquisition_grant'])

    def test_intent_corruption_and_missing_pins_reject_without_replacement(self):
        owner.reserve(self.req)
        path = Path(self.req['base']) / owner.intent_name(self.req)
        entry = io.decode(path.read_bytes())
        entry['request']['now'] += 1
        path.write_bytes(io.encode(entry))
        before = self.tree()
        with self.assertRaises(ValueError):
            owner.reserve(self.req)
        self.assertEqual(self.tree(), before)

    def test_root_replacement_and_alias_intake_reject(self):
        owner.reserve(self.req)
        root = Path(self.req['intake_root'])
        root.rename(self.base / 'retained-intake')
        root.symlink_to(self.base / 'retained-intake', target_is_directory=True)
        before = self.tree()
        with self.assertRaises((ValueError, OSError)):
            owner.seal(self.req)
        self.assertEqual(self.tree(), before)

    def test_seal_required_exact_replay_then_drift_rejects(self):
        owner.reserve(self.req)
        self.stage()
        with self.assertRaises((ValueError, OSError)):
            owner.prepare(self.req)
        owner.seal(self.req)
        before = self.tree()
        owner.seal(self.req)
        self.assertEqual(self.tree(), before)
        path = Path(self.req['intake_root']) / 'review-report.json'
        path.write_bytes(path.read_bytes() + b' ')
        before = self.tree()
        with self.assertRaisesRegex(owner.OwnerFailure, 'owner_intake_changed'):
            owner.prepare(self.req)
        self.assertEqual(self.tree(), before)

    def test_missing_invalid_stale_future_and_inconsistent_movies(self):
        variants = [('missing', {}), ('invalid', {owner.FIXED_PATHS[0]: b'bad-json'}),
                    ('stale', {**self.originals, owner.FIXED_PATHS[1]: io.encode({**self.review, 'generated_at': NOW-200000})}),
                    ('future', {**self.originals, owner.FIXED_PATHS[0]: io.encode({**self.movie, 'generated_at': NOW+400})}),
                    ('inconsistent', {**self.originals, owner.FIXED_PATHS[0]: io.encode({**self.movie, 'cases': []})})]
        self.setup_independent()
        for idx, (name, originals) in enumerate(variants):
            self.req = self.request('cycle-' + str(idx), pin=io.digest(self.independent['manifest.json']))
            with self.subTest(name=name):
                result = self.prepared(originals)
                report = io.decode((Path(self.req['cycle_root']) / 'current.json').read_bytes())['report']
                self.assertTrue(report['goals'])
                self.assertEqual(report['sources']['engineering']['status'], 'available')
                self.assertEqual(report['sources']['parent_status']['status'], 'available')
                self.assertNotEqual(report['movies'].get('reason'), 'complete')
                self.assertEqual(report['quality']['reason'], 'passive_export_missing')
                if name == 'missing':
                    self.assertEqual(report['sources']['investigations']['status'], 'unavailable')
                if name == 'stale':
                    self.assertEqual(report['sources']['research_report']['status'], 'stale')

    def test_no_manifest_authority_from_staged_json(self):
        owner.reserve(self.req)
        put(Path(self.req['evidence_root']), 'manifest.json', cycles.empty_manifest()).chmod(0o600)
        with self.assertRaisesRegex(owner.OwnerFailure, 'owner_manifest_selection'):
            owner.seal(self.req)

    def test_proposal_version_integrity_full_case_set_and_unchanged_clock(self):
        from identity_triage_store import digest as producer_digest
        result = self.prepared()
        report = io.decode(self.record(result)['payload'].encode())['report']
        self.assertEqual({r['case_id'] for r in report['movies']['known_cases']},
                         {r['case_id'] for r in self.movie['cases']})
        self.assertGreater(len(report['movies']['known_cases']), len(report['movies']['eligible_cases']))
        self.assertEqual(report['sources']['research_report']['generated_at'], self.review['generated_at'])
        changed = deepcopy(self.review)
        row = changed['cases'][0]
        row['proposal']['evidence_version'] = '0' * 64
        row['proposal']['current_evidence'] = True
        changed['versions'][row['case_id']] = producer_digest({k: v for k, v in row.items() if k != 'observed_at'})
        changed['changed_cases'] = deepcopy(changed['cases'])
        self.req = self.request('cycle-2')
        self.prepared({**self.originals, 'review-report.json': io.encode(changed)})
        current = io.decode((Path(self.req['cycle_root']) / 'current.json').read_bytes())['report']
        self.assertEqual(current['movies']['reason'], 'incompatible_report')
        self.assertEqual(current['sources']['research_report']['status'], 'inconsistent')

    def test_changed_generation_time_is_not_renewed_by_later_staging(self):
        self.req = self.request(now=NOW+3601)
        self.prepared()
        current = io.decode((Path(self.req['cycle_root']) / 'current.json').read_bytes())['report']
        self.assertEqual(current['sources']['investigations']['status'], 'stale')
        self.assertEqual(current['sources']['investigations']['generated_at'], self.movie['generated_at'])

    def test_cycle_capacity_stops_next_external_acquisition(self):
        self.prepared()
        before = self.tree()
        with patch.object(cycles, 'MAX_ACTIVE', 1):
            with self.assertRaisesRegex(ValueError, 'owner_backpressure'):
                owner.reserve(self.request('cycle-2'))
        self.assertEqual(self.tree(), before)

    def test_unsafe_output_parent_and_remote_local_overlap_fail_before_private_write(self):
        req = deepcopy(self.req)
        req['source_path'] = req['intake_root']
        before = self.tree()
        with self.assertRaisesRegex(ValueError, 'owner_overlap'):
            owner.reserve(req)
        self.assertEqual(self.tree(), before)
        path = Path(self.req['parent_output']).parent
        path.chmod(0o755)
        with self.assertRaises(ValueError):
            owner.reserve(self.req)
        self.assertFalse(Path(self.req['base']).exists())
        path.chmod(0o700)

    def test_read_only_inspect_does_not_import_receipts_or_write(self):
        self.prepared()
        before = self.tree()
        with patch.object(exports, '_write_new', side_effect=AssertionError('write')):
            with patch.object(cycles, 'write', side_effect=AssertionError('write')):
                self.assertEqual(owner.inspect(self.req)['status'], 'prepared')
        self.assertEqual(self.tree(), before)

    def test_independent_selected_manifest_exact_bytes_and_issue_qualification(self):
        self.setup_independent()
        result = self.prepared()
        record = self.record(result)
        self.assertEqual(cycles.unpack(record['evidence']['independent-manifest.json']),
                         self.independent['manifest.json'])
        self.assertEqual(cycles.unpack(record['evidence']['parent_status.json']),
                         self.independent['parent_status.json'])
        report = io.decode(record['payload'].encode())['report']
        self.assertTrue(report['goals'])
        self.assertEqual(report['sources']['engineering']['status'], 'available')
        self.assertEqual(report['sources']['parent_status']['status'], 'available')

    def test_handoff_exact_immutable_and_no_silent_resend(self):
        result = self.prepared()
        original = self.record(result)['payload'].encode()
        handoff = owner.handoff(self.req)
        self.assertTrue(handoff['may_attempt'])
        self.assertEqual(Path(self.req['parent_output']).read_bytes(), original)
        before = self.tree()
        with self.assertRaises(ValueError):
            owner.handoff(self.req)
        self.assertEqual(self.tree(), before)
        self.assertEqual(owner.prepare(self.req)['report_id'], result['report_id'])

    def test_conflicting_parent_output_never_overwritten(self):
        self.prepared()
        path = Path(self.req['parent_output'])
        path.write_bytes(b'conflicting bytes')
        path.chmod(0o600)
        before = self.tree()
        with self.assertRaisesRegex(owner.OwnerFailure, 'owner_output_exists'):
            owner.handoff(self.req)
        self.assertEqual(self.tree(), before)
        self.assertIsNone(self.record()['attempt'])

    def test_crash_after_uncertain_boundary_never_reexports(self):
        self.prepared()
        real = exports._write_new
        def crash(fd, name, raw):
            if name == Path(self.req['parent_output']).name:
                raise Crash()
            return real(fd, name, raw)
        with patch.object(exports, '_write_new', side_effect=crash):
            with self.assertRaises(Crash):
                owner.handoff(self.req)
        self.assertFalse(Path(self.req['parent_output']).exists())
        self.assertEqual(owner.inspect(self.req)['publication'], 'uncertain')
        before = self.tree()
        with self.assertRaisesRegex(owner.OwnerFailure, 'owner_publication_uncertain'):
            owner.handoff(self.req)
        self.assertEqual(self.tree(), before)

    def test_lost_publication_response_readback_reconciliation_without_resend(self):
        self.prepared()
        owner.handoff(self.req)
        # Fake publisher has committed destination but its response is lost.
        fake_remote = Path(self.req['parent_output']).read_bytes()
        self.receipt('publication', payload=fake_remote)
        self.assertEqual(owner.receipt(self.req, 'publication', 'publication')['publication'], 'verified')
        self.assertEqual(owner.inspect(self.req)['recipient'], 'pending')
        with self.assertRaises(ValueError):
            owner.archive(self.req)
        self.receipt('recipient')
        owner.receipt(self.req, 'recipient', 'recipient')
        self.assertTrue(owner.archive(self.req)['archived'])

    def test_fake_receipts_never_auto_import_or_acknowledge(self):
        self.prepared()
        owner.handoff(self.req)
        self.receipt('publication')
        self.receipt('recipient')
        before = self.tree()
        self.assertEqual(owner.inspect(self.req)['recipient'], 'pending')
        self.assertEqual(owner.prepare(self.req)['publication'], 'uncertain')
        with self.assertRaisesRegex(owner.OwnerFailure, 'owner_receipt_selection'):
            owner.receipt(self.req, None, None)
        with self.assertRaises(ValueError):
            owner.archive(self.req)
        self.assertEqual(self.tree(), before)

    def test_wrong_receipt_bindings_readback_and_extra_flags_reject(self):
        self.prepared()
        owner.handoff(self.req)
        mutations = [lambda r: r.update(issuer='wrong-issuer'),
                     lambda r: r['binding'].update(recipient='wrong-recipient'),
                     lambda r: r['binding'].update(payload_sha256='0'*64),
                     lambda r: r['binding'].update(attempt='0'*64),
                     lambda r: r['binding']['destination'].update(path='operations/wrong.json'),
                     lambda r: r.update(trusted=True), lambda r: r.update(observed_at=NOW-1)]
        for kind in ('publication', 'recipient'):
            for change in mutations:
                self.receipt(kind, change)
                before = self.tree()
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    owner.receipt(self.req, kind, kind)
                self.assertEqual(self.tree(), before)
        self.receipt('publication', payload=b'wrong-original-bytes')
        with self.assertRaises(ValueError):
            owner.receipt(self.req, 'publication', 'publication')

    def test_archive_restart_idempotence_and_original_evidence_retained(self):
        result = self.complete()
        self.assertTrue(result['archived'])
        before = self.tree()
        self.assertEqual(owner.archive(deepcopy(self.req)), result)
        self.assertEqual(self.tree(), before)
        self.assertTrue(owner.inspect(self.req)['archived'])
        for source, path in exports.EXPORTS.items():
            self.assertEqual(cycles.unpack(self.record()['evidence'][source+'.json']), self.originals[path])

    def test_quiet_new_cycle_uses_shared_baseline_without_redating_original(self):
        self.complete()
        original_req = deepcopy(self.req)
        original_record = self.record()
        self.req = self.request('cycle-2', NOW+1)
        result = self.prepared()
        self.assertEqual(result['status'], 'quiet')
        with self.assertRaises(ValueError):
            owner.handoff(self.req)
        self.req = original_req
        self.assertEqual(self.record(), original_record)

    def test_external_intake_and_receipt_backpressure_preserves_all_bytes(self):
        owner.reserve(self.req)
        self.stage()
        path = Path(self.req['intake_root']) / 'extra.json'
        path.write_bytes(b'unowned')
        before = self.tree()
        with self.assertRaisesRegex(owner.OwnerFailure, 'owner_intake_entries'):
            owner.seal(self.req)
        self.assertEqual(self.tree(), before)
        path.unlink()  # synthetic fixture only
        large = Path(self.req['intake_root']) / 'review-report.json'
        large.write_bytes(b'x' * (exports.LIMIT + 1))
        with self.assertRaisesRegex(owner.OwnerFailure, 'owner_backpressure'):
            owner.seal(self.req)
        self.stage()
        owner.seal(self.req)
        owner.prepare(self.req)
        owner.handoff(self.req)
        self.receipt('publication')
        (Path(self.req['receipt_root']) / 'publication.payload').write_bytes(b'x'*(cycles.MAX_PAYLOAD+1))
        before = self.tree()
        with self.assertRaisesRegex(owner.OwnerFailure, 'owner_backpressure'):
            owner.receipt(self.req, 'publication', 'publication')
        self.assertEqual(self.tree(), before)

    def test_intent_capacity_no_history_loss_and_no_second_grant(self):
        owner.reserve(self.req)
        before = self.tree()
        req = self.request('cycle-2')
        with patch.object(owner, 'MAX_INTENTS', 1):
            with self.assertRaisesRegex(owner.OwnerFailure, 'owner_backpressure'):
                owner.reserve(req)
        self.assertEqual(self.tree(), before)
        self.assertFalse(owner.reserve(self.req)['acquisition_grant'])

    def test_source_hardlink_symlink_and_changed_read_metadata(self):
        owner.reserve(self.req)
        self.stage()
        path = Path(self.req['intake_root']) / 'review-report.json'
        retained = self.base / 'original-review'
        path.rename(retained)
        for link in ('symlink', 'hardlink'):
            if link == 'symlink':
                path.symlink_to(retained)
            else:
                os.link(retained, path)
            before = self.tree()
            with self.assertRaises((ValueError, OSError)):
                owner.seal(self.req)
            self.assertEqual(self.tree(), before)
            path.unlink()
        path.write_bytes(retained.read_bytes())
        path.chmod(0o600)
        real_read = os.read
        mutated = []
        def changing_read(fd, size):
            raw = real_read(fd, size)
            if not mutated and raw == self.originals['review-report.json']:
                with path.open('ab') as stream:
                    stream.write(b' ')
                mutated.append(True)
            return raw
        with patch.object(owner.os, 'read', side_effect=changing_read):
            with self.assertRaisesRegex(owner.OwnerFailure, 'owner_input_changed'):
                owner.seal(self.req)
        self.assertTrue(mutated)

    def cli(self, command, req=None, extra=()):
        req = req or self.req
        argv = [sys.executable, '-m', 'automation.coordinator_owner', command]
        fields = ('base', 'runtime', 'owner', 'now', 'intake_root', 'cycle_root', 'evidence_root',
                  'receipt_root', 'parent_output', 'selector', 'source_path', 'recipient', 'expected')
        for field in fields:
            argv += ['--'+field.replace('_', '-'), str(req[field])]
        argv += ['--cycle-id', req['cycle'], '--destination-repository', req['destination']['repository'],
                 '--destination-path', req['destination']['path']]
        if req['evidence_manifest_sha256']:
            argv += ['--evidence-manifest-sha256', req['evidence_manifest_sha256']]
        return subprocess.run(argv + list(extra), capture_output=True, text=True)

    def test_actual_cli_rehearsal_all_steps_fake_publisher_distinct_recipient(self):
        self.setup_independent()
        reserved = self.cli('reserve')
        self.assertEqual(reserved.returncode, 0, reserved.stderr)
        self.assertTrue(json.loads(reserved.stdout)['acquisition_grant'])
        self.stage()  # fake externally authorized fixed-byte transport
        for cmd in ('seal', 'prepare', 'inspect', 'handoff'):
            result = self.cli(cmd)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rec = self.record()
        # Fake authenticated publisher and independent recipient live in the test,
        # outside owner code. Synthetic selections prove no genuine system origin.
        destination = self.base / 'fake-private-destination'
        destination.write_bytes(Path(self.req['parent_output']).read_bytes())
        self.assertEqual(destination.read_bytes(), rec['payload'].encode())
        self.receipt('publication', payload=destination.read_bytes())
        result = self.cli('receipt', extra=('--kind', 'publication', '--evidence-id', 'publication'))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)['recipient'], 'pending')
        self.receipt('recipient')
        result = self.cli('receipt', extra=('--kind', 'recipient', '--evidence-id', 'recipient'))
        self.assertEqual(result.returncode, 0, result.stdout)
        result = self.cli('archive')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(json.loads(result.stdout)['archived'])
        self.assertEqual(self.cli('archive').returncode, 0)
        self.assertFalse(json.loads(self.cli('reserve').stdout)['acquisition_grant'])

    def test_cli_sanitized_failure_and_import_has_no_side_effect(self):
        result = self.cli('prepare')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(str(self.base), result.stdout + result.stderr)
        self.assertFalse(Path(self.req['base']).exists())
        result = subprocess.run([sys.executable, '-c', 'import automation.coordinator_owner'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, b'')
        self.assertFalse(Path(self.req['base']).exists())


if __name__ == '__main__':
    unittest.main()
