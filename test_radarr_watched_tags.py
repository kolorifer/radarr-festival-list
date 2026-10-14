"""Synthetic watched manifest; never includes the user's private target IDs."""
import copy
import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import radarr_watched_tags as watched
from test_radarr_movie_list_sync import Fake
import radarr_client


def manifest(ids=("tt1", "tt3")):
    return {"schema_version":1,"purpose":"Synthetic watched test","target_count":len(ids),
            "match_policy":"Exact IMDb ID only","imdb_ids":list(ids)}


class WatchedTests(unittest.TestCase):
    def setUp(self):
        self.fake = Fake()
        self.transport = patch.object(radarr_client, "_request", side_effect=self.fake.request)
        self.transport.start(); self.addCleanup(self.transport.stop)
        self.api = watched.API()
        self.data = manifest()

    def apply(self):
        before = self.api.snapshot()
        expected = watched.plan(before, self.data)
        after, post, result = watched.apply(self.api, before, self.data, expected)
        return before, after, post, result

    def test_additive_only_preserves_all_movie_fields(self):
        before, after, post, result = self.apply()
        self.assertEqual(result["tagged"], 2)
        self.assertEqual(post["to_tag"], 0)
        watched.verify_preserved(before, after, {1,3}, result["tag_id"])
        self.assertEqual([(p,m) for p,m,_ in self.fake.writes],
                         [("/tag","POST"),("/movie/editor","PUT")])
        body = self.fake.writes[-1][2]
        self.assertEqual(set(body), {"movieIds","tags","applyTags"})
        self.assertEqual(body["applyTags"], "add")

    def test_repeat_is_zero_writes_and_reuses_tag(self):
        self.apply(); self.fake.calls.clear()
        _, _, _, result = self.apply()
        self.assertEqual(result["tag_action"], "reuse")
        self.assertEqual(result["tagged"], 0)
        self.assertEqual(self.fake.writes, [])

    def test_existing_watched_non_target_is_preserved(self):
        self.fake.tags.append({"id":11,"label":"watched"})
        self.fake.movies[-1]["tags"].append(11)
        before,after,_,result=self.apply()
        self.assertEqual(before["movies"][-1],after["movies"][-1])
        self.assertEqual(result["tag_action"], "reuse")

    def test_already_watched_target_is_skipped(self):
        self.fake.tags.append({"id":11,"label":"watched"})
        self.fake.movies[0]["tags"].append(11)
        _,_,_,result=self.apply()
        self.assertEqual(result["already_tagged"],1)
        self.assertEqual(result["tagged"],1)

    def test_missing_exact_id_blocks_before_every_write(self):
        self.data=manifest(("tt999",))
        with self.assertRaises(watched.WatchedError):self.apply()
        self.assertEqual(self.fake.writes,[])

    def test_title_match_cannot_substitute_for_imdb(self):
        self.fake.movies[0]["title"]="tt999"
        self.data=manifest(("tt999",))
        with self.assertRaises(watched.WatchedError):self.apply()
        self.assertEqual(self.fake.writes,[])

    def test_duplicate_target_mapping_blocks_before_write(self):
        duplicate=copy.deepcopy(self.fake.movies[0]);duplicate["id"]=99
        self.fake.movies.append(duplicate)
        with self.assertRaises(watched.WatchedError):self.apply()
        self.assertEqual(self.fake.writes,[])

    def test_manifest_duplicate_count_and_id_rejected(self):
        bad=[]
        m=manifest();m["target_count"]=3;bad.append(m)
        bad.append(manifest(("tt1","tt1")))
        bad.append(manifest(("not-an-imdb-id",)))
        m=manifest();m["extra"]="private";bad.append(m)
        m=manifest();m["match_policy"]="fuzzy title";bad.append(m)
        for data in bad:
            with self.subTest(data=data),self.assertRaises(watched.WatchedError):
                watched.validate_manifest(data)

    def test_duplicate_watched_tags_block(self):
        self.fake.tags.extend([{"id":11,"label":"watched"},{"id":12,"label":"watched"}])
        with self.assertRaises(watched.WatchedError):self.apply()
        self.assertEqual(self.fake.writes,[])

    def test_stale_dry_run_blocks_before_write(self):
        before=self.api.snapshot();expected=watched.plan(before,self.data)
        self.fake.movies[0]["monitored"]=not self.fake.movies[0]["monitored"]
        with self.assertRaises(watched.WatchedError):
            watched.apply(self.api,self.api.snapshot(),self.data,expected)
        self.assertEqual(self.fake.writes,[])

    def test_last_moment_change_blocks_before_write(self):
        before=self.api.snapshot();expected=watched.plan(before,self.data)
        self.fake.movies[0]["tags"].append(10)
        with self.assertRaises(watched.WatchedError):
            watched.apply(self.api,before,self.data,expected)
        self.assertEqual(self.fake.writes,[])

    def test_all_non_tag_changes_detected(self):
        before,after,_,result=self.apply()
        for field in ("monitored","movieFileId","path","rootFolderPath","qualityProfileId","overview"):
            changed=copy.deepcopy(after)
            changed["movies"][0][field]="unexpected"
            with self.subTest(field=field),self.assertRaises(watched.WatchedError):
                watched.verify_preserved(before,changed,{1,3},result["tag_id"])

    def test_unrelated_tag_changes_detected(self):
        before,after,_,result=self.apply()
        after["movies"][0]["tags"].remove(9)
        with self.assertRaises(watched.WatchedError):
            watched.verify_preserved(before,after,{1,3},result["tag_id"])

    def test_forbidden_write_surface(self):
        for path,method,payload in [("/movie","POST",{}),("/command","POST",{}),
                                   ("/movie/1","DELETE",None),("/movie/editor","PUT",
                                    {"movieIds":[1],"tags":[],"applyTags":"replace"}),
                                   ("/tag","POST",{"label":"other"})]:
            with self.subTest(path=path),self.assertRaises(watched.WatchedError):
                self.api.request(path,method,payload)
        self.assertEqual(self.fake.writes,[])

    def test_editor_cannot_touch_non_target_or_other_tag(self):
        self.api.allowed_movie_ids={1};self.api.watched_tag_id=11
        for body in [{"movieIds":[4],"tags":[11],"applyTags":"add"},
                     {"movieIds":[1],"tags":[12],"applyTags":"add"}]:
            with self.assertRaises(watched.WatchedError):
                self.api.request("/movie/editor","PUT",body)
        self.assertEqual(self.fake.writes,[])

    def test_cli_recorded_plan_is_read_before_replacing_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)
            expected=watched.plan(self.api.snapshot(),self.data)
            expected["snapshot_digest"]="stale"
            path=state/"dry-run.json";path.write_text(json.dumps(expected))
            with patch.object(watched,"STATE",state),patch.object(watched,"SYNC_STATE",state/"lockdir"), \
                 patch.object(watched,"fetch_manifest",return_value=self.data), \
                 patch("sys.stdout",new=io.StringIO()),patch("sys.stderr",new=io.StringIO()):
                self.assertEqual(watched.main(["--apply","--expect-plan",str(path)]),1)
        self.assertEqual(self.fake.writes,[])

    def test_publish_failure_does_not_repeat_completed_tagging(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);path=state/"dry-run.json"
            with patch.object(watched,"STATE",state),patch.object(watched,"SYNC_STATE",state/"lockdir"), \
                 patch.object(watched,"fetch_manifest",return_value=self.data), \
                 patch("sys.stdout",new=io.StringIO()),patch("sys.stderr",new=io.StringIO()):
                self.assertEqual(watched.main([]),0)
                with patch.object(watched.export,"refresh",side_effect=RuntimeError("PRIVATE")):
                    self.assertEqual(watched.main(["--apply","--expect-plan",str(path)]),1)
                self.assertEqual(json.loads((state/"latest.json").read_text())["result"]["remaining"],0)
                self.fake.calls.clear()
                self.assertEqual(watched.main([]),0)
                with patch.object(watched.export,"refresh",return_value={"status":"published"}) as publish:
                    self.assertEqual(watched.main(["--apply","--expect-plan",str(path)]),0)
                    publish.assert_called_once()
                self.assertEqual(self.fake.writes,[])

    def test_partial_timeout_resumes_without_duplicate_changes(self):
        original=self.fake.request
        def fail(path,method="GET",payload=None):
            response=original(path,method,payload)
            if method=="PUT":raise radarr_client.RadarrError("Synthetic timeout")
            return response
        with patch.object(radarr_client,"_request",side_effect=fail):
            with self.assertRaises(radarr_client.RadarrError):self.apply()
        self.fake.calls.clear()
        _,_,_,result=self.apply()
        self.assertEqual(result["tagged"],0)
        self.assertEqual(self.fake.writes,[])


if __name__=="__main__":
    unittest.main()
