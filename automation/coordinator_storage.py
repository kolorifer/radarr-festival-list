"""Parent-only fixed storage profile. No CLI, environment authority or recovery.

All reasons are fixed; paths and identities belong only in the private journal.
Stable-owner change detection, not isolation from hostile same-account processes.
"""
import contextlib
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import sys

try:
    from automation.supervisor_policy import PolicyError, unique_object
except ModuleNotFoundError:
    from supervisor_policy import PolicyError, unique_object

SUFFIX = '/.local/state/movie-project-coordinator-private'
LIMIT = 16384


class StorageError(PolicyError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise StorageError(code)


def canonical(path):
    return (isinstance(path, str) and len(path) <= 4096 and path.startswith('/')
            and len(path.split('/')) <= 128
            and all(re.fullmatch(r'[A-Za-z0-9_.-]+', p) and p not in ('.', '..')
                    for p in path[1:].split('/')))


def selection(data):
    """Parse only already authenticated immutable input bytes, before reservation."""
    require(len(data) <= LIMIT, 'storage_selection')
    try:
        value = json.loads(data.decode('ascii'), object_pairs_hook=unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, PolicyError, RecursionError):
        raise StorageError('storage_selection') from None
    require(isinstance(value, dict) and set(value) == {'version', 'path', 'expected'},
            'storage_selection')
    require(type(value['version']) is int and value['version'] == 1, 'storage_selection')
    # pwd uses the effective UID's OS account database, never HOME or a task value.
    try:
        home = pwd.getpwuid(os.geteuid()).pw_dir
    except (KeyError, OSError):
        raise StorageError('storage_account') from None
    require(canonical(home) and canonical(value['path']) and value['path'] == home + SUFFIX,
            'storage_path')
    expected = value['expected']
    require(expected == 'absent' or (isinstance(expected, dict)
            and set(expected) == {'dev', 'ino'} and type(expected['dev']) is int
            and expected['dev'] >= 0 and type(expected['ino']) is int and expected['ino'] > 0),
            'storage_selection')
    return value


def _darwin_acl(fd):
    """Darwin sys/acl.h: bounded descriptor ACL, accept only native deny entries.

    Denies cannot extend access; preserve them without interpreting principals or
    changing the filesystem ACL. Unknown tags, API failures and oversize reject.
    """
    lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    ptr = ctypes.c_void_p
    signatures = {
        'acl_get_fd_np': ([ctypes.c_int, ctypes.c_int], ptr),
        'acl_valid': ([ptr], ctypes.c_int),
        'acl_size': ([ptr], ctypes.c_ssize_t),
        'acl_get_entry': ([ptr, ctypes.c_int, ctypes.POINTER(ptr)], ctypes.c_int),
        'acl_get_tag_type': ([ptr, ctypes.POINTER(ctypes.c_int)], ctypes.c_int),
        'acl_to_text': ([ptr, ctypes.POINTER(ctypes.c_ssize_t)], ptr),
        'acl_free': ([ptr], ctypes.c_int),
    }
    for name, (args, result) in signatures.items():
        fn = getattr(lib, name); fn.argtypes = args; fn.restype = result
    ctypes.set_errno(0)
    acl = lib.acl_get_fd_np(fd, 0x100)  # ACL_TYPE_EXTENDED
    if not acl and ctypes.get_errno() == errno.ENOENT:
        return _darwin_acl_absence(lib, fd)
    require(bool(acl), 'storage_acl')
    try:
        require(lib.acl_valid(acl) == 0 and 0 <= lib.acl_size(acl) <= LIMIT, 'storage_acl')
        for index in range(129):
            entry = ptr()
            ctypes.set_errno(0)
            result = lib.acl_get_entry(acl, 0 if index == 0 else -1, ctypes.byref(entry))
            if result == -1 and ctypes.get_errno() == errno.EINVAL:
                break  # Valid ACL exhausted (Darwin, unlike Linux, returns -1).
            require(result == 0 and index < 128, 'storage_acl')
            tag = ctypes.c_int()
            require(lib.acl_get_tag_type(entry, ctypes.byref(tag)) == 0 and tag.value == 2,
                    'storage_acl')  # ACL_EXTENDED_DENY only
        length = ctypes.c_ssize_t()
        text = lib.acl_to_text(acl, ctypes.byref(length))
        require(bool(text), 'storage_acl')
        try:
            require(0 <= length.value <= LIMIT, 'storage_acl')
            return hashlib.sha256(ctypes.string_at(text, length.value)).hexdigest()
        finally:
            lib.acl_free(text)
    finally:
        lib.acl_free(acl)


def _darwin_acl_absence(lib, fd):
    """ENOENT alone proves nothing. Require supported descriptor security metadata.

    Darwin's acl_get_fd_np wraps fstatx_np/filesec_get_property; absent FILESEC_ACL
    is returned as ENOENT. Query a fresh filesec after a *successful* fstatx_np and
    independently require _PC_EXTENDED_SECURITY_NP support. No pathname fallback.
    """
    ptr = ctypes.c_void_p
    signatures = {
        'fpathconf': ([ctypes.c_int, ctypes.c_int], ctypes.c_long),
        'filesec_init': ([], ptr), 'filesec_free': ([ptr], None),
        'fstatx_np': ([ctypes.c_int, ptr, ptr], ctypes.c_int),
        'filesec_query_property': ([ptr, ctypes.c_int, ctypes.POINTER(ctypes.c_int)], ctypes.c_int),
    }
    for name, (args, result) in signatures.items():
        fn = getattr(lib, name); fn.argtypes = args; fn.restype = result
    require(lib.fpathconf(fd, 13) == 1, 'storage_acl_unsupported')
    security = lib.filesec_init()
    require(bool(security), 'storage_acl')
    try:
        # Opaque, aligned storage, larger than either Darwin struct stat ABI.
        metadata = (ctypes.c_uint64 * 512)()
        require(lib.fstatx_np(fd, metadata, security) == 0, 'storage_acl')
        present = ctypes.c_int(-1)
        require(lib.filesec_query_property(security, 5, ctypes.byref(present)) == 0
                and present.value == 0, 'storage_acl')  # FILESEC_ACL
        return hashlib.sha256(b'no_extended_acl').hexdigest()
    finally:
        lib.filesec_free(security)


def acl_identity(fd):
    try:
        if sys.platform == 'darwin':
            return _darwin_acl(fd)
        raise StorageError('storage_acl_unsupported')
    except (OSError, AttributeError):
        raise StorageError('storage_acl_unsupported') from None


def identity(info):
    return [info.st_dev, info.st_ino, info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)]


def exact_entry(fd, name):
    # Bounded metadata enumeration also detects aliases on case-insensitive FSs.
    found = False
    with os.scandir(fd) as entries:
        for index, entry in enumerate(entries):
            require(index < 8192, 'storage_spelling')
            found |= entry.name == name
    if not found:
        try:
            os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        raise StorageError('storage_spelling')
    return True


class Grant:
    def __init__(self, selected, source, protected, record):
        self.selected = selected
        self.path = Path(selected['path'])
        self.home = str(self.path)[:-len(SUFFIX)]
        self.uid = os.geteuid()
        self.protected = [Path(p) for p in protected]
        self.record = record
        self.evidence = {'version': 1, 'selection': selected, 'source': source,
                         'state': 'refused', 'reason': 'storage_not_prepared', 'identities': []}
        self.baseline = None

    def persist(self, state, reason, identities=None):
        self.evidence.update(state=state, reason=reason)
        if identities is not None:
            self.evidence['identities'] = identities
        self.record(self.evidence)

    @contextlib.contextmanager
    def chain(self, path, guard=False):
        fds, observations = [], []
        try:
            fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            fds.append(fd)
            names = str(path).split('/')[1:]
            for index in range(len(names) + 1):
                info = os.fstat(fd)
                require(stat.S_ISDIR(info.st_mode), 'storage_type')
                if guard:
                    current = '/' + '/'.join(names[:index])
                    owned = current == self.home or current.startswith(self.home + '/')
                    require(info.st_uid == self.uid if owned else info.st_uid in (0, self.uid),
                            'storage_owner')
                    require(not stat.S_IMODE(info.st_mode) & 0o022, 'storage_mode')
                    if current == str(self.path):
                        require(stat.S_IMODE(info.st_mode) == 0o700, 'storage_mode')
                    acl = acl_identity(fd)
                else:
                    acl = None
                observations.append({'path': '/' + '/'.join(names[:index]),
                                     'identity': identity(info), 'acl': acl})
                if index == len(names):
                    break
                name = names[index]
                require(exact_entry(fd, name), 'storage_missing')
                next_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                fds.append(next_fd)
                require(identity(os.stat(name, dir_fd=fd, follow_symlinks=False))
                        == identity(os.fstat(next_fd)), 'storage_changed')
                fd = next_fd
            yield fd, observations
            # Check descriptor and entry identities again, with ACLs/modes.
            for index, held in enumerate(fds):
                require(identity(os.fstat(held)) == observations[index]['identity'], 'storage_changed')
                if guard:
                    require(acl_identity(held) == observations[index]['acl'], 'storage_changed')
                if index:
                    require(exact_entry(fds[index-1], names[index-1]), 'storage_spelling')
                    require(identity(os.stat(names[index-1], dir_fd=fds[index-1], follow_symlinks=False))
                            == observations[index]['identity'], 'storage_changed')
        finally:
            for fd in reversed(fds):
                os.close(fd)

    def separation(self, observations):
        root = str(self.path)
        ancestors = [v['identity'][:2] for v in observations]
        for path in self.protected:
            other = str(path)
            require(not (root == other or root.startswith(other + '/') or other.startswith(root + '/')),
                    'storage_overlap')
            with self.chain(path) as (_, protected):
                require(protected[-1]['identity'][:2] not in ancestors, 'storage_overlap')
                if observations[-1]['path'] == root:
                    require(ancestors[-1] not in [v['identity'][:2] for v in protected], 'storage_overlap')

    def prepare(self):
        """Called only after the parent's confirmed create-only claim, under locks."""
        try:
            with self.chain(self.path.parent, guard=True) as (parent, ancestors):
                self.separation(ancestors)
                with self.chain(self.path.parent, guard=True) as (_, current):
                    require(current == ancestors, 'storage_changed')
                present = exact_entry(parent, self.path.name)
                if self.selected['expected'] == 'absent':
                    require(not present, 'storage_exists')
                    # Durable uncertain evidence precedes the sole exclusive mkdir.
                    self.persist('uncertain', 'storage_create_pending', ancestors)
                    mask = os.umask(0o077)
                    try:
                        os.mkdir(self.path.name, 0o700, dir_fd=parent)
                    finally:
                        os.umask(mask)
                    self.persist('created', 'storage_verify_pending', ancestors)
                    os.fsync(parent)
                else:
                    require(present, 'storage_missing')
                with self.chain(self.path, guard=True) as (target, observed):
                    require(observed[:-1] == ancestors, 'storage_changed')
                    self.separation(observed)
                    expected = self.selected['expected']
                    if expected != 'absent':
                        require(observed[-1]['identity'][:2] == [expected['dev'], expected['ino']],
                                'storage_identity')
                    os.fsync(target)
                    self.baseline = observed
            self.persist('created' if self.selected['expected'] == 'absent' else 'reused',
                         'storage_verified', self.baseline)
        except (OSError, StorageError) as exc:
            self.refuse(exc)

    def refuse(self, exc):
        code = exc.code if isinstance(exc, StorageError) else 'storage_filesystem'
        state = self.evidence['state']
        self.persist('uncertain' if state in ('created', 'reused', 'uncertain') else 'refused',
                     code, self.baseline)
        raise StorageError(code) from None

    def verify(self):
        try:
            require(self.baseline is not None, 'storage_unanchored')
            with self.chain(self.path, guard=True) as (_, observed):
                require(observed == self.baseline, 'storage_changed')
                self.separation(observed)
        except (OSError, StorageError) as exc:
            self.refuse(exc)
