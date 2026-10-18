"""Finite TMDb-only worker boundary; never changes the Stage1 sandbox.

Trusted startup establishes one certificate-verified TLS connection to the fixed
provider, then Landlock and libseccomp deny all new networking before research.
The provider client cannot reconnect or redirect. No tracker cookie is provisioned.
"""
import ctypes
import errno
import http.client
import os
from pathlib import Path
import resource
import socket
import ssl
import stat

from identity_triage_sandbox import _kernel, _private_directory, restrict, deny_check

HOST = 'api.themoviedb.org'
DENIED = ('socket socketpair connect bind listen accept accept4 '
          'chmod fchmod fchmodat fchmodat2 chown fchown lchown fchownat '
          'utime utimes futimesat utimensat setxattr lsetxattr fsetxattr '
          'removexattr lremovexattr fremovexattr ptrace process_vm_readv '
          'process_vm_writev pidfd_getfd io_uring_setup io_uring_enter io_uring_register').split()


class FixedConnection(http.client.HTTPSConnection):
    def connect(self):
        raise PermissionError('research_reconnect_denied')


def preconnect():
    """No credentials or HTTP request during trusted TLS setup."""
    context = ssl.create_default_context()
    raw = socket.create_connection((HOST, 443), timeout=4)
    try:
        sock = context.wrap_socket(raw, server_hostname=HOST)
    except BaseException:
        raw.close()
        raise
    c = FixedConnection(HOST, timeout=4, context=context)
    c.sock = sock
    return c


def deny_syscalls():
    lib = ctypes.CDLL('/usr/lib/x86_64-linux-gnu/libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]; lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW; native arch only
    if not ctx:
        raise ValueError('research_seccomp_init')
    try:
        for name in DENIED:
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number < 0 or lib.seccomp_rule_add(ctx, 0x50000 | errno.EPERM, number, 0) != 0:
                raise ValueError('research_seccomp_rule')
        if lib.seccomp_load(ctx) != 0:
            raise ValueError('research_seccomp_load')
    finally:
        lib.seccomp_release(ctx)


def confine(connection, config, state):
    _kernel()
    home = Path.home().resolve()
    code = _private_directory(home / '.local/lib/movie-identity-research')
    config_dir = _private_directory(home / '.config/movie-identity-research')
    state_dir = _private_directory(home / '.local/state/movie-identity-research')
    if (Path(__file__).resolve().parent != code or Path(config) != config_dir / 'config.json'
            or Path(state) != state_dir or os.environ.get('LC_ALL') != 'C.UTF-8' or set(os.environ) - {'HOME', 'PATH', 'PYTHONDONTWRITEBYTECODE', 'LC_ALL'}):
        raise ValueError('research_layout_environment')
    if not stat.S_ISCHR(os.fstat(0).st_mode) or os.fstat(0).st_rdev != os.makedev(1, 3):
        raise ValueError('research_stdio')
    if any(not (stat.S_ISSOCK(os.fstat(fd).st_mode) or stat.S_ISFIFO(os.fstat(fd).st_mode)) for fd in (1, 2)):
        raise ValueError('research_stdio')
    allowed_fd = connection.sock.fileno() if connection else -1
    if connection and (not isinstance(connection, FixedConnection) or connection.host != HOST
                       or not isinstance(connection.sock, ssl.SSLSocket)
                       or connection.sock.server_hostname != HOST
                       or connection.sock.context.verify_mode != ssl.CERT_REQUIRED
                       or not connection.sock.context.check_hostname):
        raise ValueError('research_provider_socket')
    limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    if not 4 <= limit <= 2**31-1:
        raise ValueError('research_fd_limit')
    os.closerange(3, allowed_fd if allowed_fd >= 3 else limit)
    if allowed_fd >= 3:
        os.closerange(allowed_fd + 1, limit)
    import sys
    runtime = Path('/usr/lib/python%d.%d' % sys.version_info[:2])
    abi = restrict([code, config_dir, runtime, Path('/usr/lib/x86_64-linux-gnu')], state_dir)
    deny_syscalls()
    for relative in ('.config/movie-intel', '.local/state/movie-intel', '.apps', '.ssh',
                     'radarr-festival-list', '.local/state/movie-identity-triage'):
        deny_check(lambda relative=relative: os.open(home / relative, os.O_RDONLY | os.O_DIRECTORY))
    for path in ('/proc/self/environ', '/proc/self/fd'):
        deny_check(lambda path=path: os.open(path, os.O_RDONLY))
    for family, kind in ((socket.AF_INET, socket.SOCK_STREAM), (socket.AF_INET6, socket.SOCK_STREAM),
                         (socket.AF_INET, socket.SOCK_DGRAM), (socket.AF_UNIX, socket.SOCK_STREAM)):
        deny_check(lambda family=family, kind=kind: socket.socket(family, kind))
    deny_check(lambda: os.chmod(state_dir, 0o700))
    return abi
