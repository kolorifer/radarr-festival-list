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

## Explicit operations-only publication (issue #35)

The latest validated issue-owner numbered task may include exactly this line:

```text
PUBLICATION_MODE: operations_only
```

Omission retains ordinary code publication; `PUBLICATION_MODE: code` explicitly
selects that same default. These are the only values. Unknown values, duplicates,
case/indentation/spacing variants, inline comments and multiline values fail
before claim/child execution. Older tasks, other commenters, issue text, repository
briefs, worker results and prose cannot supply the mode. Neither no diff, a READY
state nor deployment keywords imply it. Do not set operations_only on a code
implementation task merely because its implementation concerns operations.

This is a publication restriction, never an authority grant. NETWORK_ACCESS,
SEEDBOX_PERMISSION, exact private capabilities and especially AUTHORIZATION and
FORBIDDEN still control every action. No network, SSH, service, deployment,
filesystem edit or private write is authorized by this field. Operations-only
does not permit editing or reconciling this public worker checkout. Any future
remote deployment needs its own explicit scope. Claims, locks, quota, reasoning,
child credential filtering and task-number consumption remain unchanged.

For operations_only the parent never runs git add/commit/push or PR list/create/
edit, including on a branch containing earlier commits. An existing issue checkout
is not fast-forwarded or reconciled; remote advancement beyond its HEAD is refused.
Normal initial issue-worktree creation remains available. The parent validates the
clean or explicitly authorized exact retained baseline when entering the checkout,
captures its fingerprint again immediately before launching the child, and compares
it afterward even on child failure. Pre-child drift is refused, never silently
adopted. Branch, HEAD, staged entries, tracked bytes/modes, deletions, symlink text
and nonignored untracked bytes are covered. Detached HEAD is fingerprintable so
an unexpected detach can be refused and retained. Fingerprints of normal branches
are compatible with existing retention records.

An unchanged exact CONTINUE_FROM baseline may contain preceding partial work;
the child must leave every byte/index/branch/HEAD unchanged. This also applies
when operations_only is combined with private inputs/output: it permits retaining
existing explicitly bound differences, never new checkout changes or public code
publication. Default-mode private tasks may reconcile only the exact retained
files explicitly authorized by the immediately preceding CONTINUE_FROM contract.
They must finish with a clean public checkout and unchanged HEAD before private
publication; their final fingerprint need not equal a dirty retained baseline.
The local execution record still reports the exact comparison independently.
Operations-only baseline changes, or a dirty checkout/changed HEAD at default
private publication, yield PUBLIC_CHANGE_REFUSED. Failures preserve partial work
and existing private backups where snapshotting is possible. Default private
child failures remain CHILD_FAILED; operations-only changes take refusal priority,
with the child failure independently recorded locally. No stash, reset, clean,
claim deletion/reuse or automatic retry is introduced.

Ignored caches, Git metadata beyond HEAD/branch/index entries, external filesystem
state, and changes made and reverted between observations are outside this
fingerprint contract. It is change detection, not a hostile-process security
boundary or proof of external operations. Unsupported/unreadable entries fail
closed. Do not store operational evidence in the public checkout, including its
ignored caches. Private inputs, artifact staging and diagnostics remain independent;
only separately granted exact destinations can be uploaded with existing CAS and
readback. Artifact verification precedes receipt verification and public status.

Public operations results always say `PR: none`. Fixed TESTS text reports only
whether the parent verified the checkout fingerprint unchanged; SUMMARY states
the terminal reason code, disabled code publication and that external state was
not verified. READY/OK, NEEDS_USER/WORKER_BLOCKED, CHILD_FAILED, INVALID_RESULT,
PUBLIC_CHANGE_REFUSED, ARTIFACT_PUBLICATION_FAILED, RECEIPT_PUBLICATION_FAILED and
RESULT_PUBLICATION_FAILED remain distinct parent observations. Raw child text,
exception details, local paths and private evidence stay private.

The parent persists `execution-N.json` locally under the issue's common-Git state
directory, separately from `terminal-N.json` and `delivery-N.json`. Its local v1
fields record the task/mode, child process (not_started/running/exited/failed),
parsed worker_state (or null), checkout baseline/comparison, code publication
(not_started/disabled/started/completed), attempted terminal state/code, receipt
availability and public result (not_attempted/unconfirmed/posted). `exited` means
the child process returned zero; worker_state is a parsed claim, not proof of a
deployment. `running`, `started` or `unconfirmed` after interruption is inconclusive.
`posted` means the public POST returned normally, without readback verification.
Delivery errors do not erase completed child observations. Inspect/reconcile
delivery under separately authorized scope; never infer that operations need
rerunning, retry the child or delete/reuse its permanent claim. Private terminal
receipt schema stays at v1 with its existing allowlist; no new upload destination
is inferred from this local record.

See the [harmless post-merge acceptance plan](OPERATIONS_ACCEPTANCE.md).
Implementation tests are synthetic; merge, launcher deployment and live acceptance
are separate supervisor follow-up, not authorized by this implementation task.

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

The capability authorizes output only. Input staging and terminal diagnostics
require the independent capabilities below. The child receives no host GitHub
authentication. Existing tasks without these new fields retain their defaults.

## Pinned private input authorization (issue #30)

Only the latest validated issue-owner task may supply one canonical single-line
JSON object. Replace the placeholders with actual lower-case full hashes:

```text
PRIVATE_INPUTS: {"inputs":[{"repository":"kolorifer/radarr-state","path":"fixtures/synthetic.txt","commit":"<40 hex commit>","blob":"<40 hex blob>","sha256":"<64 hex content hash>","alias":"input.txt"}]}
```

All six fields are required for every input: the immutable commit establishes
path membership and file mode, the blob establishes Git identity, and SHA256
establishes content integrity independently. Mutable refs, abbreviated hashes,
missing/extra/duplicate JSON keys, duplicate source paths/aliases, other
repositories, traversal, wildcards and URL syntax are refused. Paths are exact
repository-relative ASCII paths (maximum 240 characters); local aliases are
single alphanumeric/underscore/hyphen filenames ending md/json/txt. There are
at most eight inputs, each at most 900000 bytes. Omission grants no private read.
Issue bodies, older tasks and other commenters grant nothing.

Under the existing dispatcher and issue locks, after quota but **before local
reservation and remote claim**, the authenticated host verifies full repository
identity, private visibility and main default branch. It resolves the authorized
commit, walks non-recursive Git tree metadata for that exact path and accepts
only regular blob modes 100644/100755. Symlinks, symlink parents, submodules,
truncated trees and missing/ambiguous nodes fail closed. Tree responses contain
directory metadata; no other file contents or recursive tree are requested.
The parent reads only the exact contents endpoint at the pinned commit, compares
blob/size and recomputes Git blob SHA1 plus SHA256. Advancing main cannot change
this input; changed bytes or mismatched pins are refused. All remote inputs must
validate in bounded memory before any staging files are created.

The parent stages aliases outside the public checkout, with directory mode500
and files mode400. The child receives local paths and the original narrow task
authorization, using the same filtered environment/config/sandbox as before.
There is **no --add-dir writable grant for inputs**. Only a separately authorized
output directory receives that grant. Reads outside the checkout rely on the
existing workspace sandbox read permissions; live CLI verification is pending.
Directory/file identity, modes, timestamps, size, SHA256 and directory entries
are checked before reservation, before the child and after it, including child
failure. Unexpected changes refuse artifact/public-code publication. This is
change detection plus ordinary filesystem permissions, not a claim of isolation
against a hostile process running as the same OS account.

Failed remote validation creates no partial stage, claim or consumed number.
Local staging failures retain their recorded staging path for inspection. An
input failure emits the deduplicated INPUT_VALIDATION_FAILED preflight status;
no private diagnostic is uploaded before reservation. Once reserved, existing
at-most-once rules apply even if input checks subsequently fail. Staging remains
private and is not automatically cleaned. A host crash/OS temporary-directory
cleanup can require inspected recovery; no automatic task replay is added.

Any task receiving private inputs is publication-restricted just like a
PRIVATE_ARTIFACT task: no public add/commit/push/PR, and any checkout/history
change refuses publication even for a blocked result. A separately authorized
artifact can be written locally and published by the parent after READY only.
An input-only task can process locally without granting any GitHub write.

## Structured private terminal diagnostic (version 1)

An independent exact destination may be authorized in the latest owner task:

```text
PRIVATE_DIAGNOSTIC: {"repository":"kolorifer/radarr-state","path":"operations/synthetic-terminal.json","expected_blob":"absent"}
```

Only operations/ JSON paths in the allowlisted private repository are accepted.
The path must differ from PRIVATE_ARTIFACT; neither grant implies the other,
an adjacent file, a directory or permission to publish worker prose. The same
parent-owned repository validation, destination divergence check, blob CAS,
identical-byte idempotency and exact readback protect each independent write.
An expected existing blob must be explicitly authorized by a new task.

After confirmed successful atomic claim creation, READY_FOR_REVIEW, NEEDS_USER
and caught FAILED paths attempt the authorized receipt once. Reservation alone
does not establish ownership. Claim conflicts and ambiguous responses keep the
task consumed locally and record only bounded local CLAIM_FAILED diagnostics;
they never launch a child, publish task-private outputs/receipts, or post an
authoritative WORKER_RESULT. This avoids preempting the winning host's absent
receipt destination. A process kill, interpreter/host crash, unusable
state storage or total network outage can prevent receipts; absence is never
success. Preflight refusals and quota pauses do not consume or publish receipts.

The parent constructs and validates this small schema; no receipt field is copied
from worker prose, prompts, logs, environment, stderr or exception messages:

| Field | Version 1 allowlist |
| --- | --- |
| schema_version | integer 1 |
| identity | public repository, positive issue and task integers |
| state | READY_FOR_REVIEW, NEEDS_USER, FAILED |
| code; next_action | fixed boundary code and mapped action below |
| runtime | parent Python version; launcher runner revision; checkout revision (null if unavailable) |
| retained_snapshot | exact recorded current-task SHA256, or null |
| verification | booleans: inputs_verified, inputs_unchanged, public_checkout_unchanged, artifact_readback |
| artifacts | zero/one authorized output repository/path/blob/SHA256, only after verified readback |

Runtime identifies the interpreter executing the parent and the inspected Git
revisions. It is not an assertion that arbitrary worker tests passed. A false
verification flag means unverified/not applicable; only true records a completed
parent check. Revisions are Git identities, not an attestation of a clean
launcher or of worker-reported tests. The worker result must have exactly the
original four string fields, a supported state and at most 64000 bytes. Extra
diagnostic keys and duplicate JSON keys are rejected, never forwarded.

| Code | Permitted next action |
| --- | --- |
| OK | review |
| WORKER_BLOCKED | new_task (only after resolving the blocker) |
| EXECUTION_FAILED, CHECKOUT_FAILED | inspect_local |
| CHILD_FAILED, INVALID_RESULT, INPUT_CHANGED | inspect_local |
| PUBLIC_CHANGE_REFUSED, ARTIFACT_INVALID | inspect_local |
| PUBLIC_CODE_PUBLICATION_FAILED, RECEIPT_PUBLICATION_FAILED | inspect_local |
| ARTIFACT_PUBLICATION_FAILED, RESULT_PUBLICATION_FAILED | reconcile_private |

Codes describe the observed boundary, not inferred root causes. These action
categories confer no new authorization. Cloud supervision can distinguish an
input integrity failure, child failure, blocker or publication failure, but
missing credentials, exact subjective questions, raw test failures, crash causes,
damaged checkout/snapshot and uncertain API delivery still need local inspection.
No arbitrary diagnostic text is permitted by version 1.
CLAIM_FAILED remains accepted by the version-1 reader for historical receipts;
the corrected runner records it only in local claim-failure-N.json, with
ownership=unconfirmed and consumed=true. It emits no public claim warning or
terminal result on an unconfirmed claim.

The normal order is: child -> input/checkout checks -> optional artifact write
and readback -> receipt write and readback -> fixed public result. Public results
retain WORKER_RESULT/STATE and add REASON_CODE plus PRIVATE_RECEIPT with only
verified/unavailable/not_authorized. Preflight uses not_attempted. No private
source/destination identity, hash, local path or raw worker prose is reflected.
Existing retained snapshot fields remain available for exact continuation.
RUNNING now has CLAIMED_AT and explicitly denotes a historical claim; actual
local process/heartbeat observations must carry their observation timestamp.

Local terminal-N.json preserves the intended structured receipt; delivery-N.json
records receipt availability/hashes and public-result delivery; original worker
JSON/logs, artifact copies and retained backups remain private under common Git
state. If a required receipt write/readback fails, the public terminal result is
FAILED/RECEIPT_PUBLICATION_FAILED with unavailable, never successful READY. The
intended receipt is preserved and no overwrite/retry loop is attempted. Snapshot
failure is separately recorded locally as SNAPSHOT_UNAVAILABLE, with a null
receipt fingerprint when none could be recorded.

A private PUT may succeed before its response/readback fails. The remote receipt
may then describe the intended READY even though the public result is FAILED;
it is not verified delivery. A verified receipt may likewise precede a failed or
ambiguous public comment POST. That private receipt remains untouched; the local
delivery journal records RESULT_PUBLICATION_FAILED, and no second terminal upload
or task execution occurs. Public comment delivery itself is not readback-verified.
Inspect the exact authorized private destinations and public issue, compare
bytes/hashes and permanent claim, then use a NEW task with exact expected blobs
and, if needed, the immediately preceding retained snapshot. Do not delete claims,
reuse numbers, clean/reset partial work or infer authorization for recovery files.

## Retained work continuation

NEEDS_USER/FAILED records a fingerprint bound to the exact issue checkout,
preceding task, HEAD, symbolic branch, index, tracked bytes/modes and nonignored
untracked bytes. Symlinks are fingerprinted by their link text. Ignored caches are
outside this fingerprint. A private tar plus index patch preserves partial work.
No parent reset, clean, stash, force-push or automatic retry is performed.

Recovery retains the exact validated execution checkout even after the parent
restores its launcher context. A receipt failure preserves already captured
current-task retention, including its original state, snapshot, tar and index
patch. When a successful child has no prior capture, receipt failure records
FAILED retention from that execution checkout. A checkout that was never
established has no usable continuation or backup; its receipt snapshot is null.
The launcher is never substituted as an issue continuation baseline.

A NEW task can explicitly authorize reconciliation:

```text
CONTINUE_FROM: {"task":1,"snapshot":"<64-character RETAINED_SNAPSHOT from preceding terminal result>"}
```

The prior result must be NEEDS_USER/FAILED and the immediately preceding consumed
task. The issue-local journal, checkout path and recomputed fingerprint must all
match. Changed bytes/index/HEAD/branch or remote advancement are refused before
worker mutation; worktree mismatches are checked before quota/claim. Tell the
worker exactly which partial files it may reconcile, preserving the parent backup.
Default private input/output tasks can reconcile those authorized files to a clean
checkout with unchanged HEAD before publication. Explicit operations_only tasks
instead must leave the entire exact retained baseline unchanged, including dirt.
Pre-upgrade partial states without a recorded fingerprint need inspection and a
new baseline, not an invented continuation grant. Existing issue-26 stash remains
untouched; no old task is replayed.

## Dispatch, quota and recovery

The clone-wide flock and per-issue flock are inherited by the child/probe. GitHub
create-only claim refs supply cross-machine at-most-once execution. Never delete
or edit claims. Local reservation precedes the remote claim: ambiguous failures
burn a task number. Each --once invocation selects at most one eligible latest
owner task, ordered by GitHub comment ID. Eight consumed iterations is the limit.
Two hosts may both discover before either claims. Only a successful atomic
create response establishes ownership for publication. An existing ref, even
at the same SHA, cannot establish which host created it. A lost create response
may leave a permanent ref with no executing/publishing host; keep local consumed
state, inspect the exact claim and host records, and authorize a NEW task if
needed. There is no claim retry, deletion, consumed-number reuse or automatic
execution. The losing host cannot publish a competing terminal state.

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

Task-2 owner update: the user enabled an hourly supervisor heartbeat in the
current Work/Codex chat; creation returned ACTIVE. This is supplied account-side
status, not a worker observation. No scheduled wakeup has yet been observed,
and the original cloud ChatGPT schedules remain unverified. This worker has
not inspected, activated or altered any schedule.

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

The review-ready [exact schedule prompt, account checklist and harmless post-merge
acceptance plan](SUPERVISOR_HANDOFF.md) supersedes that abbreviated prompt for
issue #30. Inspect **Codex Supervisor Sync** and **Phase B Output** in the original
account before creating any duplicate. This is a prepared handoff, not evidence
of activation or a new authorization to activate it.

## Observed deployment evidence — 2026-10-16

PR #27 merged runtime e56ff96 is deployed from main. Harmless issue #28 observed
both automatic pickups, real heartbeat/process/lock evidence, snapshot continuation
without stash/reset, host private write/readback and sanitized READY_FOR_REVIEW.
The installed LaunchAgent file/cadence stayed unchanged. See the
[engineering report](../docs/reports/2026-10-16-supervisor-stabilization.md).

Official scheduled-task documentation: [Scheduled tasks](https://learn.chatgpt.com/docs/automations).
Saved schedules provide recurring wakeups; this is distinct from the local worker
poll. The current-chat heartbeat is reported ACTIVE; an observed scheduled
wakeup and verification of the original cloud schedules are still pending.
