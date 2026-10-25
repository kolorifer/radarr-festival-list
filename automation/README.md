# GitHub supervisor / fresh Codex worker

The control plane is an open control issue owned by the authenticated runner
identity. Normal ChatGPT posts supervisor tasks and reviews the PR through
GitHub. This runner does not invoke ChatGPT Work or depend on a long conversation.

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

Omitting `--issue` enables discovery: paginate open issues created by the
authenticated GitHub identity, exclude PRs, and validate only issue-owner tasks.
Closed/DONE issues, malformed/untrusted tasks, consumed/claimed numbers and
issues with eight consumed iterations are ineligible. Each poll selects at most
one task: the oldest outstanding valid latest READY task by GitHub comment ID,
with issue number as a deterministic tie-breaker. `--issue N` keeps the explicit
operator/debug override, including the existing issue-owner trust policy.

`--dry-run` reads GitHub and git state, prints only candidate counts and selected
issue/task numbers, and exits. Task bodies/prompts are never printed. It creates
no claim, lock, journal, branch, comment, quota probe or Codex process; quota is
checked only on a real run. Preview tests use synthetic pending tasks.
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

Workers use GPT-6.1 Sol with High reasoning. An explicit task field such as
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
publishes no code. Detailed worker-reported tests/summary/questions stay in the
private local JSON result. The parent emits fixed public status text and its own
checks; it does not invent a successful full-suite result. Private-output tasks
use the exact capability below and create no public commit/PR.

For a task that must perform only explicitly authorized operations and leave the
public checkout unchanged, the latest issue-owner task can set
`PUBLICATION_MODE: operations_only`. The parent then skips all add/commit/push/PR
handling, even with earlier branch commits, and reports `PR: none`. Absence or
explicit `PUBLICATION_MODE: code` keeps ordinary publication. Parsing is strict;
the mode grants no operational access or private write. Exact checkout comparison
also runs on child failure; an unchanged explicitly bound retained baseline is
allowed, while new changes are refused and preserved. Parent-generated local
`execution-N.json` separates child exit/parsed result from later delivery failure;
neither it nor a worker READY proves external deployment state. Existing claims
remain consumed and operations are never automatically replayed. See the
[full boundary/limitations](SUPERVISOR_PROTOCOL.md#explicit-operations-only-publication-issue-35)
and [prepared harmless acceptance task](OPERATIONS_ACCEPTANCE.md).

Default-mode private tasks preserve exact authorized `CONTINUE_FROM`
reconciliation: they must finish with a clean public checkout and unchanged HEAD
before private publication, while keeping the parent backup. Their final
fingerprint may differ from the retained dirty baseline. Exact baseline
immutability applies to explicit operations-only tasks, including private ones.

```text
WORKER_RESULT: 2
STATE: READY_FOR_REVIEW
BRANCH: automation/issue-11-worker
COMMIT: <full SHA>
PR: <URL>
TESTS: Parent diff checks passed; worker checks retained privately
SUMMARY: Scoped worker result ready for supervisor review
QUESTIONS: none
```

## Quota and crash recovery

The runner reads only `event_msg` / `token_count` quota metadata from local
`~/.codex/sessions/**/*.jsonl`, following the existing `codex-health` telemetry
shape. It selects the latest timestamped Codex quota snapshot, not the most
recently modified file. Window durations are account-dependent: primary may be
weekly with no secondary window. It validates all reported primary/secondary
windows and uses the lowest remaining percentage; a malformed or expired latest
snapshot fails closed rather than falling back to an older allowance. Context usage/history is never placed in a
prompt, nor used to resume a session.

At <=15% remaining it posts `STATE: PAUSED_QUOTA` with the percentage, does not
consume the task, and checks again on a later poll. Identical notifications are
suppressed. Fresh observations are used without a probe. Missing, malformed,
expired or >5h-old observations trigger one minimal fresh non-interactive quota probe, only
when an eligible task exists and before local reservation or GitHub claim.
The probe runs outside the repository in an empty temporary directory, using
GPT-6.1 Sol / Low, read-only sandbox, approval policy `never`, disabled sandbox
network and web search, disabled shell tools/snapshots, zero project instruction
bytes, and ignored user config/rules. Its fixed prompt contains no project/task
content; stdout/stderr are discarded. Authentication/model transport still needs
the Codex service; the agent receives no network-enabled execution sandbox.
Session persistence stays enabled so token-count telemetry can be refreshed.
These flags require a current Codex CLI supporting `--ignore-user-config` and
`--ignore-rules` (the installed CLI parser was checked during implementation).

After the probe, re-read telemetry: >15% proceeds, <=15% posts/retains PAUSED_QUOTA,
and failure/no trustworthy refresh posts a generic NEEDS_USER without consuming
the task. A clone-wide private cooldown journal is written before probing and
backs off for 30 minutes after failure/crash (probe timeout: 60 seconds). Fresh
usable telemetry clears the cooldown immediately, even during that interval.
Expired windows are never assumed to mean 100% available. No eligible task or
`--dry-run` means no probe. Logs contain selection and quota outcomes, never raw
Codex output or telemetry records.

A clone-wide kernel `flock` at the common Git directory's
`github-worker/dispatcher.lock` excludes explicit and discovery invocations across
issues and linked worktrees. The existing per-issue `github-worker/N/runner.lock`
is also retained. Lock contention stops with a concise message. Lock inodes are
never removed: stale PID contents are harmless, and the kernel releases locks
after exit/crash. Workers and quota probes inherit both descriptors so an
orphaned child still prevents a replacement runner from overlapping it.
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
stops the runner before any claim. Use the explicit snapshot-bound continuation protocol for partial work;
there is no reset, clean, force-push, automatic retry or media operation.
Use a dedicated launcher clone; avoid manual edits while it is active. When a
task targets another branch, the dispatcher executes it in a retained per-issue
worktree at `github-worker/N/checkout` under the common Git directory. The
launcher checkout/branch is never switched to that issue's older code. Blocked
or failed worker changes remain in the worktree for inspection; dirty retained
worktrees fail before quota probing or claiming a follow-up unless the exact
preceding retained snapshot is explicitly authorized for continuation. Worktrees are not
automatically deleted. A task targeting the launcher's own branch uses that
checkout as before.

## Optional macOS LaunchAgent (example only)

`com.example.github-codex-worker.plist` is an inert example. Edit every absolute
path and PATH to match your CLI installation before considering use. It runs a
single discovery poll every minute (`--once`, no `--issue`); the dispatcher lock
protects overlapping invocations. It has no KeepAlive restart loop. Authentication must already work without prompts.

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

Implementation verification for issue #24 found the installed worker LaunchAgent
also uses `--once` and omits `--issue`. Its invocation is compatible without a
plist edit. No agent installation, reload, cadence/path/log change or activation
was performed. Publication/activation of dispatcher-v2 remains with the runner
and supervisor.

## Stabilized protocol

[Publication, continuation, ownership and supervisor wakeup](SUPERVISOR_PROTOCOL.md)
defines the current protocol. Worker prose stays private; public result/PR text
is generated by the parent. PRIVATE_ARTIFACT and PRIVATE_INPUTS tasks cannot
publish public changes. PRIVATE_INPUTS requires exact commit/blob/SHA256/path
and local aliases; the parent stages read-only files before reservation.
PRIVATE_DIAGNOSTIC independently authorizes one structured version-1 terminal
JSON destination, with the existing private CAS/readback boundary. No field
grants an adjacent path or sends worker prose. Public results add stable
REASON_CODE and PRIVATE_RECEIPT availability fields; task parsing/claims remain
compatible. Omitted capabilities retain their previous denied defaults.

Run all focused boundary/lifecycle checks with:

```sh
python3 -m unittest test_github_worker test_supervisor_policy test_supervisor_communication -v
```

[Account-side schedule checklist and harmless later live acceptance](SUPERVISOR_HANDOFF.md)
is prepared for review. Deployment, private fixture creation and schedule
activation require a subsequent supervisor step; do not run an unmerged runner.
