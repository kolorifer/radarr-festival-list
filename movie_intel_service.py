"""HTTP service for enriched autobrr/Radarr Telegram notifications.

Unknown-movie rejections can be approved from Telegram. Approval adds the movie
without searching and re-pushes the exact autobrr release to Radarr. Private
tracker URLs stay server-side and are never placed in Telegram messages, action
URLs, or logs.
"""
import argparse
import html
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

from movie_intel import build_index, find_local, rejection_class
from deployment_config import configuration_errors
from private_text import redact_text, sanitize
from pending_actions import create_action, delete_action, get_action, update_action
from radarr_client import (
    RadarrError,
    build_release_push,
    configured as radarr_configured,
    ensure_movie,
    push_release,
    selection_context,
)
from tmdb_resolver import resolve_movie

HOST = os.environ.get("MOVIE_INTEL_HOST", "127.0.0.1")
PORT = os.environ.get("MOVIE_INTEL_PORT", "40714")
WEBHOOK_SECRET = os.environ.get("MOVIE_INTEL_WEBHOOK_SECRET", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_TOPIC_ID = os.environ.get("TELEGRAM_TOPIC_ID", "").strip()
PUBLIC_BASE_URL = os.environ.get("MOVIE_INTEL_PUBLIC_BASE_URL", "").strip().rstrip("/")
INDEX = build_index()

# One process owns the store; serialize approvals through their complete Radarr
# transaction so simultaneous browser submissions cannot re-push a release.
_APPROVAL_LOCK = threading.Lock()
ROUTINE_RELEASE_REJECTIONS = {"quality", "existing", "not_upgrade"}
ACTION_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{20,128}$")


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
    count_text = _fmt_count(count)
    return f"{score}" + (f" ({count_text})" if count_text else "")


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
    payload = sanitize(payload)
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


def build_movie_context(payload):
    data = payload.get("data") or {}
    release = data.get("release") or {}
    title = release.get("title") or release.get("name") or "Unknown movie"
    year = release.get("year")
    movie = find_local(title, year, INDEX)
    imdb_id = movie.get("imdb_id") if movie else None
    meta = resolve_movie(title, year, imdb_id=imdb_id)
    text = format_message(payload, movie=movie, meta=meta)
    return {
        "text": text,
        "poster_url": (meta or {}).get("poster_url"),
        "movie": movie,
        "meta": meta,
        "category": rejection_class(((data.get("result") or {}).get("rejections") or [])),
    }


def build_movie_notification(payload):
    context = build_movie_context(payload)
    return context["text"], context["poster_url"]


def _pick(obj, *keys):
    for key in keys:
        value = (obj or {}).get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def create_pending_action(payload, meta):
    """Persist only what is needed to add the movie and re-push this release."""
    if not radarr_configured() or not meta or not meta.get("tmdb_id"):
        return None
    data = payload.get("data") or {}
    result = data.get("result") or {}
    if rejection_class(result.get("rejections") or []) != "unknown_movie":
        return None
    release = data.get("release") or {}
    if not _pick(release, "download_url", "downloadUrl", "magnet_uri", "magnetUrl", "magnet_url"):
        return None
    indexer = data.get("indexer") or {}
    try:
        build_release_push(release, indexer=indexer, event_timestamp=payload.get("timestamp"), tmdb_id=meta["tmdb_id"])
    except (RadarrError, TypeError, ValueError):
        # Do not offer an action that would create a movie but cannot re-push.
        return None

    release_keys = (
        "protocol", "timestamp", "publishDate", "publish_date", "name", "title", "year", "size", "seeders", "leechers",
        "download_url", "downloadUrl", "magnet_uri", "magnetUrl", "magnet_url",
        "info_url", "infoUrl", "link",
    )
    stored_release = {key: release[key] for key in release_keys if key in release}
    stored_indexer = {key: indexer[key] for key in ("name", "protocol") if key in indexer}
    movie_title = meta.get("title") or release.get("title") or release.get("name")
    action = {
        "movie": {
            "title": movie_title,
            "year": meta.get("year") or release.get("year"),
            "tmdb_id": meta.get("tmdb_id"),
            "imdb_id": meta.get("imdb_id"),
            "poster_url": meta.get("poster_url"),
        },
        "release": stored_release,
        "indexer": stored_indexer,
        "event_timestamp": payload.get("timestamp"),
    }
    return create_action(action)


def _sanitize(value):
    return sanitize(value)


def passthrough_message(payload):
    if isinstance(payload, dict):
        for container in (payload, payload.get("data")):
            if isinstance(container, dict):
                for key in ("message", "text", "body", "description"):
                    value = container.get(key)
                    if isinstance(value, str) and value.strip():
                        return redact_text(value)[:4000]
        return json.dumps(_sanitize(payload), ensure_ascii=False, indent=2)[:4000]
    if isinstance(payload, str):
        return redact_text(payload)[:4000]
    return redact_text(payload)[:4000]


def _topic_fields():
    if not TELEGRAM_TOPIC_ID:
        return {}
    try:
        return {"message_thread_id": int(TELEGRAM_TOPIC_ID)}
    except ValueError as exc:
        raise RuntimeError("TELEGRAM_TOPIC_ID must be an integer") from exc


def _reply_markup(action_url):
    if not action_url:
        return None
    return {
        "inline_keyboard": [[{
            "text": "➕ Add to Radarr & grab this release",
            "url": action_url,
        }]]
    }


def _telegram_payload(text, parse_mode="HTML", action_url=None):
    body = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
        **_topic_fields(),
    }
    if parse_mode:
        body["parse_mode"] = parse_mode
    markup = _reply_markup(action_url)
    if markup:
        body["reply_markup"] = markup
    return body


def _telegram_photo_payload(photo, caption, action_url=None):
    body = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo,
        "caption": caption,
        "parse_mode": "HTML",
        "show_caption_above_media": False,
        **_topic_fields(),
    }
    markup = _reply_markup(action_url)
    if markup:
        body["reply_markup"] = markup
    return body


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
        result = json.load(response)
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise RuntimeError("Telegram did not accept the notification")
        return response.status


def send_telegram(text, parse_mode="HTML", action_url=None):
    return _telegram_request("sendMessage", _telegram_payload(text, parse_mode=parse_mode, action_url=action_url))


def send_movie_notification(text, poster_url=None, action_url=None):
    # Telegram photo captions are limited to 1024 characters after parsing.
    if poster_url and len(text) <= 950:
        try:
            return _telegram_request("sendPhoto", _telegram_photo_payload(poster_url, text, action_url=action_url))
        except Exception:
            # Metadata/image delivery must never suppress the actual notification.
            pass
    return send_telegram(text, parse_mode="HTML", action_url=action_url)


def public_action_url(headers, token):
    if not token:
        return None
    if PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL}/action/{quote(token)}"
    # Use an explicitly configured origin/path, never caller-controlled headers.
    return None


def _page(title, body):
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:680px;margin:36px auto;padding:0 18px;background:#111;color:#eee}}
.card{{background:#1d1d1f;border-radius:14px;padding:20px}} img{{max-width:180px;border-radius:8px;float:right;margin:0 0 16px 18px}}
label{{display:block;margin:16px 0 6px;font-weight:600}} select,button{{width:100%;font:inherit;padding:11px;border-radius:8px;border:1px solid #555}}
select{{background:#202124;color:#eee}} button{{margin-top:20px;background:#eee;color:#111;font-weight:700;cursor:pointer}}
.muted{{color:#aaa}} .ok{{color:#9bd69b}} .err{{color:#ff9a9a}} code{{overflow-wrap:anywhere}} .clear{{clear:both}}
</style></head><body><div class="card">{body}<div class="clear"></div></div></body></html>"""


def render_confirmation(action, context):
    movie = action.get("movie") or {}
    release = action.get("release") or {}
    title = redact_text(movie.get("title") or "Movie")
    year = movie.get("year")
    poster = movie.get("poster_url")
    poster_html = f'<img src="{html.escape(str(poster), quote=True)}" alt="poster">' if poster else ""

    root_options = []
    for row in context["roots"]:
        path = row.get("path")
        if not path:
            continue
        selected = " selected" if path == context.get("root_default") else ""
        esc = html.escape(str(path), quote=True)
        root_options.append(f'<option value="{esc}"{selected}>{html.escape(str(path))}</option>')

    profile_options = []
    for row in context["profiles"]:
        if row.get("id") is None:
            continue
        profile_id = int(row["id"])
        selected = " selected" if profile_id == context.get("profile_default") else ""
        name = html.escape(str(row.get("name") or profile_id))
        profile_options.append(f'<option value="{profile_id}"{selected}>{name}</option>')

    body = [
        poster_html,
        f"<h2>Add {html.escape(str(title))}" + (f" ({html.escape(str(year))})" if year else "") + "</h2>",
        "<p class=\"muted\">This creates the movie in Radarr without an indexer search, then re-pushes the exact release autobrr announced.</p>",
        f"<p><b>Release</b><br><code>{html.escape(redact_text(release.get('name') or release.get('title') or 'Unknown release'))}</code></p>",
        "<form method=\"post\">",
        "<label for=\"root\">Root folder</label>",
        f'<select id="root" name="root_folder" required>{"".join(root_options)}</select>',
        "<label for=\"profile\">Quality profile</label>",
        f'<select id="profile" name="quality_profile" required>{"".join(profile_options)}</select>',
        "<button type=\"submit\">Add movie & grab this release</button>",
        "</form>",
    ]
    return _page("Add to Radarr", "".join(body))


def render_result(action, success, message):
    movie = action.get("movie") or {}
    title = redact_text(movie.get("title") or "Movie")
    klass = "ok" if success else "err"
    heading = "Added and sent to downloader" if success else "Radarr could not complete the action"
    body = (
        f'<h2 class="{klass}">{html.escape(heading)}</h2>'
        f'<p><b>{html.escape(str(title))}</b></p>'
        f'<p>{html.escape(redact_text(message))}</p>'
    )
    return _page("Radarr action", body)


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, obj):
        raw = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _html(self, status, page):
        raw = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def _action_token(self):
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "action" and ACTION_TOKEN_RE.fullmatch(parts[1]):
            return parts[1]
        return None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"ok": True, "movies": len(INDEX), "radarr": radarr_configured()})
            return

        token = self._action_token()
        if token:
            action = get_action(token)
            if not action:
                self._html(410, _page("Expired action", "<h2>Action expired or already used</h2>"))
                return
            try:
                context = selection_context()
                self._html(200, render_confirmation(action, context))
            except RadarrError as exc:
                self._html(502, render_result(action, False, str(exc)))
            return

        self._json(404, {"ok": False})

    def _handle_action_post(self, token):
        with _APPROVAL_LOCK:
            self._handle_action_post_locked(token)

    def _handle_action_post_locked(self, token):
        action = get_action(token)
        if not action:
            self._html(410, _page("Expired action", "<h2>Action expired or already used</h2>"))
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16_384:
                raise ValueError("invalid form size")
            params = parse_qs(self.rfile.read(length).decode("utf-8", errors="strict"))
            root_folder = (params.get("root_folder") or [""])[0]
            profile_raw = (params.get("quality_profile") or [""])[0]
            profile_id = int(profile_raw)

            context = selection_context()
            valid_roots = {str(row.get("path")) for row in context["roots"] if row.get("path")}
            valid_profiles = {int(row["id"]) for row in context["profiles"] if row.get("id") is not None}
            if root_folder not in valid_roots or profile_id not in valid_profiles:
                raise RadarrError("Invalid Radarr root folder or quality profile")

            movie_info = action.get("movie") or {}
            tmdb_id = movie_info.get("tmdb_id")
            if not tmdb_id:
                raise RadarrError("TMDb ID is unavailable for this movie")

            movie, created = ensure_movie(
                tmdb_id,
                profile_id,
                root_folder,
                title=movie_info.get("title"),
            )
            update_action(token, movie_id=movie.get("id"), movie_created=created)
            push_release(
                action.get("release") or {},
                indexer=action.get("indexer") or {},
                event_timestamp=action.get("event_timestamp"),
                tmdb_id=tmdb_id,
            )
            delete_action(token)
            message = "Movie is available in Radarr and the exact announced release was re-pushed. No indexer search was run."
            self._html(200, render_result(action, True, message))
        except (ValueError, UnicodeDecodeError):
            self._html(400, render_result(action, False, "Invalid confirmation form"))
        except RadarrError as exc:
            update_action(token, last_error=str(exc)[:500])
            self._html(502, render_result(action, False, str(exc)))

    def do_POST(self):
        token = self._action_token()
        if token:
            self._handle_action_post(token)
            return

        path = urlparse(self.path).path
        if not WEBHOOK_SECRET:
            self._json(503, {"ok": False, "error": "webhook_not_configured"})
            return
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
                    send_telegram(redact_text(text)[:4000], parse_mode=None)
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
                context = build_movie_context(payload)
                token = create_pending_action(payload, context.get("meta"))
                action_url = public_action_url(self.headers, token) if token else None
                if token and not action_url:
                    delete_action(token)
                    token = None
                send_movie_notification(context["text"], context["poster_url"], action_url=action_url)
                self._json(200, {
                    "ok": True,
                    "mode": "enriched",
                    "poster": bool(context["poster_url"]),
                    "action": bool(action_url),
                })
            else:
                send_telegram(passthrough_message(payload), parse_mode=None)
                self._json(200, {"ok": True, "mode": "passthrough"})
        except Exception as exc:
            # Never log payloads or request paths: both can contain secrets.
            self._json(500, {"ok": False, "error": type(exc).__name__})

    def log_message(self, fmt, *args):
        # Request paths can contain webhook/action secrets, so do not log them.
        print(f"http {getattr(self, 'command', '?')} {args[1] if len(args) > 1 else ''}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", action="store_true", help="Check deployment settings offline; do not start the service")
    parser.add_argument("--allow-unconfigured", action="store_true", help="Allow local development without integration credentials (loopback only)")
    args = parser.parse_args(argv)
    errors = configuration_errors()
    if args.check_config or not args.allow_unconfigured:
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        if args.check_config:
            print("Deployment configuration is valid (connectivity has not been checked)")
            return 0
    elif HOST not in ("127.0.0.1", "::1", "localhost"):
        print("--allow-unconfigured requires a loopback MOVIE_INTEL_HOST", file=sys.stderr)
        return 1
    try:
        port = int(PORT)
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        print("MOVIE_INTEL_PORT must be an integer between 1 and 65535", file=sys.stderr)
        return 1
    server = ThreadingHTTPServer((HOST, port), Handler)
    print(f"movie-intel listening on {HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
