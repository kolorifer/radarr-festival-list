"""Mock Radarr reconciliation; no real additions or acquisition."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import radarr_movie_list_sync as sync
import radarr_client as radarr
from production_scoring import load_catalog


def movie(iid, mid, tags, score=0):
    return {"id":mid,"imdbId":iid,"tmdbId":100+mid,"title":iid,"year":2020,
            "tags":tags,"qualityProfileId":7,"rootFolderPath":"/movies","path":"/movies/"+iid,
            "monitored":False,"minimumAvailability":"released","movieFileId":mid,"hasFile":True,
            "overview":"Original metadata"}


class Fake:
    def __init__(self):
        self.calls=[]
        self.tags=[{"id":i+1,"label":label} for i,label in enumerate(sync.MANAGED)]
        self.tags += [{"id":9,"label":"personal"},{"id":10,"label":"ml-personal"}]
        self.movies=[movie("tt1",1,[9]),movie("tt3",3,[1,3,9]),movie("tt4",4,[1,5,10])]
        self.profiles=[{"id":7,"name":"Remux"},{"id":8,"name":"Other"}]
        self.roots=[{"id":1,"path":"/movies","accessible":True}]
        self.meta={i:{"imdbId":i,"tmdbId":102,"title":"New film","year":2020} for i in ["tt2"]}
        self.fail_after_add=False

    def request(self,path,method="GET",payload=None):
        self.calls.append((path,method,copy.deepcopy(payload)))
        u=urlsplit(path);q=parse_qs(u.query)
        if method=="GET":
            if u.path=="/movie":
                rows=self.movies
                if "tmdbId" in q:rows=[m for m in rows if m["tmdbId"]==int(q["tmdbId"][0])]
                return copy.deepcopy(rows)
            if u.path.startswith("/movie/lookup/"):
                if u.path.endswith("imdb"):return copy.deepcopy(self.meta.get(q["imdbId"][0]))
                return copy.deepcopy(next((r for r in self.meta.values()
                         if isinstance(r,dict) and r.get("tmdbId")==int(q["tmdbId"][0])),None))
            if u.path.startswith("/movie/"):return copy.deepcopy(next(m for m in self.movies if m["id"]==int(u.path.split("/")[-1])))
            if u.path=="/tag":return copy.deepcopy(self.tags)
            if u.path=="/rootfolder":return copy.deepcopy(self.roots)
            if u.path=="/qualityprofile":return copy.deepcopy(self.profiles)
            if u.path=="/command":return []
            if u.path=="/queue":return {"totalRecords":0}
        if path=="/tag" and method=="POST":
            row={"id":max(t["id"] for t in self.tags)+1,"label":payload["label"]}
            self.tags.append(row);return copy.deepcopy(row)
        if path=="/movie/editor" and method=="PUT":
            assert set(payload)=={"movieIds","tags","applyTags"}
            for m in self.movies:
                if m["id"] in payload["movieIds"]:
                    tags=set(m["tags"])
                    if payload["applyTags"]=="add":tags.update(payload["tags"])
                    elif payload["applyTags"]=="remove":tags-=set(payload["tags"])
                    else:raise AssertionError("Unsafe tag replacement")
                    m["tags"]=sorted(tags)
            return copy.deepcopy(self.movies)
        if path=="/movie" and method=="POST":
            assert payload["addOptions"]=={"searchForMovie":False}
            data=copy.deepcopy(next(r for r in self.meta.values() if r.get("tmdbId")==payload["tmdbId"]))
            data.update(payload,id=max(m["id"] for m in self.movies)+1)
            self.movies.append(data)
            if self.fail_after_add:
                self.fail_after_add=False
                raise radarr.RadarrError("Simulated ambiguous response")
            return copy.deepcopy(data)
        raise AssertionError((path,method))

    @property
    def writes(self):
        return [call for call in self.calls if call[1]!="GET"]


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.fake=Fake()
        self.transport=patch.object(radarr,"_request",side_effect=self.fake.request)
        self.transport.start();self.addCleanup(self.transport.stop)
        self.api=sync.API()
        self.catalog={iid:{"imdb_id":iid,"title":iid,"year":2020,"overall_score":score,"qualified":qualified}
             for iid,score,qualified in [("tt1",224.99,True),("tt2",225,True),("tt3",300,True),("tt4",110,False)]}

    def plan(self):
        snapshot=self.api.snapshot()
        return snapshot,sync.plan_sync(self.api,self.catalog,snapshot,workers=1)

    def apply(self):
        snapshot,plan=self.plan()
        return sync.apply_plan(self.api,self.catalog,snapshot,plan)

    def test_existing_qualified_watched_unmonitored_stays_unmonitored(self):
        self.fake.tags.append({"id":11,"label":"watched"})
        self.fake.movies[0]["tags"].append(11)
        self.fake.movies[0]["monitored"]=False
        self.apply()
        row=next(m for m in self.fake.movies if m["imdbId"]=="tt1")
        self.assertIs(row["monitored"],False)
        self.assertIn(11,row["tags"])
        self.assertTrue(all("monitored" not in body for path,method,body in self.fake.writes
                            if path=="/movie/editor"))

    def test_dry_run_zero_writes(self):
        snap,plan=self.plan()
        self.assertEqual(self.fake.writes,[])
        self.assertEqual(plan["counts"],{"qualified":3,"already_correct":0,"existing_to_tag":2,
                                       "missing_to_add":1,"unresolved":0,"managed_removals":1})

    def test_repeated_apply_idempotent(self):
        self.apply();self.fake.calls=[]
        snap,plan=self.plan()
        result=sync.apply_plan(self.api,self.catalog,snap,plan)
        self.assertEqual(result["write_operations"],[])
        self.assertEqual(self.fake.writes,[])
        self.assertEqual(plan["counts"]["already_correct"],3)

    def test_existing_unrelated_tags_and_fields_preserved(self):
        before=copy.deepcopy(self.fake.movies[0])
        self.apply();after=self.fake.movies[0]
        self.assertIn(9,after["tags"]);self.assertIn(1,after["tags"]);self.assertIn(2,after["tags"])
        self.assertEqual({k:v for k,v in before.items() if k!="tags"},
                         {k:v for k,v in after.items() if k!="tags"})

    def test_stale_band_removed_only_one_managed_band(self):
        self.apply();row=next(m for m in self.fake.movies if m["imdbId"]=="tt3")
        self.assertEqual(set(row["tags"]),{1,5,9})

    def test_exact_score_band_boundaries(self):
        for score,label in [(0,"ml-below-225"),(224.999,"ml-below-225"),(225,"ml-225-249"),
                            (249.999,"ml-225-249"),(250,"ml-250-299"),(299.999,"ml-250-299"),
                            (300,"ml-300-399"),(399.999,"ml-300-399"),(400,"ml-400-plus")]:
            self.assertEqual(sync.score_band(score),label)

    def test_grandfather_below225(self):
        self.apply();self.assertEqual(set(self.fake.movies[0]["tags"]),{1,2,9})

    def test_new_monitored_no_search_correct_tags(self):
        self.apply()
        row=next(m for m in self.fake.movies if m["imdbId"]=="tt2")
        self.assertTrue(row["monitored"]);self.assertEqual(row["tags"],[1,3])
        post=next(p for path,method,p in self.fake.writes if path=="/movie")
        self.assertEqual(post["addOptions"],{"searchForMovie":False})

    def test_ambiguous_imdb_lookup_skipped(self):
        value=self.fake.meta["tt2"];self.fake.meta["tt2"]=[value,value]
        _,plan=self.plan()
        self.assertEqual(plan["counts"]["missing_to_add"],0)
        self.assertEqual(plan["counts"]["unresolved"],1)
        self.assertEqual(self.fake.writes,[])

    def test_failed_lookup_skipped(self):
        self.fake.meta={}
        _,plan=self.plan()
        self.assertEqual(plan["unresolved"][0]["imdb_id"],"tt2")
        self.assertEqual(plan["counts"]["missing_to_add"],0)

    def test_conflicting_imdb_rejected(self):
        self.fake.meta["tt2"]["imdbId"]="tt999"
        _,plan=self.plan();self.assertEqual(plan["counts"]["unresolved"],1)

    def test_tmdb_second_verification_conflict(self):
        with patch.object(self.api,"request",side_effect=[
                {"imdbId":"tt2","tmdbId":100,"title":"Film"},
                {"imdbId":"tt999","tmdbId":100,"title":"Other"}]):
            with self.assertRaises(sync.SyncError):self.api.lookup("tt2")

    def test_nonqualified_loses_only_managed_tags(self):
        before=copy.deepcopy(self.fake.movies[2]);self.apply();after=self.fake.movies[2]
        self.assertEqual(after["tags"],[10])
        self.assertEqual({k:v for k,v in before.items() if k!="tags"},
                         {k:v for k,v in after.items() if k!="tags"})

    def test_no_delete_move_search_push_commands(self):
        self.apply()
        self.assertTrue(all(path in ("/tag","/movie","/movie/editor") for path,_,_ in self.fake.writes))
        self.assertTrue(all(method in ("POST","PUT") for _,method,_ in self.fake.writes))
        for path,method,payload in self.fake.writes:
            self.assertNotIn("moveFiles",payload);self.assertNotIn("deleteFiles",payload)
        with self.assertRaises(sync.SyncError):self.api.request("/command","POST",{"name":"MoviesSearch"})
        with self.assertRaises(sync.SyncError):self.api.request("/movie/1","DELETE")

    def test_editor_refuses_non_tag_fields(self):
        with self.assertRaises(sync.SyncError):
            self.api.request("/movie/editor","PUT",{"movieIds":[1],"tags":[1],"applyTags":"add","monitored":True})

        with self.assertRaises(sync.SyncError):
            self.api.request("/movie/editor","PUT",{"movieIds":[1],"tags":[1],"applyTags":"replace"})

    def test_root_profile_single_library_convention(self):
        snap,_=self.plan();settings=sync.choose_settings(snap)
        self.assertEqual(settings["quality_profile_id"],7)
        self.assertEqual(settings["root_folder"],"/movies")

    def test_ambiguous_profile_stops_before_writes(self):
        self.fake.movies[1]["qualityProfileId"]=8
        with self.assertRaises(sync.SyncError):self.plan()
        self.assertEqual(self.fake.writes,[])

    def test_drift_stops_before_any_writes(self):
        snap,plan=self.plan();self.fake.movies[0]["tags"].append(10)
        with self.assertRaises(sync.SyncError):sync.apply_plan(self.api,self.catalog,snap,plan)
        self.assertEqual(self.fake.writes,[])

    def test_duplicate_existing_imdb_skip(self):
        self.fake.movies.append({**copy.deepcopy(self.fake.movies[0]),"id":99})
        _,plan=self.plan()
        self.assertTrue(any(r["imdb_id"]=="tt1" for r in plan["unresolved"]))

    def test_duplicate_managed_tag_stops(self):
        self.fake.tags.append({"id":99,"label":sync.MEMBERSHIP})
        with self.assertRaises(sync.SyncError):self.plan()

    def test_tags_created_only_if_needed(self):
        self.fake.tags=[t for t in self.fake.tags if t["label"] not in sync.MANAGED]
        result=self.apply()
        self.assertEqual({t["label"] for t in result["tags_created"]},
                         {"movie-list","ml-below-225","ml-225-249","ml-300-399"})

    def test_ambiguous_add_response_resumable_without_duplicate(self):
        self.fake.fail_after_add=True
        with self.assertRaises(radarr.RadarrError):self.apply()
        self.fake.calls=[];self.apply()
        self.assertEqual(sum(m["imdbId"]=="tt2" for m in self.fake.movies),1)
        self.assertFalse(any(path=="/movie" for path,_,_ in self.fake.writes))

    def test_private_reports_and_overlap_lock(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"report.json";p.write_text("{}");p.chmod(0o644)
            sync.write_private(p,{"ok":True});self.assertEqual(p.stat().st_mode&0o777,0o600)
            with sync.locked(Path(td)):
                with self.assertRaises(sync.SyncError):
                    with sync.locked(Path(td)):pass

    def test_current_frozen_387_have_one_score_band(self):
        catalog=load_catalog()
        rows=[r for r in catalog.values() if r["qualified"]]
        self.assertEqual(len(rows),387)
        self.assertTrue(all(sync.score_band(r["overall_score"]) in sync.BANDS for r in rows))
        self.assertEqual(sum(sum(sync.score_band(r["overall_score"])==b for r in rows) for b in sync.BANDS),387)

    def test_real_http_serialization_and_no_acquisition(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        fake=self.fake
        class Handler(BaseHTTPRequestHandler):
            def respond(self):
                if self.command=="GET":payload=None
                else:payload=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.headers.get("X-Api-Key")!="synthetic-key":
                    self.send_error(401);return
                result=fake.request(self.path.removeprefix("/api/v3"),self.command,payload)
                raw=json.dumps(result).encode()
                self.send_response(200);self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
            do_GET=do_POST=do_PUT=respond
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            self.transport.stop()
            with patch.object(radarr,"RADARR_URL",f"http://127.0.0.1:{server.server_port}"), \
                 patch.object(radarr,"RADARR_API_KEY","synthetic-key"):
                result=self.apply()
            self.assertEqual(result["movies_added"],1)
            self.assertEqual(result["acquisition_commands"],0)
        finally:
            server.shutdown();server.server_close();thread.join()
            self.transport.start()

    def test_corrupt_snapshot_fails_before_plan(self):
        with patch.object(radarr,"_request",return_value=None):
            with self.assertRaises(sync.SyncError):self.api.snapshot()


if __name__=="__main__":unittest.main()
