"""Synthetic 87-film cohort; no user IDs or titles in public tests."""
import copy
import json
import base64
import unittest
from unittest.mock import patch

import radarr_client
import radarr_watched_import as cohort
import radarr_watched_tags as watched
import radarr_movie_list_sync as sync
from test_radarr_movie_list_sync import Fake, movie


def fixture():
    fake=Fake()
    old=[movie("tt800000000000",1,[9])]
    imported=[movie("tt"+str(900000000000+i),100+i,[1,4,9]) for i in range(235)]
    for row in imported:
        row["added"]="2026-10-14T12:47:00Z";row["monitored"]=True
    fake.movies=old+copy.deepcopy(imported)
    data={"schema_version":1,"purpose":"Synthetic cohort","target_count":87,
          "match_policy":"Exact IMDb ID only","desired_radarr_state":{"watched_tag":True,"monitored":False},
          "imdb_ids":[row["imdbId"] for row in imported[:87]]}
    catalog={row["imdbId"]:{"qualified":True,"overall_score":250} for row in imported}
    return fake,data,{"movies":old},{"movies":old+imported},catalog


class CohortTests(unittest.TestCase):
    def setUp(self):
        self.fake,self.data,self.old,self.imported,self.catalog=fixture()
        original=self.fake.request
        def request(path,method="GET",payload=None):
            if path=="/movie/editor" and method=="PUT" and set(payload)=={"movieIds","monitored"}:
                self.assertIs(payload["monitored"],False)
                self.fake.calls.append((path,method,copy.deepcopy(payload)))
                for row in self.fake.movies:
                    if row["id"] in payload["movieIds"]:row["monitored"]=False
                return copy.deepcopy(self.fake.movies)
            return original(path,method,payload)
        self.transport=patch.object(radarr_client,"_request",side_effect=request)
        self.transport.start();self.addCleanup(self.transport.stop)
        self.api=cohort.API()

    def run_apply(self):
        before=self.api.snapshot()
        plan=cohort.verify_import(before,self.data,self.old,self.imported,self.catalog)
        after,post,result=cohort.apply(self.api,before,self.data,self.old,self.imported,self.catalog,plan)
        return before,after,post,result

    def test_verified_import_applies_only_targets_and_preserves_fields(self):
        before,after,post,result=self.run_apply()
        self.assertEqual((result["tagged"],result["unmonitored"]),(87,87))
        self.assertEqual((post["to_tag"],post["to_unmonitor"]),(0,0))
        cohort.verify_state(before,after,set(post["target_movie_ids"]),result["tag_id"])
        self.assertEqual([(p,m,set(body)) for p,m,body in self.fake.writes],
                         [("/tag","POST",{"label"}),("/movie/editor","PUT",{"movieIds","tags","applyTags"}),
                          ("/movie/editor","PUT",{"movieIds","monitored"})])
        self.assertEqual(before["movies"][0],after["movies"][0])
        self.assertEqual(before["movies"][100],after["movies"][100])

    def test_idempotence(self):
        self.run_apply();self.fake.calls.clear()
        _,_,_,result=self.run_apply()
        self.assertEqual((result["tagged"],result["unmonitored"]),(0,0))
        self.assertEqual(self.fake.writes,[])

    def test_existing_watched_unmonitored_skipped(self):
        self.fake.tags.append({"id":11,"label":"watched"})
        self.fake.movies[1]["tags"].append(11);self.fake.movies[1]["monitored"]=False
        _,_,_,result=self.run_apply()
        self.assertEqual((result["tagged"],result["unmonitored"]),(86,86))

    def test_missing_and_duplicate_exact_targets_block(self):
        for mode in ("missing","duplicate"):
            fake,data,old,imported,catalog=fixture()
            if mode=="missing":fake.movies=fake.movies[2:]
            else:
                row=copy.deepcopy(fake.movies[1]);row["id"]=999;fake.movies.append(row)
            snap={"movies":fake.movies,"tags":fake.tags}
            with self.subTest(mode=mode),self.assertRaises(watched.WatchedError):
                cohort.verify_import(snap,data,old,imported,catalog)
        self.assertEqual(self.fake.writes,[])

    def test_wrong_cohort_count_state_or_duplicates_rejected(self):
        cases=[]
        d=copy.deepcopy(self.data);d["target_count"]=86;cases.append(d)
        d=copy.deepcopy(self.data);d["desired_radarr_state"]["monitored"]=True;cases.append(d)
        d=copy.deepcopy(self.data);d["imdb_ids"][0]=d["imdb_ids"][1];cases.append(d)
        for data in cases:
            with self.assertRaises((cohort.CohortError,watched.WatchedError)):
                cohort.plain_manifest(data)

    def test_existing_pre_import_movie_cannot_be_substituted(self):
        self.old["movies"].append(copy.deepcopy(self.fake.movies[1]))
        with self.assertRaises(cohort.CohortError):self.run_apply()
        self.assertEqual(self.fake.writes,[])

    def test_import_identity_mismatch_rejected(self):
        self.imported["movies"][1]["tmdbId"]=999
        with self.assertRaises(cohort.CohortError):self.run_apply()
        self.assertEqual(self.fake.writes,[])

    def test_missing_membership_band_or_qualification_blocks(self):
        for field in ("membership","band","qualification"):
            snap=self.api.snapshot();catalog=copy.deepcopy(self.catalog)
            if field=="membership":snap["movies"][1]["tags"].remove(1)
            elif field=="band":snap["movies"][1]["tags"].remove(4)
            else:catalog[self.data["imdb_ids"][0]]["qualified"]=False
            with self.subTest(field=field),self.assertRaises(cohort.CohortError):
                cohort.verify_import(snap,self.data,self.old,self.imported,catalog)
        self.assertEqual(self.fake.writes,[])

    def test_unmonitor_rejects_non_target_and_already_false(self):
        self.api.allowed_movie_ids={100}
        rows={m["id"]:m for m in self.api.snapshot()["movies"]}
        with self.assertRaises(cohort.CohortError):self.api.turn_off([101],rows)
        self.fake.movies[1]["monitored"]=False
        with self.assertRaises(cohort.CohortError):self.api.turn_off([100],rows)
        self.assertEqual(self.fake.writes,[])

    def test_unmonitor_rechecks_full_guard(self):
        self.api.allowed_movie_ids={100}
        rows={m["id"]:m for m in self.api.snapshot()["movies"]}
        self.fake.movies[1]["qualityProfileId"]=8
        with self.assertRaises(cohort.CohortError):self.api.turn_off([100],rows)
        self.assertEqual(self.fake.writes,[])

    def test_generic_wrappers_still_refuse_monitoring_mutation(self):
        for api in (self.api,sync.API(),watched.API()):
            with self.assertRaises((sync.SyncError,watched.WatchedError)):
                api.request("/movie/editor","PUT",{"movieIds":[100],"monitored":False})
        self.assertEqual(self.fake.writes,[])

    def test_post_guard_rejects_metadata_file_tag_or_non_target_mutation(self):
        before,after,post,result=self.run_apply()
        for field in ("overview","movieFileId","qualityProfileId","tags","non_target"):
            changed=copy.deepcopy(after)
            if field=="non_target":changed["movies"][0]["monitored"]=True
            elif field=="tags":changed["movies"][1]["tags"].remove(9)
            else:changed["movies"][1][field]="changed"
            with self.subTest(field=field),self.assertRaises(watched.WatchedError):
                cohort.verify_state(before,changed,set(post["target_movie_ids"]),result["tag_id"])

    def test_canonical_merge_deduplicates_preserves_metadata_and_uses_sha(self):
        canonical={"schema_version":1,"purpose":"Prior user annotations","target_count":2,
                   "match_policy":"Exact IMDb ID only","imdb_ids":[self.data["imdb_ids"][0],"tt800000000000"]}
        calls=[]
        class GitHub:
            def request(inner,path,method="GET",payload=None):
                calls.append((path,method,payload))
                if "/contents/" not in path:return {"private":True}
                if method=="PUT":
                    inner.current=json.loads(base64.b64decode(payload["content"]))
                    return {}
                data=getattr(inner,"current",canonical)
                return {"content":base64.b64encode(json.dumps(data).encode()).decode(),"sha":"old-blob"}
        with patch.object(cohort.export,"config",return_value=("kolorifer/radarr-state","synthetic")), \
             patch.object(cohort.export,"GitHub",return_value=GitHub()):
            result=cohort.merge_canonical(self.data)
        self.assertEqual(result,{"prior_count":2,"cohort_count":87,"overlap_count":1,"result_count":88})
        body=next(body for _,method,body in calls if method=="PUT")
        self.assertEqual(body["sha"],"old-blob")
        updated=json.loads(base64.b64decode(body["content"]))
        self.assertEqual(updated["purpose"],canonical["purpose"])
        self.assertNotIn("desired_radarr_state",updated)
        self.assertEqual(len(set(updated["imdb_ids"])),88)

    def test_canonical_merge_refuses_public_repository(self):
        class Public:
            def request(inner,*args,**kwargs):return {"private":False}
        with patch.object(cohort.export,"config",return_value=("kolorifer/radarr-state","synthetic")), \
             patch.object(cohort.export,"GitHub",return_value=Public()):
            with self.assertRaises(cohort.CohortError):cohort.merge_canonical(self.data)

    def test_partial_monitor_timeout_is_resumable(self):
        transport=radarr_client._request
        def fail(path,method="GET",payload=None):
            result=transport(path,method,payload)
            if payload and set(payload)=={"movieIds","monitored"}:
                raise radarr_client.RadarrError("Synthetic timeout")
            return result
        with patch.object(radarr_client,"_request",side_effect=fail):
            with self.assertRaises(radarr_client.RadarrError):self.run_apply()
        self.fake.calls.clear()
        _,_,_,result=self.run_apply()
        self.assertEqual((result["tagged"],result["unmonitored"]),(0,0))
        self.assertEqual(self.fake.writes,[])


if __name__=="__main__":unittest.main()
