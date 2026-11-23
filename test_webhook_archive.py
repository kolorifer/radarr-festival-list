"""Invented request bytes and filesystem failures only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import movie_intel_service as svc
import pending_actions
import webhook_archive


BODY = b'{ \n "event":"action.error", "download_url":"https://invented.invalid/secret", "n":1e3 }\n'


class WebhookArchiveTests(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get('SEEDBOX_PREFLIGHT_TEST_PARENT', Path.cwd())).resolve()
        directory = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.archive = self.root / 'webhook-archive'

    def post(self, body, route='/webhook/owner-secret', *, forward=None, archive=None, before_filter=None):
        handler = object.__new__(svc.Handler)
        handler.path = route
        handler.headers = {'Content-Length':str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._json = Mock()
        original_filter = svc.valid_movie_payload

        def verify_and_filter(payload):
            if before_filter:
                before_filter()
            return original_filter(payload)

        with (patch.object(svc,'WEBHOOK_SECRET','owner-secret'),
              patch.object(pending_actions,'STORE_PATH',self.root/'actions.json'),
              patch.object(svc,'archive_json',side_effect=archive or webhook_archive.archive_json),
              patch.object(svc,'send_telegram',side_effect=forward) as send,
              patch.object(svc,'valid_movie_payload',side_effect=verify_and_filter) as filter_event):
            handler.do_POST()
        return handler._json.call_args.args, send, filter_event

    def test_normal_endpoint_archives_original_bytes_before_business_logic(self):
        def archived_before_filter():
            files = list(self.archive.glob('*.json'))
            self.assertTrue(files)
            self.assertTrue(all(path.read_bytes()==BODY for path in files))

        for _ in range(2):
            response, send, filter_event = self.post(BODY,before_filter=archived_before_filter)
            self.assertEqual(response,(200,{'ok':True,'mode':'passthrough'}))
            send.assert_called_once()
            filter_event.assert_called()
        files = list(self.archive.iterdir())
        self.assertEqual(len(files),2)
        for path in files:
            self.assertRegex(path.name,r'^\d{8}T\d{6}\.\d{6}Z_[0-9a-f]{32}\.json$')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            self.assertEqual(path.stat().st_nlink,1)
        self.assertEqual(stat.S_IMODE(self.archive.stat().st_mode),0o700)

    def test_newly_subscribed_events_archive_without_business_processing(self):
        for event in ('release.new','irc.disconnected','irc.reconnected','irc.unhealthy','irc.healthy',
                      'list.refresh_success','list.refresh_error','feed.refresh_success','feed.refresh_error',
                      'app.update_available'):
            body = ('{"event":"'+event+'","data":{"invented":true}}').encode()
            response, send, filter_event = self.post(body)
            self.assertEqual(response,(200,{'ok':True}))
            send.assert_not_called()
            filter_event.assert_not_called()
            self.assertIn(body,[path.read_bytes() for path in self.archive.glob('*.json')])

    def test_any_other_valid_json_archives_even_when_not_a_business_event(self):
        for body in (b' [true, null, 1] ',b'null',b'{"event":{"invented":true}}'):
            response, send, _ = self.post(body)
            self.assertEqual(response,(200,{'ok':True,'mode':'passthrough'}))
            send.assert_called_once()
            self.assertIn(body,[path.read_bytes() for path in self.archive.glob('*.json')])

    def test_unauthenticated_text_and_nonstandard_json_do_not_archive(self):
        response, send, filters = self.post(BODY,'/webhook/wrong')
        self.assertEqual(response[0],404)
        send.assert_not_called()
        filters.assert_not_called()
        response, send, filters = self.post(b'{"event":"release.new","number":NaN}')
        self.assertEqual(response[0],400)
        send.assert_not_called()
        filters.assert_not_called()
        response, send, _ = self.post(b'legacy text')
        self.assertEqual(response,(200,{'ok':True,'forwarded':'text'}))
        send.assert_called_once()
        self.assertFalse(self.archive.exists())

    def test_failure_is_observable_and_normal_route_still_runs(self):
        def unavailable(*args):
            raise OSError('invented private URL and credentials')

        errors = io.StringIO()
        with redirect_stderr(errors):
            normal,send,_ = self.post(BODY,archive=unavailable)
            only, archive_send, filters = self.post(b'{"event":"release.new"}',archive=unavailable)
        self.assertEqual(normal[0],200)
        send.assert_called_once()
        self.assertEqual(only,(503,{'ok':False,'error':'archive_unavailable'}))
        archive_send.assert_not_called()
        filters.assert_not_called()
        self.assertEqual(errors.getvalue().splitlines(),['webhook_archive write_failed']*2)

    def test_missing_passwd_record_refuses_archive_without_changing_business_route(self):
        errors = io.StringIO()
        with (patch.object(webhook_archive.pwd,'getpwuid',side_effect=KeyError('invented account')),
              redirect_stderr(errors)):
            normal, send, _ = self.post(BODY)
            only, only_send, _ = self.post(b'{"event":"release.new"}')
        self.assertEqual(normal[0],200)
        send.assert_called_once()
        self.assertEqual(only,(503,{'ok':False,'error':'archive_unavailable'}))
        only_send.assert_not_called()
        self.assertEqual(errors.getvalue().splitlines(),['webhook_archive write_failed']*2)
        self.assertFalse(self.archive.exists())

    def test_concurrent_duplicates_keep_complete_distinct_files(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: webhook_archive.archive_json(BODY,self.root),range(24)))
        files = list(self.archive.iterdir())
        self.assertEqual(len(files),24)
        self.assertTrue(all(path.suffix=='.json' and path.read_bytes()==BODY for path in files))

    def test_symlink_unsafe_mode_and_collision_fail_closed(self):
        other = self.root / 'other'
        other.mkdir(mode=0o700)
        self.archive.symlink_to(other)
        with self.assertRaises(OSError):
            webhook_archive.archive_json(BODY,self.root)
        self.assertEqual(list(other.iterdir()),[])
        self.archive.unlink()
        self.archive.mkdir(mode=0o755)
        os.chmod(self.archive,0o755)
        with self.assertRaises(ValueError):
            webhook_archive.archive_json(BODY,self.root)
        self.archive.chmod(0o700)
        with (patch.object(webhook_archive,'datetime') as clock,
              patch.object(webhook_archive.secrets,'token_hex',return_value='a'*32)):
            clock.now.return_value.strftime.return_value='20261123T010203.000000Z'
            webhook_archive.archive_json(BODY,self.root)
            with self.assertRaises(FileExistsError):
                webhook_archive.archive_json(b'null',self.root)
        self.assertEqual([path.read_bytes() for path in self.archive.iterdir()],[BODY])

    def test_only_trusted_passwd_home_alias_is_followed(self):
        home_base = self.root / 'home'
        home_base.mkdir(mode=0o755)
        home = home_base / 'account'
        target = self.root / 'provider-home'
        state = target / '.local' / 'state' / 'movie-intel'
        state.mkdir(mode=0o700,parents=True)
        home.symlink_to(target)
        configured = home / '.local' / 'state' / 'movie-intel'
        real_stat = os.stat

        def alias_stat(name, *args, **kwargs):
            info = real_stat(name,*args,**kwargs)
            if name == home.name and kwargs.get('follow_symlinks') is False:
                return SimpleNamespace(st_mode=info.st_mode,st_uid=0)
            return info

        with (patch.object(webhook_archive.pwd,'getpwuid',return_value=SimpleNamespace(pw_dir=str(home))),
              patch.object(webhook_archive.os,'stat',side_effect=alias_stat)):
            webhook_archive.archive_json(BODY,configured)
            self.assertEqual([p.read_bytes() for p in (state/'webhook-archive').glob('*.json')],[BODY])
            (target/'linked').symlink_to(state)
            with self.assertRaises(OSError):
                webhook_archive.archive_json(BODY,home/'linked')
        with patch.object(webhook_archive.pwd,'getpwuid',return_value=SimpleNamespace(pw_dir=str(target))):
            with self.assertRaises(OSError):
                webhook_archive.archive_json(BODY,configured)

    def test_file_sync_failure_does_not_publish_or_leave_a_partial(self):
        with patch.object(webhook_archive.os,'fsync',side_effect=[None,OSError('invented write failure')]):
            with self.assertRaises(OSError):
                webhook_archive.archive_json(BODY,self.root)
        self.assertEqual(list(self.archive.iterdir()),[])

    def test_valid_json_beyond_object_parser_limits_is_archived_only(self):
        deep = b'['*200_000+b'null'+b']'*200_000
        integer = b'{"number":'+b'9'*5000+b'}'
        for body, error, valid in (
            (deep,RecursionError('invented nesting limit'),True),
            (deep[:-1],RecursionError('invented nesting limit'),False),
            (integer,ValueError('invented integer limit'),True),
            (integer[:-1]+b',}',ValueError('invented integer limit'),False),
        ):
            with self.subTest(length=len(body), valid=valid):
                self.assertIs(webhook_archive.valid_json_syntax(body),valid)
                with patch.object(svc.json,'loads',side_effect=error):
                    response, send, filters = self.post(body)
                self.assertEqual(response[0],500)
                send.assert_not_called()
                filters.assert_not_called()
        self.assertEqual({p.read_bytes() for p in self.archive.glob('*.json')},{deep,integer})

    def test_fallback_grammar_handles_strict_delimiters_escapes_and_encoding(self):
        valid = ' { "x": [-0, 2.25E-5, true, false, null, {"escaped": "\\u1234"}] } '
        invalid = ('[1,]', '{"a" 2}', '{"a":}', '[01]', '1e+', '"\\uqqqq"', 'true false', 'NaN', '')
        self.assertTrue(webhook_archive.valid_json_syntax(valid.encode('utf-16')))
        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(webhook_archive.valid_json_syntax(value.encode()))
