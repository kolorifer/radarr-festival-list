"""Bounded offline JSON reads. No discovery, credentials or network transport."""
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat

from automation.coordinator import MAX_BYTES, require
from automation.supervisor_policy import unique_object


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def decode(raw):
    value = json.loads(raw, object_pairs_hook=unique_object,
                       parse_constant=lambda _: require(False, 'invalid_json'))
    # JSON exponent overflow (1e999) bypasses parse_constant.
    def finite(v):
        if isinstance(v, float):
            require(math.isfinite(v), 'invalid_json')
        elif isinstance(v, dict):
            for item in v.values():
                finite(item)
        elif isinstance(v, list):
            for item in v:
                finite(item)
    finite(value)
    return value


def relative_path(value):
    require(isinstance(value, str) and len(value) <= 240
            and re.fullmatch(r'[A-Za-z0-9_./-]+', value)
            and not value.startswith('/') and all(p not in ('', '.', '..') for p in value.split('/')),
            'confined_path')
    return PurePosixPath(value).parts


@contextlib.contextmanager
def directory(root):
    """Open each directory without following links, including root ancestors."""
    root = Path(root).absolute()
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in root.parts[1:]:
            require(part not in ('.', '..'), 'confined_root')
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


class ReadFailure(ValueError):
    """Typed, fixed reason; compatible with existing ValueError callers."""
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def read_from_directory(root_fd, relative, limit=MAX_BYTES, reject_hardlinks=False):
    """Read through a caller-pinned root; caller retains ownership of root_fd."""
    parts = relative_path(relative)
    fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        target = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            before = os.fstat(target)
            if not stat.S_ISREG(before.st_mode):
                raise ReadFailure('nonregular_file')
            if reject_hardlinks and before.st_nlink != 1:
                raise ReadFailure('hardlink_rejected')
            if before.st_size > limit:
                raise ReadFailure('byte_limit')
            chunks = []
            remaining = limit + 1
            while remaining:
                chunk = os.read(target, min(remaining, 65536))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(target)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns,
                before.st_nlink) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                                    after.st_ctime_ns, after.st_nlink):
                raise ReadFailure('changed_during_read')
            raw = b''.join(chunks)
            if len(raw) > limit:
                raise ReadFailure('byte_limit')
            if len(raw) != after.st_size:
                raise ReadFailure('changed_during_read')
            return raw
        finally:
            os.close(target)
    finally:
        os.close(fd)


def read_bytes(root, relative, limit=MAX_BYTES):
    with directory(root) as root_fd:
        return read_from_directory(root_fd, relative, limit)


def read_json(root, relative, limit=MAX_BYTES):
    return decode(read_bytes(root, relative, limit))
