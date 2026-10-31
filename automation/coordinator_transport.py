"""Fixed read-only remote helper and bounded parent transport. No CLI or discovery.

The helper source is sent on stdin to one explicitly selected SSH endpoint. It
uses only Python's standard library; no remote shell parameters contain input.
"""
import base64
import contextlib
import errno
import hashlib
import json
import os
import selectors
import signal
import stat
import subprocess
import time

LIMIT = 2097152
OUTPUT_LIMIT = 6 * 1024 * 1024
ERROR_LIMIT = 16384
PATHS = ('incoming/snapshot.json', 'review-report.json')
LOCAL_SECONDS = 45
REMOTE_SECONDS = 30


def need(value):
    if not value:
        raise ValueError('source_guard')


def metadata(fd):
    s = os.fstat(fd)
    return [s.st_dev, s.st_ino, s.st_uid, s.st_gid, s.st_mode,
            s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def acl(fd, directory):
    # Linux descriptor xattrs: only proven absence of POSIX ACLs is accepted.
    # Unsupported ACL inspection is uncertainty, never absence. No getfacl shell.
    for name in ('system.posix_acl_access', 'system.posix_acl_default') if directory else ('system.posix_acl_access',):
        try:
            os.getxattr(fd, name)
        except OSError as e:
            need(e.errno == errno.ENODATA)
        else:
            need(False)


def exact(fd, name):
    found = False
    with os.scandir(fd) as entries:
        for i, entry in enumerate(entries):
            need(i < 8192)
            found |= entry.name == name
    if not found:
        try:
            os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        need(False)  # Alias/case mismatch.
    return True


@contextlib.contextmanager
def chain(config):
    names = config['root'].split('/')[1:]
    held, observed = [], []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        held.append(fd)
        for index in range(len(names) + 1):
            before = metadata(fd)
            pinned = config['ancestors'][index]
            need(before[:5] == pinned and stat.S_ISDIR(before[4])
                 and before[2] in (0, config['uid']) and not before[4] & 0o022)
            if index == len(names):
                need(before[2] == config['uid'])
            acl(fd, True)
            observed.append(before)
            if index < len(names):
                need(exact(fd, names[index]))
                child = os.open(names[index], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                held.append(child)
                need(os.path.samestat(os.fstat(child), os.stat(names[index], dir_fd=fd, follow_symlinks=False)))
                fd = child
        yield fd
        for i, fd in enumerate(held):
            need(metadata(fd) == observed[i])
            acl(fd, True)
            if i:
                need(exact(held[i-1], names[i-1]))
                need(os.path.samestat(os.fstat(fd), os.stat(names[i-1], dir_fd=held[i-1], follow_symlinks=False)))
    finally:
        for fd in reversed(held):
            os.close(fd)


def read_export(root, path, uid, gid=None):
    with contextlib.ExitStack() as stack:
        parent = root
        if '/' in path:
            name, path = path.split('/')
            if not exact(root, name):
                return {'status': 'missing'}
            parent = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            stack.callback(os.close, parent)
            before_dir = metadata(parent)
            need(before_dir[2] == uid and (gid is None or before_dir[3] == gid)
                 and stat.S_IMODE(before_dir[4]) == 0o700)
            acl(parent, True)
        if not exact(parent, path):
            return {'status': 'missing'}
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        stack.callback(os.close, fd)
        before = metadata(fd)
        need(stat.S_ISREG(before[4]) and before[2] == uid and (gid is None or before[3] == gid)
             and stat.S_IMODE(before[4]) == 0o600 and before[8] == 1)
        acl(fd, False)
        if before[5] > LIMIT:
            return {'status': 'oversized', 'metadata': before}
        chunks, left = [], LIMIT + 1
        while left:
            chunk = os.read(fd, min(left, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            left -= len(chunk)
        raw = b''.join(chunks)
        need(len(raw) == before[5] and len(raw) <= LIMIT and before == metadata(fd))
        acl(fd, False)
        need(exact(parent, path) and os.path.samestat(os.fstat(fd), os.stat(path, dir_fd=parent, follow_symlinks=False)))
        if parent != root:
            need(before_dir == metadata(parent))
            acl(parent, True)
            need(os.path.samestat(os.fstat(parent), os.stat('incoming', dir_fd=root, follow_symlinks=False)))
        return {'status': 'read', 'metadata': before, 'sha256': hashlib.sha256(raw).hexdigest(),
                'bytes': base64.b64encode(raw).decode('ascii')}


def remote(config):
    # No output until all guards (including post-read ancestry) succeed. Unsafe
    # origin conditions discard acquired bytes rather than presenting them as safe.
    need(os.geteuid() > 0 and os.geteuid() == config['uid']
         and os.getegid() == config['gid'])
    with chain(config) as fd:
        files = {p: read_export(fd, p, config['uid'], config['gid']) for p in PATHS}
    return {'version': 1, 'files': files}


def bounded_process(argv, script, pass_fds):
    """One process, bounded stdout/stderr and wall time; never a shell/retry."""
    with subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, pass_fds=pass_fds,
                          env={'PATH': '/usr/bin:/bin', 'LANG': 'C'}) as proc:
        streams = {'out': bytearray(), 'err': bytearray()}
        deadline = time.monotonic() + LOCAL_SECONDS
        try:
            # The reviewed helper is small enough for the pipe; use nonblocking
            # selector-driven stdin too, so an unresponsive SSH cannot block us.
            with selectors.DefaultSelector() as sel:
                for stream, label, events in ((proc.stdin, 'in', selectors.EVENT_WRITE),
                                               (proc.stdout, 'out', selectors.EVENT_READ),
                                               (proc.stderr, 'err', selectors.EVENT_READ)):
                    os.set_blocking(stream.fileno(), False)
                    sel.register(stream, events, label)
                offset = 0
                if not script:
                    sel.unregister(proc.stdin)
                    proc.stdin.close()
                while sel.get_map():
                    need(time.monotonic() < deadline)
                    for key, _ in sel.select(min(0.1, max(0, deadline - time.monotonic()))):
                        if key.data == 'in':
                            count = os.write(key.fd, script[offset:offset+4096])
                            offset += count
                            if offset == len(script):
                                sel.unregister(key.fileobj)
                                key.fileobj.close()
                        else:
                            raw = os.read(key.fd, 65536)
                            if not raw:
                                sel.unregister(key.fileobj)
                            else:
                                limit = OUTPUT_LIMIT if key.data == 'out' else ERROR_LIMIT
                                remaining = limit - len(streams[key.data])
                                streams[key.data].extend(raw[:remaining])
                                need(len(raw) <= remaining)
                proc.wait(timeout=max(0.01, deadline - time.monotonic()))
            return {'returncode': proc.returncode, 'stdout': bytes(streams['out']),
                    'stderr': bytes(streams['err']), 'complete': True}
        except BaseException:
            proc.kill()
            proc.wait()
            return {'returncode': proc.returncode, 'stdout': bytes(streams['out']),
                    'stderr': bytes(streams['err']), 'complete': False}


def ssh_argv(selected):
    options = ('BatchMode=yes', 'IdentitiesOnly=yes', 'IdentityAgent=none',
               'ForwardAgent=no', 'PasswordAuthentication=no', 'KbdInteractiveAuthentication=no',
               'PreferredAuthentications=publickey', 'StrictHostKeyChecking=yes',
               'GlobalKnownHostsFile=/dev/null', 'ProxyCommand=none', 'ProxyJump=none',
               'PermitLocalCommand=no', 'ClearAllForwardings=yes', 'RequestTTY=no',
               'ConnectionAttempts=1', 'ConnectTimeout=10', 'ServerAliveInterval=5',
               'ServerAliveCountMax=1', 'UpdateHostKeys=no', 'CanonicalizeHostname=no',
               'HostbasedAuthentication=no', 'GSSAPIAuthentication=no',
               'NumberOfPasswordPrompts=0', 'ControlMaster=no', 'ControlPath=none',
               'ControlPersist=no', 'CertificateFile=none')
    argv = ['/usr/bin/ssh', '-F', '/dev/null', '-T']
    for option in options:
        argv.extend(('-o', option))
    argv.extend(('-o', 'UserKnownHostsFile=' + selected['known_hosts']['path'],
                 '-i', selected['key']['path'], '-p', str(selected['port']),
                 selected['account'] + '@' + selected['host'], '/usr/bin/python3 -I -B -'))
    return argv


def remote_script(selected, helper):
    # repr protects literal data in Python; it is never part of the SSH command.
    config = {k: selected[k] for k in ('root', 'uid', 'gid', 'ancestors')}
    return (helper + b'\nsignal.signal(signal.SIGALRM, lambda *_: os._exit(124))\n'
            + ('signal.alarm(%d)\n' % REMOTE_SECONDS).encode()
            + b'try:\n print(json.dumps(remote(json.loads(' + repr(json.dumps(config)).encode()
            + b'))))\nexcept Exception:\n print("{\\"error\\":\\"source_guard\\"}")\n')


def acquire(selected, helper, check, lock_fds=()):
    """Fork only fixed transport code, never an argv/script from a request.

    The keeper owns one bounded SSH child and holds the inherited open lock
    descriptions even if the dispatcher dies and OpenSSH closes its own FDs.
    It has no CLI, exec protocol, retry, detached loop or persistent service.
    """
    # OpenSSH opens the guarded original canonical files. Held descriptor and
    # namespace checks detect stable-owner changes; they cannot give atomicity
    # against hostile same-account swap-and-restore during pathname opening.
    need(len(lock_fds) == 2 and len(set(lock_fds)) == 2)
    for fd in lock_fds:
        os.fstat(fd)
    reader, writer = os.pipe()
    try:
        pid = os.fork()
    except BaseException:
        os.close(reader); os.close(writer)
        raise
    if pid == 0:
        os.close(reader)
        # Parent death must not kill the keeper via its terminal/process group.
        # Only this keeper's bounded subprocess is killed by bounded_process.
        try:
            os.setsid()
            check()
            result = bounded_process(ssh_argv(selected), remote_script(selected, helper), ())
            check()
            raw = json.dumps({**result, 'stdout': base64.b64encode(result['stdout']).decode(),
                              'stderr': base64.b64encode(result['stderr']).decode()}).encode()
            offset = 0
            os.set_blocking(writer, False)
            deadline = time.monotonic() + 5
            with selectors.DefaultSelector() as sel:
                sel.register(writer, selectors.EVENT_WRITE)
                while offset < len(raw):
                    need(time.monotonic() < deadline)
                    if sel.select(0.1):
                        offset += os.write(writer, raw[offset:offset+65536])
        except BaseException:
            pass  # No private diagnostics on inherited public stdout/stderr.
        finally:
            os.close(writer)
            os._exit(0)
    os.close(writer)
    raw = bytearray()
    try:
        os.set_blocking(reader, False)
        deadline = time.monotonic() + LOCAL_SECONDS + 10
        with selectors.DefaultSelector() as sel:
            sel.register(reader, selectors.EVENT_READ)
            while True:
                need(time.monotonic() < deadline)
                if not sel.select(0.1):
                    continue
                chunk = os.read(reader, 65536)
                if not chunk:
                    break
                raw.extend(chunk)
                need(len(raw) <= (OUTPUT_LIMIT + ERROR_LIMIT) * 2 + 4096)
        os.waitpid(pid, 0)  # EOF: keeper has finished its child/transfer cleanup.
        result = json.loads(raw)
        for name in ('stdout', 'stderr'):
            result[name] = base64.b64decode(result[name], validate=True)
        need(len(result['stdout']) <= OUTPUT_LIMIT and len(result['stderr']) <= ERROR_LIMIT)
        return result
    finally:
        os.close(reader)
        # A failed initiating parent never kills a keeper that still owns SSH.
        # Its own deadline/cleanup governs the single child; no connection retry.
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            pass
