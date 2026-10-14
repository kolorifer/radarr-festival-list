"""Redact untrusted notification/error text before it leaves the service."""
import os
import re

PRIVATE_KEYS = {
    "downloadurl", "magneturi", "magneturl", "infourl", "link", "passkey",
    "apikey", "token", "authorization", "cookie", "cookies", "password", "secret",
}
SECRET_NAMES = (
    "MOVIE_INTEL_WEBHOOK_SECRET", "TELEGRAM_BOT_TOKEN", "RADARR_API_KEY", "TMDB_API_TOKEN",
)
URL_RE = re.compile(r"(?:https?://|magnet:\?)[^\s<>\"']+", re.IGNORECASE)


def redact_text(value):
    text = str(value)
    for name in SECRET_NAMES:
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, "[redacted]")
    return URL_RE.sub("[redacted URL]", text)


def sanitize(value):
    if isinstance(value, dict):
        return {
            key: "[redacted]" if re.sub(r"[^a-z]", "", str(key).lower()) in PRIVATE_KEYS
            else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return redact_text(value) if isinstance(value, str) else value
