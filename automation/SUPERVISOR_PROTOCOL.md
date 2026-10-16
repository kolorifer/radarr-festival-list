# Supervisor protocol and deployed responsibilities

## Ownership

ChatGPT/user posts an issue-owner numbered task. The macOS LaunchAgent launches
one parent dispatcher poll per minute. The parent discovers eligible owner issues,
checks quota, reserves locally, creates an immutable claim ref and posts RUNNING.
A fresh sandboxed Codex child implements the task. The parent owns issue results,
public commits/push/PR, and authorized private publication. No child receives host
GitHub token environment variables, SSH agent socket, user integrations or exec
rules. Workspace-write and approval=never remain enforced. Reasoning defaults to
high; the isolated quota metadata probe uses low to minimize overhead.

The parent never invokes ChatGPT. A saved ChatGPT/Work schedule must wake the
supervisor to review terminal results and post a new numbered task. A public
RUNNING comment is a claim history record, not proof of liveness. Inspect the local
heartbeat (active, timestamp, PID), actual process and inherited kernel locks.

## Exact private output authorization

Only a valid issue-owner task can include this single-line JSON capability:

```text
PRIVATE_ARTIFACT: {"repository":"kolorifer/radarr-state","path":"operations/synthetic-example.md","expected_blob":"absent","source":"artifact.md"}
```

The host allowlist admits only that private repository, main, operations/ paths
ending md/json/txt, and a single staging filename. Traversal, query strings,
duplicate/malformed fields and other repositories are rejected before claim.
Codex receives a mode700 local staging directory through --add-dir. It writes the
local file only. The parent refuses public repository changes/commits for these
tasks, reads the bounded regular artifact, verifies private repository metadata,
checks the exact destination, uploads via host gh and reads it back for byte and
SHA256 verification. READY_FOR_REVIEW follows successful verification only.

Use expected_blob=absent for create-only behavior. Existing identical bytes are
idempotent. An existing divergent file is refused. Replacing an existing file
requires a NEW supervisor task authorizing its exact current 40-character blob;
GitHub PUT uses that blob as a compare-and-swap condition. A concurrent edit or
failed readback fails the task. No wildcard or unconditional overwrite exists.
Private receipt and artifact copies remain under the common Git directory, never
in public commits. Staging directories are retained; durable private copies are
made after a normally exiting child. A child crash may leave only its original
staging file, which must be preserved before OS temporary-file cleanup.

Private output tasks publish fixed parent-generated status fields, never raw
worker summaries, tests, questions, private paths or contents. They need no empty
public PR. Ordinary code tasks retain the existing public branch/PR workflow;
worker prose is private there too. Code-task diffs still require scope/privacy
review: this is not a general classifier for arbitrary sensitive source code.

The capability authorizes output, not private input access. Tasks needing private
source data must receive separately authorized local input staging or use an
approved read-only connector. The child does not gain host GitHub authentication.

## Retained work continuation

NEEDS_USER/FAILED records a fingerprint bound to the exact issue checkout,
preceding task, HEAD, symbolic branch, index, tracked bytes/modes and nonignored
untracked bytes. Symlinks are fingerprinted by their link text. Ignored caches are
outside this fingerprint. A private tar plus index patch preserves partial work.
No parent reset, clean, stash, force-push or automatic retry is performed.

A NEW task can explicitly authorize reconciliation:

```text
CONTINUE_FROM: {"task":1,"snapshot":"<64-character RETAINED_SNAPSHOT from preceding terminal result>"}
```

The prior result must be NEEDS_USER/FAILED and the immediately preceding consumed
task. The issue-local journal, checkout path and recomputed fingerprint must all
match. Changed bytes/index/HEAD/branch or remote advancement are refused before
worker mutation; worktree mismatches are checked before quota/claim. Tell the
worker exactly which partial files it may reconcile, preserving the parent backup.
Pre-upgrade partial states without a recorded fingerprint need inspection and a
new baseline, not an invented continuation grant. Existing issue-26 stash remains
untouched; no old task is replayed.

## Dispatch, quota and recovery

The clone-wide flock and per-issue flock are inherited by the child/probe. GitHub
create-only claim refs supply cross-machine at-most-once execution. Never delete
or edit claims. Local reservation precedes the remote claim: ambiguous failures
burn a task number. Each --once invocation selects at most one eligible latest
owner task, ordered by GitHub comment ID. Eight consumed iterations is the limit.

Fresh 300-minute telemetry >15% permits work. <=15% pauses without consuming.
Missing/stale telemetry triggers one fixed read-only, tool-disabled low-reasoning
probe. Failed/crashed probes back off 30 minutes; fresh trustworthy telemetry
clears cooldown. Probe logs are discarded. Failure and cooldown tests are
synthetic; a successful live probe can be observed separately. Poll frequency is
not a guarantee of start time; machine sleep, network/auth and quota can delay it.

Preflight refusal is deduplicated in public as NEEDS_USER with no task consumption.
Execution exceptions publish generic FAILED and retain local details. Publication
can succeed privately before a later public-result failure: reconcile by private
readback/identical retry under a NEW task, never by deleting the old claim.

## Supervisor schedule handoff

No local automation.toml entry was present during the initial audit. That does
not establish whether a cloud ChatGPT schedule exists. The available desktop
schedule tool cannot enumerate the original ChatGPT account schedules; the
original cloud schedule must be inspected there before creating a duplicate.

Suggested hourly supervisor prompt: inspect the latest trusted terminal worker
results and PR state for the public control repository; remain quiet while state
is unchanged; distinguish RUNNING claims from process liveness; review aggregate
results and authorized private artifacts through the private connection; only post
new REASONING: high tasks within an already approved infrastructure/research goal.
For continuation, bind the new task to the exact preceding snapshot. For private
outputs, authorize one exact repository/path and expected blob. Never put private
identities/evidence in public comments. Never make subjective KEEP/REMOVE decisions
or authorize Radarr/media/seedbox mutations automatically. Notify on meaningful
completion/failure or a decision requiring the user. Verify schedule activation,
next run and one observed wakeup in ChatGPT; this parent runner cannot prove it.

## Observed deployment evidence — 2026-10-16

PR #27 merged runtime e56ff96 is deployed from main. Harmless issue #28 observed
both automatic pickups, real heartbeat/process/lock evidence, snapshot continuation
without stash/reset, host private write/readback and sanitized READY_FOR_REVIEW.
The installed LaunchAgent file/cadence stayed unchanged. See the
[engineering report](../docs/reports/2026-10-16-supervisor-stabilization.md).

Official scheduled-task documentation: [Scheduled tasks](https://learn.chatgpt.com/docs/automations).
Saved schedules provide recurring wakeups; this is distinct from the local worker
poll. Account-specific activation and an observed supervisor run are still pending.
