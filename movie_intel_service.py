"""Small HTTP service for autobrr movie rejection enrichment.

Unknown-movie and unusual movie rejection events are enriched. Routine release-only
rejections stay compact. Unknown/test payloads are forwarded to Telegram instead
of being silently ignored. Sensitive tracker fields are never forwarded from
structured payloads. Secrets are read from environment only.
"""
import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from movie_intel import build_index, find_local, rejection_class

HOST = os.environ.get("MOVIE_INTEL_HOST", "127.0.0.1")
PORT = int(os.environ.get("MOVIE_INTEL_PORT", "40714"))
WEBHOOK_SECRET = os.environ.get("MOVIE_INTEL_WEBHOOK_SECRET", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_TOPIC_ID = os.environ.get("TELEGRAM_TOPIC_ID", "").strip()
INDEX = build_index()

SENSITIVE_KEYS = {
    "download_url", "passkey", "api_key", "apikey", "token", "authorization",
    "cookie", "cookies", "password", "secret",
}
ROUTINE_RELEASE_REJECTIONS = {"quality", "existing", "not_upgrade"}


def _fmt_count(value):
    if not isinstance(value, (int, float)):
        return None
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    return str(int(value))


def _rating(obj):
    if not obj:
        return None
    score = obj.get("rating") or obj.get("score") or obj.get("value")
    count = obj.get("votes") or obj.get("vote_count") or obj.get("ratings") or obj.get("rating_count")
    if score is None:
        return None
    return f"{score}" + (f" ({_fmt_count(count)})" if _fmt_count(count) else "")


def _append_rejection_details(lines, rejections, release_name):
    if rejections:
        if len(rejections) == 1:
            lines += ["", "<b>Radarr:</b> " + html.escape(str(rejections[0]))]
        else:
            lines += ["", "<b>Radarr:</b>"]
            lines.extend("• " + html.escape(str(reason)) for reason in rejections if str(reason).strip())
    if release_name:
        lines.append("<b>Release:</b> " + html.escape(str(release_name)))


def format_message(payload):
    data = payload.get("data") or {}
    release = data.get("release") or {}
    result = data.get("result") or {}
    title = release.get("title") or release.get("name") or "Unknown movie"
    year = release.get("year")
    rejections = result.get("rejections") or []
    category = rejection_class(rejections)
    release_name = release.get("name")

    if category in ROUTINE_RELEASE_REJECTIONS:
        # Radarr already knows the movie. The rejection is about this specific
        # release/profile/file state, so model/cache enrichment adds noise.
        lines = [
            "⏭️ RELEASE REJECTED",
            f"<b>{html.escape(str(title))}</b>" + (f" ({year})" if year else ""),
        ]
        _append_rejection_details(lines, rejections, release_name)
        return "\n".join(lines)

    movie = find_local(title, year, INDEX)
    heading = "❌ UNKNOWN MOVIE" if category == "unknown_movie" else "❌ RADARR REJECTED"
    lines = [heading, f"<b>{html.escape(str(title))}</b>" + (f" ({year})" if year else "")]

    if movie:
        ratings = []
        imdb = _rating(movie.get("imdb"))
        letterboxd = _rating(movie.get("letterboxd"))
        if imdb:
            ratings.append(f"IMDb {html.escape(imdb)}")
        if letterboxd:
            ratings.append(f"Letterboxd {html.escape(letterboxd)}")
        if ratings:
            lines += ["", "⭐ " + " · ".join(ratings)]

        recognition = []
        if movie.get("tspdt_rank"):
            recognition.append(f"TSPDT #{movie['tspdt_rank']}")
        recognition.extend(str(x) for x in (movie.get("institutional_signals") or [])[:4])
        if recognition:
            lines += ["", "🏆 <b>Recognition</b>"] + ["• " + html.escape(x) for x in recognition]

        if movie.get("qualified"):
            routes = ", ".join(movie.get("routes") or []) or "model"
            lines += ["", "⚠️ <b>POTENTIAL FALSE NEGATIVE</b>", "Our model: QUALIFIES — " + html.escape(routes)]
        else:
            lines += ["", "Our model: does not currently qualify"]
        lines.append(f"IMDb ID: {html.escape(movie['imdb_id'])}")
    else:
        lines += ["", "ℹ️ Not found unambiguously in the local intelligence cache."]

    _append_rejection_details(lines, rejections, release_name)
    return "\n".join(lines)


def _sanitize(value):
    """Remove obvious credentials before forwarding an unknown structured payload."""
    if isinstance(value, dict):
        return {
            k: ("[redacted]" if str(k).lower() in SENSITIVE_KEYS else _sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


def passthrough_message(payload):
    """Prefer autobrr's own human-readable message; otherwise show safe JSON."""
    if isinstance(payload, dict):
        for container in (payload, payload.get("data")):
            if isinstance(container, dict):
                for key in ("message", "text", "body", "description"):
                    value = container.get(key)
                    if isinstance(value, str) and value.strip():
                        return value[:4000]
        return json.dumps(_sanitize(payload), ensure_ascii=False, indent=2)[:4000]
    if isinstance(payload, str):
        return payload[:4000]
    return str(payload)[:4000]


def _telegram_payload(text, parse_mode="HTML"):
    body = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        body["parse_mode"] = parse_mode
    if TELEGRAM_TOPIC_ID:
        try:
            body["message_thread_id"] = int(TELEGRAM_TOPIC_ID)
        except ValueError as exc:
            raise RuntimeError("TELEGRAM_TOPIC_ID must be an integer") from exc
    return body


def send_telegram(text, parse_mode="HTML"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram credentials are not configured")
    body = json.dumps(_telegram_payload(text, parse_mode=parse_mode)).encode()
    req = Request(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=15) as response:
        return response.status


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, obj):
        raw = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if urlparse(self.path).path == "/health":
            self._json(200, {"ok": True, "movies": len(INDEX)})
        else:
            self._json(404, {"ok": False})

    def do_POST(self):
        path = urlparse(self.path).path
        expected = "/webhook" + (f"/{WEBHOOK_SECRET}" if WEBHOOK_SECRET else "")
        if path != expected:
            self._json(404, {"ok": False})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                raise ValueError("invalid body size")
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                text = raw.decode("utf-8", errors="replace").strip()
                if text:
                    send_telegram(text[:4000], parse_mode=None)
                self._json(200, {"ok": True, "forwarded": "text"})
                return

            data = payload.get("data") if isinstance(payload, dict) else None
            release = (data or {}).get("release") if isinstance(data, dict) else None
            is_movie_rejection = (
                isinstance(payload, dict)
                and payload.get("event") == "action.rejected"
                and isinstance(release, dict)
                and release.get("type") == "movie"
            )

            if is_movie_rejection:
                send_telegram(format_message(payload), parse_mode="HTML")
                self._json(200, {"ok": True, "mode": "enriched"})
            else:
                send_telegram(passthrough_message(payload), parse_mode=None)
                self._json(200, {"ok": True, "mode": "passthrough"})
        except Exception as exc:
            # Do not log payloads: they may contain personalized tracker URLs.
            self._json(500, {"ok": False, "error": type(exc).__name__})

    def log_message(self, fmt, *args):
        # Keep standard logs free of request paths because the path can contain
        # the webhook secret.
        print(f"http {getattr(self, 'command', '?')} {args[1] if len(args) > 1 else ''}")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"movie-intel listening on {HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
