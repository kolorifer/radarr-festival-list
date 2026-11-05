"""Fixed-origin, one-shot HTTPS. No SDK, proxies, environment auth or retries.

Inactive runtime primitive: the transport does not ship a real-send authorizer.
A main-thread POSIX timer bounds DNS, connect, TLS, headers AND slow body reads.
Unsupported timer/thread state refuses before creating a socket.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import http.client
import ipaddress
import signal
import socket
import ssl
import threading
import time

from .contracts import Refusal, require

ENDPOINT = 'https://api.openai.com/v1/responses'
HOST = 'api.openai.com'
PATH = '/v1/responses'
MAX_RESPONSE = 32768
SYNTHETIC_CREDENTIAL = 'SIMULATED-NOT-A-KEY'
SYNTHETIC_PROJECT = 'proj_SIMULATED'


@dataclass(frozen=True, repr=False)
class ExplicitCredential:
    """Transport-only value; no discovery, serialization or printable secret."""
    value: str = field(repr=False)

    def __repr__(self):
        return 'ExplicitCredential(<redacted>)'


@dataclass(frozen=True)
class HTTPResult:
    status: int
    body: bytes = field(repr=False)
    request_id: str = None
    # Stamped locally by the fixed I/O boundary, never parsed from model JSON.
    request_sha256: str = None
    project: str = None
    path: str = None


def headers(credential, project):
    # Only a future trusted authorizer may choose the real project/credential.
    import re
    require(type(credential) is ExplicitCredential and isinstance(credential.value, str)
            and re.fullmatch(r'[A-Za-z0-9_-]{8,256}', credential.value), 'responses_credential_invalid')
    require(isinstance(project, str) and re.fullmatch(r'proj_[A-Za-z0-9_-]{1,100}', project),
            'responses_project_invalid')
    return {'Authorization': 'Bearer ' + credential.value, 'OpenAI-Project': project,
            'Content-Type': 'application/json', 'Accept': 'application/json',
            'Accept-Encoding': 'identity'}


@contextmanager
def total_deadline(seconds, *, response_observation=None):
    require(type(seconds) in (int, float) and 0 < seconds <= 25, 'responses_deadline')
    require(response_observation in (None,120), 'responses_observation_profile')
    require(threading.current_thread() is threading.main_thread()
            and hasattr(signal, 'setitimer'), 'responses_timer_unavailable')
    require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
            and signal.getsignal(signal.SIGALRM) == signal.SIG_DFL, 'responses_timer_busy')
    reason='responses_setup_deadline_exceeded' if response_observation is not None else None
    def expired(*_):
        if reason is not None:raise Refusal(reason)
        raise TimeoutError()
    deadline = time.monotonic() + seconds
    observing=False
    def check():
        require(time.monotonic() < deadline, reason or 'responses_deadline_exceeded')
    def remaining():
        check()
        return max(0.000001,deadline-time.monotonic())
    def begin_observation(post_completed):
        nonlocal deadline,reason,observing
        # Single transition after the one POST, never a sliding read timeout.
        check()
        require(response_observation==120 and not observing and
                type(post_completed) in (int,float) and
                post_completed<=time.monotonic() and post_completed<deadline,
                'responses_observation_transition')
        observing=True
        deadline=post_completed+response_observation
        reason='responses_observation_deadline_exceeded'
        signal.setitimer(signal.ITIMER_REAL,remaining())
    check.begin_observation=begin_observation
    check.remaining=remaining
    previous = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield check
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def tls_context():
    # load_default_certs/create_default_context can honor SSL_CERT_* and key-log
    # environment values. Select compiled platform trust paths explicitly.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    paths = ssl.get_default_verify_paths()
    require(bool(paths.openssl_cafile or paths.openssl_capath), 'responses_tls_roots_unavailable')
    context.load_verify_locations(cafile=paths.openssl_cafile, capath=paths.openssl_capath)
    require(context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED, 'responses_tls_required')
    return context


class FixedResponsesHTTP:
    """No configurable URL, headers, proxy, redirect, TLS mode or retry policy."""
    def post(self, body, *, credential, project, timeout, authorization=None):
        return self._request(body, credential=credential, project=project, timeout=timeout,
                             authorization=authorization, path=PATH)

    def count(self, body, *, credential, project, timeout, authorization=None):
        """Dormant token-count route; identical fixed-origin safety boundary."""
        return self._request(body, credential=credential, project=project, timeout=timeout,
                             authorization=authorization, path='/v1/responses/input_tokens')

    def _request(self, body, *, credential, project, timeout, authorization, path):
        from .supervised_authorization import observe_phase, response_observation_window
        observe_phase('http_setup')
        require(path in (PATH, '/v1/responses/input_tokens'), 'responses_path_denied')
        from .responses_transport import real_activation_refusal
        refusal = real_activation_refusal(authorization, body=body, credential=credential,
                                           project=project, path=path)
        require(refusal is None, refusal or 'responses_denied')
        require(type(body) is bytes and len(body) <= 65536, 'responses_request_size')
        selected_headers = headers(credential, project)
        observation=response_observation_window(authorization,body,credential,project,path)
        connection = None
        raw_socket = None
        primary = False
        try:
            with total_deadline(timeout,response_observation=observation) as check:
                observe_phase('tls_setup')
                context = tls_context()
                check()
                observe_phase('dns_lookup')
                addresses = socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
                check()
                require(bool(addresses), 'responses_dns_failed')
                # Reject non-public/mixed DNS answers; connect to exactly the
                # checked numeric address, never resolve again or fail over.
                for family, kind, proto, _, address in addresses:
                    require(family in (socket.AF_INET, socket.AF_INET6)
                            and kind == socket.SOCK_STREAM and proto == socket.IPPROTO_TCP
                            and ipaddress.ip_address(address[0]).is_global
                            and address[1] == 443, 'responses_network_denied')
                family, kind, proto, _, address = addresses[0]
                refusal = real_activation_refusal(authorization, body=body, credential=credential,
                    project=project, path=path, consume=False)
                require(refusal is None, refusal or 'responses_denied')
                observe_phase('socket_connect')
                raw_socket = socket.socket(family, kind, proto)
                raw_socket.settimeout(timeout)
                raw_socket.connect(address)
                check()
                require(raw_socket.getpeername()[0] == address[0], 'responses_peer_changed')
                observe_phase('tls_handshake')
                secure = context.wrap_socket(raw_socket, server_hostname=HOST)
                connection = http.client.HTTPConnection(HOST, port=443, timeout=timeout)
                connection.sock = secure
                raw_socket = None  # connection now owns the TLS socket
                check()
                refusal = real_activation_refusal(authorization, body=body, credential=credential,
                    project=project, path=path, consume=False)
                require(refusal is None, refusal or 'responses_denied')
                observe_phase('http_send')
                connection.request('POST', path, body=body, headers=selected_headers)
                post_completed=time.monotonic()
                check()
                if observation is not None:
                    check.begin_observation(post_completed)
                    secure.settimeout(check.remaining())
                observe_phase('http_receive')
                response = connection.getresponse()
                observe_phase('http_response_received')
                check()
                # Never follow Location or consume/echo error bodies.
                require(response.status == 200, 'responses_http_rejected')
                hs = response.getheaders()
                lengths = [v for k, v in hs if k.lower() == 'content-length']
                types = [v for k, v in hs if k.lower() == 'content-type']
                encodings = [v for k, v in hs if k.lower() == 'content-encoding']
                require(len(types) == 1 and types[0].split(';')[0].strip().lower() == 'application/json'
                        and encodings in ([], ['identity']), 'responses_http_shape')
                require(len(lengths) <= 1 and (not lengths or lengths[0].isascii() and lengths[0].isdigit()
                        and int(lengths[0]) <= MAX_RESPONSE), 'responses_body_limit')
                observe_phase('http_body_read')
                data = bytearray()
                while True:
                    part = response.read1(min(4096, MAX_RESPONSE + 1 - len(data)))
                    check()
                    if not part:
                        break
                    data.extend(part)
                    require(len(data) <= MAX_RESPONSE, 'responses_body_limit')
                require(not lengths or len(data) == int(lengths[0]), 'responses_body_truncated')
                observe_phase('http_body_received')
                ids = [v for k, v in hs if k.lower() == 'x-request-id']
                require(len(ids) <= 1, 'responses_http_shape')
                return HTTPResult(200, bytes(data), ids[0] if ids else None,
                                  hashlib.sha256(body).hexdigest(), project, path)
        except Refusal:
            primary = True
            raise
        except (TimeoutError, OSError, ValueError, http.client.HTTPException):
            primary = True
            raise Refusal('responses_network_completion_unknown') from None
        except BaseException:
            primary = True
            raise
        finally:
            # Preserve a primary failure, but never report success after a
            # failed cleanup. Attempt both closes without exposing their text.
            cleanup_failed=False
            for resource in (connection,raw_socket):
                if resource is not None:
                    try:resource.close()
                    except BaseException:cleanup_failed=True
            if cleanup_failed and not primary:
                raise Refusal('responses_cleanup_failed') from None


class SimulatedHTTP:
    """Finite static HTTP fixture, incapable of socket/provider requests.

    Only this exact class is admitted to the simulation route. No callback,
    arbitrary HTTP implementation or claimed simulated flag grants live access.
    """
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.lock = threading.Lock()

    def post(self, body, *, credential, project, timeout):
        require(type(credential) is ExplicitCredential and credential.value == SYNTHETIC_CREDENTIAL
                and project == SYNTHETIC_PROJECT, 'simulation_credential_required')
        with self.lock:
            self.requests.append(dict(endpoint=ENDPOINT, body=body, timeout=timeout,
                                      header_names=sorted(headers(credential, project))))
            require(bool(self.responses), 'simulation_response_missing')
            response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        require(type(response) is HTTPResult, 'simulation_response_invalid')
        return response
