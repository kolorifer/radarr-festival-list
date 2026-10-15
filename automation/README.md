# GitHub supervisor / fresh Codex worker

The control plane is [issue #11](https://github.com/kolorifer/radarr-festival-list/issues/11).
Normal ChatGPT posts supervisor tasks and reviews the PR through GitHub. This
runner does not invoke ChatGPT Work or depend on a long conversation.

## Requirements and authentication

Use a dedicated, clean local clone on macOS (Python 3.9+; CI uses 3.12/3.13).
The runner has no pip dependencies. Install Git, GitHub CLI (`gh`), and Codex CLI
separately. Keep their executables on PATH, then authenticate interactively:

```sh
gh auth login
gh auth setup-git
codex login
gh auth status
codex login status
```

The GitHub identity needs repository contents/branch/PR and issue-comment write
access. `origin` must identify the selected GitHub repository. Configure Git's
commit name/email. Verify that the Codex account has access to `gpt-6.1-sol`.
Credentials stay in each CLI's private credential store, never in task comments.
Do not use a seedbox/production checkout. Seedbox tasks may use existing private
SSH authentication; never copy credentials into prompts, logs or the repository.

## Operator smoke test

From the dedicated clone root, check CLI availability/authentication and confirm
the repository is clean before previewing:

```sh
gh --version
gh auth status
codex --version
codex login status
git status --short --branch
test -z "$(git status --porcelain)" && python3 automation/github_worker.py --dry-run --once
```

Resolve any failed preflight check before proceeding. `--dry-run --once` must not
launch Codex, claim a task, create commits/branches/comments, or consume task
numbers. It only previews an eligible task (or reports that none is pending).

## Preview, start and stop

From the clone root:

```sh
python3 -m unittest test_github_worker -v
python3 automation/github_worker.py --dry-run --once
python3 automation/github_worker.py --once
python3 automation/github_worker.py --interval 60
```

`--dry-run` reads GitHub and git state, prints the newest eligible task's prompt,
and exits. It creates no claim, lock, journal, branch, comment, or Codex process;
quota is checked only on a real run. If task 1 has already been reported, it prints
that there is no unprocessed task. Preview tests use a synthetic pending task.
`--once` polls once and executes at most one task; otherwise polling continues
until Ctrl-C (or SIGTERM). A failure exits; restart manually after inspection.
No service is installed or started by any of these commands.

Options: `--repo /absolute/clone`, `--github-repo owner/repo`, `--issue 11`,
`--base main`, `--sessions ~/.codex/sessions`, and `--interval 60` (minimum 10s).
The issue's author is the supervisor: only their numbered task instructions can
launch work. The authenticated worker and issue author's RUNNING/result comments
also prevent duplicate execution. Closing the issue or posting `STATE: DONE`
as its latest trusted state stops new launches. Keep one issue per goal; the
maximum of eight consumed iterations is deliberately not reset inside an issue.

## Task and result protocol

Post a NEW positive integer for each iteration. Never edit/reuse a consumed
number to retry. Example supervisor comment:

```text
SUPERVISOR_TASK: 2
STATE: READY_FOR_CODEX
GOAL: Fix the specific review finding
ACCEPTANCE_CRITERIA:
- Describe observable passing behavior
AUTHORIZATION:
- Scoped repository edits, tests, commit, push and PR update
FORBIDDEN:
- Radarr, seedbox and media mutations
- Persistent service installation/start
INSTRUCTIONS:
- Inspect partial work and the current PR before editing
```

Workers use GPT-6.1 Sol with Medium reasoning. An explicit task field such as
`REASONING: high` overrides the effort. Every launch is a new non-interactive
`codex exec`, with a workspace-write sandbox and approval policy `never`. No
resume/fork command or prior transcript is supplied. The compact prompt includes
the issue body, latest task, repository `AGENTS.md` instructions and current git
status/three commits. Other task briefs are explicitly not execution authority.
Daemons remain forbidden. Network and seedbox access default to denied. Only the
latest numbered task from the issue owner can opt in with these top-level fields:

```text
NETWORK_ACCESS: enabled
SEEDBOX_PERMISSION: read-only
```

`NETWORK_ACCESS` accepts `disabled` (default) or `enabled`. The runner explicitly
sets `sandbox_workspace_write.network_access=false` or `true` on `codex exec`,
preserving workspace-write and approval policy `never`; no sandbox bypass is used.
Network availability alone grants no seedbox permission.

`SEEDBOX_PERMISSION` accepts `none` (default; no seedbox access, including reads),
`read-only` (only non-mutating SSH/read operations within AUTHORIZATION; no
seedbox/Radarr/media mutations), or `authorized-mutations` (only exact mutations
explicitly stated in that task's AUTHORIZATION; no unrelated access or changes).
Both non-`none` levels require `NETWORK_ACCESS: enabled`. With `none`, Radarr and
media mutations remain forbidden. Capability fields never override FORBIDDEN or
authorize operations by themselves. Keep exact targets/actions in AUTHORIZATION.
Missing fields deny access; malformed, duplicate, unsupported or inconsistent
fields stop before claiming or launching, with NEEDS_USER (dry-run exits with an
error). Older tasks, other commenters, issue text and repository briefs cannot
grant capabilities. Seedbox read/mutation restrictions are worker prompt policy,
not an SSH command filter; the network flag controls sandbox network availability.

The worker implements, inspects and tests. It returns a JSON result (tests,
summary, questions, READY_FOR_REVIEW or NEEDS_USER). The runner then checks the
diff, commits scoped work, pushes `automation/issue-11-worker`, and creates or
updates one open PR to main. Subsequent tasks use that branch. It does not merge
or deploy. A blocked worker leaves any partial changes for human inspection and
publishes no code. Tests reported in a result are the worker's stated actual
checks; the runner does not invent a successful full-suite result.

```text
WORKER_RESULT: 2
STATE: READY_FOR_REVIEW
BRANCH: automation/issue-11-worker
COMMIT: <full SHA>
PR: <URL>
TESTS: <actual commands and results>
SUMMARY: <concise result>
QUESTIONS: none
```

## Quota and crash recovery

The runner reads only `event_msg` / `token_count` quota metadata from local
`~/.codex/sessions/**/*.jsonl`, following the existing `codex-health` telemetry
shape. It selects the latest timestamped primary 300-minute observation, not
the most recently modified file. Context usage/history is never placed in a
prompt, nor used to resume a session.

At <=15% remaining it posts `STATE: PAUSED_QUOTA` with the percentage, does not
consume the task, and checks again on a later poll. Identical notifications are
suppressed. Missing, malformed, expired or >5h-old observations fail closed with
`STATE: NEEDS_USER`. Refresh telemetry through a fresh authenticated interactive
Codex run, without resuming prior work. A later poll with valid telemetry can
proceed. An expired window is not assumed to mean 100% available.

A kernel `flock` on the common Git directory's
`github-worker/11/runner.lock` excludes local instances across linked worktrees.
The lock inode is never removed: stale PID contents are harmless, and the kernel
releases the lock after exit/crash. The worker inherits the lock descriptor so
an orphaned worker still prevents a replacement runner from overlapping it.
Stop that worker and inspect its changes before restarting after an interruption.

Before launch the runner durably records the number locally, then atomically
creates `refs/heads/automation/issue-11-claim-N` on GitHub and posts RUNNING.
GitHub's create-only ref provides the cross-machine claim; issue comments alone
cannot atomically claim a task. Claim refs are intentional permanent audit
markers, not work branches; never edit/delete them. All runners must use this
implementation's namespace. Ref claim failure, including an ambiguous network
failure, never launches a worker. A crash anywhere after local reservation burns
the number. Inspect the journal, claim, PR and working tree and post a NEW number
for follow-up. This prioritizes at-most-once execution over automatic recovery.

State, worker output/logs and precommit diffs live under the common Git directory
in `github-worker/11/`, private to the local account and excluded from commits.
Do not publish these logs: they may contain worker tool output. A dirty checkout
stops the runner before any claim. Preserve/reconcile partial work manually;
there is no reset, clean, force-push, automatic retry or media operation.
Use a dedicated clone per control issue; avoid manual edits while it is active.

## Optional macOS LaunchAgent (example only)

`com.example.github-codex-worker.plist` is an inert example. Edit every absolute
path and PATH to match your CLI installation before considering use. It runs a
single poll every minute; the same lock protects overlapping invocations. It
has no KeepAlive restart loop. Authentication must already work without prompts.

Only after explicit user approval, an operator can copy the edited example into
`~/Library/LaunchAgents/` and load it using:

```sh
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.github-codex-worker.plist
```

Stop/unload it with:

```sh
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.example.github-codex-worker.plist
```

Nothing in this repository installs, enables or invokes this example.

### LaunchAgent verification

For an enabled agent using the example label and logs configured under
`~/Library/Logs/github-codex-worker/`, inspect its status and recent output:

```sh
launchctl print gui/$(id -u)/com.example.github-codex-worker
tail -n 50 ~/Library/Logs/github-codex-worker/worker.stdout.log
tail -n 50 ~/Library/Logs/github-codex-worker/worker.stderr.log
```

Substitute the installed label and log filenames if different. The healthy idle
result is no pending `READY_FOR_CODEX` task and empty stderr.

Codex command/output-schema details: [official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode).
