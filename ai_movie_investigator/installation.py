"""Explicit self-contained offline installation; no service/config operations."""
import hashlib
import json
import os
from pathlib import Path
import stat

RUNTIME_FILES = (
    'ai_movie_investigator/__init__.py', 'ai_movie_investigator/contracts.py',
    'ai_movie_investigator/history.py', 'ai_movie_investigator/controller.py',
    'ai_movie_investigator/codex_transport.py', 'ai_movie_investigator/review.py',
    'ai_movie_investigator/replay.py', 'ai_movie_investigator/synthetic.json',
    'ai_movie_investigator/responses_http.py', 'ai_movie_investigator/responses_protocol.py',
    'ai_movie_investigator/responses_transport.py', 'ai_movie_investigator/responses_replay.py',
    'ai_movie_investigator/research.py', 'ai_movie_investigator/spending.py',
    'ai_movie_investigator/pilot.py', 'ai_movie_investigator/catalogue_replay.py',
    'ai_movie_investigator/installation.py',
    'identity_triage_intake.py', 'identity_triage_store.py', 'identity_selection.py',
    'torrent_research_evidence.py', 'identity_research_handoff.py',
    'identity_research_provider.py', 'identity_research_store.py', 'identity_recurring_store.py',
)


def _read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576 or info.st_nlink != 1:
            raise ValueError('installation_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            return stream.read(1048577)
    finally:
        os.close(fd)


def verify_installation(root):
    root = Path(root)
    if not root.is_absolute() or root.resolve(strict=True) != root:
        raise ValueError('installation_path')
    manifest = json.loads(_read(root / 'runtime-files.json'))
    if set(manifest) != set(RUNTIME_FILES):
        raise ValueError('installation_closure')
    for name, expected in manifest.items():
        path = root / name
        if path.parent.resolve(strict=True) != path.parent or hashlib.sha256(_read(path)).hexdigest() != expected:
            raise ValueError('installation_hash')
    return manifest


def install_runtime(source, destination):
    """Caller-selected code roots only. Explicit call; never invoked on import.

    No copying ledgers, credentials, private inputs or output, and no source
    lookup/fallback at runtime. The destination must be an existing empty 0700
    directory. This helper neither installs nor starts any daemon.
    """
    source, destination = Path(source), Path(destination)
    if any(not p.is_absolute() or p.resolve(strict=True) != p for p in (source, destination)):
        raise ValueError('installation_path')
    info = destination.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('installation_permissions')
    if list(destination.iterdir()):
        raise ValueError('installation_not_empty')
    frozen = {}
    source_manifest = json.loads(_read(source / 'docs/reports/2026-11-01-issue-127-task7-runtime-manifest.json'))
    expected = source_manifest['runtime_files']
    if set(expected) != set(RUNTIME_FILES):
        raise ValueError('installation_closure')
    for name in RUNTIME_FILES:
        path = source / name
        if path.parent.resolve(strict=True) != path.parent:
            raise ValueError('installation_path')
        frozen[name] = _read(path)
        if hashlib.sha256(frozen[name]).hexdigest() != expected[name]:
            raise ValueError('installation_source_hash')
    manifest = {name: hashlib.sha256(body).hexdigest() for name, body in frozen.items()}
    (destination / 'ai_movie_investigator').mkdir(mode=0o700)
    frozen['runtime-files.json'] = json.dumps(manifest, sort_keys=True).encode()
    for name, body in frozen.items():
        fd = os.open(destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(body)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
    return verify_installation(destination)
