"""Minimal Radarr API client for the movie-intel approval workflow.

Secrets stay in environment variables. The client never logs request payloads,
which is important because release download URLs can contain tracker passkeys.
"""
import json
import os
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from private_text import redact_text

RADARR_URL = os.environ.get("RADARR_URL", "").strip().rstrip("/")
RADARR_API_KEY = os.environ.get("RADARR_API_KEY", "").strip()


class RadarrError(RuntimeError):
    pass


def configured():
    return bool(RADARR_URL and RADARR_API_KEY)


def _api_base():
    if not RADARR_URL:
        return ""
    if RADARR_URL.endswith("/api/v3"):
        return RADARR_URL
    return RADARR_URL + "/api/v3"


def _request(path, method="GET", payload=None):
    if not configured():
        raise RadarrError("Radarr is not configured")
    url = _api_base() + path
    data = None
    headers = {
        "X-Api-Key": RADARR_API_KEY,
        "Accept": "application/json",
        "User-Agent": "movie-intel/1.0",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=20) as response:
            raw = response.read()
            if not raw:
                return None
            return json.loads(raw)
    except HTTPError as exc:
        # Do not include response bodies or request URLs here: either could echo
        # a private tracker URL from a pushed release.
        raise RadarrError(f"Radarr returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise RadarrError("Unable to reach Radarr") from exc
    except json.JSONDecodeError as exc:
        raise RadarrError("Radarr returned invalid JSON") from exc


def get_root_folders():
    rows = _request("/rootfolder") or []
    return rows if isinstance(rows, list) else []


def get_quality_profiles():
    rows = _request("/qualityprofile") or []
    return rows if isinstance(rows, list) else []


def get_movies():
    rows = _request("/movie?excludeLocalCovers=true") or []
    return rows if isinstance(rows, list) else []


def get_movie_by_tmdb(tmdb_id):
    query = urlencode({"tmdbId": int(tmdb_id), "excludeLocalCovers": "true"})
    rows = _request("/movie?" + query) or []
    if isinstance(rows, list) and rows:
        return rows[0]
    return None


def selection_context():
    """Return roots/profiles plus sensible defaults inferred from the library."""
    roots = get_root_folders()
    profiles = get_quality_profiles()
    movies = get_movies()

    if not roots:
        raise RadarrError("Radarr has no configured root folder")
    if not profiles:
        raise RadarrError("Radarr has no configured quality profile")

    root_paths = {str(row.get("path")) for row in roots if row.get("path")}
    profile_ids = {int(row["id"]) for row in profiles if row.get("id") is not None}

    root_default = None
    if len(root_paths) == 1:
        root_default = next(iter(root_paths))
    else:
        counts = Counter(
            str(row.get("rootFolderPath"))
            for row in movies
            if row.get("monitored", True) and row.get("rootFolderPath") in root_paths
        )
        if counts:
            root_default = counts.most_common(1)[0][0]
        else:
            root_default = next((row.get("path") for row in roots if row.get("path")), None)

    profile_default = None
    if len(profile_ids) == 1:
        profile_default = next(iter(profile_ids))
    else:
        counts = Counter(
            int(row.get("qualityProfileId"))
            for row in movies
            if row.get("monitored", True) and row.get("qualityProfileId") in profile_ids
        )
        if counts:
            profile_default = counts.most_common(1)[0][0]
        else:
            profile_default = next((int(row["id"]) for row in profiles if row.get("id") is not None), None)

    return {
        "roots": roots,
        "profiles": profiles,
        "root_default": root_default,
        "profile_default": profile_default,
    }


def ensure_movie(tmdb_id, quality_profile_id, root_folder_path, title=None):
    """Return (movie, created). Never trigger an indexer search."""
    existing = get_movie_by_tmdb(tmdb_id)
    if existing:
        return existing, False

    body = {
        "tmdbId": int(tmdb_id),
        "qualityProfileId": int(quality_profile_id),
        "rootFolderPath": str(root_folder_path),
        "monitored": True,
        "minimumAvailability": "released",
        "addOptions": {"searchForMovie": False},
    }
    if title:
        body["title"] = str(title)

    movie = _request("/movie", method="POST", payload=body)
    if not isinstance(movie, dict) or not movie.get("id"):
        movie = get_movie_by_tmdb(tmdb_id)
    if not isinstance(movie, dict) or not movie.get("id"):
        raise RadarrError("Radarr did not return the added movie")
    return movie, True


def _pick(obj, *keys):
    for key in keys:
        value = obj.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def build_release_push(release, indexer=None, event_timestamp=None, tmdb_id=None):
    """Map an autobrr webhook release back into Radarr's /release/push shape."""
    release = release or {}
    indexer = indexer or {}
    download_url = _pick(release, "download_url", "downloadUrl")
    magnet_url = _pick(release, "magnet_uri", "magnetUrl", "magnet_url")
    if not download_url and not magnet_url:
        raise RadarrError("The original release has no reusable download link")

    protocol = _pick(release, "protocol") or _pick(indexer, "protocol")
    if not protocol and magnet_url:
        protocol = "torrent"
    if not protocol:
        raise RadarrError("The original release protocol is missing")

    publish_date = _pick(release, "timestamp", "publishDate", "publish_date") or event_timestamp
    if not publish_date:
        raise RadarrError("The original release timestamp is missing")

    title = _pick(release, "name", "title")
    if not title:
        raise RadarrError("The original release name is missing")

    body = {
        "title": str(title),
        "protocol": str(protocol).lower(),
        "publishDate": publish_date,
    }
    if download_url:
        body["downloadUrl"] = download_url
    if magnet_url:
        body["magnetUrl"] = magnet_url

    mapping = {
        "size": ("size",),
        "seeders": ("seeders",),
        "leechers": ("leechers",),
        "infoUrl": ("info_url", "infoUrl", "link"),
    }
    for target, keys in mapping.items():
        value = _pick(release, *keys)
        if value is not None:
            body[target] = value

    indexer_name = _pick(indexer, "name")
    if indexer_name:
        body["indexer"] = str(indexer_name)
    if tmdb_id:
        body["tmdbId"] = int(tmdb_id)
    return body


def push_release(release, indexer=None, event_timestamp=None, tmdb_id=None):
    body = build_release_push(release, indexer=indexer, event_timestamp=event_timestamp, tmdb_id=tmdb_id)
    result = _request("/release/push", method="POST", payload=body)

    # Radarr returns one release decision. A 200 can still represent a normal
    # rejection by the decision engine, so surface that instead of claiming grab.
    if isinstance(result, list) and len(result) != 1:
        raise RadarrError("Radarr did not return one release decision")
    row = result[0] if isinstance(result, list) else result
    if isinstance(row, dict) and (row.get("rejected") or row.get("temporarilyRejected")):
        reasons = [str(x) for x in (row.get("rejections") or []) if str(x).strip()]
        message = redact_text("; ".join(reasons[:3])) or "Radarr rejected the release"
        raise RadarrError(message)
    if not isinstance(row, dict) or row.get("approved") is not True or row.get("rejected") is not False:
        raise RadarrError("Radarr did not confirm release approval; check Radarr history before retrying")
    return result
