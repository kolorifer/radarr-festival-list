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
import time
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
        # CI provisions a private fixture parent outside the checkout and tool
        # cache so their permissions do not require mocking the ACL guards.
        fixture_parent = Path(os.environ.get('SEEDBOX_PREFLIGHT_TEST_PARENT', Path.cwd())).resolve()
        temporary = tempfile.TemporaryDirectory(dir=fixture_parent)
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
if sys.argv[3] == 'source-read-check':
    import time

    fixture = os.environ['SEEDBOX_TEST_LISTING']
    heading = b'<h2 id="torrentnameid">Invented.Film.2001</h2>'
    field = b'<input name="imdbID" value="tt1234567">'
    pages = {
        'ok': heading + field,
        'login_required': b'<input type="password">' + heading + field,
        'listing_mismatch': heading.replace(b'Invented', b'Different') + field,
        'listing_id_missing': heading,
        'listing_id_invalid': heading + field.replace(b'tt1234567', b'unrecognized'),
        'listing_id_conflict': heading + field + b'<p>tt7654321</p>',
        'listing_expected_imdb_mismatch': heading + field.replace(b'tt1234567', b'tt7654321'),
        'listing_facts_refused': heading + field,
        'listing_facts_imdb_mismatch': heading + field,
    }

    def fixture_fetch(url, *, cookies=None, token=None):
        if url == 'https://www.torrentleech.org/torrent/123' and cookies and token is None:
            return pages[fixture], time.time()
        if fixture == 'ok' and url == 'https://api.themoviedb.org/3/find/tt1234567?external_source=imdb_id' and token and cookies is None:
            return b'{"movie_results":[]}', time.time()
        raise AssertionError("unselected source request")

    def fixture_facts(*args, **kwargs):
        if fixture == 'listing_facts_imdb_mismatch':
            return {'imdb': 'tt7654321'}
        raise ValueError('invented-secret-never-in-output')

    def inject(frame, event, arg):
        if event == 'call' and frame.f_globals.get('__name__') == 'automation.seedbox_source_read_check' \
                and frame.f_code.co_name == 'observe':
            from automation import seedbox_host_io
            seedbox_host_io._get = fixture_fetch
            if fixture in ('listing_facts_refused', 'listing_facts_imdb_mismatch'):
                from automation import seedbox_source_evidence
                seedbox_source_evidence.listing_facts = fixture_facts
            sys.settrace(None)
        return None

    sys.settrace(inject)
runpy.run_path(sys.argv[0], run_name='__main__')
""")

        def run(status, stage, reason, *, audited, read_check=False, listing='ok'):
            pin = write_pin(config_path, json.dumps(self.config).encode())
            args = [str(bootstrap), str(runtime / 'seedbox-runtime.json'), package['manifest_sha256'],
                    'source-preflight', str(config_path), pin['sha256']]
            request = None
            if read_check:
                from test_seedbox_source_read_check import selection_fixture
                args[3] = 'source-read-check'
                request = json.dumps(selection_fixture(pin['sha256'],time.time()))
                args.append(hashlib.sha256(request.encode()).hexdigest())

            def snapshot():
                return {str(path): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
            before = snapshot()
            result = subprocess.run([sys.executable, '-I', '-B', *([str(guard)] if audited else []), *args],
                                    cwd='/', env=dict(os.environ,SEEDBOX_TEST_LISTING=listing),
                                    capture_output=True, text=True, input=request, timeout=20)
            self.assertEqual(result.stderr, '')
            self.assertNotIn(SECRET, result.stdout)
            self.assertNotIn(str(self.root), result.stdout)
            for private in ('tt1234567','tt7654321','Invented.Film.2001','Different.Film.2001'):
                self.assertNotIn(private, result.stdout)
            self.assertEqual(result.returncode, int(status != 'passed'), result.stdout)
            identity = (dict(kind='seedbox_source_read_check_v1',retention='not_tested') if read_check else
                        dict(kind='seedbox_source_preflight_v1',external_source_authentication='not_tested'))
            self.assertEqual(json.loads(result.stdout), dict(identity, full_source_access='not_established',
                status=status, stage=stage, reason=reason))
            self.assertEqual(snapshot(), before)

        run('passed', 'complete', 'local_inputs_only', audited=False)
        run('passed', 'complete', 'local_inputs_only', audited=True)
        self.config.update(sources={'example':'Example'},listing_source='example')
        run('passed', 'complete', 'authenticated_no_movie_mapping', audited=True, read_check=True)
        for reason in ('login_required','listing_mismatch','listing_id_missing','listing_id_invalid',
                       'listing_id_conflict','listing_expected_imdb_mismatch',
                       'listing_facts_refused','listing_facts_imdb_mismatch'):
            with self.subTest(reason=reason):
                stage = 'listing_facts' if reason.startswith('listing_facts_') else 'listing_heading_id'
                run('failed',stage,reason,audited=True,read_check=True,listing=reason)
        self.config['cookie_file'] = write_pin(self.cookie, json.dumps({'session': SECRET + ';'}).encode())
        run('failed', 'cookie_format', 'refused', audited=True)
