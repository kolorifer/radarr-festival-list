# Engineering report: issue #113 Task 1 — offline coordinator integration

**Specification:** [Scoped implementation brief](2026-10-29-coordinator-integration-brief.md),
latest issue-owner supervisor Task 1 supplied to this fresh worker. Existing
D001/D005/D007 research, identity and product-ownership boundaries are preserved.
**Result:** Implemented and synthetically verified; ready for independent review.
**Repository revision:** `automation/issue-113-worker`, clean starting HEAD
`1ffa380feb63a321b6c67fdafe32b33824cb1dc4`. Parent owns the containing commit,
push, one retained PR and issue result. This worker has not published Git changes.
**Verification date:** 29 October 2026, local macOS / Python 3.9.6 worker.
No real private source, installed runtime or deployment status was inspected.

## What changed

A fingerprint-only report could be suppressed after an interrupted stdout emission
without its payload being recoverable. Both report CLIs now prepare the complete
immutable payload and suppressing transition in one fsynced atomic v2 state
commit, while holding a coordinator-owned lock across all source/state reads,
reconciliation, preparation and save. Restart and unchanged polls recover the
same ID/hash/bytes without another report, task or publication attempt.

The new offline CLI ingests an explicit five-source manifest using bounded,
no-follow regular-file reads and exact SHA256 identity. Source failures remain
available/unavailable/stale/inconsistent/partial with fixed public reasons;
reading an old file does not refresh its source. Independent engineering findings
survive missing/rejected movie evidence. Unknown times/revisions remain unknown.
The engineering input retains the foundation's owner-task authority binding,
whole-task validators and staged completion reconciliation; imported evidence is
never execution authorization.

Movie ingestion uses the actual investigations v1 validator and actual report v1
producer shape. It compares the complete known case-ID set, all base fields,
occurrence versions, coverage and eligible subset, recomputes report row hashes
and current research-material version bindings, validates times, and retains prior
proposals as retained evidence. Missing/incompatible report preserves the whole
known snapshot set with review incomplete. Private reports retain base titles and
all routes; arbitrary raw proposal fields remain in their hash-pinned staged
source for private review. CLI public projections expose only fixed source status
and outbox metadata. Even the foundation CLI cannot print a prior private staged
payload if it is pointed at the same outbox; recovery writes an explicit local
file instead.

The parent exporter reads only selected issue/task journals under an explicit
caller-supplied root. Actual existing parent writers and tests were inspected and
used to generate synthetic fixtures. Associations are checked wherever present;
consumption never crosses issues. No logs, prompts, private paths, patches,
artifact destinations or credentials are projected. Process liveness stays
unknown, and execution records retain null event time independently of read time.
A recorded code publication or terminal state cannot prove review, merge,
deployment, recipient receipt or live correctness.

Publication intent binds exact repository/issue/task and private destination to
the prepared bytes. Pending/uncertain/verified states are distinct from recipient
delivery. Offline reconciliation requires an independently pinned, externally
authenticated parent terminal receipt, its actual artifact-readback flag/reference,
matching exact destination/task/hash, staged identical report bytes and recomputed
Git blob identity. Invalid/missing/conflicting evidence cannot acknowledge; repeat
reconciliation is idempotent. No sender, credential client, network mutation or
automatic resend exists. Recipient delivery remains `not_configured`.

Production score/release review is explicitly unavailable until a passive producer
exists; unknown identity/acquisition approval remains unknown. Neither synthetic
quality rows, action state/retry scripts nor #86 scoring research is presented as
a complete production notification ledger.

## Files and components changed

| File/component | Purpose |
| --- | --- |
| `automation/coordinator.py` | Reusable validated-report reconciliation; issue-bound legacy local evidence; locked durable CLI and safe pending metadata. |
| `automation/coordinator_io.py` | Strict JSON, nonfinite/overflow rejection, confined bounded no-follow reads. |
| `automation/coordinator_sources.py` | Versioned manifest, actual movie producer contracts, independent source availability and private report projection. |
| `automation/coordinator_parent.py` | Selected read-only allowlisted parent status, conflict checks and unknown event/liveness semantics. |
| `automation/coordinator_outbox.py` | Coordinator lock, v2 migration/preparation/recovery, capacity backpressure, publication intent and exact offline receipt reconciliation. |
| `automation/coordinator_integration.py` | Offline commands, fixed public summaries and create-only exact-byte local recovery. |
| `test_coordinator_integration.py` | 44 new synthetic boundary tests and executable actual-producer-shaped rehearsal helpers. |
| `automation/COORDINATOR.md`, `automation/COORDINATOR_PILOT.md`, `automation/README.md` | Schemas, trust boundaries, reproducible rehearsal and separately scoped pilot/recurrence prerequisites. |
| `docs/PROJECT_STATE.md`, dated brief/report | Verified implementation facts, environment limits, remaining gates and handoff. |

No dispatcher, policy, terminal-receipt schema, claim/quota/publication behavior,
production/scoring/catalog, #86/#110 packet, existing sender/ledger or unrelated
`docs/CODEX_TASK.md` was changed. All 76 original coordinator methods/assertions
are preserved in an unchanged `test_coordinator.py`.

## Acceptance criteria and evidence

| Criterion | Result | Evidence / remaining gate |
| --- | --- | --- |
| 1: accepted baseline and scope | Passed locally | Clean branch/HEAD inspected; protected-file diff empty. Parent publication pending. |
| 2: offline manifest and truthful availability | Passed synthetic | Five explicit source IDs, strict identity/JSON/path/size checks; symlink ancestors/FIFO/directory/traversal rejection; stale/future/missing/hash/revision/time failures preserve other findings; status participates in material changes. |
| 3: actual movie pair | Passed synthetic | Fixture calls actual `write_report` using in-memory synthetic SQL; full cases/base fields/eligible material/coverage/versions and proposal dates checked. Complete set remains visible when report fails. |
| 4: parent allowlist and issue binding | Passed synthetic | Fixtures call actual parent record/terminal/heartbeat writers with external methods stubbed; byte/mtime/file-set checks show read-only export. #86 Task 1 cannot satisfy another issue's Task 1; conflicting journals remain inconsistent. |
| 5: durable preparation | Passed synthetic | Crash after save before emission, new-process restart, unchanged byte/ID/hash recovery, two independent processes, threads, rename failure, payload corruption/missing payload and outbox exhaustion. Pending data is never evicted. |
| 6: offline receipt reconciliation | Passed synthetic | Wrong/missing/malformed/wrong-task/hash/destination/blob/readback receipts fail; uncertain attempts stay uncertain; exact repeat succeeds idempotently; verified publication leaves recipient unconfigured. Trust/provenance is explicitly external. |
| 7: production score/release gap | Passed implementation | Unavailable source and incomplete review/unknown approval fields; passive export requirements documented without production/research changes. |
| 8: checks and supported CI | Local scoped checks passed; supported CI pending | Combined 239 checks, final 120 coordinator/integration checks after final receipt-blob binding/backpressure projection; dependency/frozen-score/diff checks. Full 3.12/3.13 CI at parent-published head still required. |
| 9: documentation and later pilot | Prepared, not activated | Exact schemas, synthetic rehearsal and operations_only preconditions documented. Installed runner/source paths/revisions/times, private grants, recurring owner and observed receipt remain unverified until later authorized tasks. |
| 10: parent handoff | Ready for review | Coherent retained diff on this issue's branch; no child commit/push/PR/comment/worker launch. |

## Tests run and results

Actual local commands (standard library additions; no dependency changes):

```sh
python3 -m unittest test_coordinator -q
python3 -m unittest test_coordinator_integration -q
python3 -m unittest test_coordinator_integration test_coordinator test_github_worker test_supervisor_policy test_supervisor_communication test_identity_automation.HandoffTests -q
python3 -m unittest test_coordinator_integration test_coordinator -q
python3 -m pip check
python3 production_scoring.py --check
git diff --check
```

- Foundation check: **76 passed**, with original assertions unchanged.
- Initial new boundary runs exposed a quality-list summary assumption and a
  reproducible concurrent macOS lock-creation race. Both were corrected. A later
  stricter parent-export edit briefly failed import validation and was corrected
  before final passing runs; no failing result is claimed as acceptance.
- Combined applicable suite: **239 tests passed in 66.427 seconds**. It includes
  dispatcher, policy, communication and handoff tests. After the final added
  receipt Git-blob comparison/fixture adjustment, the coordinator/integration
  suite passed again: **120 tests in 4.582 seconds** (44 new, 76 original), including the final
  explicit pending-material backpressure flag.
- `pip check`: **No broken requirements found**. Pip emitted only its existing
  unwritable user-cache warning; no environment/dependency installation occurred.
- Frozen scorer check passed: **1,909 candidates, 224 grandfathered, 163 new,
  387 qualified**. No scoring file changed.
- The exact Python rehearsal block in `COORDINATOR_PILOT.md` was extracted and
  executed successfully: first changed, unchanged replay, identical pending ID/
  hash/bytes, unknown parent liveness, and exact local report recovery.
- Changed-source compilation, changed/untracked whitespace, relative documentation
  links and protected-file diffs were inspected. Final results are recorded below.

Only `/usr/bin/python3` / **3.9.6** was available on PATH; neither Python 3.12 nor
3.13 nor a project virtual environment was present in this checkout. Per this
supervisor task's explicit environment exception, the known irrelevant unsupported
full-suite failures were **not rerun** and no runtime/dependency was changed.
No full local/supported-suite pass is claimed. The owner's supplied accepted
foundation CI count (1,008 per supported job) is historical evidence, not this
implementation's test result. Parent-published-head 3.12/3.13 CI and independent
review remain required before merge and the pilot.

## Deployment result

Not authorized and not performed. No SSH/seedbox, private operational state,
service, schedule, daemon, provider, Radarr/media or notification operation.
No real private publication or recipient delivery occurred. Source systems and
installed dispatcher state remain operationally unverified by this worker.

## Unexpected findings

Concurrent `O_CREAT|O_NOFOLLOW` opens of the same new lock file reproduced
`ENOENT` on macOS even while the file existed and both directory FDs identified
the correct directory. Exclusive creation plus open-existing on `EEXIST` resolved
the reproduction; the final independent-process/thread checks pass. The stable
owner-only containing directory remains a trust precondition.

The producer's current research evidence version is a digest of the eligible
research item excluding top-level observation time, not the collector occurrence
version. The staged adapter checks this distinction without tightening or changing
legacy synthetic fixture assertions. Parent execution records have no transition
time; only journal read time can be dated. A local terminal receipt is intended
parent evidence; it does not prove remote receipt publication or recipient receipt.

## Unresolved issues and risks

- Real-input compatibility/freshness/coverage and installed runner/discovery
  invocation are unverified. A later exact operations_only task must establish
  actual source/destination grants, single coordinator ownership, zero provider
  requests and private report/receipt readback; the written runbook is not access.
- Publication evidence provenance must be authenticated externally. A SHA256 pin
  alone cannot make arbitrary JSON trustworthy; this importer is offline and has
  no authentication or credential authority.
- Parent journal reads are separate bounded observations, not an atomic snapshot
  or proof of process-to-lock association. Conflicts are surfaced, never converted
  into healthy/active status.
- The outbox retains at most 20 reports, 512 KiB each, 8 MiB total. It surfaces
  backpressure rather than evicting undelivered reports. No recipient interface or
  archival policy is implemented; indefinite daily operation is not ready.
- V1 migration can reprepare a current report but cannot recover already-lost
  historical payloads or infer delivery/review/approval from old fingerprints.
- The production quality/release producer is absent. The passive follow-on export
  must preserve already-computed rating/count/design provenance and known delivery
  outcomes without new provider acquisition, scoring policy or sender ownership.
- Recurring reporting requires an inspected existing runtime/publication owner and
  an observed scheduled cycle plus actual receipt. No daily Codex task consumption,
  second executor or broad activation is introduced here.

## Commit and PR reference

The containing parent-published commit and this issue's retained PR are the change
references. Starting revision is pinned above. Independent review, current-head
CI, merge, deployment, private pilot, publication and recipient acceptance remain
separate; the worker does not assign fictitious commit/PR/operational identities.

## Project context updates

Updated project state with this implementation and its explicit unverified
operational gates; preserved older historical entries and the unrelated active
assignment. Completed brief/report remain under `docs/reports/`. Decisions and the
user notification guide are unchanged because no product decision or live
notification routing/identification/confirmation safeguard changed. Next action:
parent publication and independent exact-revision review/CI, followed only after
acceptance by a separately scoped one-report private pilot.

Final handoff verification: `git diff --check` passed; all 13 changed/new files
passed whitespace and relative-documentation-link checks; all changed Python
sources compiled; the protected-file diff was empty. The exact documented
synthetic rehearsal passed again after the final code changes. The branch HEAD
remains the accepted starting merge; the parent will supply the publication
commit/PR and run supported CI. No deployment or operational receipt is claimed.


## Task 2 correction report — 29 October 2026

**Specification:** [Completed Task 2 scoped brief](2026-10-29-coordinator-integration-brief.md#task-2--refresh-deduplication-and-source-write-boundary-29-october-2026),
latest issue-owner `SUPERVISOR_TASK: 2` supplied to this fresh worker.
**Result:** Both defects corrected; synthetic implementation verification complete,
awaiting parent publication, independent review and current-head supported CI.
**Repository revision:** Existing `automation/issue-113-worker`, clean starting
HEAD `a91d848c59b144d19a2b240400474993203add2f`, retained PR #114.
Parent owns the containing commit/push/PR/result; this worker has not published.
**Verification date/environment:** 29 October 2026, local macOS, Python 3.9.6.
No private input, source-system/host fact or operational state was inspected.

### What changed and reproduced failures

Against the exact clean starting head, synthetic staging prepared one report.
Advancing only engineering `observed_at` by one second, regenerating bytes and
updating matching observation/collection/SHA256 manifest pins produced
`changed=true`, `changed_sections=['sources']`, two pending entries. Separately,
CLI parent-export with output `<synthetic-worker-root>/113/state.json` returned
zero and removed the journal's top-level `consumed` key by replacing its bytes.
These reproductions ran before editing the implementation.

The persistent report path now compares validated findings separately from raw
serialization provenance. Only source metadata `sha256` and `generated_at` are
newly omitted from comparison; existing observation/read/collection clock
exclusions are preserved. Exact raw source-byte hash validation still runs,
private payloads retain original hashes/times, and all other hashes remain.
Evidence/occurrence/report versions, explicit source revisions, task/head/result
facts, availability/freshness/reason transitions and limits remain material.
The Task 1 guide's raw-byte-material choice is **superseded**, not evidence of
accepted behavior: it retained exact provenance but incorrectly made normal
refreshes consume the bounded outbox. The original Task 1 report/brief above
remain historical evidence, including their earlier tests and pending gates.

Comparison semantics are explicitly versioned in new payloads as
`comparison_version: 2`; the state envelope/entry ID formula remain v2. A legacy
pending-v2 payload without that marker validates against the original comparison
v1. Its ID, material, bytes, payload hash, intent, publication evidence and
recipient status are retained. Polling computes an in-memory semantic baseline
from the last actual payload; a quiet refresh/restart writes no state and emits
no report, preserving the original dated provenance. A genuine transition appends
one new entry. Unknown comparison versions fail closed. Existing pure-v1
reconciliation defaults remain compatible. Old validators reject new staged
comparison-v2 reports; readers must be upgraded with writers. No downgrade or
historical payload reconstruction is attempted.

The committed pre-correction fixture was generated with the actual starting-head
outbox and synthetic source producer helpers, before the correction. Its exact
file SHA256 is `dd6cff17bd2f31169800d6cd033069e0e89daabace776355275c5e08bfdf05cc`.
It contains one unacknowledged synthetic pending-v2 entry with an explicit intent,
not fabricated historical or operational bytes/receipt. Regressions recover it
unchanged through refresh/restart, append a material change without altering it,
and separately bind a synthetic receipt to its original payload/hash/intent.
Private publication and recipient delivery remain separate facts.

The parent-export CLI now refuses outputs at or beneath the caller's worker root
before any write. It opens source/output directories without following symlinks,
checks resolved path exclusion plus source/destination ancestor filesystem
identity (including case-insensitive aliases), and rejects symlink, traversal,
hardlink and nonregular destinations. A separate existing staged directory is
supported. Mode600 temporary writes, replacement and fsync use the pinned output
directory FD, preventing a later path alias from redirecting a write into source
journals. No source directory/journal is created or modified. Failures use only
the existing fixed sanitized error. Bounded source reads remain unchanged.
The containing directories must remain stable/trusted as already required by
the staged local workflow; this is not a hostile same-account isolation boundary.

### Files and components changed

| Component | Change |
| --- | --- |
| `automation/coordinator_sources.py` | Scoped report material projection; retains raw provenance in original payload. |
| `automation/coordinator.py` | Optional report materializer; existing default semantics/assertions retained. |
| `automation/coordinator_outbox.py` | Versioned material validation and transient baseline from immutable last payload. |
| `automation/coordinator_integration.py` | Source-root exclusion and no-follow, pinned-directory parent export writes. |
| `test_coordinator_integration.py`, `tests/fixtures/coordinator-pending-v2-task1.json` | Sixteen added synthetic regression methods and exact pre-correction pending fixture. |
| Coordinator guide/pilot runbook, project state, scoped brief/report | Corrected semantics, compatibility, test evidence and remaining gates. |

No original test/assertion was removed or changed. `test_coordinator.py`, parent
exporter/read helpers, dispatcher, supervisor protocol/policy, terminal-receipt
schema, claims/locks/quota/publication implementation, scoring/catalog, #86/#110,
research packets, delivery state and unrelated `docs/CODEX_TASK.md` are unchanged.

### Acceptance criteria and evidence

| Criterion | Result / evidence |
| --- | --- |
| 1: exact baseline and scope | Clean branch/HEAD verified; Task 1 history/PR retained; changes confined to authorized helpers/tests/docs. |
| 2–3: quiet source refresh and compatibility | Engineering observation, newer unchanged parent export and coherent movie generation refresh all regenerate bytes/pins, stay fresh, return unchanged across a new interpreter, preserve pending bytes/ID/hash and state bytes. Actual evidence, occurrence version, explicit revision, engineering head/test result and freshness/availability changes append appropriate reports. Incorrect raw pins still reject. Legacy pending bytes and exact receipt binding tested. |
| 4: CLI source-write boundary | Direct state/execution/terminal/new-source output, source-root output, symlink ancestors/final/cyclic/dangling links, traversal, case alias, hardlinks and FIFO rejected with exact fixed error; all synthetic source bytes/mtimes/file sets unchanged. Separate staged output succeeds and remains mode600. |
| 5: required checks | Scoped tests, frozen-scoring and diff/compile/docs verification recorded below. Supported current-head full CI still required. |
| 6: handoff | Task 2 brief/report appended; guide/pilot/project state updated; historical Task 1 evidence retained and old choice marked superseded. |
| 7: publication/operation | Worker diff ready; parent owns retained PR #114 update. No merge, deployment, pilot, private publication or recipient-delivery claim. |

### Tests run and results

Actual commands:

```sh
python3 -m unittest test_coordinator test_coordinator_integration -q
python3 -m unittest test_coordinator_integration.RefreshTests test_coordinator_integration.ParentExportCLITests -v
python3 -m unittest test_coordinator_integration.ParentExportCLITests -v
python3 -m unittest test_coordinator_integration.RefreshTests.test_engineering_head_and_test_result_changes_remain_material test_coordinator_integration.OutboxTests.test_precorrection_pending_v2_receipt_binds_original_bytes -v
python3 -m unittest test_coordinator_integration test_coordinator test_github_worker test_supervisor_policy test_supervisor_communication test_identity_automation.HandoffTests -q
python3 production_scoring.py --check
PYTHONPYCACHEPREFIX=/private/tmp/issue113-task2-pycache python3 -m py_compile automation/coordinator.py automation/coordinator_sources.py automation/coordinator_outbox.py automation/coordinator_integration.py test_coordinator_integration.py
git diff --check
```

The first preservation run passed all **120 original coordinator/integration
tests** in 4.341 seconds. The initial added boundary set passed **13 tests**;
then the case-alias check and two engineering/legacy-receipt checks passed.
An intermediate combined applicable run passed **252 tests in 64.146 seconds**;
its code preceded the final case-alias/engineering/legacy-receipt additions.
Final containing-diff results are recorded below rather than attributed to that
intermediate run. No failing test result is claimed as acceptance.

Frozen scoring passed: **1,909 candidates, 224 grandfathered, 163 new,
387 qualified**. Changed Python sources compiled. The exact existing synthetic
rehearsal Python block was extracted from the pilot runbook and executed:
first report changed, unchanged replay preserved ID/hash/bytes, read-only parent
liveness stayed unknown and exact report recovery succeeded. Related relative
documentation file links resolved. Source/diff/fixture review is recorded below.

Only `/usr/bin/python3` 3.9.6 is on PATH; no project `.venv`/`venv`, Python 3.12
or 3.13 executable was present in the checked standard locations. Per Task 2's
explicit exception, unsupported full-suite failures were not repeated. No
runtime/dependency installation or dependency change occurred; no local supported
full-suite pass is claimed. Full Python 3.12/3.13 CI at the new parent-published
revision is required. The owner-supplied prior-head CI at `a91d848` (1,052 tests
per job, run 40939700511) and separate 120-test Python 3.12 check belong to
Task 1, were not freshly queried by this worker and do not accept this correction.

### Deployment result

Not authorized/performed. No private input/host inspection, provider acquisition,
source-system operation, deployment, activation, schedule/daemon change, live
notification/movie/download test, Git publication or task-comment publication.
Tests use synthetic task-local files, inert parent-writer fixtures and in-memory
research stores only. No worker/runner was launched as an engineering executor.

### Unexpected findings and remaining risks

Final source-boundary inspection identified case-insensitive path aliases on the
local filesystem. Resolved string comparisons alone were insufficient; directory
identity checks now reject that alias and the local regression passes. Pending
legacy reports cannot be relabeled to reflect later source times; quiet polls
therefore retain their original payload rather than rewriting provenance.

The outbox capacity/recipient workflow, absent production quality/release passive
producer, unknown journal event/liveness facts and later recurring-owner inspection
remain Task 1 gaps. This correction adds no source acquisition/sender/executor or
product policy. Forward recovery is supported; downgrading a reader after a new
comparison-v2 report is prepared is not supported.

Next gate is parent publication on PR #114, independent exact-revision review,
full supported current-head CI, then acceptance/merge. A real pilot requires a
separate **operations_only** task with verified exact source/destination grants,
a **new explicitly authorized writable derived staging/state root outside the
parent's read-only PRIVATE_INPUTS directory**, only the **final report in the
parent artifact output**, and the **exact receipt hash of the actual supplied
bytes**. Source freshness/coverage, zero provider acquisition, actual private
report/readback, restart/replay, publication and recipient delivery must each be
verified under that later authority. No current private input or host fact is
established by this code task. Recurrence still requires an observed scheduled
cycle and its receipt through an inspected existing owner.

### Commit/PR and project context

The containing parent-published commit and existing PR #114 identify this scoped
correction; the starting commit is pinned above. The worker leaves publication
to the existing parent. Project state, guide/pilot and dated brief/report record
implementation separately from independent review, supported CI, merge,
deployment, live verification, private publication and recipient delivery.
Decisions and the notification guide need no change because this correction does
not adopt a new product decision or change live notification safeguards.
The unrelated active task is preserved rather than cleared.


Final Task 2 verification: **255 applicable tests passed in 70.311 seconds**,
including all **120 original** coordinator/integration tests and **16 new**
regression methods (136 coordinator/integration tests in the combined run), plus
existing dispatcher/policy/communication/handoff checks. The final run includes
the filesystem-identity alias correction and legacy receipt test; no local skips
were reported. `git diff --check`, changed-Python compilation, synthetic runbook
rehearsal, related documentation file-link checks and protected-file/scope review
passed. The pre-correction fixture hash is unchanged. HEAD/branch are retained;
parent publication/current-head supported CI and independent review remain pending.

The canonical public [owner Task 1](https://github.com/kolorifer/radarr-festival-list/issues/113#issuecomment-6505747957)
was also read through one bounded unauthenticated public comments endpoint; it
provided context only. Latest supplied owner Task 2 remained the sole correction
authority. No CI/private endpoint, credential or host token was accessed.
