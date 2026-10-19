import time
"""Isolated shadow receiver: loopback HTTP metadata in, SQLite only out."""
import argparse
import errno
import hmac
import json
import os
from pathlib import Path
import re
import socket
import sys
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import BaseServer

# -I ignores user/site configuration; explicitly load only sibling collector code.
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from identity_triage_intake import MAX_BODY, Reject, decode, normalize
from identity_triage_store import Store, private_path


def read_config(path):
    path = private_path(Path(path))
    private_path(path.parent, True)
    if path.stat().st_size > 8192:
        raise ValueError('configuration')
    cfg = decode(path.read_bytes())
    if set(cfg) != {'version', 'enabled', 'port', 'sources', 'release_key', 'outcome_key'}:
        raise ValueError('configuration')
    if cfg['version'] != 1 or type(cfg['enabled']) != bool or type(cfg['port']) != int or not 1024 <= cfg['port'] <= 65535:
        raise ValueError('configuration')
    if (not isinstance(cfg['sources'], dict) or not 1 <= len(cfg['sources']) <= 32
            or any(not re.fullmatch('[a-z0-9_-]{1,64}', k) or not isinstance(v, str)
                   or not re.fullmatch('[A-Za-z0-9 ._-]{1,80}', v) for k, v in cfg['sources'].items())):
        raise ValueError('configuration')
    for key in ('release_key', 'outcome_key'):
        if not isinstance(cfg[key], str) or not re.fullmatch('[A-Za-z0-9_-]{43,128}', cfg[key]):
            raise ValueError('configuration')
    if hmac.compare_digest(cfg['release_key'], cfg['outcome_key']):
        raise ValueError('separate_credentials')
    return cfg


def isolation_check(home=None):
    # Mandatory at every service start, not a configurable bypass. A unit setting
    # alone is insufficient: some user managers silently ignore mount restrictions.
    home = Path.home() if home is None else Path(home)
    for relative in ('.config/movie-intel', '.local/state/movie-intel', '.apps', '.ssh', 'radarr-festival-list'):
        try:
            fd = os.open(home / relative, os.O_RDONLY | os.O_DIRECTORY)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.ENOENT):
                continue  # Missing paths are harmless; Landlock denies all ungranted paths.
            raise ValueError('isolation') from None
        else:
            os.close(fd)
            raise ValueError('isolation')
    # No inherited credentials. Collector launcher/unit must use a clean env.
    if any(k.startswith(('RADARR_', 'TELEGRAM_', 'TMDB_', 'MOVIE_INTEL_', 'PROWLARR_')) for k in os.environ):
        raise ValueError('credential_environment')


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 8

    def __init__(self, address, config_path, store, listener=None):
        if address[0] != '127.0.0.1':
            raise ValueError('loopback_only')
        self.config_path, self.store = config_path, store
        self.slots = threading.BoundedSemaphore(8)
        self.failure_lock = threading.Lock()
        self.storage_failures = 0  # volatile: cannot claim durable disk-failure counters
        if listener is None:
            super().__init__(address, Handler)  # isolated in-process test fixtures
        else:
            if listener.getsockname() != address:
                raise ValueError('listener_address')
            BaseServer.__init__(self, address, Handler)
            self.socket = listener
            self.server_name, self.server_port = 'localhost', address[1]

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(3)
        return connection, address

    def process_request(self, request, client_address):
        if not self.slots.acquire(False):
            try:
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n')
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        print('triage request_failed', flush=True)

    def storage_failed(self, error=None):
        with self.failure_lock:
            self.storage_failures += 1
        print('triage storage_unavailable reason=' + storage_reason(error), flush=True)


def storage_reason(error):
    """Fixed reason codes only; no exception text, paths or payloads."""
    import errno
    if isinstance(error, sqlite3.Error):
        primary = getattr(error, 'sqlite_errorcode', 0) & 255
        return {sqlite3.SQLITE_BUSY:'sqlite_busy', sqlite3.SQLITE_LOCKED:'sqlite_locked',
                sqlite3.SQLITE_FULL:'sqlite_full', sqlite3.SQLITE_IOERR:'sqlite_io',
                sqlite3.SQLITE_READONLY:'sqlite_readonly'}.get(primary, 'sqlite_other')
    if isinstance(error, OSError):
        return {errno.EACCES:'permission', errno.EPERM:'permission', errno.ENOSPC:'disk_full',
                errno.ENOENT:'path_missing'}.get(error.errno, 'os_other')
    return 'validation' if isinstance(error, ValueError) else 'unknown'


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def handle(self):
        # Socket idle timeout alone does not bound a slow trickle of headers/body.
        # A hard lifetime also prevents eight slow clients occupying every slot.
        def expire():
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        deadline = threading.Timer(5, expire)
        deadline.daemon = True
        deadline.start()
        try:
            super().handle()
        finally:
            deadline.cancel()

    def log_message(self, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        self.reply(code)

    def reply(self, status, metrics=None):
        raw = json.dumps(metrics if metrics is not None else {'ok': status == 200}, separators=(',', ':')).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (OSError, socket.timeout):
            pass  # committed deliveries survive lost acknowledgements
        self.close_connection = True

    def authenticate(self, channel):
        cfg = read_config(self.server.config_path)  # immediate disable/key revocation
        if not cfg['enabled']:
            self.reply(503)
            return None
        values = self.headers.get_all('X-Identity-Intake-Key', [])
        expected = cfg['outcome_key' if channel == 'outcome' else 'release_key']
        if (len(values) != 1 or not values[0].isascii() or len(values[0]) > 128
                or not hmac.compare_digest(values[0], expected)):
            self.server.store.reject(channel)
            self.reply(401)
            return None
        return cfg

    def do_GET(self):
        try:
            if self.path not in ('/health', '/metrics', '/v1/eligible', '/v1/investigations'):
                self.reply(404)
                return
            if not self.authenticate('outcome' if self.path in ('/v1/eligible','/v1/investigations') else 'release_new'):
                return
            if self.path=='/v1/investigations':
                import identity_selection
                with self.server.store.connection(readonly=True) as c:
                    snapshot=identity_selection.snapshot(c,time.time())
                self.reply(200,snapshot)
                return
            if self.path=='/v1/eligible':
                import identity_selection
                with self.server.store.connection(readonly=True) as c:
                    items=identity_selection.export(c,10)
                self.reply(200,{'items':items,'research_enabled':False})
                return
            metrics = self.server.store.metrics()
            metrics['storage_failures_since_start'] = self.server.storage_failures
            self.reply(200, metrics if self.path == '/metrics' else None)
        except (ValueError, OSError, sqlite3.Error) as exc:
            self.server.storage_failed(exc)
            self.reply(503)

    def do_POST(self):
        channel = {'/v1/release': 'release_new', '/v1/outcome': 'outcome'}.get(self.path)
        if channel is None:
            self.reply(404)
            return
        try:
            cfg = self.authenticate(channel)
            if cfg is None:
                return
            lengths = self.headers.get_all('Content-Length', [])
            if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not re.fullmatch('[0-9]{1,8}', lengths[0]):
                self.server.store.reject(channel)
                self.reply(400)
                return
            length = int(lengths[0])
            if not 0 < length <= MAX_BODY:
                self.server.store.reject(channel)
                self.reply(413)
                return
            if self.headers.get_content_type() != 'application/json':
                self.server.store.reject(channel)
                self.reply(415)
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise Reject('truncated')
            record = normalize(decode(raw), cfg['sources'], channel)
            result = self.server.store.ingest(record, channel)
            self.reply(409 if result == 'event_conflict' else 200)
        except Reject:
            try:
                self.server.store.reject(channel)
                self.reply(400)
            except (ValueError, OSError, sqlite3.Error) as exc:
                self.server.storage_failed(exc)
                self.reply(503)
        except (ValueError, OSError, sqlite3.Error) as exc:
            self.server.storage_failed(exc)
            self.reply(503)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--state', required=True)
    parser.add_argument('--check-config', action='store_true')
    args = parser.parse_args(argv)
    os.umask(0o077)
    # Provider home aliases may be symlinks; policy compares canonical roots.
    args.config = str(Path(args.config).resolve())
    args.state = str(Path(args.state).resolve())
    try:
        from identity_triage_sandbox import confine
        listener, abi = confine(args.config, args.state)
        cfg = read_config(args.config)
        if listener.getsockname()[1] != cfg['port']:
            raise ValueError('listener_port')
        if not cfg['enabled']:
            raise ValueError('disabled')
        isolation_check()
        store = Store(args.state)
        if args.check_config:
            print('triage preflight_ok')
            return 0
        with Server(('127.0.0.1', cfg['port']), args.config, store, listener=listener) as server:
            print('triage sandbox_verified abi=' + str(abi) + ' shadow_observation_only coverage_incomplete', flush=True)
            stop = threading.Event()
            def monitor():
                while not stop.wait(60):
                    try:
                        print('triage metrics ' + json.dumps(store.metrics(), sort_keys=True), flush=True)
                    except (ValueError, OSError, sqlite3.Error) as exc:
                        server.storage_failed(exc)
            thread = threading.Thread(target=monitor, daemon=True, name='triage-health')
            thread.start()
            try:
                server.serve_forever(poll_interval=0.5)
            finally:
                stop.set()
                thread.join(timeout=1)

    except (ValueError, OSError, sqlite3.Error):
        print('triage preflight_or_service_failed', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
