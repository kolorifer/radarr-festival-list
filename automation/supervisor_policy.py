"""Fail-closed task capabilities and retained-work fingerprints. No credentials."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


class PolicyError(RuntimeError):
    pass


PRIVATE_REPOSITORY = 'kolorifer/radarr-state'
MAX_PRIVATE_BYTES = 900000
MAX_INPUTS = 8


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError('Duplicate JSON capability field')
        result[key] = value
    return result


def directive(body, name):
    lines = [line for line in body.splitlines() if re.match(r'^\s*' + name + r'\b', line, re.I)]
    if not lines:
        return None
    if len(lines) != 1 or not lines[0].startswith(name + ': '):
        raise PolicyError('Malformed or duplicate publication/continuation capability')
    try:
        value = json.loads(lines[0][len(name) + 2:], object_pairs_hook=unique_object)
    except ValueError:
        raise PolicyError('Capability must be one JSON object') from None
    if not isinstance(value, dict):
        raise PolicyError('Capability must be one JSON object')
    return value


def exact_path(path, destination=False):
    if (not isinstance(path, str) or len(path) > 240
            or not re.fullmatch(r'[A-Za-z0-9_/-][A-Za-z0-9._/-]*', path)
            or any(p in ('', '.', '..', '.git') for p in path.split('/'))):
        raise PolicyError('Invalid exact private path')
    if destination and (not path.startswith('operations/')
                        or PurePosixPath(path).suffix not in ('.md', '.json', '.txt')):
        raise PolicyError('Invalid private destination')
    return path


def hex_value(value, length):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{' + str(length) + '}', value) is not None


def private_inputs(body):
    value = directive(body, 'PRIVATE_INPUTS')
    if value is None:
        return []
    if (set(value) != {'inputs'} or not isinstance(value['inputs'], list)
            or not 1 <= len(value['inputs']) <= MAX_INPUTS):
        raise PolicyError('Invalid private inputs capability')
    aliases, paths = set(), set()
    for entry in value['inputs']:
        if (not isinstance(entry, dict)
                or set(entry) != {'repository', 'path', 'commit', 'blob', 'sha256', 'alias'}):
            raise PolicyError('Invalid private input keys')
        if entry['repository'] != PRIVATE_REPOSITORY:
            raise PolicyError('Private repository is outside host allowlist')
        exact_path(entry['path'])
        if not hex_value(entry['commit'], 40) or not hex_value(entry['blob'], 40) or not hex_value(entry['sha256'], 64):
            raise PolicyError('Private inputs require exact commit, blob and SHA256')
        if not isinstance(entry['alias'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.(md|json|txt)', entry['alias']):
            raise PolicyError('Invalid local input alias')
        if entry['alias'] in aliases or entry['path'] in paths:
            raise PolicyError('Duplicate input alias or source')
        aliases.add(entry['alias']); paths.add(entry['path'])
    return value['inputs']


def private_diagnostic(body):
    value = directive(body, 'PRIVATE_DIAGNOSTIC')
    if value is None:
        return None
    if set(value) != {'repository', 'path', 'expected_blob'} or value['repository'] != PRIVATE_REPOSITORY:
        raise PolicyError('Invalid private diagnostic capability')
    exact_path(value['path'], destination=True)
    if not value['path'].endswith('.json') or not (value['expected_blob'] == 'absent' or hex_value(value['expected_blob'], 40)):
        raise PolicyError('Diagnostic requires exact JSON destination and expected blob')
    artifact = private_artifact(body)
    if artifact and artifact['path'] == value['path']:
        raise PolicyError('Artifact and diagnostic destinations must differ')
    return value


def private_artifact(body):
    value = directive(body, 'PRIVATE_ARTIFACT')
    if value is None:
        return None
    if set(value) != {'repository', 'path', 'expected_blob', 'source'}:
        raise PolicyError('Invalid private artifact capability keys')
    if value['repository'] != PRIVATE_REPOSITORY:
        raise PolicyError('Private repository is outside host allowlist')
    exact_path(value['path'], destination=True)
    if not isinstance(value['source'], str) or not re.fullmatch(r'[A-Za-z0-9_-]+\.(md|json|txt)', value['source']):
        raise PolicyError('Source must be one staging filename')
    if not isinstance(value['expected_blob'], str) or not re.fullmatch(r'absent|[0-9a-f]{40}', value['expected_blob']):
        raise PolicyError('Expected destination must be absent or an exact Git blob')
    return value


def continuation(body):
    value = directive(body, 'CONTINUE_FROM')
    if value is None:
        return None
    if (set(value) != {'task', 'snapshot'} or type(value['task']) is not int or value['task'] < 1
            or not isinstance(value['snapshot'], str) or not re.fullmatch(r'[0-9a-f]{64}', value['snapshot'])):
        raise PolicyError('Invalid continuation capability')
    return value


def snapshot(repo):
    """Bind HEAD, branch, index, all tracked and nonignored untracked bytes/modes.

    Symlinks are fingerprinted by link text, never followed. Ignored caches are
    outside the contract; private staging is separately recorded by the runner.
    """
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=repo, stderr=subprocess.DEVNULL)
    digest = hashlib.sha256()
    def add(data):
        digest.update(len(data).to_bytes(8, 'big')); digest.update(data)
    for args in [('rev-parse', 'HEAD'), ('symbolic-ref', 'HEAD'), ('ls-files', '--stage', '-z')]:
        add(git(*args))
    paths = set(git('ls-files', '-z').split(b'\0') + git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0')) - {b''}
    for name in sorted(paths):
        add(name)
        path = Path(repo) / os.fsdecode(name)
        if path.is_symlink():
            add(b'link'); add(os.fsencode(os.readlink(path)))
        elif path.is_file():
            add(str(path.stat().st_mode).encode()); add(path.read_bytes())
        elif not path.exists():
            add(b'deleted')
        else:
            raise PolicyError('Unsupported retained filesystem entry')
    return digest.hexdigest()


def worker_environment():
    # No host GitHub/API tokens or agent socket cross the parent/child boundary.
    allowed = ('PATH', 'HOME', 'USER', 'LOGNAME', 'TMPDIR', 'LANG', 'LC_ALL', 'CODEX_HOME')
    return {k: os.environ[k] for k in allowed if k in os.environ}
