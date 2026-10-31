"""Optional Codex exec transport, with no shipped live-client boundary approval.

Only reviewed, exact executable profiles can pass preflight. Help/config flags
are necessary compatibility evidence, not proof of isolation. In particular,
ignoring user config does not prove absence of managed MCP, skills or hooks.
No supported real-client profile is yet established. Do not add one based on a
model name or a synthetic protocol test. See docs/AI-MOVIE-INVESTIGATOR.md.
"""
from contextlib import contextmanager
import copy
import hashlib
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import tempfile
import time

from .contracts import MAX_INPUT, MAX_OUTPUT, Refusal, decode, digest, encoded, hash_id, require, shape, text

# Reviewed source changes, with independent real-client boundary evidence, must
# supply a profile. There is intentionally no owner JSON "boundary=true" bypass.
REVIEWED_CLIENTS = {}
REQUIRED_FLAGS = ('--strict-config', '--ignore-user-config', '--ignore-rules', '--sandbox', '--skip-git-repo-check',
                  '--cd', '--output-schema', '--json', '--ephemeral', '--model')
CONTROLS = {
    'approval_policy': '"never"', 'forced_login_method': '"chatgpt"',
    'web_search': '"disabled"', 'features.shell_tool': 'false',
    'features.shell_snapshot': 'false', 'project_doc_max_bytes': '0',
    'features.multi_agent': 'false', 'agents.enabled': 'false',
    'features.hooks': 'false', 'features.memories': 'false',
    'features.apps': 'false', 'tools.view_image': 'false',
    'features.plugins': 'false', 'features.remote_plugin': 'false',
    'features.browser_use': 'false', 'features.browser_use_external': 'false',
    'features.browser_use_full_cdp_access': 'false', 'features.computer_use': 'false',
    'features.in_app_browser': 'false', 'features.image_generation': 'false',
    'features.code_mode_host': 'false', 'features.skill_search': 'false',
    'features.request_permissions_tool': 'false',
}


METADATA_SECONDS = 5
PREFLIGHT_SECONDS = 10
# Exact dependency closure established by a future reviewed adapter, not a list
# of guessed file paths. Hashes cover effective values and the full inventories,
# including denied/absent entries and mandatory security instructions.
BOUNDARY_DEPENDENCIES = frozenset((
    'client_runtime', 'effective_config', 'managed_policy', 'tools',
    'integrations', 'instructions', 'skills', 'environment', 'protocol',
))


def transport_environment():
    env = {k: os.environ[k] for k in ('HOME', 'PATH', 'TMPDIR', 'SYSTEMROOT') if k in os.environ}
    env['NO_COLOR'] = '1'
    return env


def executable_hash(path):
    require(path.is_absolute() and path.resolve(strict=True) == path, 'client_path')
    s = path.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and not s.st_mode & 0o022
            and s.st_size <= 256 * 1024 * 1024 and os.access(path, os.X_OK), 'client_permissions')
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def bounded_process(argv, payload, *, cwd, timeout, limit, env=None):
    """No shell, inherited stdin, ambient environment, or unlimited communicate().

    Kill the whole new process group on timeout, invalid output or interruption.
    stderr is drained with the same total bound, then discarded, never logged.
    """
    require(0 < timeout <= 25 and len(payload) <= MAX_INPUT, 'transport_bounds')
    # Auth remains inside the existing client. No CODEX_HOME/auth file reads or
    # copies. Keys, proxy overrides, NODE_OPTIONS and loader variables are absent.
    env = transport_environment() if env is None else dict(env)
    deadline = time.monotonic() + timeout
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    selector = selectors.DefaultSelector()
    output = bytearray()
    total = 0
    pending = memoryview(payload)
    try:
        for stream in (process.stdin, process.stdout, process.stderr):
            os.set_blocking(stream.fileno(), False)
        if pending:
            selector.register(process.stdin, selectors.EVENT_WRITE)
        else:
            process.stdin.close()
        selector.register(process.stdout, selectors.EVENT_READ)
        selector.register(process.stderr, selectors.EVENT_READ)
        while selector.get_map():
            require(time.monotonic() < deadline, 'model_timeout')
            for key, _ in selector.select(max(0, min(.1, deadline - time.monotonic()))):
                stream = key.fileobj
                if stream is process.stdin:
                    try:
                        count = os.write(stream.fileno(), pending[:8192])
                    except BlockingIOError:
                        continue
                    except BrokenPipeError as exc:
                        raise Refusal('model_stdin_closed') from exc
                    pending = pending[count:]
                    if not pending:
                        selector.unregister(stream)
                        stream.close()
                else:
                    try:
                        chunk = os.read(stream.fileno(), 8192)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(stream)
                        continue
                    total += len(chunk)
                    require(total <= limit, 'transport_output_limit')
                    if stream is process.stdout:
                        output.extend(chunk)
        try:
            process.wait(timeout=max(.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired as exc:
            raise Refusal('model_timeout') from exc
        require(time.monotonic() < deadline, 'model_timeout')
        require(process.returncode == 0, 'client_failed_or_auth_unavailable')
        return bytes(output)
    finally:
        # Also terminate descendants holding inherited pipes or running after
        # the direct client exits. No detached helper or daemon is permitted.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        selector.close()
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()


def configuration_args():
    """The complete selected vector shared by exec and optional metadata inspection."""
    return [arg for key, value in CONTROLS.items() for arg in ('-c', key + '=' + value)]


def inspect_configuration_metadata(executable, *, expected_version, expected_help_hashes):
    """Explicit optional read-only check; never called by runtime or ordinary tests.

    Caller supplies previously inspected version/help pins. This checks only
    root-route configuration acceptance and reported feature states, never exec
    isolation, authentication, tools, policy or a stable dependency lease. It
    neither registers a profile nor enables a transport. Unknown schema/features,
    missing client, failed commands and drift raise visible Refusal errors.
    No raw help/configuration/environment/account data is returned or logged.
    """
    deadline = time.monotonic() + PREFLIGHT_SECONDS
    executable = Path(executable)
    try:
        pin = executable_hash(executable)
        text(expected_version, 100)
        help_commands = {'root': ['--help'], 'features': ['features', '--help'], 'exec': ['exec', '--help']}
        require(isinstance(expected_help_hashes, dict) and set(expected_help_hashes) == set(help_commands),
                'metadata_help_pins_unknown')
        for value in expected_help_hashes.values():
            hash_id(value)
        # Feature names are checked against the client's own listing below.
        # Unrecognized non-feature schema must not be silently ignored by a
        # permissive config parser. A catalogue budget is never isolation.
        scalar_schema = {
            'approval_policy': '"never"', 'forced_login_method': '"chatgpt"',
            'web_search': '"disabled"', 'project_doc_max_bytes': '0',
            'agents.enabled': 'false', 'tools.view_image': 'false',
        }
        require({k: v for k, v in CONTROLS.items() if not k.startswith('features.')} == scalar_schema,
                'metadata_config_schema_unknown')
        selected = {k.removeprefix('features.') for k in CONTROLS if k.startswith('features.')}
        require(selected and all(CONTROLS['features.' + k] == 'false' for k in selected),
                'metadata_feature_value_unsupported')
        with tempfile.TemporaryDirectory(prefix='movie-investigator-metadata-') as tmp:
            tmp = str(Path(tmp).resolve(strict=True))
            env = transport_environment()
            def metadata(args, limit=32768):
                remaining = min(METADATA_SECONDS, deadline - time.monotonic())
                require(remaining > 0, 'metadata_timeout')
                return bounded_process([str(executable)] + args, b'', cwd=tmp,
                                       timeout=remaining, limit=limit, env=env)
            def version():
                require(metadata(['--version'], 4096).decode().strip() == expected_version,
                        'metadata_version_drift')
            version()
            for name, command in help_commands.items():
                raw = metadata(command)
                require(hashlib.sha256(raw).hexdigest() == expected_help_hashes[name], 'metadata_help_drift')
                if name == 'root':
                    require(b'--config' in raw and b'features' in raw, 'metadata_route_unknown')
                elif name == 'features':
                    require(b'--config' in raw and b'list' in raw, 'metadata_route_unknown')
                else:
                    require(all(flag.encode() in raw for flag in REQUIRED_FLAGS), 'metadata_route_unknown')
            # --strict-config and --ignore-user-config/--ignore-rules are exec
            # flags, not supported features-list flags. Do not guess equivalents
            # or suppress mandatory managed requirements to make parsing pass.
            raw = metadata(configuration_args() + ['features', 'list'])
            states = {}
            for line in raw.decode().splitlines():
                match = re.fullmatch(r'([a-z][a-z0-9_.]*)\s+(stable|experimental|under development|deprecated|removed)\s+(true|false)', line)
                require(match is not None, 'metadata_feature_schema_unknown')
                name, _, state = match.groups()
                require(name not in states, 'metadata_feature_schema_unknown')
                states[name] = state
            require(selected <= states.keys(), 'metadata_features_unknown')
            require(all(states[name] == 'false' for name in selected), 'metadata_features_enabled')
            version()
        require(time.monotonic() < deadline, 'metadata_timeout')
        require(executable_hash(executable) == pin, 'metadata_client_drift')
        return dict(configuration_accepted=True, exec_isolation_verified=False,
                    version=expected_version, executable_hash=pin,
                    help_hashes=dict(expected_help_hashes), controls_hash=digest(CONTROLS),
                    selected_features={name: False for name in sorted(selected)})
    except (OSError, UnicodeError) as exc:
        raise Refusal('metadata_inspection_failed') from exc


def parse_events(raw):
    require(len(raw) <= 32768, 'transport_output_limit')
    state = 'new'
    message = None
    for line in raw.splitlines():
        event = decode(line, 16384)
        require(isinstance(event, dict), 'unsupported_model_event')
        kind = event.get('type')
        if kind == 'thread.started' and state == 'new':
            require(set(event) == {'type', 'thread_id'} and isinstance(event['thread_id'], str), 'model_protocol')
            state = 'thread'
        elif kind == 'turn.started' and state == 'thread':
            require(set(event) == {'type'}, 'model_protocol')
            state = 'turn'
        elif kind == 'item.completed' and state == 'turn':
            require(set(event) == {'type', 'item'}, 'model_protocol')
            item = event['item']
            # Reasoning/tool events are neither persisted nor accepted. A future
            # exact client profile must explicitly establish its event grammar.
            require(isinstance(item, dict) and set(item) == {'id', 'type', 'text'}
                    and item['type'] == 'agent_message' and message is None, 'unsupported_model_event')
            require(isinstance(item['text'], str) and len(item['text'].encode()) <= MAX_OUTPUT, 'model_output_limit')
            message = item['text']
        elif kind == 'turn.completed' and state == 'turn' and message is not None:
            require(set(event) == {'type', 'usage'} and isinstance(event['usage'], dict), 'model_protocol')
            state = 'complete'
        else:
            raise Refusal('unsupported_model_event')
    require(state == 'complete' and message is not None, 'unknown_model_completion')
    return message


class CodexCLI:
    def __init__(self, *, enabled=False, executable=None, configured_model=None):
        self.enabled = enabled
        self.executable = Path(executable) if executable is not None else None
        self.model = configured_model
        self.profile = None

    def identity(self):
        return dict(transport='codex_cli', model=self.model or 'unverified',
                    client=self.profile['version'] if self.profile else 'unverified', simulated=False)

    def audit_identity(self):
        return {key: self.profile[key] for key in
                ('executable_hash', 'exec_help_hash', 'boundary_evidence_hash', 'dependency_hashes')} if self.profile else None

    @contextmanager
    def boundary(self, argv, payload, schema, cwd, env):
        """Require a reviewed CODE adapter to hold the effective dependency lease.

        A future adapter must obtain authoritative, complete effective tool,
        context and policy state, and prevent drift for the entire subprocess.
        No such adapter ships. Unknown dependencies or inability to hold that
        boundary must refuse before yield. This is not caller-supplied approval.
        """
        profile = self.profile
        expected = profile['dependency_hashes']
        require(set(expected) == BOUNDARY_DEPENDENCIES, 'client_dependencies_unknown')
        for value in expected.values():
            hash_id(value)
        context = dict(argv=list(argv), input_hash=hashlib.sha256(payload).hexdigest(),
                       schema_hash=digest(schema), cwd=cwd, environment=dict(env),
                       executable_hash=executable_hash(self.executable))
        # No raw configuration or environment is persisted in audit records.
        with profile['boundary_adapter'].lease(copy.deepcopy(context)) as observed:
            shape(observed, 'invocation_hash dependency_hashes')
            require(observed['invocation_hash'] == digest(context), 'client_invocation_changed')
            require(observed['dependency_hashes'] == expected, 'client_dependencies_changed')
            require(context['executable_hash'] == profile['executable_hash'], 'client_changed')
            yield

    def preflight(self):
        self.profile = None  # A failed recheck must discard earlier success.
        if self.enabled is not True:
            return 'model_transport_disabled'
        if self.executable is None or not self.model:
            return 'model_dependency_missing'
        deadline = time.monotonic() + PREFLIGHT_SECONDS
        try:
            text(self.model, 100)
            pin = executable_hash(self.executable)
            profile = REVIEWED_CLIENTS.get(pin)
            if not profile or 'boundary_adapter' not in profile:
                return 'model_tool_boundary_unverified'
            require(profile['model'] == self.model, 'configured_model_changed')
            require(profile['controls'] == CONTROLS, 'model_tool_boundary_unverified')
            hash_id(profile['boundary_evidence_hash'])
            # Copy mutable profile values; the code adapter owns its lease.
            self.profile = dict(copy.deepcopy({k: v for k, v in profile.items()
                                              if k != 'boundary_adapter'}),
                                boundary_adapter=profile['boundary_adapter'], executable_hash=pin)
            env = transport_environment()
            with tempfile.TemporaryDirectory(prefix='movie-investigator-preflight-') as tmp:
                tmp = str(Path(tmp).resolve(strict=True))
                def metadata(args, limit):
                    argv = [str(self.executable)] + args
                    with self.boundary(argv, b'', None, tmp, env):
                        remaining = min(METADATA_SECONDS, deadline - time.monotonic())
                        require(remaining > 0, 'metadata_timeout')
                        return bounded_process(argv, b'', cwd=tmp, timeout=remaining, limit=limit, env=env)
                version = metadata(['--version'], 4096)
                help_text = metadata(['exec', '--help'], 32768)
            require(time.monotonic() < deadline, 'metadata_timeout')
            require(version.decode().strip() == profile['version'] and
                    hashlib.sha256(help_text).hexdigest() == profile['exec_help_hash'] and
                    all(flag.encode() in help_text for flag in REQUIRED_FLAGS), 'client_compatibility_unverified')
            return None
        except (OSError, ValueError, KeyError, TypeError, AttributeError, UnicodeError):
            self.profile = None
            return 'model_tool_boundary_unverified'

    def complete(self, payload, *, schema, timeout):
        require(0 < timeout <= 25, 'transport_bounds')
        deadline = time.monotonic() + timeout
        require(self.profile is not None and self.enabled is True, 'model_tool_boundary_unverified')
        require(executable_hash(self.executable) == self.profile['executable_hash'], 'client_changed')
        require(self.model == self.profile['model'], 'configured_model_changed')
        require(CONTROLS == self.profile['controls'], 'client_controls_changed')
        require(len(payload) <= MAX_INPUT, 'model_input_limit')
        with tempfile.TemporaryDirectory(prefix='movie-investigator-call-') as tmp:
            tmp = str(Path(tmp).resolve(strict=True))
            os.chmod(tmp, 0o700)
            schema_path = Path(tmp) / 'output-schema.json'
            fd = os.open(schema_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(encoded(schema))
            argv = [str(self.executable), '-c', 'approval_policy="never"', 'exec',
                    '--strict-config', '--ignore-user-config', '--ignore-rules', '--ephemeral', '--json',
                    '--sandbox', 'read-only', '--skip-git-repo-check', '--cd', tmp,
                    '--model', self.model, '--output-schema', str(schema_path)]
            argv.extend(configuration_args())
            argv.append('-')
            env = transport_environment()
            with self.boundary(argv, payload, schema, tmp, env):
                remaining = deadline - time.monotonic()
                require(remaining > 0, 'model_timeout')
                raw = bounded_process(argv, payload, cwd=tmp, timeout=remaining, limit=32768, env=env)
        return parse_events(raw)


class FakeTransport:
    """Inject explicit protocol replies; never claim a real identification."""
    def __init__(self, replies):
        self.replies = list(replies)
        self.inputs = []

    def identity(self):
        return dict(transport='fake', model='simulated_model', client='fixture_v1', simulated=True)

    def preflight(self):
        return None

    def complete(self, payload, *, schema, timeout):
        require(0 < timeout <= 25, 'transport_bounds')
        self.inputs.append(decode(payload, MAX_INPUT))
        require(bool(self.replies), 'fake_reply_missing')
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return encoded(reply) if isinstance(reply, dict) else reply
