"""Small server-side store for Telegram approval actions.

The opaque token is the only value sent to Telegram. Private tracker URLs remain
on the movie-intel host, expire automatically, and are never placed in the URL.
"""
import json
import os
import secrets
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent
STORE_PATH = Path(os.environ.get("MOVIE_INTEL_ACTION_STORE", ROOT / "movie-intel-actions.json"))
try:
    TTL_SECONDS = int(os.environ.get("MOVIE_INTEL_ACTION_TTL_SECONDS", "86400"))
except ValueError:
    # Startup preflight reports invalid configuration without echoing its value.
    TTL_SECONDS = 86400
_LOCK = threading.Lock()


def _load_unlocked():
    try:
        data = json.loads(STORE_PATH.read_text())
        if not isinstance(data, dict):
            raise ValueError('Invalid private action store')
        return data
    except FileNotFoundError:
        return {}


def _save_unlocked(data):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE_PATH.with_name(STORE_PATH.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        os.fchmod(handle.fileno(), 0o600)
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, STORE_PATH)
    directory_fd = os.open(STORE_PATH.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    try:
        os.chmod(STORE_PATH, 0o600)
    except OSError:
        pass


def _prune_unlocked(data, now=None):
    now = time.time() if now is None else now
    expired = [token for token, row in data.items() if float(row.get("expires_at", 0)) <= now]
    for token in expired:
        data.pop(token, None)
    return bool(expired)


def create_action(action, ttl_seconds=None):
    ttl = TTL_SECONDS if ttl_seconds is None else int(ttl_seconds)
    now = time.time()
    row = dict(action)
    row["created_at"] = now
    row["expires_at"] = now + max(60, ttl)
    token = secrets.token_urlsafe(24)
    with _LOCK:
        data = _load_unlocked()
        _prune_unlocked(data, now)
        # Duplicate webhooks reuse the same capability and attempt state. A
        # repeated notification cannot sidestep an uncertain acquisition.
        release = action.get('release') or {}
        if release.get('name'):
            for existing_token, existing in data.items():
                if (existing.get('movie', {}).get('tmdb_id') == action.get('movie', {}).get('tmdb_id')
                        and existing.get('release') == release):
                    return existing_token
        while token in data:
            token = secrets.token_urlsafe(24)
        data[token] = row
        _save_unlocked(data)
    return token


def get_action(token):
    if not token:
        return None
    with _LOCK:
        data = _load_unlocked()
        changed = _prune_unlocked(data)
        row = data.get(token)
        if changed:
            _save_unlocked(data)
        return dict(row) if isinstance(row, dict) else None


def update_action(token, **changes):
    with _LOCK:
        data = _load_unlocked()
        _prune_unlocked(data)
        row = data.get(token)
        if not isinstance(row, dict):
            return False
        row.update(changes)
        data[token] = row
        _save_unlocked(data)
        return True


def delete_action(token):
    with _LOCK:
        data = _load_unlocked()
        removed = data.pop(token, None) is not None
        _prune_unlocked(data)
        if removed or STORE_PATH.exists():
            _save_unlocked(data)
        return removed
