"""Allowlisted read-only Radarr snapshot and private GitHub publication."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

CONFIG = Path.home() / ".config/movie-intel/radarr-snapshot.json"
STATE = Path.home() / ".local/state/movie-intel/radarr-snapshot"
REPOSITORY = "kolorifer/radarr-state"
FILENAME = "radarr-current.json"
TOP_FIELDS = {"schema_version", "generated_at", "movie_count", "movies"}
MOVIE_FIELDS = {"radarr_id", "title", "year", "imdb_id", "tmdb_id", "monitored",
                "has_file", "movie_file_id", "date_added", "tags"}


class SnapshotError(RuntimeError):
    """Safe fixed messages only; never include HTTP payloads or input values."""


def utc(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise SnapshotError("Invalid snapshot timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        raise SnapshotError("Invalid snapshot timestamp") from None


def integer(value, nullable=False, positive=False):
    if nullable and value is None:
        return None
    if type(value) is not int or value < (1 if positive else 0):
        raise SnapshotError("Invalid snapshot numeric field")
    return value


def sensitive_values(environment=None):
    environment = os.environ if environment is None else environment
    values = [v for k, v in environment.items()
              if v and any(word in k.upper() for word in ("TOKEN", "SECRET", "API_KEY", "PASSWORD"))]
    for key in ("RADARR_URL", "MOVIE_INTEL_PUBLIC_BASE_URL"):
        parsed = urlsplit(environment.get(key, ""))
        values.extend(v for v in (parsed.hostname, parsed.username, parsed.password) if v)
    values.extend([str(Path.home()), Path.home().name])
    return values


def safe_text(value, forbidden=()):
    if not isinstance(value, str) or not value or len(value) > 500:
        raise SnapshotError("Invalid snapshot text field")
    if (any(ord(c) < 32 for c in value) or re.search(
            r"(?i)(https?://|magnet:|www\.|(?:\d{1,3}\.){3}\d{1,3}|"
            r"(?:^|\s)/[a-zA-Z0-9_.-]+/|"
            r"[a-z]:\\|(?:api[_-]?key|password|passkey|bearer|token|secret)\s*[:=])", value)):
        raise SnapshotError("Private data detected in snapshot text")
    for private in forbidden:
        if private and private.casefold() in value.casefold():
            raise SnapshotError("Configured private value detected in snapshot")
    return value


def sanitize(movies, tags, generated_at=None, forbidden=()):
    if not isinstance(movies, list) or not isinstance(tags, list):
        raise SnapshotError("Invalid Radarr collection")
    labels = {}
    for tag in tags:
        tid = integer(tag.get("id"), positive=True)
        if tid in labels:
            raise SnapshotError("Duplicate Radarr tag ID")
        labels[tid] = safe_text(tag.get("label"), forbidden)
    rows = []
    for movie in movies:
        iid = movie.get("imdbId") or None
        if iid is not None and (not isinstance(iid, str) or not re.fullmatch(r"tt[0-9]+", iid)):
            raise SnapshotError("Invalid IMDb ID")
        if type(movie.get("monitored")) is not bool or type(movie.get("hasFile")) is not bool:
            raise SnapshotError("Invalid snapshot boolean field")
        tids = movie.get("tags", [])
        if not isinstance(tids, list) or any(type(t) is not int or t not in labels for t in tids):
            raise SnapshotError("Unresolved snapshot tag ID")
        rows.append({
            "radarr_id": integer(movie.get("id"), positive=True),
            "title": safe_text(movie.get("title"), forbidden),
            "year": integer(movie.get("year")),
            "imdb_id": iid,
            "tmdb_id": integer(movie.get("tmdbId"), nullable=True, positive=True),
            "monitored": movie["monitored"],
            "has_file": movie["hasFile"],
            "movie_file_id": integer(movie.get("movieFileId", 0)),
            "date_added": utc(movie.get("added")),
            "tags": sorted({labels[t] for t in tids}),
        })
    rows.sort(key=lambda row: row["radarr_id"])
    snapshot = {"schema_version": 1,
                "generated_at": utc(generated_at or datetime.now(timezone.utc).isoformat()),
                "movie_count": len(rows), "movies": rows}
    validate(snapshot, forbidden)
    return snapshot


def validate(snapshot, forbidden=()):
    if not isinstance(snapshot, dict) or set(snapshot) != TOP_FIELDS or snapshot["schema_version"] != 1:
        raise SnapshotError("Invalid snapshot schema")
    if not snapshot["generated_at"] or utc(snapshot["generated_at"]) != snapshot["generated_at"]:
        raise SnapshotError("Invalid snapshot generation time")
    rows = snapshot["movies"]
    if not isinstance(rows, list) or type(snapshot["movie_count"]) is not int or snapshot["movie_count"] != len(rows):
        raise SnapshotError("Snapshot count mismatch")
    ids = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != MOVIE_FIELDS:
            raise SnapshotError("Unexpected snapshot movie fields")
        ids.append(integer(row["radarr_id"], positive=True))
        safe_text(row["title"], forbidden)
        integer(row["year"])
        integer(row["tmdb_id"], nullable=True, positive=True)
        integer(row["movie_file_id"])
        if row["imdb_id"] is not None and not re.fullmatch(r"tt[0-9]+", row["imdb_id"]):
            raise SnapshotError("Invalid IMDb ID")
        if type(row["monitored"]) is not bool or type(row["has_file"]) is not bool:
            raise SnapshotError("Invalid snapshot boolean field")
        if row["date_added"] is not None and utc(row["date_added"]) != row["date_added"]:
            raise SnapshotError("Invalid movie timestamp")
        if not isinstance(row["tags"], list) or row["tags"] != sorted(set(row["tags"])):
            raise SnapshotError("Invalid snapshot tag labels")
        for label in row["tags"]:
            safe_text(label, forbidden)
    if ids != sorted(set(ids)):
        raise SnapshotError("Duplicate or unordered snapshot movie IDs")
    return snapshot


def encoded(snapshot):
    validate(snapshot)
    return (json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def read_private(path):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise SnapshotError("Snapshot configuration/credential must be a private regular file")
    return path.read_text()


def config(path=CONFIG):
    data = json.loads(read_private(path))
    if not isinstance(data, dict) or set(data) - {"repository", "token_file"}:
        raise SnapshotError("Unexpected snapshot configuration fields")
    if data.get("repository", REPOSITORY) != REPOSITORY:
        raise SnapshotError("Snapshot destination must be the dedicated state repository")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        token = read_private(Path(data.get("token_file",
                             str(Path.home() / ".config/movie-intel/github-state-token")))).strip()
    if not token or any(c.isspace() for c in token):
        raise SnapshotError("Invalid GitHub publishing credential")
    return REPOSITORY, token


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SnapshotError("GitHub redirect refused")


class GitHub:
    def __init__(self, token):
        self.token = token
        self.opener = build_opener(NoRedirect())

    def request(self, path, method="GET", payload=None, missing=False):
        body = json.dumps(payload).encode() if payload is not None else None
        req = Request("https://api.github.com" + path, data=body, method=method,
                      headers={"Authorization": "Bearer " + self.token,
                               "Accept": "application/vnd.github+json",
                               "Content-Type": "application/json",
                               "X-GitHub-Api-Version": "2026-03-10",
                               "User-Agent": "movie-list-private-snapshot"})
        try:
            with self.opener.open(req, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if missing and exc.code == 404:
                return None
            raise SnapshotError("GitHub request failed (HTTP " + str(exc.code) + ")") from None
        except (URLError, OSError, ValueError):
            raise SnapshotError("GitHub request failed") from None


def publish(snapshot, github, repository=REPOSITORY):
    if repository != REPOSITORY:
        raise SnapshotError("Snapshot destination must be the dedicated state repository")
    metadata = github.request("/repos/" + repository)
    if metadata.get("private") is not True or metadata.get("full_name", "").casefold() != repository.casefold():
        raise SnapshotError("Snapshot publication requires the verified private state repository")
    content_path = "/repos/" + repository + "/contents/" + FILENAME
    previous = github.request(content_path, missing=True)
    body = {"message": "Refresh sanitized current Radarr state",
            "content": base64.b64encode(encoded(snapshot)).decode()}
    if previous is not None:
        if previous.get("type") != "file" or not previous.get("sha"):
            raise SnapshotError("Invalid current snapshot file")
        body["sha"] = previous["sha"]
    result = github.request(content_path, "PUT", body)
    # Verify exactly what was written; do not expose payload/URL on errors.
    current = github.request(content_path)
    try:
        received = base64.b64decode(current["content"])
    except (KeyError, ValueError):
        raise SnapshotError("Published snapshot could not be verified") from None
    if received != encoded(snapshot):
        raise SnapshotError("Published snapshot content mismatch")
    return {"status": "published", "movie_count": snapshot["movie_count"],
            "repository": repository, "file": FILENAME,
            "sha256": hashlib.sha256(received).hexdigest(),
            "commit": result.get("commit", {}).get("sha")}


def refresh(movies, tags, config_path=CONFIG, state=STATE, github=None):
    from radarr_movie_list_sync import write_private
    forbidden = sensitive_values()
    snapshot = sanitize(movies, tags, forbidden=forbidden)
    # Atomic replace only after strict validation; local data also stays private.
    write_private(Path(state) / FILENAME, snapshot)
    if github is None:
        repository, token = config(config_path)
        validate(snapshot, [*forbidden, token])
        github = GitHub(token)
    else:
        repository = REPOSITORY
    result = publish(snapshot, github, repository)
    write_private(Path(state) / "publication.json", result)
    return result


def after_success(snapshot):
    """Nonfatal publication status: reconciliation never repeats on this failure."""
    try:
        return refresh(snapshot["movies"], snapshot["tags"])
    except Exception:
        # Third-party HTTP/config values must never reach journal or chat.
        return {"status": "failed", "reason": "Private snapshot refresh failed; inspect private configuration/access"}


def main(argv=None):
    """Manual read-only export/publish; uses the existing private launcher."""
    from radarr_movie_list_sync import API, locked, STATE as SYNC_STATE, write_private
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        with locked(SYNC_STATE):
            api = API()
            # No command, queue, root-folder or profile reads needed here.
            movies = api.request("/movie?excludeLocalCovers=true")
            tags = api.request("/tag")
            if args.publish:
                result = refresh(movies, tags)
            else:
                snapshot = sanitize(movies, tags, forbidden=sensitive_values())
                write_private(STATE / FILENAME, snapshot)
                result = {"status": "exported", "movie_count": snapshot["movie_count"]}
            print(json.dumps(result))
            return 0
    except Exception:
        print('{"status":"failed","reason":"Private snapshot export/publication failed"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
