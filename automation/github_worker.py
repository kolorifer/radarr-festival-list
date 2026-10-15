#!/usr/bin/env python3
"""Issue-driven fresh Codex workers. Standard library + git, gh and codex only."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

MODEL = "gpt-6.1-sol"
FIELDS = re.compile(r"^([A-Z_]+):[ \t]*(.*)$", re.M)


class Stop(RuntimeError):
    pass


def fields(body):
    return dict(FIELDS.findall(body))


def task_number(body):
    value = fields(body).get("SUPERVISOR_TASK", "")
    return int(value) if value.isdecimal() and int(value) > 0 else None


def choose_task(comments, supervisor, consumed):
    # A new comment for an old number cannot authorize another execution.
    tasks = [c for c in comments if c["user"]["login"] == supervisor
             and task_number(c["body"]) is not None
             and (fields(c["body"]).get("STATE") == "READY_FOR_CODEX"
                  or "GOAL" in fields(c["body"]))]
    if not tasks:
        return None
    latest = max(tasks, key=lambda c: c["id"])
    n = task_number(latest["body"])
    if n in consumed or fields(latest["body"]).get("STATE") != "READY_FOR_CODEX":
        return None
    headings = list(FIELDS.finditer(latest["body"]))
    sections = {match[1]: (match[2] + latest["body"][match.end():
                headings[i + 1].start() if i + 1 < len(headings) else len(latest["body"])])
                for i, match in enumerate(headings)}
    for section in ("GOAL", "ACCEPTANCE_CRITERIA", "AUTHORIZATION", "FORBIDDEN", "INSTRUCTIONS"):
        if not sections.get(section, "").strip():
            raise Stop(f"Task {n} has no {section}")
    return latest


def remote_consumed(comments, trusted):
    result = set()
    for c in comments:
        if c["user"]["login"] not in trusted:
            continue
        f = fields(c["body"])
        n = task_number(c["body"])
        if n and f.get("STATE") == "RUNNING":
            result.add(n)
        if f.get("WORKER_RESULT", "").isdecimal():
            result.add(int(f["WORKER_RESULT"]))
    return result


def quota_remaining(root, now=None):
    """Read only token_count quota metadata; never return conversation/context."""
    now = time.time() if now is None else now
    newest = None
    for path in Path(root).rglob("*.jsonl"):
        with path.open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                # Avoid parsing conversation/tool records at all.
                if '"token_count"' not in line:
                    continue
                try:
                    event = json.loads(line)
                    payload = event.get("payload") or {}
                    if event.get("type") != "event_msg" or payload.get("type") != "token_count":
                        continue
                    primary = (payload.get("rate_limits") or {}).get("primary") or {}
                    if primary.get("window_minutes") != 300:
                        continue
                    stamp = dt.datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")).timestamp()
                    used = float(primary["used_percent"])
                    reset = float(primary["resets_at"])
                    if not all(math.isfinite(v) for v in (stamp, used, reset)) or not 0 <= used <= 100:
                        continue
                    if stamp > now + 60:
                        continue
                    if newest is None or stamp > newest[0]:
                        newest = (stamp, used, reset)
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
    if newest is None or now - newest[0] > 5 * 3600 or newest[2] <= now:
        raise Stop("No current 5-hour quota telemetry; open a fresh authenticated Codex session to refresh it")
    return 100 - newest[1]


@contextlib.contextmanager
def lock(path):
    # Never unlink a flock inode: the kernel releases it even after SIGKILL.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stop("Another runner or its worker still holds the lock")
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        yield handle.fileno()


def save(path, data):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def prompt_for(issue, task, repo, git_state, branch):
    instructions = []
    for path in sorted(repo.rglob("AGENTS.md")):
        if not any(p.startswith(".") for p in path.relative_to(repo).parts):
            instructions.append(f"{path.relative_to(repo)}:\n{path.read_text()}")
    return f"""Fresh implementation worker. Do not resume/fork another Codex session or read prior conversation history.
Source of truth: the control issue and latest supervisor task below. Repository task briefs describe other work and are NOT authorization to perform it.
Stay strictly within AUTHORIZATION and FORBIDDEN. No Radarr, seedbox or media mutations. No ChatGPT Work. Do not install/start daemons.
Inspect current code and useful partial work. Implement and test only the assigned task. Inspect your diff before finishing.
The runner owns commit/push/PR/issue reporting on {branch}; do not perform Git publication or post comments yourself. Do not launch another worker or runner.
If blocked, return state NEEDS_USER with the reason. Otherwise return READY_FOR_REVIEW with actual tests and a concise summary. Do not claim unrun tests.

CONTROL ISSUE (goal, acceptance criteria and safety protocol):
{issue['body']}

LATEST SUPERVISOR TASK:
{task['body']}

REPOSITORY INSTRUCTIONS:
{chr(10).join(instructions)}

CURRENT GIT STATE:
{git_state}
"""


def codex_command(repo, output, schema, effort="medium"):
    return ["codex", "-c", 'approval_policy="never"', "exec", "--model", MODEL,
            "--sandbox", "workspace-write", "--config", f'model_reasoning_effort="{effort}"',
            "--cd", str(repo), "--output-schema", str(schema), "--output-last-message", str(output), "-"]


class Runner:
    def __init__(self, args):
        self.args = args
        self.repo = args.repo.resolve()
        self.branch = f"automation/issue-{args.issue}-worker"
        common = Path(self.git("rev-parse", "--git-common-dir").strip())
        self.state_dir = (self.repo / common).resolve() / "github-worker" / str(args.issue)
        self.state_file = self.state_dir / "state.json"
        self.state = {"consumed": [], "notifications": {}}
        self.lock_fd = None

    def run(self, command, **kwargs):
        return subprocess.run(command, cwd=self.repo, text=True, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs).stdout

    def git(self, *args):
        return self.run(["git", *args])

    def gh(self, *args):
        return self.run(["gh", *args])

    def api(self, endpoint, **data):
        command = ["api", endpoint]
        if data:
            command += ["--method", "POST", "--input", "-"]
        return json.loads(self.gh(*command) if not data else
                          self.run(["gh", *command], input=json.dumps(data)))

    def comments(self):
        pages = json.loads(self.gh("api", "--paginate", "--slurp",
                                  f"repos/{self.args.github_repo}/issues/{self.args.issue}/comments?per_page=100"))
        return [c for page in pages for c in page]

    def post(self, body):
        self.api(f"repos/{self.args.github_repo}/issues/{self.args.issue}/comments", body=body)

    def notify(self, n, state, reason):
        body = f"SUPERVISOR_TASK: {n}\nSTATE: {state}\nSUMMARY: {reason}"
        if self.state["notifications"].get(str(n)) != body:
            self.post(body)
            self.state["notifications"][str(n)] = body
            save(self.state_file, self.state)

    def poll(self):
        issue = self.api(f"repos/{self.args.github_repo}/issues/{self.args.issue}")
        if issue["state"] != "open":
            return
        comments = self.comments()
        login = self.api("user")["login"]
        trusted = {login, issue["user"]["login"]}
        # An explicit supervisor stop applies even while the issue stays open.
        trusted_comments = [c for c in comments if c["user"]["login"] in trusted]
        if trusted_comments and fields(max(trusted_comments, key=lambda c: c["id"])["body"]).get("STATE") == "DONE":
            return
        refs = self.api(f"repos/{self.args.github_repo}/git/matching-refs/heads/automation/issue-{self.args.issue}-claim-")
        claimed = {int(r["ref"].rsplit("-", 1)[1]) for r in refs
                   if r["ref"].rsplit("-", 1)[1].isdecimal()}
        consumed = set(self.state["consumed"]) | remote_consumed(comments, trusted) | claimed
        try:
            task = choose_task(comments, issue["user"]["login"], consumed)
        except Stop as exc:
            if self.args.dry_run:
                raise
            candidates = [c for c in comments if c["user"]["login"] == issue["user"]["login"]
                          and task_number(c["body"]) is not None
                          and fields(c["body"]).get("STATE") == "READY_FOR_CODEX"]
            self.notify(task_number(max(candidates, key=lambda c: c["id"])["body"]), "NEEDS_USER", str(exc))
            return
        if task is None:
            print("No unprocessed READY_FOR_CODEX task", flush=True)
            return
        n = task_number(task["body"])
        if self.git("status", "--porcelain").strip():
            raise Stop("Working tree is dirty; preserve/reconcile it before running")
        # gh must target the same repository as git push, even in dry-run.
        origin = self.git("remote", "get-url", "origin").strip()
        if origin not in (f"https://github.com/{self.args.github_repo}.git",
                          f"https://github.com/{self.args.github_repo}",
                          f"git@github.com:{self.args.github_repo}.git"):
            raise Stop("origin does not match --github-repo")
        if self.args.dry_run:
            print(prompt_for(issue, task, self.repo, self.git("status", "--short", "--branch"), self.branch))
            print("DRY RUN: no claim, journal, branch change, Codex or publication. Quota is checked on a real run.")
            return
        if len(consumed) >= 8:
            self.notify(n, "NEEDS_USER", "Maximum 8 worker iterations reached for this control issue; use supervisor review to resolve convergence")
            return
        try:
            remaining = quota_remaining(self.args.sessions)
        except Stop as exc:
            self.notify(n, "NEEDS_USER", str(exc))
            return
        if remaining <= 15:
            self.notify(n, "PAUSED_QUOTA", f"5-hour allowance remaining: {remaining:g}% (<=15%); task not consumed")
            return
        # Reserve locally before any network claim: ambiguous failures never rerun.
        self.state["consumed"] = sorted(consumed | {n})
        save(self.state_file, self.state)
        try:
            # GitHub ref creation is atomic, unlike posting an issue comment.
            # Never update/delete these refs. All machines use this same namespace.
            self.api(f"repos/{self.args.github_repo}/git/refs",
                     ref=f"refs/heads/automation/issue-{self.args.issue}-claim-{n}",
                     sha=self.git("rev-parse", "HEAD").strip())
        except subprocess.CalledProcessError:
            self.notify(n, "NEEDS_USER", "Atomic claim failed or already exists; task consumed locally, no worker launched. Inspect claim/API access; use a NEW task number")
            return
        self.post(f"SUPERVISOR_TASK: {n}\nSTATE: RUNNING\nBRANCH: {self.branch}")
        try:
            self.execute(issue, task, n)
        except Exception as exc:
            # Do not publish captured stderr, which may contain credentials.
            self.post(f"WORKER_RESULT: {n}\nSTATE: FAILED\nBRANCH: {self.branch}\nCOMMIT: {self.git('rev-parse', 'HEAD').strip()}\nPR: none\nTESTS: incomplete\nSUMMARY: {type(exc).__name__}; inspect private local logs and working tree. Task will not retry.\nQUESTIONS: supervisor must inspect and issue a new task number")
            raise

    def execute(self, issue, task, n):
        self.git("fetch", "origin")
        local = self.git("branch", "--list", self.branch).strip()
        remote = self.git("branch", "-r", "--list", f"origin/{self.branch}").strip()
        if local:
            self.git("switch", self.branch)
        elif remote:
            self.git("switch", "--track", "-c", self.branch, f"origin/{self.branch}")
        else:
            self.git("switch", "-c", self.branch, f"origin/{self.args.base}")
        if remote:
            # Fail rather than overwrite another publisher or silently omit work.
            self.git("merge", "--ff-only", f"origin/{self.branch}")
        effort = fields(task["body"]).get("REASONING", "medium").lower()
        if effort not in ("low", "medium", "high", "xhigh", "max"):
            raise Stop("Unsupported explicit REASONING override")
        output = self.state_dir / f"result-{n}.json"
        schema = self.state_dir / "result-schema.json"
        save(schema, {"type": "object", "properties": {
            "state": {"type": "string", "enum": ["READY_FOR_REVIEW", "NEEDS_USER"]},
            "tests": {"type": "string"}, "summary": {"type": "string"},
            "questions": {"type": "string"}},
            "required": ["state", "tests", "summary", "questions"], "additionalProperties": False})
        prompt = prompt_for(issue, task, self.repo,
                            self.git("status", "--short", "--branch") + self.git("log", "-3", "--oneline"), self.branch)
        with (self.state_dir / f"worker-{n}.log").open("w") as log:
            subprocess.run(codex_command(self.repo, output, schema, effort), input=prompt,
                           cwd=self.repo, text=True, check=True, stdout=log, stderr=log,
                           pass_fds=(self.lock_fd,))
        result = json.loads(output.read_text())
        if result["state"] not in ("READY_FOR_REVIEW", "NEEDS_USER"):
            raise Stop("Invalid worker result")
        pr = "none"
        if result["state"] == "READY_FOR_REVIEW":
            self.git("diff", "--check")
            self.git("add", "--all")
            # Preserve the actual inspected diff privately before committing.
            (self.state_dir / f"diff-{n}.patch").write_text(self.git("diff", "--cached"))
            if self.git("diff", "--cached", "--name-only").strip():
                self.git("commit", "-m", f"Implement supervisor task {n} for issue #{self.args.issue}")
            self.git("push", "--set-upstream", "origin", self.branch)
            prs = json.loads(self.gh("pr", "list", "--repo", self.args.github_repo,
                                     "--head", self.branch, "--base", self.args.base, "--json", "url"))
            body = f"Implements supervisor task {n} from #{self.args.issue}.\n\n{result['summary']}\n\nValidation: {result['tests']}\n\nControl issue: #{self.args.issue}"
            body_file = self.state_dir / "pr-body.md"
            body_file.write_text(body)
            if prs:
                pr = prs[0]["url"]
                self.gh("pr", "edit", pr, "--repo", self.args.github_repo, "--body-file", str(body_file))
            else:
                pr = self.gh("pr", "create", "--repo", self.args.github_repo, "--head", self.branch,
                             "--base", self.args.base, "--title", f"GitHub worker loop (issue #{self.args.issue})",
                             "--body-file", str(body_file)).strip()
        # Keep each protocol field on one line; arbitrary worker text cannot add states.
        clean = lambda s: " ".join(str(s).split())
        self.post(f"WORKER_RESULT: {n}\nSTATE: {result['state']}\nBRANCH: {self.branch}\nCOMMIT: {self.git('rev-parse', 'HEAD').strip()}\nPR: {pr}\nTESTS: {clean(result['tests'])}\nSUMMARY: {clean(result['summary'])}\nQUESTIONS: {clean(result['questions'])}")

    def start(self):
        if self.args.dry_run:
            # Read-only mode does not even create a lock/state directory.
            if self.state_file.exists():
                self.state = json.loads(self.state_file.read_text())
            self.poll()
            return
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        with lock(self.state_dir / "runner.lock") as self.lock_fd:
            if self.state_file.exists():
                self.state = json.loads(self.state_file.read_text())
            while True:
                self.poll()
                if self.args.once:
                    return
                time.sleep(self.args.interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--github-repo", default="kolorifer/radarr-festival-list")
    parser.add_argument("--issue", type=int, default=11)
    parser.add_argument("--base", default="main")
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex/sessions")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.issue < 1 or args.interval < 10 or not re.fullmatch(r"[\w.-]+/[\w.-]+", args.github_repo):
        parser.error("invalid issue, interval (<10s), or repository")
    os.umask(0o077)
    try:
        Runner(args).start()
    except (Stop, subprocess.CalledProcessError, OSError, ValueError) as exc:
        print(f"Stopped: {type(exc).__name__}: " + (str(exc) if isinstance(exc, Stop) else "inspect local configuration/logs"), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
