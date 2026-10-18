"""Offline deployment preflight. Reports names/errors, never configuration values."""
import os
from pathlib import Path
from urllib.parse import urlsplit
from tracker_metadata import cookie_file
from reviewed_identity import ENV_NAME, read_rules

REQUIRED = (
    "MOVIE_INTEL_WEBHOOK_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "TMDB_API_TOKEN", "RADARR_URL", "RADARR_API_KEY", "MOVIE_INTEL_PUBLIC_BASE_URL",
)


def configuration_errors(env=None):
    env = os.environ if env is None else env
    errors = [f"{name} is required" for name in REQUIRED if not env.get(name, "").strip()]
    if env.get(ENV_NAME):
        try:
            read_rules(env[ENV_NAME])
        except (OSError, ValueError, TypeError, UnicodeError):
            errors.append(ENV_NAME + ' must be an absolute, owner-only valid reviewed context file')
    enabled = env.get('MOVIE_INTEL_TL_METADATA_ENABLED', '0')
    if enabled not in ('0', '1'):
        errors.append('MOVIE_INTEL_TL_METADATA_ENABLED must be 0 or 1')
    if enabled == '1':
        try:
            cookie_file(env.get('MOVIE_INTEL_TL_COOKIE_FILE'))
        except (OSError, ValueError, TypeError):
            errors.append('MOVIE_INTEL_TL_COOKIE_FILE must be an absolute, owner-only regular JSON cookie file')
    secret = env.get("MOVIE_INTEL_WEBHOOK_SECRET", "")
    if secret and (len(secret) < 32 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in secret)):
        errors.append("MOVIE_INTEL_WEBHOOK_SECRET must be at least 32 URL-safe characters")
    for name in ("TELEGRAM_CHAT_ID", "TELEGRAM_TOPIC_ID", "MOVIE_INTEL_PORT", "MOVIE_INTEL_ACTION_TTL_SECONDS"):
        value = env.get(name, "")
        if not value:
            continue
        try:
            number = int(value)
            if name == "MOVIE_INTEL_PORT" and not 1 <= number <= 65535:
                raise ValueError
            if name in ("TELEGRAM_TOPIC_ID", "MOVIE_INTEL_ACTION_TTL_SECONDS") and number <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"{name} must be a valid integer in its supported range")
    for name in ("RADARR_URL", "MOVIE_INTEL_PUBLIC_BASE_URL"):
        value = env.get(name, "")
        if not value:
            continue
        try:
            url = urlsplit(value)
            valid = url.scheme in ("http", "https") and bool(url.hostname) and url.port != 0
            valid = valid and not (url.username or url.password or url.query or url.fragment)
            if name == "MOVIE_INTEL_PUBLIC_BASE_URL":
                valid = valid and url.scheme == "https"
            if not valid:
                raise ValueError
        except ValueError:
            errors.append(f"{name} must be an absolute {'HTTPS' if name == 'MOVIE_INTEL_PUBLIC_BASE_URL' else 'HTTP(S)'} URL without credentials, query, or fragment")
    for name in ("MOVIE_INTEL_ACTION_STORE", "TMDB_CACHE_PATH"):
        value = env.get(name)
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            errors.append(f"{name} must be an absolute path")
            continue
        parent = path.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        if (path.exists() and (not path.is_file() or not os.access(path, os.W_OK))) or not parent.is_dir() or not os.access(parent, os.W_OK):
            errors.append(f"{name} must have a writable file/parent directory")
    return errors
