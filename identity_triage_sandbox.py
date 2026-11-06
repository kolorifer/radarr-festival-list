"""Linux x86-64 Landlock ABI6 boundary for the socket-activated collector.

Systemd supplies the sole loopback listener and complementary syscall restrictions.
No hand-written seccomp program, helper daemon, privileged setup or extra dependency.
Confinement is applied on the single startup thread before imports/worker threads.
"""
import ctypes
import errno
import os
from pathlib import Path
import platform
import resource
import socket
import stat

READ = (1 << 2) | (1 << 3)
STATE = READ | (1 << 1) | (1 << 5) | (1 << 8) | (1 << 14)
HANDLED_FS = (1 << 16) - 1  # ABI1-5 through IOCTL_DEV


class Ruleset(ctypes.Structure):
    _fields_ = [('filesystem', ctypes.c_uint64), ('network', ctypes.c_uint64),
                ('scoped', ctypes.c_uint64)]


class Beneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


def _kernel():
    if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
            or ctypes.sizeof(ctypes.c_void_p) != 8):
        raise ValueError('unsupported_sandbox_platform')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    return libc


def _call(libc, number, *args):
    result = libc.syscall(ctypes.c_long(number), *args)
    if result < 0:
        raise OSError(ctypes.get_errno(), 'sandbox_kernel_denial')
    return result


def restrict(read_paths, state):
    """Irreversibly apply known rights, TCP deny-all and ABI6 IPC scoping."""
    libc = _kernel()
    abi = _call(libc, 444, ctypes.c_void_p(), ctypes.c_size_t(0), ctypes.c_uint(1))
    if abi < 6:
        raise ValueError('sandbox_abi_insufficient')
    if libc.prctl(38, 1, 0, 0, 0) != 0 or libc.prctl(39, 0, 0, 0, 0) != 1:
        raise ValueError('sandbox_no_new_privs')
    policy = Ruleset(HANDLED_FS, 3, 3)
    rules_fd = _call(libc, 444, ctypes.byref(policy), ctypes.c_size_t(ctypes.sizeof(policy)), 0)
    try:
        for path, rights in [(p, READ) for p in read_paths] + [(state, STATE)]:
            fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = Beneath(rights, fd)
                _call(libc, 445, rules_fd, 1, ctypes.byref(rule), 0)
            finally:
                os.close(fd)
        _call(libc, 446, rules_fd, 0)
    finally:
        os.close(rules_fd)
    return abi


def verify_isolation(home=None):
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



# Trusted-code capability, not an isolation boundary against malicious Python.
# Only confine mints one; main completes it after isolation_check and a recheck.
_STARTUP_KEY = object()


class _StartupEvidence:
    __slots__ = ('_values', '_complete', '_owner')

    def __init__(self, key, values):
        if key is not _STARTUP_KEY:
            raise ValueError('startup_evidence')
        self._values = values
        self._complete = False
        self._owner = None


def _runtime_identity():
    libc = _kernel()
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(39, 0, 0, 0, 0) != 1 or libc.prctl(21, 0, 0, 0, 0) != 2:
        raise ValueError('startup_runtime_flags')
    # Linux rejects this invalid uid/gid BEFORE prepare_creds/commit_creds,
    # returning the old filesystem ID. Never pass a valid replacement ID.
    filesystem_ids = []
    for number in (122, 123):  # native x86-64 setfsuid/setfsgid
        ctypes.set_errno(0)
        value = libc.syscall(ctypes.c_long(number), ctypes.c_uint(0xffffffff))
        if value < 0 or ctypes.get_errno() != 0 or value != 1094:
            raise ValueError('startup_filesystem_identity')
        filesystem_ids.append(value)
    uids, gids = os.getresuid(), os.getresgid()
    if uids != (1094, 1094, 1094) or gids != (1094, 1094, 1094):
        raise ValueError('startup_identity')
    return (os.getpid(), 1, 2, uids + (filesystem_ids[0],), gids + (filesystem_ids[1],))


def prepare_startup(evidence, enabled):
    """No new capture-only syscalls at all when preparation is disabled."""
    if (type(evidence) is not _StartupEvidence or evidence._complete is not False
            or evidence._values[1] is not None):
        return None
    evidence._complete = None
    if enabled is not True:
        return None
    try:
        values = _runtime_identity()
        if values[0] != evidence._values[0]:
            return None
    except (OSError, ValueError):
        return None
    evidence._values = values + (evidence._values[5],)
    evidence._complete = False
    return evidence


def complete_startup(evidence):
    """Capture-only recheck, after isolation/Store and before app workers.

    Failure never weakens old confinement or blocks ordinary default-off intake.
    An attempted/failed capability cannot be completed or bound later.
    """
    if type(evidence) is not _StartupEvidence or evidence._complete is not False:
        return None
    evidence._complete = None  # terminal until this one recheck succeeds
    try:
        verify_isolation()
        if evidence._values[:5] != _runtime_identity():
            return None
    except (OSError, ValueError):
        return None
    evidence._complete = True
    return evidence


def bind_startup(evidence, owner):
    if (type(evidence) is not _StartupEvidence or evidence._complete is not True
            or evidence._owner is not None or evidence._values[0] != os.getpid()):
        return None
    evidence._owner = owner
    return evidence


def startup_statement(evidence, owner):
    if (type(evidence) is not _StartupEvidence or evidence._complete is not True
            or evidence._owner is not owner or evidence._values[0] != os.getpid()):
        return None
    pid, nnp, seccomp, uids, gids, abi = evidence._values
    return dict(version=1, pid=pid, no_new_privileges=nnp, seccomp_mode=seccomp,
                uids=list(uids), gids=list(gids), landlock_abi=abi,
                denial_suite='collector-startup-v1', isolation_check=True,
                evidence_kind='trusted_startup_self_observation',
                loaded_code_identity='not_attested')


def _private_directory(path):
    path = Path(path)
    info = path.lstat()
    if (not path.is_absolute() or path.resolve() != path or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError('sandbox_directory')
    return path


def deny_check(operation, missing=False):
    """Require effective denial, not a configuration marker or seccomp mode flag."""
    try:
        result = operation()
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EPERM) or (missing and exc.errno == errno.ENOENT):
            return
        raise ValueError('sandbox_probe_error') from None
    if type(result) == int and result >= 0:
        os.close(result)
    elif hasattr(result, 'close'):
        result.close()
    raise ValueError('sandbox_access_allowed')


def confine(config, state):
    """Only supported service entrypoint. Plain invocation cannot bypass the gate.

    Layout is fixed deliberately: changing a code/config/state root requires review,
    not an arbitrary --state argument that could grant access to movie-intel files.
    """
    _kernel()  # refuse unsupported hosts before touching activation descriptors
    home = Path.home().resolve()
    code = _private_directory(home / '.local/lib/movie-identity-triage')
    config_dir = _private_directory(home / '.config/movie-identity-triage')
    state_dir = _private_directory(home / '.local/state/movie-identity-triage')
    if (Path(__file__).resolve().parent != code or Path(config) != config_dir / 'config.json'
            or Path(state) != state_dir):
        raise ValueError('sandbox_layout')
    if any(k.startswith(('RADARR_', 'TELEGRAM_', 'TMDB_', 'MOVIE_INTEL_', 'PROWLARR_')) for k in os.environ):
        raise ValueError('sandbox_credentials')
    # systemd's clean stdio is allowed; no inherited regular file or sensitive fd.
    stdin = os.fstat(0)
    if not stat.S_ISCHR(stdin.st_mode) or stdin.st_rdev != os.makedev(1, 3):
        raise ValueError('sandbox_stdin')
    if any(not (stat.S_ISSOCK(os.fstat(fd).st_mode) or stat.S_ISFIFO(os.fstat(fd).st_mode)) for fd in (1, 2)):
        raise ValueError('sandbox_stdio')
    listener = socket.socket(fileno=3)
    address = listener.getsockname()
    if (listener.family != socket.AF_INET or listener.type != socket.SOCK_STREAM
            or not listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN)
            or address[0] != '127.0.0.1' or not 1024 <= address[1] <= 65535):
        raise ValueError('sandbox_listener')
    limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    if not 4 <= limit <= 2**31-1:
        raise ValueError('sandbox_fd_limit')
    os.closerange(4, limit)
    # Runtime allowlist is narrow and version-specific; no blanket /usr, /etc,
    # /proc or home access. Loaded native libraries need no execute permission.
    runtime = Path('/usr/lib') / ('python' + platform.python_version_tuple()[0] + '.' + platform.python_version_tuple()[1])
    abi = restrict([code, config_dir, runtime, Path('/usr/lib/x86_64-linux-gnu')], state_dir)
    for relative in ('.config/movie-intel', '.local/state/movie-intel', '.apps', '.ssh', 'radarr-festival-list'):
        deny_check(lambda relative=relative: os.open(home / relative, os.O_RDONLY | os.O_DIRECTORY), missing=True)
    deny_check(lambda: os.open('/proc/self/environ', os.O_RDONLY))
    deny_check(lambda: os.open('/proc/self/fd', os.O_RDONLY))
    for family, kind in ((socket.AF_INET, socket.SOCK_STREAM), (socket.AF_INET, socket.SOCK_DGRAM),
                         (socket.AF_UNIX, socket.SOCK_STREAM)):
        deny_check(lambda family=family, kind=kind: socket.socket(family, kind))
    # Same-mode chmod is harmless even if a unit was misconfigured. Any success
    # fails startup before the receiver reads requests. Unit forbids the full
    # chmod/chown/xattr/time syscall families, which ABI6 cannot mediate itself.
    deny_check(lambda: os.chmod(state_dir, 0o700))
    evidence = _StartupEvidence(_STARTUP_KEY, (os.getpid(), None, None, None, None, abi))
    return listener, abi, evidence
