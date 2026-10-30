# Engineering report: issue #117 supervisor Task 1 — coordinator cycles

**Specification:** [scoped brief](2026-10-30-coordinator-cycles-brief.md) and the
latest canonical owner task supplied to this fresh implementation worker.
**Result:** offline CLI/library implemented; synthetic verification completed as
recorded below; parent publication, independent review and supported CI pending.
**Repository revision:** `automation/issue-117-worker`, based on accepted main
`4e85008b161be6b57c52585cc02e8a2e9a5be636`. The parent runner owns the containing
commit/PR; this worker made no commit, push or issue/PR comment.
**Verification date:** 2026-10-30, local synthetic temporary state, Python 3.9.6.

## What changed

The legacy outbox ties reports to issue/task terminal receipts and never
acknowledges a recipient, so it cannot serve as an indefinite recurring lifecycle.
The new independent cycle module runs one actual original-byte reader collection,
combines explicitly staged engineering/parent evidence, checkpoints acquisition
identity, prepares immutable reports and offers an offline publication handoff.
It separates publication readback from ingestion by the named system recipient,
then archives the exact complete record and original source evidence before
releasing active capacity. It runs without a numbered engineering execution per
report and adds no dispatcher integration, daemon, sender or schedule.

The new component uses schema version 1 for its identity/state/envelopes/payloads
and receipts, while material comparison stays at accepted comparison version 2.
Legacy v2 formats/APIs are not changed. Cycle identity binds the original complete
request; report identity binds runtime/cycle/payload bytes; a single attempt binds
report, destination, payload hash and recipient. Intent precedes source reads;
a completed collection is retained across preparation failure. Incomplete
collection recovery finalizes the old identity as interrupted using only durable
independent evidence. It never reads newer sources under that identity.

Quiet observations update a separately dated current record without modifying
older report bytes/provenance or the archive comparison baseline. Source failure
or invalid movie pairing cannot erase independently valid engineering/parent
findings. Compatible movies retain incomplete upstream coverage and the existing
3600/172800-second freshness limits. No quality/release producer is invented.

A handoff durably records uncertainty before exposing a one-time publication
opportunity. Replays never offer another attempt, even when the first call lost
its output. The selected external owner must authenticate publication/recipient
origin before staging the offline inbox; structure, directory permissions, hashes
and exact bytes cannot themselves prove external origin. Receipt binding and
exact readback checks are enforced locally, with distinct recipient issuer and
publication issuer. Nothing here proves human reading or engineering/product/
movie/download approval.

## Files and components changed

| File/component | Purpose |
| --- | --- |
| `automation/coordinator_cycles.py` | Actual cycle, bounded owned state/staging, original-byte composition, checkpoint recovery, handoff, receipt imports and verified archival |
| `test_coordinator_cycles.py` | Synthetic behavior/rehearsal, failure injection, >20 material archives, quiet/failed polling, concurrent calls and legacy preservation |
| `automation/COORDINATOR_CYCLES.md` | Exact future owner calls, schemas, trust boundary, invariants, recovery, finite bounds and activation gates |
| `automation/COORDINATOR.md`, `automation/COORDINATOR_PILOT.md` | Distinguish new component from old issue/task outboxes and later live integration |
| `docs/PROJECT_STATE.md`, `docs/MOVIE-NOTIFICATIONS-GUIDE.md` | Verified implementation status and user-facing limits without changing live behavior |
| This report and its brief | Recoverable scope and engineering handoff |

No changes to `github_worker.py`, `supervisor_policy.py`, `terminal_receipt.py`,
legacy outbox/source/reader modules, production scoring, dependencies, launcher,
schedules or unrelated `docs/CODEX_TASK.md`.

## Acceptance criteria and evidence

| Criterion | Result | Evidence/limit |
| --- | --- | --- |
| Real reader plus explicit independent sources | Implemented, synthetically verified | Actual reader/report writer, engineering findings and parent-export validators; fixed paths and original-byte tests |
| Stable cycle identity/restart | Synthetically verified | Conflicting reuse rejected; concurrent callers acquire once; intent/independent/complete-collection/outcome checkpoints exercised; incomplete replay cannot reread sources |
| Comparison-v2 quiet/material behavior | Synthetically verified | 35 fresh-clock quiet polls retain the original report; availability transition creates one report; archived baseline survives restart |
| Exact handoff/ambiguous publication | Synthetically verified | Uncertain boundary precedes handoff; one opportunity; failed/lost attempt checkpoint never resends; create-only collisions preserve bytes |
| Distinct recipient evidence | Synthetically verified | Publication cannot acknowledge recipient; recipient-first cannot prove publication; wrong owner/issuer/identity/destination/hash/attempt/extra flags rejected |
| Safe archival and >20 reports | Synthetically verified | 25 successive material reports acknowledged/archived with original evidence; archive/state/cleanup interruptions replay safely; conflicts/capacity preserve active bytes |
| Bounded staging and retention | Implemented, synthetically verified | One disposable slot; repeated quiet/failed cycles leave no stage files; active/archive/ledger/state-byte/payload bounds expose backpressure; no history deletion |
| Filesystem/privacy | Synthetically verified within stable owner-directory assumption | No-follow traversal, source/checkout identity exclusions, source/owned hardlink/symlink rejection, owner-only state, fixed public projection, I/O/fsync/readback/descriptor tests and secret sentinels |
| Legacy preservation | Verified by diff and synthetic legacy tests | Unchanged modules/fixture bytes; existing legacy recovery/receipt suite passes; no old-state migration/reconciliation |
| Reproducible CLI/library rehearsal | Synthetically verified | CLI collection subprocess, every lifecycle CLI command with fake-owner adapter, actual reader plus independent source fixtures |
| Required local checks | See exact results below | Unsupported runtime/dependency failures are retained; no dependencies installed |
| Live integration/current-head CI/review | Not verified here | Separate parent/supervisor gates; no host/runtime/private source/recipient/publication inspection or activation |

## Tests run and results

The only available interpreter was `/usr/bin/python3`, Python **3.9.6**. No project
virtual environment or supported 3.12/3.13 executable was available through the
local repository/PATH inspection. No dependencies were installed or changed.
Commands used `PYTHONPYCACHEPREFIX=/private/tmp/issue117-pycache` because the default
Apple cache location is outside the writable sandbox. Test logs stay under the
new synthetic `/private/tmp/issue117-*` paths, not in repository artifacts.

- `python3 -m unittest test_coordinator_cycles test_coordinator_exports test_coordinator_integration test_coordinator -v`: **199 passed** (41 new cycle tests plus 158 preserved coordinator/reader/export/integration tests).
- `python3 -m unittest -v`: **830 run; 109 errors, 2 skips, no assertion failures; not passing on this unsupported local environment**.
- `python3 -m compileall -q automation test_coordinator_cycles.py test_coordinator_exports.py test_coordinator_integration.py test_coordinator.py`: **passed**.
- `python3 production_scoring.py --check`: **passed**, candidate 1909,
  grandfathered 224, new 163, qualified 387.
- `git diff --check`, new-file whitespace checks, local documentation-link checks
  and explicit protected-file diff checks: **passed**; 137 local documentation targets verified; protected files unchanged.

The final full-suite environment failures include missing `requests`/`bs4`, unsupported
Python 3.9 `unittest.TestCase.enterContext` and SQLite exception/error-code APIs,
and dependent local HTTP/queue failures. The 109 errors comprise 84 missing
  `requests`, 9 missing `bs4`, 10 missing `TestCase.enterContext`, 3 unsupported
  SQLite error-code/exception APIs and 3 dependent HTTP disconnects. An
  intermediate overlapping run also
  had one deadline-test assertion (`malformed_response` versus `transport_failure`);
  that unchanged test passed in the later full run and an explicit isolated rerun:
  `python3 -m unittest test_identity_research.AdditionalGates.test_response_absolute_deadline_and_secret_echo -v`
  (**1 passed**). These full-suite results are not passing checks. Fresh
exact published-head Python 3.12/3.13 full CI remains required. Earlier reader
acceptance/CI and intermediate local test runs are not current-head acceptance.

The reproducible end-to-end commands are in the
[owner runbook](../../automation/COORDINATOR_CYCLES.md#synthetic-rehearsal-and-later-activation-gates).
The fake owner stages selected publication readback and separate recipient
receipts using only temporary synthetic fixtures. Test coverage includes coherent,
missing, stale, conflicting, partial and inaccessible sources; independent-source
failures; exact original bytes; cycle conflicts/concurrency; interrupted recovery;
quiet refresh; one material transition; single-attempt ambiguity; receipt trust
context/binding conflicts; pending/archive/capacity backpressure; bounded staging;
archive verification/fsync/state/cleanup failures; recognized transient-link
recovery and descriptor cleanup. No real/private inputs or publication were used.

## Retention choices and technical rationale

The active cap remains 20 for this component; verified archival, rather than a cap
increase, permits >20 completed material transitions. Archives retain up to 256
complete records/256 MiB, active envelopes up to 128 MiB with receipt growth
reserves, the cycle ledger up to 4096 identities/4 MiB, one staging slot up to
64 MiB/32 declared files, report payloads up to 512 KiB and original evidence up
to 8 MiB per record. Envelope/collection bounds are 12 MiB. Handoff copies add at
most 10 MiB, current observations 512 KiB, and fixed atomic temporaries at most
12 MiB beyond stable files. The runbook gives full accounting. Count/byte limits
include the source bytes/references embedded in archives; no uncounted retained
source bundle is left elsewhere.

The ledger keeps quiet cycle identities so a later caller cannot silently reuse
an old ID to acquire newer bytes. This deliberately has a finite horizon, with
backpressure and no automatic deletion. A later retention decision must not
silently migrate or remove existing history. Unknown files or unsafe link/
ownership substitutions stop cleanup. A failed initialization leaving an
unmarked root is rejected without adoption; preserve it and select a fresh root.
Concurrent initialization can require identical retry; collection itself is
serialized and at-most-once. A full active set stops new acquisition, including
quiet polls, until completed reports release capacity. This is conservative
bounded operation, not a claim of an indefinitely activated daily service.

## Deployment result

Not deployed or activated; operational work was forbidden. No SSH/seedbox,
credentials, real/private state retrieval, source refresh, provider research,
notification, Radarr/media/download mutation, actual private publication or
recipient action occurred. No daemon, runtime, launcher or schedule was installed
or started. The parent runner retains all Git publication/CI/reporting ownership.

## Unexpected findings

The accepted reader's create-only bundle cannot be reused after interruption.
The cycle therefore retains its own independent checkpoint and completed
collection, composing exact source copies through the existing validators rather
than modifying the reader bundle. Recognized temporary publication hardlinks need
explicit recovery before strict permanent-file hardlink checks; only generated
files in this new owned namespace are eligible. Archive reference updates and
active reclamation are deliberately separate durable steps.

The combined investigation scan service can also run provider research. Later
source-timing inspection must not treat invoking it as a read-only refresh. No
request budget or source producer policy is chosen in this task. Historical
issue #113 Task 8's precise source rejection remains unknown.

## Unresolved issues and risks

External receipt provenance remains the accountable owner's responsibility. An
identical forged receipt/readback from a dishonest owner is indistinguishable
offline; a hash pin or success flag is not authentication. The owner-selected
inbox itself needs separately bounded external adapter retention. The component
assumes stable owner-controlled directories and fails closed on I/O/collision/
unsafe cleanup, potentially retaining capacity until the same identity resumes.
The finite archive and cycle ledger eventually require an explicit owner capacity
policy; no history eviction or migration is supplied.

Fresh supported current-head CI and independent review are pending. Live source
timing/runtime/launcher inspection, exact transport/destination/recipient wiring,
one actual cycle with authenticated destination/recipient evidence and recurrence
verification require a later bounded task. Production quality/release export
remains unavailable; neither valid movie pairing nor a report receipt fills that
gap or grants approval. No broader activation is claimed.

## Commit and PR reference

The containing parent-published commit/PR on `automation/issue-117-worker` supplies
the final revision reference. At worker handoff the checkout HEAD remains accepted
baseline `4e85008b161be6b57c52585cc02e8a2e9a5be636` with the scoped diff awaiting
the runner. This worker did not publish, merge, deploy or post comments.

## Project context updates

Saved this completed scope and report under the requested date/name. Added the
new owner contract and appended current-code facts to coordinator/pilot/user
guides; prepended implementation/verification/acceptance distinctions to project
state. Decisions are unchanged because no new product policy was chosen.
The unrelated active task is preserved byte-for-byte, as required by the canonical
supervisor task. Parent/supervisor review should assess this component and fresh
supported CI before defining its separate bounded integration task.
