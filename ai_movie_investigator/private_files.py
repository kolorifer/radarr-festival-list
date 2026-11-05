"""Bounded descriptor privacy guards reused from the existing manual/coordinator guards.

Self-contained installed closure: no SSH, transport, service or credential discovery.
"""
import contextlib
import ctypes
import errno
import hashlib
import os
import stat
import sys
from pathlib import Path
from .contracts import Refusal, require
from .history import checked
LIMIT = 16384

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
        raise Refusal('storage_acl_unsupported')
    except (OSError, AttributeError):
        raise Refusal('storage_acl_unsupported') from None


def linux_acl(fd, directory):
    # Linux descriptor xattrs: only proven absence of POSIX ACLs is accepted.
    # Unsupported ACL inspection is uncertainty, never absence. No getfacl shell.
    for name in ('system.posix_acl_access', 'system.posix_acl_default') if directory else ('system.posix_acl_access',):
        try:
            os.getxattr(fd, name)
        except OSError as e:
            require(e.errno == errno.ENODATA, 'storage_acl')
        else:
            require(False, 'storage_acl')


def safe_acl(fd, directory):
    if sys.platform == 'darwin':
        return acl_identity(fd)
    if sys.platform.startswith('linux'):
        linux_acl(fd, directory)
        return 'posix_acl_absent'
    raise Refusal('acl_unsupported')


def identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode)


@contextlib.contextmanager
def private_chain(path):
    # Reuse the existing storage guard's descriptor, owner, mode and ACL
    # principles, without granting coordinator access or changing permissions.
    require(path.is_absolute() and path.resolve(strict=True) == path, 'unsafe_history_path')
    names = path.parts[1:]
    fds, observed = [], []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fds.append(fd)
        for index in range(len(names) + 1):
            info = os.fstat(fd)
            require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, os.getuid()) and
                    not stat.S_IMODE(info.st_mode) & 0o022, 'unsafe_parent')
            if index == len(names):
                checked(info, True)
            observed.append((identity(info), safe_acl(fd, True)))
            if index < len(names):
                child = os.open(names[index], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                fds.append(child)
                require(identity(os.stat(names[index], dir_fd=fd, follow_symlinks=False)) ==
                        identity(os.fstat(child)), 'parent_changed')
                fd = child
        yield fd
        for index, held in enumerate(fds):
            require((identity(os.fstat(held)), safe_acl(held, True)) == observed[index], 'parent_changed')
            if index:
                require(identity(os.stat(names[index - 1], dir_fd=fds[index - 1], follow_symlinks=False)) ==
                        observed[index][0], 'parent_changed')
    finally:
        for fd in reversed(fds):
            os.close(fd)


def read_private(path, limit=65536):
    path = Path(path)
    with private_chain(path.parent) as dfd:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
        try:
            info = os.fstat(fd)
            checked(info)
            require(info.st_size <= limit and
                    identity(os.stat(path.name, dir_fd=dfd, follow_symlinks=False)) == identity(info), 'unsafe_packet')
            file_acl = safe_acl(fd, False)
            data = bytearray()
            while len(data) <= limit:
                part = os.read(fd, min(4096, (limit + 1) - len(data)))
                if not part:
                    break
                data.extend(part)
            after = os.fstat(fd)
            checked(after)
            require(len(data) <= limit and identity(after) == identity(info) and
                    (after.st_size, after.st_mtime_ns, after.st_ctime_ns) ==
                    (info.st_size, info.st_mtime_ns, info.st_ctime_ns) and
                    identity(os.stat(path.name, dir_fd=dfd, follow_symlinks=False)) == identity(info) and
                    safe_acl(fd, False) == file_acl, 'packet_changed')
        finally:
            os.close(fd)
    return bytes(data)


