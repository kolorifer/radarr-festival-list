"""HTTP service for enriched autobrr/Radarr Telegram notifications.

Movie rejection events get conservative local/TMDb enrichment. Routine release
rejections stay compact. Unknown/test payloads pass through to Telegram. Sensitive
tracker fields are never forwarded from structured payloads.
"""
import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from movie_intel import build_index, find_local, rejection_class
from tmdb_resolver import resolve_movie

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


def _runtime(minutes):
    if not isinstance(minutes, int) or minutes <= 0:
        return None
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    return f"{hours}h" if hours else f"{mins}m"


def _links(movie, meta):
    imdb_id = (meta or {}).get("imdb_id") or (movie or {}).get("imdb_id")
    tmdb_id = (meta or {}).get("tmdb_id")
    links = []
    if imdb_id:
        url = f"https://www.imdb.com/title/{imdb_id}/"
        links.append(f'<a href="{html.escape(url, quote=True)}">IMDb</a>')
    if tmdb_id:
        url = f"https://www.themoviedb.org/movie/{tmdb_id}"
        links.append(f'<a href="{html.escape(url, quote=True)}">TMDb</a>')
    return " · ".join(links)


def _append_rejection_details(lines, rejections, release_name):
    clean = [str(x).strip() for x in rejections if str(x).strip()]
    if clean:
        if len(clean) == 1:
            lines += ["", "<b>Radarr:</b> " + html.escape(clean[0][:350])]
        else:
            lines += ["", "<b>Radarr:</b>"]
            lines.extend("• " + html.escape(reason[:280]) for reason in clean[:3])
    if release_name:
        lines.append("<b>Release:</b> " + html.escape(str(release_name)[:220]))


def format_message(payload, movie=None, meta=None):
    data = payload.get("data") or {}
    release = data.get("release") or {}
    result = data.get("result") or {}
    title = release.get("title") or release.get("name") or "Unknown movie"
    year = release.get("year")
    rejections = result.get("rejections") or []
    category = rejection_class(rejections)
    release_name = release.get("name")
    if movie is None:
        movie = find_local(title, year, INDEX)

    canonical_title = (meta or {}).get("title") or title
    canonical_year = (meta or {}).get("year") or year
    link_line = _links(movie, meta)

    if category in ROUTINE_RELEASE_REJECTIONS:
        lines = [
            "⏭️ <b>Radarr — Release Rejected</b>",
            f"<b>{html.escape(str(canonical_title))}</b>" + (f" ({canonical_year})" if canonical_year else ""),
        ]
        if link_line:
            lines.append(link_line)
        _append_rejection_details(lines, rejections, release_name)
        return "\n".join(lines)

    heading = "❌ <b>Radarr — Unknown Movie</b>" if category == "unknown_movie" else "❌ <b>Radarr — Rejected</b>"
    lines = [heading, f"<b>{html.escape(str(canonical_title))}</b>" + (f" ({canonical_year})" if canonical_year else "")]
    if link_line:
        lines.append(link_line)

    ratings = []
    if movie:
        imdb = _rating(movie.get("imdb"))
        letterboxd = _rating(movie.get("letterboxd"))
        if imdb:
            ratings.append(f"IMDb {html.escape(imdb)}")
        if letterboxd:
            ratings.append(f"Letterboxd {html.escape(letterboxd)}")
    elif meta and isinstance(meta.get("tmdb_rating"), (int, float)) and meta.get("tmdb_votes"):
        ratings.append(f"TMDb {meta['tmdb_rating']:.1f} ({_fmt_count(meta['tmdb_votes'])})")
    if ratings:
        lines += ["", "⭐ " + " · ".join(ratings)]

    if meta:
        facts = []
        genres = meta.get("genres") or []
        if genres:
            facts.append(", ".join(genres[:3]))
        runtime = _runtime(meta.get("runtime"))
        if runtime:
            facts.append(runtime)
        if facts:
            lines.append(" · ".join(html.escape(x) for x in facts))

    if movie:
        recognition = []
        if movie.get("tspdt_rank"):
            recognition.append(f"TSPDT #{movie['tspdt_rank']}")
        recognition.extend(str(x) for x in (movie.get("institutional_signals") or [])[:3])
        if recognition:
            lines += ["", "🏆 <b>Recognition</b>"] + ["• " + html.escape(x) for x in recognition]

        if movie.get("qualified"):
            routes = ", ".join(movie.get("routes") or []) or "model"
            lines += ["", "⚠️ <b>POTENTIAL FALSE NEGATIVE</b>", "Our model: QUALIFIES — " + html.escape(routes)]
        else:
            lines += ["", "Our model: does not currently qualify"]
    else:
        lines += ["", "ℹ️ Outside or unresolved in the current local intelligence universe."]

    _append_rejection_details(lines, rejections, release_name)
    return "\n".join(lines)


def build_movie_notification(payload):
    data = payload.get("data") or {}
    release = data.get("release") or {}
    title = release.get("title") or release.get("name") or "Unknown movie"
    year = release.get("year")
    movie = find_local(title, year, INDEX)
    imdb_id = movie.get("imdb_id") if movie else None
    meta = resolve_movie(title, year, imdb_id=imdb_id)
    text = format_message(payload, movie=movie, meta=meta)
    return text, (meta or {}).get("poster_url")


def _sanitize(value):
    if isinstance(value, dict):
        return {
            k: ("[redacted]" if str(k).lower() in SENSITIVE_KEYS else _sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


def passthrough_message(payload):
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


def _topic_fields():
    if not TELEGRAM_TOPIC_ID:
        return {}
    try:
        return {"message_thread_id": int(TELEGRAM_TOPIC_ID)}
    except ValueError as exc:
        raise RuntimeError("TELEGRAM_TOPIC_ID must be an integer") from exc


def _telegram_payload(text, parse_mode="HTML"):
    body = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
        **_topic_fields(),
    }
    if parse_mode:
        body["parse_mode"] = parse_mode
    return body


def _telegram_photo_payload(photo, caption):
    return {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo,
        "caption": caption,
        "parse_mode": "HTML",
        "show_caption_above_media": False,
        **_topic_fields(),
    }


def _telegram_request(method, body):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram credentials are not configured")
    raw = json.dumps(body).encode()
    req = Request(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}",
        data=raw,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=15) as response:
        return response.status


def send_telegram(text, parse_mode="HTML"):
    return _telegram_request("sendMessage", _telegram_payload(text, parse_mode=parse_mode))


def send_movie_notification(text, poster_url=None):
    # Telegram photo captions are limited to 1024 characters after parsing.
    # Keep a safety margin; long intelligence reports fall back to text.
    if poster_url and len(text) <= 950:
        try:
            return _telegram_request("sendPhoto", _telegram_photo_payload(poster_url, text))
        except Exception:
            # Metadata/image delivery must never suppress the actual notification.
            pass
    return send_telegram(text, parse_mode="HTML")


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
                text, poster_url = build_movie_notification(payload)
                send_movie_notification(text, poster_url)
                self._json(200, {"ok": True, "mode": "enriched", "poster": bool(poster_url)})
            else:
                send_telegram(passthrough_message(payload), parse_mode=None)
                self._json(200, {"ok": True, "mode": "passthrough"})
        except Exception as exc:
            self._json(500, {"ok": False, "error": type(exc).__name__})

    def log_message(self, fmt, *args):
        # Request paths can contain the webhook secret, so do not log them.
        print(f"http {getattr(self, 'command', '?')} {args[1] if len(args) > 1 else ''}")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"movie-intel listening on {HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
