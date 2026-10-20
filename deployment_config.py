"""Offline deployment preflight. Reports names/errors, never configuration values."""
import os
from pathlib import Path
from urllib.parse import urlsplit
from tracker_metadata import cookie_file

REQUIRED = (
    "MOVIE_INTEL_WEBHOOK_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "TMDB_API_TOKEN", "RADARR_URL", "RADARR_API_KEY", "MOVIE_INTEL_PUBLIC_BASE_URL",
)


def configuration_errors(env=None):
    env = os.environ if env is None else env
    errors = [f"{name} is required" for name in REQUIRED if not env.get(name, "").strip()]
    if env.get('MOVIE_INTEL_REVIEWED_CONTEXT_FILE'):
        errors.append('MOVIE_INTEL_REVIEWED_CONTEXT_FILE is retired; remove this setting')
    if env.get('MOVIE_INTEL_IDENTITY_DIGEST_ENABLED', '0') not in ('0', '1'):
        errors.append('MOVIE_INTEL_IDENTITY_DIGEST_ENABLED must be 0 or 1')
    if env.get('MOVIE_INTEL_TORRENT_EVIDENCE_ENABLED', '0') not in ('0', '1'):
        errors.append('MOVIE_INTEL_TORRENT_EVIDENCE_ENABLED must be 0 or 1')
    if env.get('MOVIE_INTEL_TRACKER_TYPO_ENABLED', '0') not in ('0', '1'):
        errors.append('MOVIE_INTEL_TRACKER_TYPO_ENABLED must be 0 or 1')
    retry_mode=env.get('MOVIE_INTEL_IDENTITY_RETRY_MODE','off')
    if retry_mode not in ('off','shadow','active'):errors.append('MOVIE_INTEL_IDENTITY_RETRY_MODE must be off, shadow or active')
    if retry_mode!='off' and env.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED')!='1':errors.append('identity retries require the observer')
    triage_enabled = env.get('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED', '0')
    if triage_enabled not in ('0', '1'):
        errors.append('MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED must be 0 or 1')
    if triage_enabled == '1':
        from identity_triage_observer import read_config as read_observer_config
        try:
            read_observer_config(env.get('MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG', ''))
        except (OSError, ValueError, TypeError):
            errors.append('MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG must be an owner-only valid observer config')
    enabled = env.get('MOVIE_INTEL_TL_METADATA_ENABLED', '0')
    if enabled not in ('0', '1'):
        errors.append('MOVIE_INTEL_TL_METADATA_ENABLED must be 0 or 1')
    if enabled == '1':
        try:
            cookie_file(env.get('MOVIE_INTEL_TL_COOKIE_FILE'))
        except (OSError, ValueError, TypeError):
            errors.append('MOVIE_INTEL_TL_COOKIE_FILE must be an absolute, owner-only regular JSON cookie file')
    if env.get('MOVIE_INTEL_ALTERNATIVE_GRAB_CONFIG'):
        from alternative_grab_helper import private_config
        try:
            private_config(env['MOVIE_INTEL_ALTERNATIVE_GRAB_CONFIG'])
        except (OSError, ValueError, TypeError, KeyError):
            errors.append('MOVIE_INTEL_ALTERNATIVE_GRAB_CONFIG must be an absolute owner-only helper configuration')
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
