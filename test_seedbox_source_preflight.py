"""Invented local inputs and the installed entry. No live services."""
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from automation.seedbox_host_io import _source_inputs
from automation.seedbox_package import build


SECRET = 'invented-secret-never-in-output'


def write_pin(path, body):
    path.write_bytes(body)
    path.chmod(0o600)
    return dict(path=str(path), sha256=hashlib.sha256(body).hexdigest())


class SourcePreflightTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=Path.cwd().resolve())
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.cookie = self.root / 'cookie'
        self.env = self.root / 'environment'
        self.config = dict(cookie_file=write_pin(self.cookie, json.dumps({'session': SECRET}).encode()),
                           source_configuration=self.environment(self.cookie))

    def environment(self, cookie):
        return write_pin(self.env, (f'TMDB_API_TOKEN={SECRET}\n'
                                   f'MOVIE_INTEL_TL_COOKIE_FILE="{cookie}"\n'
                                   'MOVIE_INTEL_TL_METADATA_ENABLED=1\n').encode())

    def test_early_exit_emits_only_finite_diagnostic(self):
        from automation import seedbox_bootstrap

        def fail(mark):
            mark('source_runtime')
            raise SystemExit(SECRET)

        output, errors = io.StringIO(), io.StringIO()
        with patch.object(seedbox_bootstrap, 'main', side_effect=fail):
            with redirect_stdout(output), redirect_stderr(errors):
                self.assertEqual(seedbox_bootstrap.source_preflight(), 1)
        self.assertEqual(errors.getvalue(), '')
        self.assertNotIn(SECRET, output.getvalue())
        self.assertEqual(json.loads(output.getvalue()), dict(
            kind='seedbox_source_preflight_v1', external_source_authentication='not_tested',
            full_source_access='not_established', status='failed', stage='source_runtime',
            reason='runtime_unavailable'))

    def test_selected_input_stages(self):
        stages = []

        def rejected(expected):
            with self.assertRaises((ValueError, OSError)):
                _source_inputs(self.config, stages.append)
            self.assertEqual(stages[-1], expected)

        _source_inputs(self.config, stages.append)
        self.assertEqual(stages[-1], 'cookie_format')
        self.env.chmod(0o644)
        rejected('source_configuration_access')
        self.env.chmod(0o600)
        self.config['source_configuration']['sha256'] = '0' * 64
        rejected('source_configuration_pin')
        self.config['source_configuration'] = write_pin(self.env, b'invalid=' + b'"' + SECRET.encode())
        rejected('source_configuration_format')
        self.config['source_configuration'] = self.environment(self.env)
        rejected('cookie_selection')
        self.config['source_configuration'] = self.environment(self.cookie)
        self.cookie.chmod(0o644)
        rejected('cookie_access')
        self.cookie.chmod(0o600)
        self.config['cookie_file']['sha256'] = '0' * 64
        rejected('cookie_pin')
        self.config['cookie_file'] = write_pin(self.cookie, json.dumps({'session': SECRET + ';'}).encode())
        rejected('cookie_format')

    def test_installed_entry_preserves_files_and_never_opens_socket_or_sqlite(self):
        if sys.platform != 'linux':
            self.skipTest('actual Linux ABI6 confinement required')
        from identity_triage_sandbox import _kernel, _call
        abi = _call(_kernel(), 444, ctypes.c_void_p(), ctypes.c_size_t(0), ctypes.c_uint(1))
        self.assertGreaterEqual(abi, 6)
        for directory in ('runtime', 'state', 'actor', 'collector'):
            (self.root / directory).mkdir(mode=0o700)
        runtime = self.root / 'runtime'
        package = build(Path(__file__).resolve().parent, runtime)
        for name in ('actor/outcomes.sqlite3', 'collector/inbox', 'collector/inbox-wal', 'collector/inbox-shm',
                     'state/queue-fixture'):
            # Deliberately not valid SQLite. The installed path must never open a DB.
            write_pin(self.root / name, b'invented fixture')
        pid = os.getpid()
        proc = Path('/proc') / str(pid)
        self.config.update(
            state=str(self.root / 'state'),
            actor_database=dict(path=str(self.root / 'actor/outcomes.sqlite3'), journal_mode='delete'),
            collector_database=dict(path=str(self.root / 'collector/inbox'), journal_mode='wal'),
            sender=dict(deployed_files={}, process=dict(
                pid=pid, start_ticks=int((proc / 'stat').read_bytes().rsplit(b') ', 1)[1].split()[19]),
                cmdline_sha256=hashlib.sha256((proc / 'cmdline').read_bytes()).hexdigest())))
        config_path = self.root / 'config'
        bootstrap = runtime / 'automation/seedbox_bootstrap.py'
        guard = self.root / 'audit.py'
        guard.write_text("""import os, runpy, sys

def audit(event, args):
    mutating = ('os.mkdir', 'os.remove', 'os.rename', 'os.rmdir', 'os.chmod', 'os.link',
                'os.symlink', 'os.truncate', 'os.utime', 'subprocess.Popen')
    if event in mutating or event.startswith(('socket.', 'sqlite3.connect')):
        raise AssertionError('unexpected audit event')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('unexpected writable open')

sys.argv = sys.argv[1:]
sys.addaudithook(audit)
runpy.run_path(sys.argv[0], run_name='__main__')
""")

        def run(status, stage, reason, *, audited):
            pin = write_pin(config_path, json.dumps(self.config).encode())
            args = [str(bootstrap), str(runtime / 'seedbox-runtime.json'), package['manifest_sha256'],
                    'source-preflight', str(config_path), pin['sha256']]
            def snapshot():
                return {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
            before = snapshot()
            result = subprocess.run([sys.executable, '-I', '-B', *([str(guard)] if audited else []), *args],
                                    cwd='/', capture_output=True, text=True, timeout=20)
            self.assertEqual(result.stderr, '')
            self.assertNotIn(SECRET, result.stdout)
            self.assertNotIn(str(self.root), result.stdout)
            self.assertEqual(result.returncode, int(status != 'passed'), result.stdout)
            self.assertEqual(json.loads(result.stdout), dict(kind='seedbox_source_preflight_v1',
                external_source_authentication='not_tested', full_source_access='not_established',
                status=status, stage=stage, reason=reason))
            self.assertEqual(snapshot(), before)

        run('passed', 'complete', 'local_inputs_only', audited=False)
        run('passed', 'complete', 'local_inputs_only', audited=True)
        self.config['cookie_file'] = write_pin(self.cookie, json.dumps({'session': SECRET + ';'}).encode())
        run('failed', 'cookie_format', 'refused', audited=True)
