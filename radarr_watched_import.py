"""One-time watched/unmonitored state for the verified private import cohort."""
import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import radarr_client as radarr
import radarr_watched_tags as watched
import radarr_snapshot as export
from radarr_movie_list_sync import locked, STATE as SYNC_STATE, write_private, digest, MEMBERSHIP, BANDS
from production_scoring import load_catalog

STATE = Path.home() / ".local/state/movie-intel/watched-import"
IMPORT = Path.home() / ".local/state/movie-intel/radarr-sync/backups/20261014T124727Z"
COHORT_FILE = "watched-targets-2026-10-14-import.json"


class CohortError(RuntimeError):
    pass


def plain_manifest(cohort):
    if (not isinstance(cohort, dict) or set(cohort) != {"schema_version", "purpose", "target_count",
            "match_policy", "desired_radarr_state", "imdb_ids"}
            or cohort["target_count"] != 87
            or cohort["desired_radarr_state"] != {"watched_tag":True, "monitored":False}):
        raise CohortError("Invalid private 87-target state manifest")
    plain = {k:v for k,v in cohort.items() if k != "desired_radarr_state"}
    watched.validate_manifest(plain)
    return plain


def fetch_inputs():
    repo, token = export.config()
    github = export.GitHub(token)
    if github.request("/repos/" + repo).get("private") is not True:
        raise CohortError("Private manifest repository required")
    result = {}
    for name in (COHORT_FILE, "watched-targets.json"):
        remote = github.request("/repos/" + repo + "/contents/" + name)
        if remote.get("encoding") != "base64" or remote.get("type") != "file":
            raise CohortError("Invalid manifest response")
        result[name] = json.loads(base64.b64decode(remote["content"]))
    plain_manifest(result[COHORT_FILE])
    watched.validate_manifest(result["watched-targets.json"])
    return result[COHORT_FILE], result["watched-targets.json"]


def verify_import(snapshot, cohort, import_before, import_after, catalog):
    plain = plain_manifest(cohort)
    planned = watched.plan(snapshot, plain)
    watched.clean(planned)
    old_ids = {m["id"] for m in import_before["movies"]}
    imported = {m["id"]:m for m in import_after["movies"] if m["id"] not in old_ids}
    if len(imported) != 235:
        raise CohortError("Original import audit does not prove the 235-film batch")
    current = {m["id"]:m for m in snapshot["movies"]}
    tag_labels = {t["id"]:t["label"] for t in snapshot["tags"]}
    for mid in planned["target_movie_ids"]:
        row = current[mid];original = imported.get(mid)
        if not original or row.get("imdbId") != original.get("imdbId") or row.get("tmdbId") != original.get("tmdbId"):
            raise CohortError("Target is not proven to belong to original import")
        if row.get("added") != original.get("added"):
            raise CohortError("Target import timestamp changed")
        record = catalog.get(row["imdbId"])
        labels = {tag_labels.get(t) for t in row.get("tags", [])}
        if not record or not record["qualified"] or MEMBERSHIP not in labels or len(labels.intersection(BANDS)) != 1:
            raise CohortError("Target lacks qualified Movie List membership/band evidence")
        if type(row.get("monitored")) is not bool:
            raise CohortError("Invalid target monitoring state")
    off = sorted(mid for mid in planned["target_movie_ids"] if current[mid]["monitored"])
    planned.update({"to_unmonitor":len(off), "unmonitor_ids":off, "import_provenance_verified":True,
                    "cohort_digest":digest(cohort)})
    return planned


class API(watched.API):
    def turn_off(self, ids, expected_rows):
        # Separate guarded operation: never broaden normal SyncAPI/request().
        if (not ids or len(set(ids)) != len(ids) or any(type(mid) is not int for mid in ids)
                or not set(ids).issubset(self.allowed_movie_ids)):
            raise CohortError("Monitoring-off IDs must be verified exact cohort targets")
        live = {m["id"]:m for m in self.snapshot()["movies"]}
        if any(mid not in live or live[mid] != expected_rows.get(mid)
               or live[mid].get("monitored") is not True for mid in ids):
            raise CohortError("Monitoring-off live guard differs or target is not monitored")
        body = {"movieIds": sorted(ids), "monitored":False}
        self.operations.append({"method":"PUT","path":"/movie/editor","payload":body})
        return radarr._request("/movie/editor", method="PUT", payload=body)


def verify_state(before, after, targets, watched_tag):
    # Reuse strict full-field/tag verification after accounting for exactly the
    # authorized true->false transition on targets.
    expected = json.loads(json.dumps(before))
    for row in expected["movies"]:
        if row["id"] in targets:
            row["monitored"] = False
    watched.verify_preserved(expected, after, targets, watched_tag)


def apply(api, before, cohort, audit_before, audit_after, catalog, expected):
    plan = verify_import(before,cohort,audit_before,audit_after,catalog)
    if plan != expected or api.snapshot() != before:
        raise CohortError("Recorded plan/fresh live guard changed")
    api.allowed_movie_ids = set(plan["target_movie_ids"])
    tid = plan["tag_id"]
    if tid is None:
        response = api.request("/tag","POST",{"label":"watched"})
        if response.get("label") != "watched" or type(response.get("id")) is not int:
            raise CohortError("Watched tag creation not verified")
        tid = response["id"]
    current = api.snapshot()
    if current["movies"] != before["movies"]:
        raise CohortError("Movie guard changed before tagging")
    current_plan = verify_import(current,cohort,audit_before,audit_after,catalog)
    if current_plan["tag_id"] != tid:
        raise CohortError("Watched tag identity changed")
    api.watched_tag_id = tid
    if current_plan["movie_ids"]:
        api.request("/movie/editor","PUT",{"movieIds":current_plan["movie_ids"],"tags":[tid],"applyTags":"add"})
    tagged = api.snapshot()
    watched.verify_preserved(before,tagged,api.allowed_movie_ids,tid)
    tagged_plan = verify_import(tagged,cohort,audit_before,audit_after,catalog)
    if tagged_plan["unmonitor_ids"]:
        api.turn_off(tagged_plan["unmonitor_ids"],{m["id"]:m for m in tagged["movies"]})
    after = api.snapshot()
    verify_state(before,after,api.allowed_movie_ids,tid)
    post = verify_import(after,cohort,audit_before,audit_after,catalog)
    if post["to_tag"] or post["to_unmonitor"]:
        raise CohortError("Post-state still requires changes")
    return after,post,{"targets":87,"tagged":len(current_plan["movie_ids"]),
                      "unmonitored":len(tagged_plan["unmonitor_ids"]),"tag_id":tid,
                      "remaining":0,"all_other_fields_and_tags_preserved":True}


def merge_canonical(cohort):
    plain = plain_manifest(cohort)
    repo,token = export.config();github = export.GitHub(token)
    if github.request("/repos/" + repo).get("private") is not True:
        raise CohortError("Private repository required before canonical merge")
    path = "/repos/" + repo + "/contents/watched-targets.json"
    old = github.request(path)
    canonical = json.loads(base64.b64decode(old["content"]))
    prior = set(watched.validate_manifest(canonical))
    additions = set(watched.validate_manifest(plain))
    combined = prior | additions
    updated = {**canonical,"imdb_ids":sorted(combined),"target_count":len(combined)}
    watched.validate_manifest(updated)
    if updated != canonical:
        data = (json.dumps(updated,ensure_ascii=False,indent=2)+"\n").encode()
        github.request(path,"PUT",{"message":"Merge verified watched import cohort",
                                  "sha":old["sha"],"content":base64.b64encode(data).decode()})
        fetched = json.loads(base64.b64decode(github.request(path)["content"]))
        if fetched != updated:
            raise CohortError("Canonical manifest readback mismatch")
    return {"prior_count":len(prior),"cohort_count":len(additions),
            "overlap_count":len(prior & additions),"result_count":len(combined)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--expect-plan",type=Path)
    args = parser.parse_args(argv)
    try:
        with locked(SYNC_STATE):
            expected = json.loads(args.expect_plan.read_text()) if args.expect_plan else None
            cohort,canonical = fetch_inputs()
            audit_before = json.loads((IMPORT/"before.json").read_text())
            audit_after = json.loads((IMPORT/"after.json").read_text())
            catalog = load_catalog();api = API();before = api.snapshot()
            planned = verify_import(before,cohort,audit_before,audit_after,catalog)
            write_private(STATE/"cohort.json",cohort)
            write_private(STATE/"canonical-before.json",canonical)
            write_private(STATE/"dry-run.json",planned)
            summary = {k:planned[k] for k in ("target_count","already_tagged","to_tag","to_unmonitor",
                                             "missing_count","ambiguous_count","import_provenance_verified")}
            if not args.apply:
                print(json.dumps({"mode":"dry-run",**summary}));return 0
            if expected is None:
                raise CohortError("Apply requires a recorded clean dry-run")
            backup = STATE/"backups"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            write_private(backup/"before.json",before)
            try:
                after,post,result = apply(api,before,cohort,audit_before,audit_after,catalog,expected)
            finally:
                write_private(backup/"operations.json",api.operations)
            write_private(backup/"after.json",after)
            write_private(STATE/"post-dry-run.json",post)
            report = {"result":result,"post":post,"backup":str(backup),"operations":api.operations}
            write_private(STATE/"latest.json",report)
            # Neither publisher failure nor canonical conflict repeats Radarr writes.
            report["canonical_merge"] = merge_canonical(cohort)
            write_private(STATE/"latest.json",report)
            report["snapshot_publication"] = export.refresh(after["movies"],after["tags"])
            write_private(STATE/"latest.json",report)
            print(json.dumps({"mode":"apply",**result,"canonical_merge":report["canonical_merge"],
                              "snapshot_publication":report["snapshot_publication"]["status"]}))
            return 0
    except Exception as exc:
        if isinstance(exc,(CohortError,watched.WatchedError)):
            write_private(STATE/"failure.json",{"reason":str(exc)})
        print('{"status":"failed","reason":"Cohort state blocked; inspect private report"}',file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
