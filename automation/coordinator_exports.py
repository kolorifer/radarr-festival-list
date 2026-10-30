"""Offline fixed movie-export reader/stager. No discovery, transport or refresh."""
import contextlib
import os
from pathlib import Path
import secrets

from automation import coordinator as c
from automation import coordinator_io as files
from automation import coordinator_diagnostics as diagnostics
from automation.coordinator_sources import SOURCES, MAX_AGE, FAILURES, observations

# Relative to the explicitly authorized, canonical research-state directory.
EXPORTS = {'investigations': 'incoming/snapshot.json',
           'research_report': 'review-report.json'}
LIMIT = min(c.MAX_BYTES, 2 * 1024 * 1024)


def _outside_source(parent_fd, source_fd):
    """Reject ancestors in a protected tree (source or checkout) by identity."""
    source = os.fstat(source_fd)
    ancestor = os.dup(parent_fd)
    try:
        while True:
            here = os.fstat(ancestor)
            identity = (here.st_dev, here.st_ino)
            c.require(identity != (source.st_dev, source.st_ino), 'export_destination')
            # Transfer cleanup ownership before any operation on the new fd.
            previous, ancestor = ancestor, os.open(
                '..', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=ancestor)
            os.close(previous)
            up = os.fstat(ancestor)
            if identity == (up.st_dev, up.st_ino):
                break
    finally:
        os.close(ancestor)


def _write_new(root_fd, name, raw):
    """Atomic create-only publication in the pinned newly owned directory."""
    temporary = '.export-' + secrets.token_hex(16)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=root_fd)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, name, src_dir_fd=root_fd, dst_dir_fd=root_fd, follow_symlinks=False)
        os.fsync(root_fd)
    finally:
        os.unlink(temporary, dir_fd=root_fd)


class StagingFailure(ValueError):
    """Private fixed diagnostics; CLI emits only its generic failure projection."""
    def __init__(self, details):
        self.diagnostics = diagnostics.validate(details)
        super().__init__('export_staging_failed')


def _install(root_fd, name, raw, sources):
    try:
        _write_new(root_fd, name, raw)
    except FAILURES as exc:
        details = [diagnostics.diagnostic(source, 'staging', diagnostics.staging_reason(exc))
                   for source in sources]
        # Best effort only: output failure may also prevent this private record.
        # Never overwrite a competing diagnostic file or retry the bundle.
        try:
            _write_new(root_fd, 'diagnostics.json', files.encode(details))
        except FAILURES:
            pass
        raise StagingFailure(details) from None


def stage_exports(source_root, output_root, now):
    """Preserve each acquired export independently, even if content is invalid.

    Roots are explicit caller authority. Output must be new, outside source and
    checkout, under an existing owner-only parent. No reuse/resume/overwrite.
    Manifest v2 pins bytes and acquisition facts; observations validate them.
    Return private observations. CLI must project them, never print them raw.
    """
    c.stamp(now)
    c.require(Path(source_root).is_absolute() and Path(output_root).is_absolute(), 'confined_root')
    source_root, output_root = Path(source_root), Path(output_root)
    for path in (source_root, output_root):
        c.require(path.anchor == '/' and all(p not in ('.', '..') for p in path.parts),
                  'confined_root')
    c.require(output_root != source_root and source_root not in output_root.parents,
              'export_destination')
    checkout = Path(__file__).resolve().parent.parent
    c.require(output_root != checkout and checkout not in output_root.parents, 'export_destination')
    with contextlib.ExitStack() as stack:
        try:
            source_fd = stack.enter_context(files.directory(source_root))
        except FAILURES as exc:
            raise files.ReadFailure(diagnostics.acquisition_reason(exc)) from None
        parent = stack.enter_context(files.directory(output_root.parent))
        info = os.fstat(parent)
        c.require(info.st_uid == os.getuid() and info.st_mode & 0o077 == 0, 'export_parent')
        checkout_fd = stack.enter_context(files.directory(checkout))
        try:
            existing = os.stat(output_root.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        for protected_fd in (source_fd, checkout_fd):
            _outside_source(parent, protected_fd)
            # A final-entry alias of a protected root has a parent outside it.
            if existing is not None:
                c.require(not os.path.samestat(existing, os.fstat(protected_fd)),
                          'export_destination')
        # mkdir is exclusive even for dangling links, files, aliases or old roots.
        try:
            os.mkdir(output_root.name, mode=0o700, dir_fd=parent)
        except OSError as exc:
            raise StagingFailure([diagnostics.diagnostic(source, 'staging', diagnostics.staging_reason(exc))
                                  for source in EXPORTS]) from None
        target = os.open(output_root.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        stack.callback(os.close, target)
        os.fchmod(target, 0o700)
        os.fsync(parent)
        entries, details = [], []
        for source in SOURCES:
            entry = {'id': source, 'path': None, 'sha256': None, 'revision': None,
                     'generated_at': None, 'observed_at': None, 'collected_at': None,
                     'max_age_seconds': MAX_AGE[source]}
            entries.append(entry)
            if source not in EXPORTS:
                continue
            try:
                raw = files.read_from_directory(source_fd, EXPORTS[source], LIMIT, reject_hardlinks=True)
            except FAILURES as exc:
                details.append(diagnostics.diagnostic(source, 'acquisition', diagnostics.acquisition_reason(exc)))
                continue
            details.append(diagnostics.diagnostic(source, 'acquisition', 'read_complete'))
            name = source + '.json'
            _install(target, name, raw, (source,))
            details.append(diagnostics.diagnostic(source, 'staging', 'staged'))
            entry.update(path=name, sha256=files.digest(raw), collected_at=now)
            # Extract only a valid embedded generation clock. Never substitute now.
            try:
                content = files.decode(raw)
                generated = content.get('generated_at') if isinstance(content, dict) else None
                c.stamp(generated)
                entry['generated_at'] = generated
            except FAILURES:
                pass
        manifest = {'version': 2, 'repository': c.REPOSITORY, 'sources': entries,
                    'diagnostics': details}
        _install(target, 'manifest.json', files.encode(manifest), EXPORTS)
        report = observations(output_root, 'manifest.json', now)
        encoded = files.encode(report)
        # Same private payload ceiling as the coordinator report owner.
        from automation.coordinator_outbox import MAX_PAYLOAD
        c.require(len(encoded) <= MAX_PAYLOAD, 'export_observations_bound')
        _install(target, 'observations.json', encoded, EXPORTS)
        return report
