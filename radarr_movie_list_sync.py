"""D016 Radarr membership/score-band reconciliation without acquisition commands."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlencode

import radarr_client as radarr
from production_scoring import ROOT, load_catalog

MEMBERSHIP = "movie-list"
BANDS = ("ml-below-225", "ml-225-249", "ml-250-299", "ml-300-399", "ml-400-plus")
MANAGED = (MEMBERSHIP, *BANDS)
STATE = Path.home() / ".local/state/movie-intel/radarr-sync"
CONFIG = Path.home() / ".config/movie-intel/radarr-sync.json"
PROTECTED = ("imdbId", "tmdbId", "monitored", "qualityProfileId", "rootFolderPath",
             "path", "minimumAvailability", "movieFileId", "hasFile")


class SyncError(RuntimeError):
    pass


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def write_private(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    temporary.replace(path)


@contextmanager
def locked(state):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(state / "lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SyncError("Another Movie List sync is running") from exc
        yield
    finally:
        os.close(fd)


def score_band(score):
    for floor, label in ((400, BANDS[4]), (300, BANDS[3]), (250, BANDS[2]), (225, BANDS[1])):
        if score >= floor:
            return label
    return BANDS[0]


def movie_guard(movie):
    return {k:movie.get(k) for k in PROTECTED}


class API:
    def request(self, path, method="GET", payload=None):
        # A closed write surface prevents accidental search/grab/delete commands.
        allowed = (method == "POST" and path in ("/tag", "/movie")
                   or method == "PUT" and path == "/movie/editor")
        if method != "GET" and not allowed:
            raise SyncError("Unsupported Radarr write operation")
        if method == "PUT" and set(payload) != {"movieIds", "tags", "applyTags"}:
            raise SyncError("Movie editor must change tags only")
        if method == "POST" and path == "/movie":
            if payload.get("addOptions") != {"searchForMovie":False} or payload.get("monitored") is not True:
                raise SyncError("Unsafe movie addition options")
        return radarr._request(path, method=method, payload=payload)

    def snapshot(self):
        result = {
            "movies":self.request("/movie?excludeLocalCovers=true"),
            "tags":self.request("/tag"),
            "roots":self.request("/rootfolder"),
            "profiles":self.request("/qualityprofile"),
        }
        if any(not isinstance(v,list) for v in result.values()):
            raise SyncError("Unexpected Radarr snapshot schema")
        for key in ("movies","tags","roots","profiles"):
            rows=result[key]
            if any(not isinstance(r,dict) or not isinstance(r.get("id"),int) for r in rows) or len({r["id"] for r in rows})!=len(rows):
                raise SyncError("Duplicate/invalid Radarr snapshot IDs")
        return result

    def lookup(self, iid):
        result = self.request("/movie/lookup/imdb?" + urlencode({"imdbId":iid}))
        if isinstance(result, list):
            if len(result) != 1:
                raise SyncError("Ambiguous IMDb lookup")
            result = result[0]
        checked = verify_identity(result, iid)
        confirmed = self.request("/movie/lookup/tmdb?" + urlencode({"tmdbId":checked["tmdb_id"]}))
        return verify_identity(confirmed, iid, checked["tmdb_id"])


def verify_identity(row, iid, tmdb_id=None):
    if not isinstance(row, dict) or row.get("imdbId") != iid:
        raise SyncError("IMDb lookup identity mismatch")
    tid = row.get("tmdbId")
    if isinstance(tid, bool) or not isinstance(tid, int) or tid <= 0:
        raise SyncError("Invalid TMDb identity")
    if tmdb_id is not None and tid != tmdb_id:
        raise SyncError("IMDb/TMDb lookup conflict")
    if not row.get("title"):
        raise SyncError("Missing verified movie title")
    return {"imdb_id":iid, "tmdb_id":tid, "title":row["title"], "year":row.get("year")}


def snapshot_fingerprint(snapshot):
    return digest({
        "movies":[{"id":m["id"], "tags":sorted(m.get("tags") or []),
                   **movie_guard(m)} for m in sorted(snapshot["movies"], key=lambda m:m["id"])],
        "tags":sorted(snapshot["tags"], key=lambda t:t["id"]),
        "roots":[{k:r.get(k) for k in ("id","path","accessible")}
                 for r in sorted(snapshot["roots"], key=lambda r:r["id"])],
        "profiles":sorted(snapshot["profiles"], key=lambda p:p["id"]),
    })


def choose_settings(snapshot, explicit=None):
    explicit = explicit or {}
    paths = {r["path"] for r in snapshot["roots"] if r.get("path") and r.get("accessible") is not False}
    profiles = {p["id"]:p["name"] for p in snapshot["profiles"]}
    used_roots = {m.get("rootFolderPath") for m in snapshot["movies"] if m.get("rootFolderPath")}
    used_profiles = {m.get("qualityProfileId") for m in snapshot["movies"] if m.get("qualityProfileId") is not None}
    root = explicit.get("root_folder")
    profile = explicit.get("quality_profile_id")
    if root is None:
        choices = paths if len(paths) == 1 else used_roots & paths
        if len(choices) != 1:
            raise SyncError("Ambiguous root folder; configure root_folder explicitly")
        root = next(iter(choices))
    if profile is None:
        choices = set(profiles) if len(profiles) == 1 else used_profiles & set(profiles)
        if len(choices) != 1:
            raise SyncError("Ambiguous quality profile; configure quality_profile_id explicitly")
        profile = next(iter(choices))
    if root not in paths or profile not in profiles:
        raise SyncError("Configured root/profile is unavailable")
    return {"root_folder":root,"quality_profile_id":profile,"quality_profile_name":profiles[profile],
            "reason":"Explicit validated config" if explicit else "Single existing root/profile convention"}


def tag_index(tags):
    labels = {}
    for tag in tags:
        label = tag.get("label")
        if label in MANAGED:
            if label in labels:
                raise SyncError("Duplicate managed tag label")
            labels[label] = tag["id"]
    return labels


def plan_sync(api, catalog, snapshot, explicit=None, identities=None, workers=4):
    qualified = {i:r for i,r in catalog.items() if r["qualified"]}
    tags = tag_index(snapshot["tags"])
    by_imdb = {}
    by_tmdb = {}
    for m in snapshot["movies"]:
        if m.get("imdbId"):
            by_imdb.setdefault(m["imdbId"], []).append(m)
        if m.get("tmdbId"):
            by_tmdb.setdefault(m["tmdbId"], []).append(m)
    missing = sorted(set(qualified)-set(by_imdb))
    lookups = {}
    failures = {}
    identities = identities or {}
    def resolve(iid):
        try:
            if iid in identities:
                value = identities[iid]
                if value.get("imdb_id") != iid or not isinstance(value.get("tmdb_id"), int) or value["tmdb_id"] <= 0:
                    raise SyncError("Invalid saved identity")
                return iid, value, None
            return iid, api.lookup(iid), None
        except (SyncError, radarr.RadarrError) as exc:
            return iid, None, str(exc)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for iid, value, failure in pool.map(resolve, missing):
            if failure:failures[iid] = failure
            else:lookups[iid] = value
    collisions = {}
    for iid, row in lookups.items():
        collisions.setdefault(row["tmdb_id"], []).append(iid)
    updates, additions, removals, correct, unresolved = [], [], [], [], []
    identities_out = {}
    for iid, row in sorted(qualified.items()):
        base = {"imdb_id":iid,"title":row["title"],"year":row["year"],
                "score":row["overall_score"],"band":score_band(row["overall_score"])}
        matches = by_imdb.get(iid, [])
        if len(matches) > 1:
            unresolved.append({**base,"reason":"Duplicate IMDb IDs in Radarr"});continue
        if not matches:
            value = lookups.get(iid)
            if not value:
                unresolved.append({**base,"reason":failures.get(iid,"Lookup unavailable")});continue
            if len(collisions[value["tmdb_id"]]) != 1:
                unresolved.append({**base,"reason":"Multiple catalog IMDb IDs map to one TMDb movie"});continue
            matches = by_tmdb.get(value["tmdb_id"], [])
            if len(matches) > 1 or matches and matches[0].get("imdbId") not in (None,"",iid):
                unresolved.append({**base,"reason":"Existing Radarr TMDb/IMDb identity conflict"});continue
            identities_out[iid] = value
            if not matches:
                additions.append({**base,**value});continue
        movie = matches[0]
        required = (MEMBERSHIP, base["band"])
        wanted = {tags[t] for t in required if t in tags}
        managed_ids = set(tags.values())
        current = set(movie.get("tags") or [])
        remove = sorted((current & managed_ids) - wanted)
        add = [t for t in required if t not in tags or tags[t] not in current]
        action = {**base,"radarr_id":movie["id"],"remove_tag_ids":remove,"add_labels":add}
        if remove or add:updates.append(action)
        else:correct.append(action)
    for movie in sorted(snapshot["movies"], key=lambda m:m["id"]):
        if movie.get("imdbId") in qualified:
            continue
        # Preserve ambiguous qualified identities skipped above; do not mistake
        # them for removals. A verified TMDb join also counts as a qualified movie.
        if any(a["radarr_id"] == movie["id"] for a in updates+correct):
            continue
        if movie.get("imdbId") in {r["imdb_id"] for r in unresolved}:
            continue
        remove = sorted(set(movie.get("tags") or []) & set(tags.values()))
        if remove and not movie.get("imdbId"):
            unresolved.append({"imdb_id":None,"title":movie.get("title"),"reason":"Managed movie lacks IMDb identity; tags preserved"})
            continue
        if remove:
            removals.append({"radarr_id":movie["id"],"imdb_id":movie.get("imdbId"),
                             "title":movie.get("title"),"remove_tag_ids":remove,"add_labels":[]})
    settings = choose_settings(snapshot, explicit) if additions else None
    used_labels = {label for r in updates for label in r["add_labels"]}
    for row in additions:used_labels.update((MEMBERSHIP,row["band"]))
    create = [label for label in MANAGED if label in used_labels and label not in tags]
    counts = {"qualified":len(qualified),"already_correct":len(correct),"existing_to_tag":len(updates),
              "missing_to_add":len(additions),"unresolved":len(unresolved),"managed_removals":len(removals)}
    return {"schema_version":1,"catalog_sha256":digest(catalog),
            "state_fingerprint":snapshot_fingerprint(snapshot),"counts":counts,
            "settings":settings,"tag_create":create,"tag_reuse":tags,
            "updates":updates,"additions":additions,"removals":removals,
            "unresolved":unresolved,"correct":correct,"identities":identities_out}


def verify_tags(api, movie_id, labels, remove, guard):
    row = api.request("/movie/" + str(movie_id) + "?excludeLocalCovers=true")
    if row is None or movie_guard(row) != guard:
        raise SyncError("Existing movie settings/files changed during tag update")
    current = set(row.get("tags") or [])
    if not set(labels) <= current or set(remove) & current:
        raise SyncError("Radarr did not retain the requested managed tags")
    return row


def apply_plan(api, catalog, snapshot, plan, journal=None):
    if digest(catalog) != plan["catalog_sha256"] or snapshot_fingerprint(api.snapshot()) != plan["state_fingerprint"]:
        raise SyncError("Live state/catalog differs from the recorded dry-run; generate a new plan")
    tags = tag_index(snapshot["tags"])
    result = {"tags_created":[],"movies_tagged":0,"movies_added":0,"managed_removals":0,
              "write_operations":[],"acquisition_commands":0}
    def record(operation):
        result["write_operations"].append(operation)
        if journal:write_private(journal,result)
    for label in plan["tag_create"]:
        response = api.request("/tag", "POST", {"label":label})
        if not isinstance(response,dict) or response.get("label") != label or not response.get("id"):
            raise SyncError("Tag creation could not be verified; inspect before retry")
        tags[label] = response["id"];result["tags_created"].append({"id":response["id"],"label":label})
        record({"method":"POST","path":"/tag","label":label})
    old = {m["id"]:m for m in snapshot["movies"]}
    # Per-movie tag-only calls avoid replacing unrelated fields and make partial
    # application resumable. No more than two small writes per changed movie.
    for action in plan["updates"]+plan["removals"]:
        mid=action["radarr_id"]
        fresh=api.request("/movie/"+str(mid)+"?excludeLocalCovers=true")
        if fresh is None or movie_guard(fresh)!=movie_guard(old[mid]) or set(fresh.get("tags") or [])!=set(old[mid].get("tags") or []):
            raise SyncError("Movie changed after dry-run; stop and reconcile")
        for mode,ids in (("remove",action["remove_tag_ids"]),("add",[tags[t] for t in action["add_labels"]])):
            if ids:
                api.request("/movie/editor","PUT",{"movieIds":[mid],"tags":ids,"applyTags":mode})
                record({"method":"PUT","path":"/movie/editor","movie_id":mid,"mode":mode,"tag_ids":ids})
        desired=(set(old[mid].get("tags") or [])-set(action["remove_tag_ids"]))|{tags[t] for t in action["add_labels"]}
        verified=verify_tags(api,mid,desired,action["remove_tag_ids"],movie_guard(old[mid]))
        if set(verified.get("tags") or []) != desired:
            raise SyncError("Unexpected concurrent tag changes; stop and reconcile")
        if action in plan["updates"]:result["movies_tagged"]+=1
        else:result["managed_removals"]+=1
    for action in plan["additions"]:
        iid=action["imdb_id"];tid=action["tmdb_id"]
        verified=api.request("/movie/lookup/tmdb?"+urlencode({"tmdbId":tid}))
        verify_identity(verified,iid,tid)
        current=api.request("/movie?"+urlencode({"tmdbId":tid,"excludeLocalCovers":"true"})) or []
        if any(m.get("imdbId")==iid or m.get("tmdbId")==tid for m in current):
            raise SyncError("A planned missing movie appeared after dry-run")
        body={"tmdbId":tid,"title":verified["title"],"qualityProfileId":plan["settings"]["quality_profile_id"],
              "rootFolderPath":plan["settings"]["root_folder"],"monitored":True,"minimumAvailability":"released",
              "tags":[tags[MEMBERSHIP],tags[action["band"]]],"addOptions":{"searchForMovie":False}}
        response=api.request("/movie","POST",body)
        if not isinstance(response,dict) or not response.get("id"):
            raise SyncError("Movie addition response ambiguous; inspect before retry")
        if response.get("imdbId")!=iid or response.get("tmdbId")!=tid or response.get("monitored") is not True:
            raise SyncError("Added movie identity/monitoring could not be verified")
        if response.get("qualityProfileId") != body["qualityProfileId"] or response.get("rootFolderPath") != body["rootFolderPath"]:
            raise SyncError("Added movie root/profile differ from plan")
        if set(response.get("tags") or []) != set(body["tags"]):
            raise SyncError("Added movie tags differ from plan")
        result["movies_added"]+=1
        record({"method":"POST","path":"/movie","imdb_id":iid,"tmdb_id":tid,
                "movie_id":response["id"],"searchForMovie":False,"monitored":True,"tag_ids":body["tags"]})
    result["managed_tags"]=tags
    if journal:write_private(journal,result)
    return result


def acquisition_snapshot(api):
    commands=api.request("/command") or []
    queue=api.request("/queue?"+urlencode({"pageSize":1000})) or {}
    return {"queue_count":queue.get("totalRecords",0),
            "acquisition_commands":[{"id":c.get("id"),"name":c.get("name"),"status":c.get("status")}
              for c in commands if any(x in str(c.get("name","")).lower() for x in ("search","grab","download","importlist"))]}


def load_config(path):
    if not path.exists():return {}
    if path.stat().st_mode & 0o077:raise SyncError("Sync configuration must have mode600")
    data=json.loads(path.read_text())
    if set(data)-{"root_folder","quality_profile_id"}:raise SyncError("Unexpected sync configuration fields")
    return data


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run",action="store_true")
    mode.add_argument("--apply",action="store_true")
    parser.add_argument("--expect-plan",type=Path)
    parser.add_argument("--config",type=Path,default=CONFIG)
    parser.add_argument("--report",type=Path,default=STATE/"latest.json")
    args=parser.parse_args(argv)
    os.umask(0o077)
    try:
        with locked(STATE):
            api=API();catalog=load_catalog();snapshot=api.snapshot()
            expected=json.loads(args.expect_plan.read_text()) if args.expect_plan else None
            config=load_config(args.config)
            plan=plan_sync(api,catalog,snapshot,config,identities=(expected or {}).get("identities"))
            if expected and (plan["state_fingerprint"] != expected["state_fingerprint"]
                             or plan["catalog_sha256"] != expected["catalog_sha256"]
                             or plan["counts"] != expected["counts"]
                             or any(plan[k] != expected[k] for k in ("updates","additions","removals","tag_create","tag_reuse"))
                             or (plan["settings"] or {}).get("root_folder") != (expected["settings"] or {}).get("root_folder")
                             or (plan["settings"] or {}).get("quality_profile_id") != (expected["settings"] or {}).get("quality_profile_id")):
                raise SyncError("Recorded dry-run no longer matches live state")
            stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            if not args.apply:
                write_private(args.report,plan)
                print(json.dumps({"mode":"dry-run",**plan["counts"],"settings":plan["settings"],
                                  "tag_create":plan["tag_create"],"report":str(args.report)}))
                return 0
            # Preserve full private API state before the first write; public reports
            # receive only the explicit plan and operation whitelist audit.
            backup=STATE/"backups"/stamp
            write_private(backup/"before.json",snapshot)
            write_private(backup/"plan.json",plan)
            before_activity=acquisition_snapshot(api)
            result=apply_plan(api,catalog,snapshot,plan,backup/"operations.json")
            after=api.snapshot()
            post=plan_sync(api,catalog,after,config,identities=plan["identities"])
            after_activity=acquisition_snapshot(api)
            remaining=sum(post["counts"][k] for k in ("existing_to_tag","missing_to_add","managed_removals"))
            if remaining:raise SyncError("Post-apply reconciliation still requires changes")
            report={"mode":"apply","plan":plan,"result":result,"post":post,
                    "activity_before":before_activity,"activity_after":after_activity,
                    "backup":str(backup),"completed_at":datetime.now(timezone.utc).isoformat()}
            write_private(backup/"after.json",after)
            write_private(args.report,report)
            print(json.dumps({"mode":"apply",**{k:v for k,v in result.items() if k!="write_operations"},"remaining_changes":remaining,
                              "unresolved":post["counts"]["unresolved"],"report":str(args.report)}))
            return 0
    except (SyncError,radarr.RadarrError,OSError,ValueError) as exc:
        # No exception chain/HTTP payload is exposed by the client.
        message=str(exc) if isinstance(exc,(SyncError,radarr.RadarrError)) else type(exc).__name__
        print(json.dumps({"status":"failed","reason":message}),file=sys.stderr)
        return 1


if __name__=="__main__":
    sys.exit(main())
