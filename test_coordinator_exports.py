"""Reproducible offline export-to-report rehearsal and boundary regressions."""
from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import errno
import io
import json
import os
from pathlib import Path
import stat
import unittest
from unittest.mock import patch

from automation import coordinator as c
from automation import coordinator_diagnostics as d
from automation import coordinator_exports as exports
from automation import coordinator_integration as cli
from automation import coordinator_io as files
from automation import coordinator_outbox as outbox
from automation import coordinator_parent as parent
from automation import coordinator_sources as sources
from test_coordinator_integration import Base, CANARY, NOW, pair, put, synthetic_stage, parent_fixture
from identity_triage_store import digest as producer_digest


class ExportTests(Base):
    def setUp(self):
        super().setUp()
        self.source = self.root / 'source'
        self.source.mkdir(mode=0o700)
        snapshot, report = pair(self.source)
        self.originals = {}
        for source, content in (('investigations', snapshot), ('research_report', report)):
            # Deliberately noncanonical formatting, with no final newline rewrite.
            raw = (json.dumps(content, indent=2) + '\n\n').encode()
            path = self.source / exports.EXPORTS[source]
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(raw)
            self.originals[source] = raw
        self.output = self.root / 'new-output'

    def run_stage(self, output=None, now=NOW):
        return exports.stage_exports(self.source, output or self.output, now)

    def reasons(self, report, source):
        values = report['sources'][source]['diagnostics']
        d.validate(values)
        return [(v['stage'], v['reason']) for v in values]

    def test_original_bytes_hash_modes_and_report_rehearsal(self):
        before = {s: ((self.source / p).stat().st_mtime_ns, (self.source / p).read_bytes())
                  for s, p in exports.EXPORTS.items()}
        report = self.run_stage()
        self.assertEqual(report['movies']['reason'], 'incomplete_upstream')
        self.assertEqual(report['quality']['status'], 'unavailable')
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        for source, raw in self.originals.items():
            self.assertEqual((self.output / (source + '.json')).read_bytes(), raw)
            self.assertEqual(report['sources'][source]['sha256'], files.digest(raw))
            self.assertEqual(self.reasons(report, source), [('acquisition', 'read_complete'), ('staging', 'staged')])
            path = self.source / exports.EXPORTS[source]
            self.assertEqual((path.stat().st_mtime_ns, path.read_bytes()), before[source])
        for path in self.output.iterdir():
            self.assertTrue(stat.S_ISREG(path.stat().st_mode))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_nlink, 1)
        self.assertEqual(files.read_json(self.output, 'observations.json'), report)
        first = outbox.poll(self.state, lambda: sources.observations(self.output, 'manifest.json', NOW))
        self.assertTrue(first['changed'])
        original = first['pending_outbox'][0]
        recovered = self.root / 'recovered.json'
        self.assertEqual(cli.recover(self.state, original['id'], recovered), original['sha256'])
        self.assertEqual(recovered.read_bytes(), original['payload'].encode())
        self.assertFalse(outbox.poll(self.state, lambda: sources.observations(self.output, 'manifest.json', NOW+1))['changed'])

    def test_canonical_root_success_symlink_spelling_rejected_without_writes(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(files.ReadFailure) as caught:
            exports.stage_exports(alias, self.output, NOW)
        self.assertIn(caught.exception.reason, ('path_rejected', 'path_component_ambiguous'))
        self.assertFalse(self.output.exists())
        self.assertEqual(self.run_stage()['sources']['investigations']['status'], 'available')

    def test_links_escape_aliases_and_collisions_preserve_sources(self):
        before = {p: (self.source / p).read_bytes() for p in exports.EXPORTS.values()}
        alias = self.root / 'alias'
        alias.symlink_to(self.source, target_is_directory=True)
        existing = self.root / 'existing'
        existing.mkdir(mode=0o700)
        marker = existing / 'marker'
        marker.write_bytes(b'untouched')
        hardlink = self.root / 'hardlink'
        os.link(self.source / 'review-report.json', hardlink)
        for destination in (self.source, self.source / 'new', alias / 'new', existing,
                            self.source / 'incoming', hardlink, self.root / '../escape'):
            with self.subTest(destination=destination), self.assertRaises((ValueError, OSError)):
                exports.stage_exports(self.source, destination, NOW)
        self.assertEqual(marker.read_bytes(), b'untouched')
        self.assertFalse((self.source / 'new').exists())
        for path, raw in before.items():
            self.assertEqual((self.source / path).read_bytes(), raw)
        for relative in ('../review-report.json', '/review-report.json', 'incoming/./snapshot.json'):
            with self.assertRaises(ValueError):
                files.read_bytes(self.source, relative)

    def test_destination_dangling_symlink_and_old_root_cannot_be_reused(self):
        self.output.symlink_to(self.root / 'missing', target_is_directory=True)
        with self.assertRaises(exports.StagingFailure):
            self.run_stage()
        self.assertFalse((self.root / 'missing').exists())
        self.output.unlink()
        self.run_stage()
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        with self.assertRaises(exports.StagingFailure):
            self.run_stage()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})

    def test_ancestor_final_links_and_source_hardlinks_are_rejected(self):
        snapshot = self.source / 'incoming/snapshot.json'
        real = self.root / 'real-snapshot'
        snapshot.rename(real)
        snapshot.symlink_to(real)
        first = self.run_stage()
        self.assertIn(self.reasons(first, 'investigations')[-1][1], ('path_rejected', 'path_component_ambiguous'))
        snapshot.unlink()
        os.link(real, snapshot)
        second = self.run_stage(self.root / 'hardlink-output')
        self.assertIn(('acquisition', 'hardlink_rejected'), self.reasons(second, 'investigations'))
        snapshot.unlink()
        (self.source / 'incoming').rmdir()
        real_dir = self.root / 'real-incoming'
        real_dir.mkdir()
        real.rename(real_dir / 'snapshot.json')
        (self.source / 'incoming').symlink_to(real_dir, target_is_directory=True)
        third = self.run_stage(self.root / 'ancestor-output')
        self.assertIn(self.reasons(third, 'investigations')[-1][1], ('path_rejected', 'path_component_ambiguous'))
        self.assertEqual((real_dir / 'snapshot.json').read_bytes(), self.originals['investigations'])

    def test_inode_alias_preflight_even_when_spelling_is_different(self):
        # Inject equal source/ancestor identity to model a filesystem alias.
        with files.directory(self.source) as source_fd, files.directory(self.root) as parent_fd:
            original = os.fstat
            source_stat = original(source_fd)
            def aliased(fd):
                return source_stat if fd != source_fd else original(fd)
            with patch.object(exports.os, 'fstat', side_effect=aliased):
                with self.assertRaises(ValueError):
                    exports._outside_source(parent_fd, source_fd)
        self.assertFalse(self.output.exists())

    def test_partial_missing_no_invented_provenance_no_stale_substitution(self):
        (self.source / 'review-report.json').unlink()
        report = self.run_stage()
        info = report['sources']['research_report']
        self.assertEqual(self.reasons(report, 'research_report'), [('acquisition', 'missing_entry')])
        for key in ('sha256', 'generated_at', 'collected_at'):
            self.assertIsNone(info[key])
        self.assertEqual(report['movies']['reason'], 'compatible_report_missing')
        self.assertEqual(len(report['movies']['known_cases']), 2)
        self.assertFalse((self.output / 'research_report.json').exists())
        (self.source / 'review-report.json').write_bytes(self.originals['research_report'])
        success = self.run_stage(self.root / 'second')
        self.assertEqual(success['movies']['reason'], 'incomplete_upstream')
        self.assertEqual(sources.observations(self.output, 'manifest.json', NOW), report)
        (self.source / 'review-report.json').unlink()
        failed_again = self.run_stage(self.root / 'third')
        self.assertEqual(failed_again['movies']['reason'], 'compatible_report_missing')
        self.assertFalse((self.root / 'third/research_report.json').exists())

    def test_nonregular_fifo_and_oversize_are_bounded(self):
        target = self.source / 'incoming/snapshot.json'
        for kind, expected in (('directory', 'nonregular_file'), ('fifo', 'nonregular_file'), ('big', 'byte_limit')):
            if target.is_dir():
                target.rmdir()
            else:
                target.unlink()
            if kind == 'directory':
                target.mkdir()
            elif kind == 'fifo':
                os.mkfifo(target)
            else:
                target.write_bytes(b'x' * (exports.LIMIT + 1))
            with patch.object(files.os, 'read', wraps=os.read) as reads:
                result = self.run_stage(self.root / kind)
            self.assertIn(('acquisition', expected), self.reasons(result, 'investigations'))
            self.assertLessEqual(sum(call.args[1] for call in reads.call_args_list), 6 * exports.LIMIT)
            self.assertFalse((self.root / kind / 'investigations.json').exists())
            self.assertEqual(result['sources']['research_report']['status'], 'partial')

    def test_access_denied_unknown_and_enotdir_use_errno_not_exception_text(self):
        real = files.read_from_directory
        for number, reason in ((errno.EACCES, 'access_denied'), (errno.ENOTDIR, 'path_component_ambiguous'),
                               (errno.EIO, 'io_unknown')):
            def injected(fd, path, *args, **kwargs):
                if path == 'incoming/snapshot.json':
                    raise OSError(number, CANARY)
                return real(fd, path, *args, **kwargs)
            with patch.object(files, 'read_from_directory', side_effect=injected):
                result = self.run_stage(self.root / str(number))
            self.assertEqual(self.reasons(result, 'investigations'), [('acquisition', reason)])
            self.assertNotIn(CANARY, json.dumps(result))

    def test_change_during_read_and_all_descriptor_paths_close(self):
        original_open, original_dup, original_close, original_read = os.open, os.dup, os.close, os.read
        target = self.source / 'incoming/snapshot.json'
        for failure in ('change', 'read_error', 'fstat_error', 'success'):
            target.write_bytes(self.originals['investigations'])
            acquired, closed = Counter(), Counter()
            def opened(*args, **kwargs):
                fd = original_open(*args, **kwargs); acquired[fd] += 1; return fd
            def duplicated(fd):
                new = original_dup(fd); acquired[new] += 1; return new
            def close(fd):
                closed[fd] += 1; return original_close(fd)
            def read(fd, size):
                if failure == 'read_error':
                    raise OSError(errno.EIO, CANARY)
                chunk = original_read(fd, size)
                if failure == 'change' and chunk:
                    # Change once; append changes size even on low-resolution filesystems.
                    with target.open('ab') as stream:
                        stream.write(b' ')
                return chunk
            # Keep the race finite: mutate only on the first read.
            called = [False]
            def once(fd, size):
                if called[0]:
                    return original_read(fd, size)
                called[0] = True
                return read(fd, size)
            with patch.object(files.os, 'open', side_effect=opened), patch.object(files.os, 'dup', side_effect=duplicated), patch.object(files.os, 'close', side_effect=close), patch.object(files.os, 'read', side_effect=once):
                with files.directory(self.source) as fd:
                    if failure == 'fstat_error':
                        with patch.object(files.os, 'fstat', side_effect=OSError(errno.EIO, CANARY)), self.assertRaises(OSError):
                            files.read_from_directory(fd, 'incoming/snapshot.json')
                    elif failure == 'success':
                        self.assertEqual(files.read_from_directory(fd, 'incoming/snapshot.json'), self.originals['investigations'])
                    else:
                        with self.assertRaises((files.ReadFailure, OSError)) as caught:
                            files.read_from_directory(fd, 'incoming/snapshot.json')
                        self.assertEqual(d.acquisition_reason(caught.exception), 'changed_during_read' if failure == 'change' else 'io_unknown')
            self.assertEqual(acquired, closed)

    def test_validation_diagnostics_preserve_independent_engineering_and_parent(self):
        manifest = synthetic_stage(self.staged)
        # Existing source findings must survive each isolated movie failure.
        journal_root = self.root / 'journals'
        parent_fixture(journal_root)
        parent_content = parent.export_parent(journal_root, 113, [1], NOW)
        raw_parent = files.encode(parent_content)
        (self.staged / 'parent.json').write_bytes(raw_parent)
        manifest['sources'][3].update(path='parent.json', sha256=files.digest(raw_parent), collected_at=NOW)
        original = deepcopy(manifest)
        raw_original = (self.staged / 'investigations.json').read_bytes()
        for kind, stage, reason in (('hash', 'identity', 'hash_mismatch'), ('json', 'decoding', 'invalid_json'),
                                    ('schema', 'schema', 'invalid_source_schema'), ('stale', 'freshness', 'stale_evidence'),
                                    ('future', 'freshness', 'future_evidence'), ('time', 'provenance', 'time_mismatch')):
            manifest = deepcopy(original)
            entry = manifest['sources'][1]
            content = files.decode(raw_original)
            raw = raw_original
            if kind == 'hash': entry['sha256'] = 'f' * 64
            if kind == 'json': raw = ('{"private":"' + CANARY + '","private":0}').encode()
            if kind == 'schema': content['version'] = 7
            if kind in ('stale', 'future'): content['generated_at'] = entry['generated_at'] = NOW + (-3600 if kind == 'stale' else 301)
            if kind == 'time': entry['generated_at'] -= 1
            if kind not in ('json', 'hash'): raw = files.encode(content)
            if kind != 'hash': entry['sha256'] = files.digest(raw)
            (self.staged / 'investigations.json').write_bytes(raw)
            put(self.staged, 'manifest.json', manifest)
            result = sources.observations(self.staged, 'manifest.json', NOW)
            self.assertIn((stage, reason), self.reasons(result, 'investigations'))
            self.assertEqual(len(result['goals']), 1)
            self.assertEqual(result['parent']['status'], 'available')
            self.assertNotIn(CANARY, json.dumps(result))
        # Revision and movie-pair failures are separate from byte identity.
        manifest = synthetic_stage(self.staged)
        manifest['sources'][0]['revision'] = 'f' * 40
        put(self.staged, 'manifest.json', manifest)
        result = sources.observations(self.staged, 'manifest.json', NOW)
        self.assertIn(('provenance', 'revision_mismatch'), self.reasons(result, 'engineering'))
        self.assertEqual(result['movies']['reason'], 'incomplete_upstream')
        content = files.read_json(self.staged, 'research_report.json')
        content['cases'][0]['year'] += 1
        row = content['cases'][0]
        content['versions'][row['case_id']] = producer_digest({k: v for k, v in row.items() if k != 'observed_at'})
        content['changed_cases'] = deepcopy(content['cases'])
        raw = files.encode(content)
        (self.staged / 'research_report.json').write_bytes(raw)
        manifest['sources'][2]['sha256'] = files.digest(raw)
        put(self.staged, 'manifest.json', manifest)
        result = sources.observations(self.staged, 'manifest.json', NOW)
        self.assertIn(('pair', 'incompatible_movie_pair'), self.reasons(result, 'research_report'))
        self.assertEqual(len(result['movies']['known_cases']), 2)

    def test_invalid_json_is_staged_exactly_and_has_no_fabricated_generation(self):
        for index, raw in enumerate((b'{"x":NaN}', b'{"x":1e999}', b'{"x":0,"x":1}', b'{"x":"\xff"}', b'[')):
            (self.source / 'incoming/snapshot.json').write_bytes(raw)
            root = self.root / ('invalid-' + str(index))
            report = self.run_stage(root)
            self.assertEqual((root / 'investigations.json').read_bytes(), raw)
            self.assertEqual(report['sources']['investigations']['sha256'], files.digest(raw))
            self.assertIsNone(report['sources']['investigations']['generated_at'])
            self.assertIn(('decoding', 'invalid_json'), self.reasons(report, 'investigations'))

    def test_failure_success_transition_once_and_refresh_is_quiet(self):
        (self.source / 'review-report.json').unlink()
        failed = self.run_stage()
        one = outbox.poll(self.state, lambda: failed)
        (self.source / 'review-report.json').write_bytes(self.originals['research_report'])
        good = self.run_stage(self.root / 'second', NOW+1)
        two = outbox.poll(self.state, lambda: good)
        self.assertTrue(one['changed'] and two['changed'])
        self.assertEqual(len(two['pending_outbox']), 2)
        third = self.run_stage(self.root / 'third', NOW+2)
        self.assertFalse(outbox.poll(self.state, lambda: third)['changed'])
        self.assertEqual(len(outbox.view(self.state)), 2)
        self.assertEqual(outbox.view(self.state)[0], one['pending_outbox'][0])

    def test_destination_collision_during_atomic_install_preserves_existing_bytes(self):
        original_link = os.link
        def collision(src, dst, **kwargs):
            if dst == 'investigations.json':
                fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600,
                             dir_fd=kwargs['dst_dir_fd'])
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(b'collision sentinel')
            return original_link(src, dst, **kwargs)
        with patch.object(exports.os, 'link', side_effect=collision):
            with self.assertRaises(exports.StagingFailure) as caught:
                self.run_stage()
        self.assertEqual(caught.exception.diagnostics[0]['stage'], 'staging')
        self.assertEqual(caught.exception.diagnostics[0]['reason'], 'destination_collision')
        self.assertEqual((self.output / 'investigations.json').read_bytes(), b'collision sentinel')
        self.assertEqual({p.name for p in self.output.iterdir()}, {'investigations.json', 'diagnostics.json'})
        d.validate(files.read_json(self.output, 'diagnostics.json'))
        for source, raw in self.originals.items():
            self.assertEqual((self.source / exports.EXPORTS[source]).read_bytes(), raw)
        with self.assertRaises(exports.StagingFailure):
            self.run_stage()

    def test_relative_roots_are_not_interpreted_as_caller_authority(self):
        for source, output in ((Path('relative-source'), self.output), (self.source, Path('relative-output'))):
            with self.assertRaises(ValueError):
                exports.stage_exports(source, output, NOW)
        self.assertFalse(self.output.exists())

    def test_private_diagnostics_bounded_and_never_projected(self):
        report = self.run_stage()
        public = cli.public_projection({'report': report})
        self.assertNotIn('diagnostics', json.dumps(public))
        self.assertNotIn(CANARY, json.dumps(public))
        details = [x for info in report['sources'].values() for x in info['diagnostics']]
        d.validate(details)
        self.assertLess(len(files.encode(details)), 8192)
        for invalid in ([details[0]] * (d.MAX_DIAGNOSTICS+1),
                        [dict(details[0], reason=CANARY)], [dict(details[0], source=CANARY)],
                        [dict(details[0], extra=CANARY)], [dict(details[0], stage=CANARY)],
                        [dict(details[0], version=True)]):
            with self.assertRaises(ValueError): d.validate(invalid)

    def test_cli_fixed_errors_and_success_no_private_text(self):
        args = ['stage-exports', '--source-root', str(self.source), '--output-root', str(self.output)]
        with patch.object(cli.time, 'time', return_value=NOW), redirect_stdout(io.StringIO()) as capture:
            self.assertEqual(cli.main(args), 0)
        for marker in (CANARY, str(self.source), str(self.output), 'diagnostics', 'Synthetic Movie'):
            self.assertNotIn(marker, capture.getvalue())
        with patch.object(exports, 'stage_exports', side_effect=PermissionError(errno.EACCES, CANARY)), redirect_stdout(io.StringIO()) as capture:
            self.assertEqual(cli.main(args), 1)
        self.assertNotIn(CANARY, capture.getvalue())
        with redirect_stderr(io.StringIO()) as capture, self.assertRaises(SystemExit):
            cli.main(['stage-exports', '--private-'+CANARY])
        self.assertNotIn(CANARY, capture.getvalue())
        self.assertEqual(json.loads(capture.getvalue())['reason'], 'invalid_or_unavailable_input')


if __name__ == '__main__':
    unittest.main()
