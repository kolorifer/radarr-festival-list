"""Owner-only byte archive. No outbound calls and no content-derived names."""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import pwd
import secrets
import stat


DIRECTORY = 'webhook-archive'
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _owner_only(fd, mode):
    info = os.fstat(fd)
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != mode:
        raise ValueError('archive_private_permissions')


@contextmanager
def _trusted_directory(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('archive_state_path')
    current = os.open('/', DIRECTORY_FLAGS)
    try:
        for component in (*path.parts[1:], None):
            info = os.fstat(current)
            if info.st_uid not in (0, os.getuid()) or stat.S_IMODE(info.st_mode) & 0o022:
                raise ValueError('archive_state_ancestor')
            if component is None:
                break
            child = os.open(component, DIRECTORY_FLAGS, dir_fd=current)
            os.close(current)
            current = child
        yield current
    finally:
        os.close(current)


def _physical_state(path):
    """Allow only the provider's root-owned passwd-home alias."""
    path = Path(path)
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    if not path.is_relative_to(home):
        return path
    with _trusted_directory(home.parent) as parent_fd:
        info = os.stat(home.name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISLNK(info.st_mode):
            return path
        if info.st_uid != 0:
            raise ValueError('archive_home_alias_owner')
        target = Path(os.readlink(home.name, dir_fd=parent_fd))
        if not target.is_absolute() or '..' in target.parts:
            raise ValueError('archive_home_alias_target')
        return target / path.relative_to(home)


def archive_json(raw, state_directory):
    """Publish one complete, durable file for each delivery, including repeats."""
    with _trusted_directory(_physical_state(state_directory)) as state_fd:
        _owner_only(state_fd, 0o700)
        try:
            os.mkdir(DIRECTORY, 0o700, dir_fd=state_fd)
        except FileExistsError:
            pass
        archive_fd = os.open(DIRECTORY, DIRECTORY_FLAGS, dir_fd=state_fd)
        try:
            _owner_only(archive_fd, 0o700)
            # Also covers a concurrent creator that has not synced the parent.
            os.fsync(state_fd)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
            stem = stamp + '_' + secrets.token_hex(16)
            pending = '.' + stem + '.partial'
            final = stem + '.json'
            fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=archive_fd)
            try:
                with os.fdopen(fd, 'wb') as output:
                    _owner_only(output.fileno(), 0o600)
                    output.write(raw)
                    output.flush()
                    os.fsync(output.fileno())
                # Same-directory hard link publishes atomically without overwrite.
                os.link(pending, final, src_dir_fd=archive_fd, dst_dir_fd=archive_fd,
                        follow_symlinks=False)
            finally:
                os.unlink(pending, dir_fd=archive_fd)
            os.fsync(archive_fd)
        finally:
            os.close(archive_fd)
