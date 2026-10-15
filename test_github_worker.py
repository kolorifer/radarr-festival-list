"""Offline contract tests: no GitHub, Codex, Radarr, seedbox or media calls."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from automation import github_worker as w

TASK = """SUPERVISOR_TASK: 1
STATE: READY_FOR_CODEX
GOAL: Build the worker
ACCEPTANCE_CRITERIA:
- Test it
AUTHORIZATION:
- Repository changes and PR
FORBIDDEN:
- Media mutations
INSTRUCTIONS:
- Inspect partial work
"""
ISSUE = {"state": "open", "user": {"login": "owner"}, "body": "Original goal and safety criteria"}


def comment(body=TASK, number=1, login="owner"):
    return {"id": number, "body": body, "user": {"login": login}}


class FakeRunner(w.Runner):
    def __init__(self, root, **options):
        args = argparse.Namespace(repo=root, issue=11, github_repo="owner/project", base="main",
                                  sessions=root / "sessions", interval=10, once=True, dry_run=False)
        vars(args).update(options)
        self.calls = []
        self.messages = [comment()]
        self.refs = []
        self.dirty = False
        self.origin = "https://github.com/owner/project.git"
        self.claim_error = False
        self.crash = False
        super().__init__(args)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def git(self, *args):
        if args == ("rev-parse", "--git-common-dir"):
            return ".git"
        if args == ("status", "--porcelain"):
            return "dirty" if self.dirty else ""
        if args == ("remote", "get-url", "origin"):
            return self.origin
        if args == ("rev-parse", "HEAD"):
            return "abc123"
        return "main: abc123\n"

    def api(self, endpoint, **data):
        self.calls.append((endpoint, data))
        if endpoint == "user":
            return {"login": "worker"}
        if "/matching-refs/" in endpoint:
            return self.refs
        if endpoint.endswith("/git/refs"):
            # Consumption must already be persisted BEFORE a possibly ambiguous claim.
            assert 1 in json.loads(self.state_file.read_text())["consumed"]
            if self.claim_error:
                raise subprocess.CalledProcessError(422, ["gh"])
            self.refs.append({"ref": data["ref"]})
            return {"ref": data["ref"]}
        return ISSUE

    def comments(self):
        return self.messages

    def post(self, body):
        self.calls.append(("post", body))

    def execute(self, issue, task, n):
        self.calls.append(("execute", n))
        if self.crash:
            raise SystemExit("interrupted")


class ProtocolTests(unittest.TestCase):
    def test_newest_directive_and_untrusted_comment(self):
        newer = TASK.replace("TASK: 1", "TASK: 2")
        result = w.choose_task([comment(), comment(newer, 2), comment(TASK, 3, "stranger")], "owner", set())
        self.assertEqual(w.task_number(result["body"]), 2)

    def test_consumed_latest_does_not_fall_back_to_older_task(self):
        self.assertIsNone(w.choose_task([comment(), comment(TASK.replace("TASK: 1", "TASK: 2"), 2)], "owner", {2}))

    def test_missing_authorization_rejected(self):
        with self.assertRaises(w.Stop):
            w.choose_task([comment(TASK.replace("AUTHORIZATION:", "OTHER:"))], "owner", set())

    def test_empty_authorization_cannot_borrow_next_heading(self):
        with self.assertRaises(w.Stop):
            w.choose_task([comment(TASK.replace("- Repository changes and PR", ""))], "owner", set())

    def test_remote_results_and_running_never_repeat(self):
        messages = [comment("SUPERVISOR_TASK: 1\nSTATE: RUNNING", login="worker"),
                    comment("WORKER_RESULT: 2\nSTATE: FAILED", 2, "worker"),
                    comment("WORKER_RESULT: 3\nSTATE: READY_FOR_REVIEW", 3, "stranger")]
        self.assertEqual(w.remote_consumed(messages, {"owner", "worker"}), {1, 2})

    def test_pause_is_not_a_new_supervisor_directive_with_same_login(self):
        self.assertEqual(w.choose_task([comment(), comment("SUPERVISOR_TASK: 1\nSTATE: PAUSED_QUOTA", 2)], "owner", set())["id"], 1)

    def test_prompt_from_sample_has_no_other_conversation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("Use unit tests")
            (root / "docs").mkdir()
            (root / "docs/CODEX_TASK.md").write_text("UNRELATED MEDIA CLEANUP")
            prompt = w.prompt_for(ISSUE, comment(), root, "clean main abc", "task-branch")
        for expected in ("Original goal", TASK, "Use unit tests", "clean main abc", "NOT authorization"):
            self.assertIn(expected, prompt)
        self.assertNotIn("UNRELATED MEDIA CLEANUP", prompt)

    def test_exec_is_fresh_and_pins_model_medium_and_sandbox(self):
        cmd = w.codex_command(Path("repo"), Path("output"), Path("schema"))
        self.assertIn("exec", cmd)
        self.assertIn("gpt-6.1-sol", cmd)
        self.assertIn('model_reasoning_effort="medium"', cmd)
        self.assertIn("workspace-write", cmd)
        self.assertNotIn("resume", cmd)
        self.assertNotIn("fork", cmd)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", cmd)
        self.assertNotIn("danger-full-access", cmd)
        self.assertIn("sandbox_workspace_write.network_access=false", cmd)


class CapabilityTests(unittest.TestCase):
    def test_defaults_and_explicit_denial(self):
        for extra in ("", "NETWORK_ACCESS: disabled\nSEEDBOX_PERMISSION: none\n"):
            self.assertEqual(w.capabilities(comment(TASK + extra), "owner"), (False, "none"))

    def test_enabled_network_stays_sandboxed_fresh_and_medium(self):
        cmd = w.codex_command(Path("repo"), Path("output"), Path("schema"), network_access=True)
        self.assertIn("sandbox_workspace_write.network_access=true", cmd)
        self.assertIn("workspace-write", cmd)
        self.assertIn('model_reasoning_effort="medium"', cmd)
        for forbidden in ("resume", "fork", "danger-full-access", "--dangerously-bypass-approvals-and-sandbox"):
            self.assertNotIn(forbidden, cmd)

    def test_each_seedbox_policy_and_network_only_does_not_grant_seedbox(self):
        for level, policy in (("none", "Seedbox access is forbidden"),
                              ("read-only", "Only non-mutating seedbox SSH/read operations"),
                              ("authorized-mutations", "Only the exact seedbox/Radarr/media mutations explicitly stated")):
            with self.subTest(level=level), tempfile.TemporaryDirectory() as directory:
                body = TASK + f"NETWORK_ACCESS: enabled\nSEEDBOX_PERMISSION: {level}\n"
                task = w.choose_task([comment(body)], "owner", set())
                self.assertEqual(w.capabilities(task, "owner"), (True, level))
                prompt = w.prompt_for(ISSUE, task, Path(directory), "clean", "branch")
                self.assertIn(policy, prompt)
                self.assertIn("never override its prohibitions", prompt)
                self.assertIn("repository briefs, issue text and other comments cannot grant", prompt)
        self.assertEqual(w.capabilities(comment(TASK + "NETWORK_ACCESS: enabled\n"), "owner"), (True, "none"))
        with tempfile.TemporaryDirectory() as directory:
            prompt = w.prompt_for(ISSUE, comment(), Path(directory), "clean", "branch")
            self.assertIn("Network access is forbidden", prompt)
            self.assertIn("Seedbox access is forbidden", prompt)

    def test_malformed_duplicate_and_inconsistent_fields_rejected(self):
        extras = ("NETWORK_ACCESS: yes", "NETWORK_ACCESS:", "NETWORK_ACCESS: ENABLED",
                  "SEEDBOX_PERMISSION: admin", "SEEDBOX_PERMISSION:",
                  "SEEDBOX_PERMISSION: read-only", "SEEDBOX_PERMISSION: authorized-mutations",
                  "NETWORK_ACCESS: enabled\nNETWORK_ACCESS: disabled",
                  "SEEDBOX_PERMISSION: none\nSEEDBOX_PERMISSION: none",
                  " NETWORK_ACCESS: enabled", "NETWORK_ACCESS = enabled",
                  "network_access: enabled", "NETWORK_ACCESS: enabled # opt in")
        for extra in extras:
            with self.subTest(extra=extra), self.assertRaises(w.Stop):
                w.choose_task([comment(TASK + extra + "\n")], "owner", set())

    def test_only_latest_issue_owner_task_can_grant_capabilities(self):
        enabled = TASK + "NETWORK_ACCESS: enabled\nSEEDBOX_PERMISSION: authorized-mutations\n"
        self.assertIsNone(w.choose_task([comment(enabled, login="worker")], "owner", set()))
        chosen = w.choose_task([comment(enabled), comment(TASK, 2), comment(enabled, 3, "worker")], "owner", set())
        self.assertEqual(w.capabilities(chosen, "owner"), (False, "none"))
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(w.Stop):
            w.prompt_for(ISSUE, comment(enabled, login="worker"), Path(directory), "clean", "branch")


class QuotaTests(unittest.TestCase):
    now = 1800000000

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def event(self, used=84, stamp=None, reset=None, minutes=300):
        return {"type": "event_msg", "timestamp": w.dt.datetime.fromtimestamp(
            self.now - 10 if stamp is None else stamp, w.dt.timezone.utc).isoformat(),
            "payload": {"type": "token_count", "rate_limits": {"primary": {
                "used_percent": used, "window_minutes": minutes,
                "resets_at": self.now + 1000 if reset is None else reset}}}}

    def write(self, events, name="quota.jsonl"):
        (self.root / name).write_text("\n".join(json.dumps(e) for e in events) + "\n{truncated")

    def test_synthetic_remaining_thresholds(self):
        for used, remaining in ((84, 16), (85, 15), (100, 0), (0, 100)):
            self.write([self.event(used)])
            self.assertEqual(w.quota_remaining(self.root, self.now), remaining)

    def test_latest_timestamp_across_files_not_file_mtime(self):
        self.write([self.event(90, self.now - 1)], "a.jsonl")
        self.write([self.event(20, self.now - 20)], "b.jsonl")
        self.assertEqual(w.quota_remaining(self.root, self.now), 10)

    def test_context_usage_is_ignored(self):
        self.write([{"type": "turn_context", "payload": {"model_context_window": 999999}}, self.event(10)])
        self.assertEqual(w.quota_remaining(self.root, self.now), 90)

    def test_unusable_telemetry_fails_closed(self):
        for events in ([], [self.event(minutes=10080)], [self.event(reset=self.now)],
                       [self.event(stamp=self.now - 18001)], [self.event(used=float("nan"))],
                       [self.event(used=-1)], [self.event(stamp=self.now + 100)]):
            self.write(events)
            with self.assertRaises(w.Stop):
                w.quota_remaining(self.root, self.now)

    def test_newest_expired_record_does_not_fall_back(self):
        self.write([self.event(stamp=self.now - 20), self.event(stamp=self.now - 1, reset=self.now)])
        with self.assertRaises(w.Stop):
            w.quota_remaining(self.root, self.now)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runner = FakeRunner(Path(self.temp.name))
        self.quota = patch.object(w, "quota_remaining", return_value=80)
        self.quota.start()
        self.addCleanup(self.quota.stop)

    def test_claim_prompt_and_launch_once_across_restart(self):
        self.runner.start()
        self.assertEqual(sum(c[0] == "execute" for c in self.runner.calls), 1)
        running = [c for c in self.runner.calls if c[0] == "post"][0][1]
        self.assertIn("STATE: RUNNING", running)
        restarted = FakeRunner(self.runner.repo)
        restarted.start()
        self.assertFalse(any(c[0] == "execute" for c in restarted.calls))

    def test_crash_after_claim_never_reexecutes(self):
        self.runner.crash = True
        with self.assertRaises(SystemExit):
            self.runner.start()
        restarted = FakeRunner(self.runner.repo)
        restarted.start()
        self.assertFalse(any(c[0] == "execute" for c in restarted.calls))

    def test_atomic_claim_conflict_does_not_launch(self):
        self.runner.claim_error = True
        self.runner.start()
        self.assertFalse(any(c[0] == "execute" for c in self.runner.calls))
        self.assertIn("NEEDS_USER", [c for c in self.runner.calls if c[0] == "post"][0][1])

    def test_remote_claim_blocks_run_without_local_journal(self):
        self.runner.refs = [{"ref": "refs/heads/automation/issue-11-claim-1"}]
        self.runner.start()
        self.assertFalse(any(c[0] == "execute" for c in self.runner.calls))

    def test_eighth_allowed_ninth_stops(self):
        for count, executes in ((7, True), (8, False)):
            self.runner.calls.clear()
            self.runner.refs = [{"ref": f"refs/heads/automation/issue-11-claim-{i}"} for i in range(2, count + 2)]
            self.runner.state["consumed"] = []
            self.runner.poll()
            self.assertEqual(any(c[0] == "execute" for c in self.runner.calls), executes)

    def test_quota_pause_not_consumed_and_retries_when_refreshed(self):
        with patch.object(w, "quota_remaining", return_value=15):
            self.runner.start()
            self.runner.poll()
        self.assertEqual(len([c for c in self.runner.calls if c[0] == "post"]), 1)
        self.assertIn("15%", [c for c in self.runner.calls if c[0] == "post"][0][1])
        self.assertEqual(self.runner.state["consumed"], [])
        self.runner.poll()
        self.assertTrue(any(c[0] == "execute" for c in self.runner.calls))

    def test_unknown_quota_needs_user(self):
        with patch.object(w, "quota_remaining", side_effect=w.Stop("missing telemetry")):
            self.runner.start()
        self.assertEqual(self.runner.state["consumed"], [])
        self.assertIn("NEEDS_USER", [c for c in self.runner.calls if c[0] == "post"][0][1])

    def test_enabled_capabilities_preserve_quota_and_duplicate_protection(self):
        self.runner.messages = [comment(TASK + "NETWORK_ACCESS: enabled\nSEEDBOX_PERMISSION: authorized-mutations\n")]
        with patch.object(w, "quota_remaining", return_value=15):
            self.runner.start()
        self.assertEqual(self.runner.state["consumed"], [])
        self.assertFalse(any(c[0] == "execute" for c in self.runner.calls))
        self.runner.poll()
        self.runner.poll()
        self.assertEqual(sum(c[0] == "execute" for c in self.runner.calls), 1)
        restarted = FakeRunner(self.runner.repo)
        restarted.messages = self.runner.messages
        restarted.start()
        self.assertFalse(any(c[0] == "execute" for c in restarted.calls))

    def test_dirty_tree_and_wrong_origin_stop_before_claim(self):
        self.runner.dirty = True
        with self.assertRaises(w.Stop):
            self.runner.start()
        self.runner.dirty = False
        self.runner.origin = "https://github.com/wrong/project.git"
        with self.assertRaises(w.Stop):
            self.runner.start()
        self.assertFalse(any(c[0].endswith("/git/refs") for c in self.runner.calls))

    def test_dry_run_is_read_only_and_prints_prompt_without_codex(self):
        self.runner.args.dry_run = True
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.runner.start()
        self.assertIn(TASK, output.getvalue())
        self.assertFalse(self.runner.state_file.exists())
        self.assertFalse((self.runner.state_dir / "runner.lock").exists())
        self.assertFalse(any(c[0] in ("post", "execute") or c[1] for c in self.runner.calls))

    def test_invalid_task_reports_needs_user_without_claim(self):
        self.runner.messages = [comment(TASK.replace("AUTHORIZATION:", "OTHER:"))]
        self.runner.start()
        self.assertIn("NEEDS_USER", [c for c in self.runner.calls if c[0] == "post"][0][1])
        self.assertFalse(any(c[0] == "execute" for c in self.runner.calls))

    def test_invalid_capability_stops_before_claim_or_worker(self):
        self.runner.messages = [comment(TASK + "NETWORK_ACCESS: unsupported\n")]
        with patch.object(w.subprocess, "run") as launch:
            self.runner.start()
        launch.assert_not_called()
        self.assertIn("NEEDS_USER", [c for c in self.runner.calls if c[0] == "post"][0][1])
        self.assertEqual(self.runner.state["consumed"], [])
        self.assertFalse(any(c[0] == "execute" or c[0].endswith("/git/refs") for c in self.runner.calls))

    def test_closed_and_done_issue_do_not_launch(self):
        self.runner.messages.append(comment("STATE: DONE", 2))
        self.runner.start()
        self.assertFalse(any(c[0] == "execute" for c in self.runner.calls))
        with patch.dict(ISSUE, state="closed"):
            self.runner.start()


class PublicationTests(unittest.TestCase):
    def test_worker_to_commit_push_pr_and_result_without_running_codex(self):
        for existing, network in ((False, False), (True, False), (True, True)):
            with tempfile.TemporaryDirectory() as directory:
                runner = FakeRunner(Path(directory))
                runner.lock_fd = 123
                actions = []
                original_git = runner.git

                def git(*args):
                    actions.append(("git", args))
                    return original_git(*args)

                def gh(*args):
                    actions.append(("gh", args))
                    if args[:2] == ("pr", "list"):
                        return json.dumps([{"url": "https://github.com/owner/project/pull/12"}] if existing else [])
                    return "https://github.com/owner/project/pull/12"

                def worker(command, **kwargs):
                    self.assertIn("exec", command)
                    self.assertIn(f"sandbox_workspace_write.network_access={str(network).lower()}", command)
                    self.assertEqual(kwargs["pass_fds"], (123,))
                    self.assertIn(TASK, kwargs["input"])
                    output = Path(command[command.index("--output-last-message") + 1])
                    output.write_text(json.dumps({"state": "READY_FOR_REVIEW", "tests": "24 tests passed",
                                                  "summary": "Implemented worker", "questions": "none"}))
                    return subprocess.CompletedProcess(command, 0)

                runner.git = git
                runner.gh = gh
                task = comment(TASK + ("NETWORK_ACCESS: enabled\nSEEDBOX_PERMISSION: read-only\n" if network else ""))
                with patch.object(w.subprocess, "run", side_effect=worker):
                    w.Runner.execute(runner, ISSUE, task, 1)
                self.assertTrue(any(a == ("git", ("push", "--set-upstream", "origin", runner.branch)) for a in actions))
                diff = next(i for i, a in enumerate(actions) if a == ("git", ("diff", "--cached")))
                commit = next(i for i, a in enumerate(actions) if a[0] == "git" and a[1][0] == "commit")
                self.assertLess(diff, commit)
                operation = "edit" if existing else "create"
                self.assertEqual(sum(a[0] == "gh" and a[1][:2] == ("pr", operation) for a in actions), 1)
                result = [a[1] for a in runner.calls if a[0] == "post"][-1]
                for expected in ("WORKER_RESULT: 1", "STATE: READY_FOR_REVIEW", "COMMIT: abc123",
                                 "PR: https://github.com/owner/project/pull/12", "TESTS: 24 tests passed"):
                    self.assertIn(expected, result)

    def test_blocked_worker_leaves_changes_for_review_without_publishing(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeRunner(Path(directory))
            runner.lock_fd = 123
            actions = []
            original_git = runner.git

            def git(*args):
                actions.append(args)
                return original_git(*args)

            def worker(command, **kwargs):
                output = Path(command[command.index("--output-last-message") + 1])
                output.write_text(json.dumps({"state": "NEEDS_USER", "tests": "not run",
                                              "summary": "Missing access", "questions": "Need credential"}))

            runner.git = git
            with patch.object(w.subprocess, "run", side_effect=worker):
                w.Runner.execute(runner, ISSUE, comment(), 1)
            self.assertFalse(any(a[0] in ("push", "commit", "add") for a in actions))
            self.assertIn("STATE: NEEDS_USER", [a[1] for a in runner.calls if a[0] == "post"][-1])


class LockTests(unittest.TestCase):
    def test_second_instance_excluded_and_stale_pid_file_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runner.lock"
            with w.lock(path):
                with self.assertRaises(w.Stop):
                    with w.lock(path):
                        self.fail("second instance acquired lock")
            path.write_text("999999")
            with w.lock(path):
                self.assertNotEqual(path.read_text(), "999999")

    def test_kernel_releases_lock_after_killed_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runner.lock"
            code = "import fcntl,sys,time; f=open(sys.argv[1],'a+'); fcntl.flock(f,fcntl.LOCK_EX); print('locked',flush=True); time.sleep(30)"
            child = subprocess.Popen([sys.executable, "-c", code, str(path)], stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(), "locked")
                with self.assertRaises(w.Stop):
                    with w.lock(path):
                        pass
            finally:
                child.kill()
                child.wait()
                child.stdout.close()
            with w.lock(path):
                pass


if __name__ == "__main__":
    unittest.main()
