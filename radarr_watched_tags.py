"""One-time exact-IMDb additive watched tagging; private targets/reports only."""
import argparse
import base64
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

import radarr_client
from radarr_movie_list_sync import API as SyncAPI, STATE as SYNC_STATE, locked, write_private, digest
import radarr_snapshot as export

STATE = Path.home() / ".local/state/movie-intel/watched-tagging"


class WatchedError(RuntimeError):
    pass


def validate_manifest(data):
    if (not isinstance(data, dict) or set(data) != {"schema_version", "purpose", "target_count", "match_policy", "imdb_ids"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["match_policy"] != "Exact IMDb ID only"
            or not isinstance(data["purpose"], str)):
        raise WatchedError("Invalid private target manifest")
    ids = data["imdb_ids"]
    if (not isinstance(ids, list) or not ids or type(data["target_count"]) is not int
            or data["target_count"] != len(ids)
            or any(not isinstance(i, str) or not re.fullmatch(r"tt[0-9]+", i) for i in ids)
            or len(set(ids)) != len(ids)):
        raise WatchedError("Invalid target count/identity/uniqueness")
    return sorted(ids)


def fetch_manifest():
    repository, token = export.config()
    github = export.GitHub(token)
    repo = github.request("/repos/" + repository)
    if repo.get("private") is not True:
        raise WatchedError("Target manifest repository must be private")
    remote = github.request("/repos/" + repository + "/contents/watched-targets.json")
    if remote.get("type") != "file" or remote.get("encoding") != "base64":
        raise WatchedError("Invalid private manifest file")
    data = json.loads(base64.b64decode(remote["content"]))
    validate_manifest(data)
    return data


class API:
    """No movie additions, commands, deletes or tag replacement in this client."""
    def __init__(self):
        self.client = SyncAPI()
        self.allowed_movie_ids = set()
        self.watched_tag_id = None
        self.operations = []

    def request(self, path, method="GET", payload=None):
        if method == "GET":
            if path not in ("/movie?excludeLocalCovers=true", "/tag"):
                raise WatchedError("Unsupported read operation")
        elif method == "POST":
            if path != "/tag" or payload != {"label": "watched"}:
                raise WatchedError("Unsupported write operation")
        elif method == "PUT":
            if (path != "/movie/editor" or not isinstance(payload, dict)
                    or set(payload) != {"movieIds", "tags", "applyTags"}
                    or payload["applyTags"] != "add" or self.watched_tag_id is None
                    or payload["tags"] != [self.watched_tag_id]
                    or not payload["movieIds"]
                    or not set(payload["movieIds"]).issubset(self.allowed_movie_ids)):
                raise WatchedError("Unsupported movie editor operation")
        else:
            raise WatchedError("Unsupported write operation")
        if method != "GET":
            self.operations.append({"method": method, "path": path, "payload": payload})
        return self.client.request(path, method, payload)

    def snapshot(self):
        movies = self.request("/movie?excludeLocalCovers=true")
        tags = self.request("/tag")
        if not isinstance(movies, list) or not isinstance(tags, list):
            raise WatchedError("Unexpected Radarr collections")
        for rows in (movies, tags):
            if (any(not isinstance(r, dict) or type(r.get("id")) is not int for r in rows)
                    or len({r["id"] for r in rows}) != len(rows)):
                raise WatchedError("Invalid or duplicate Radarr resource ID")
        return {"movies": movies, "tags": tags}


def plan(snapshot, manifest):
    ids = validate_manifest(manifest)
    by_imdb = defaultdict(list)
    for m in snapshot["movies"]:
        by_imdb[m.get("imdbId")].append(m)
    tags = [t for t in snapshot["tags"] if t.get("label") == "watched"]
    if len(tags) > 1:
        raise WatchedError("Ambiguous watched tag")
    tag_id = tags[0]["id"] if tags else None
    missing = [iid for iid in ids if not by_imdb[iid]]
    ambiguous = [iid for iid in ids if len(by_imdb[iid]) > 1]
    targets = [by_imdb[iid][0] for iid in ids if len(by_imdb[iid]) == 1]
    pending = sorted(m["id"] for m in targets if tag_id is None or tag_id not in (m.get("tags") or []))
    return {"target_count": len(ids), "already_tagged": len(targets)-len(pending),
            "to_tag": len(pending), "missing_count": len(missing), "ambiguous_count": len(ambiguous),
            "missing": missing, "ambiguous": ambiguous, "tag_id": tag_id,
            "tag_action": "reuse" if tag_id is not None else "create",
            "movie_ids": pending, "target_movie_ids": sorted(m["id"] for m in targets),
            "manifest_digest": digest(manifest), "snapshot_digest": digest(snapshot)}


def clean(plan):
    if plan["missing_count"] or plan["ambiguous_count"]:
        raise WatchedError("Target resolution blocked; inspect private dry-run counts/report")


def verify_preserved(before, after, target_ids, tag_id):
    old = {m["id"]: m for m in before["movies"]}
    new = {m["id"]: m for m in after["movies"]}
    if set(old) != set(new):
        raise WatchedError("Radarr movie membership changed during tagging")
    for mid, previous in old.items():
        current = new[mid]
        if {k:v for k,v in previous.items() if k != "tags"} != {k:v for k,v in current.items() if k != "tags"}:
            raise WatchedError("Non-tag movie state changed during tagging")
        expected = set(previous.get("tags") or [])
        if mid in target_ids:
            expected.add(tag_id)
        if set(current.get("tags") or []) != expected:
            raise WatchedError("Unexpected movie tag change")
    old_tags = {t["id"]:t for t in before["tags"]}
    new_tags = {t["id"]:t for t in after["tags"]}
    if any(new_tags.get(tid) != t for tid,t in old_tags.items()) or set(new_tags)-set(old_tags)-{tag_id}:
        raise WatchedError("Unrelated tag definitions changed")


def apply(api, snapshot, manifest, expected):
    planned = plan(snapshot, manifest)
    clean(planned)
    if planned != expected:
        raise WatchedError("Recorded dry-run differs from fresh live state")
    # Re-read all targets immediately before the first write.
    fresh = api.snapshot()
    if fresh != snapshot:
        raise WatchedError("Live state changed since dry-run")
    tag_id = planned["tag_id"]
    if tag_id is None:
        tag = api.request("/tag", "POST", {"label": "watched"})
        if not isinstance(tag, dict) or tag.get("label") != "watched" or type(tag.get("id")) is not int:
            raise WatchedError("Watched tag creation could not be verified")
        tag_id = tag["id"]
    current = api.snapshot()
    # Creating a tag must not change movie state or unrelated tag definitions.
    if current["movies"] != snapshot["movies"]:
        raise WatchedError("Movie state changed before additive update")
    if any(t not in current["tags"] for t in snapshot["tags"]):
        raise WatchedError("Tag state changed before additive update")
    current_plan = plan(current, manifest)
    clean(current_plan)
    if current_plan["tag_id"] != tag_id:
        raise WatchedError("Watched tag identity changed")
    api.watched_tag_id = tag_id
    api.allowed_movie_ids = set(planned["target_movie_ids"])
    if current_plan["movie_ids"]:
        api.request("/movie/editor", "PUT", {"movieIds": current_plan["movie_ids"],
                    "tags": [tag_id], "applyTags": "add"})
    after = api.snapshot()
    verify_preserved(snapshot, after, api.allowed_movie_ids, tag_id)
    post = plan(after, manifest)
    clean(post)
    if post["to_tag"]:
        raise WatchedError("Post-apply dry-run still requires watched tags")
    return after, post, {"targets": planned["target_count"], "already_tagged": planned["already_tagged"],
                         "tagged": len(current_plan["movie_ids"]), "tag_id": tag_id,
                         "tag_action": planned["tag_action"], "remaining": 0,
                         "monitored_files_settings_metadata_preserved": True,
                         "unrelated_tags_preserved": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expect-plan", type=Path)
    args = parser.parse_args(argv)
    try:
        with locked(SYNC_STATE):
            expected = json.loads(args.expect_plan.read_text()) if args.expect_plan else None
            manifest = fetch_manifest()
            snapshot = API().snapshot()
            planned = plan(snapshot, manifest)
            write_private(STATE/"manifest.json", manifest)
            write_private(STATE/"dry-run.json", planned)
            summary = {k:planned[k] for k in ("target_count","already_tagged","to_tag","missing_count","ambiguous_count","tag_action")}
            clean(planned)
            if not args.apply:
                print(json.dumps({"mode":"dry-run", **summary}))
                return 0
            if not args.expect_plan:
                raise WatchedError("Apply requires recorded clean dry-run")
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = STATE/"backups"/stamp
            write_private(backup/"before.json", snapshot)
            api = API()
            try:
                after, post, result = apply(api, snapshot, manifest, expected)
            finally:
                write_private(backup/"operations.json", api.operations)
            write_private(backup/"after.json", after)
            write_private(STATE/"post-dry-run.json", post)
            # Publishing failure does not undo/repeat tagging. Re-running with a
            # new dry-run is safe and skips already-tagged targets.
            report = {"result":result,"post":post,"backup":str(backup),"operations":api.operations}
            write_private(STATE/"latest.json", report)
            report["snapshot_publication"] = export.refresh(after["movies"], after["tags"])
            write_private(STATE/"latest.json", report)
            print(json.dumps({"mode":"apply", **result,
                              "snapshot_publication":report["snapshot_publication"]["status"]}))
            return 0
    except Exception:
        # No private IMDb lists, credentials, paths or HTTP payloads in logs.
        print('{"status":"failed","reason":"Watched tagging blocked; inspect private report/configuration"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
