# Engineering report: issue122 Task2 final finite-route correction

**Specification:** [saved Task2 brief](2026-10-31-issue-122-correction-brief.md),
owner supervisor Task2 and independent [review6542515755](https://github.com/kolorifer/radarr-festival-list/issues/122#issuecomment-6542515755).
**Result:** Scoped corrections implemented; exact-revision independent review,
supported CI, deployment and live acceptance remain separate gates.
**Repository revision:** Clean starting `automation/issue-122-worker` at
`70ad14ebf23c1f68e79a6a073056c0d29303e465`, [PR123](https://github.com/kolorifer/radarr-festival-list/pull/123).
The existing parent alone publishes the correction's containing commit.
**Verification date:** 2026-10-31; native macOS Python3.9.6/OpenSSH9.0p1, synthetic
fixtures and connection-free SSH configuration evaluation only.

## What changed

OpenSSH closes inherited descriptors above 2 before interpreting identity options.
The route now gives it the already selected exact canonical credential paths.
The parent and fixed keeper hold/revalidate file and ancestor descriptors,
namespace/spelling, trusted OS-account ownership, modes/ACLs, device/inode,
hardlink count and byte bounds before/after use. The dispatcher/keeper never
read/copy/hash/stage private-key bytes. OpenSSH opens the original files itself;
no agent, ambient config, relaxed authentication, repair or alternative path is
introduced. This is stable-owner change detection. It does not offer atomic
protection against a hostile same-account pathname swap-and-restore.

Deterministic local credential preflight now precedes phase consumption, remote
claim, evidence/adapter creation, owner reservation and acquisition. Optional
independent original-export reads also wait for that preflight, so a bad local
credential cannot fetch them. The existing OS-account home override is preserved,
including short SSH-parent paths and safe system ancestors. Credential evidence
remains held around transport; later changes fail closed before publication.
Remote source checks still follow the one durable acquisition grant.

A small fixed forked transport keeper holds both inherited dispatcher lock
*descriptions* while it supervises one SSH child; SSH receives no lock or
credential FDs. Parent death therefore does not release locks while SSH is active.
There is no keeper CLI, request-supplied command/script protocol, daemon, scheduler,
worker or retry. Only the reviewed fixed transport code executes. The single
child has a 45s deadline, 6 MiB stdout and 16 KiB stderr bounds; failure kills/reaps
only that child. Keeper transfer is bounded 5s, parent wait 55s. Diagnostics remain
in private pipes. Normal completion reaps the keeper; initiating-parent failure
never kills a still-active keeper out from under its own SSH cleanup.

The fixed remote command is `/usr/bin/python3 -I -B -`. Before source path access,
actual effective UID must be non-root and equal the selected numeric UID, and
effective GID must equal the selected GID. A separate 30s remote alarm bounds
helper execution after code loading even if SSH disappears. The same two fixed
read-only exports and original bytes/timestamps/no-follow/spelling/identity/
owner/mode/ACL/hardlink/size/race checks remain intact. Bytecode writes are
explicitly disabled; no remote write, source refresh, DB or provider call is added.

Dispatcher closed/latest-trusted DONE semantics now precede reporting selection.
A guarded, bounded, structurally/request/start/pin-bound local scheduling filter
excludes consumed starts, inert reconciles and archived acknowledgements before
private-input fetch or full runtime validation. Other issues can progress in
ordinary discovery. Malformed/unbound state grants no work. An ambiguous claim
or pre-publication interruption permits no reconciliation work. Fresh explicit
matching reconciliation remains possible after uncertain publication; the same
consumed reconcile can finish exact receipt import only with its anchored durable
publication observation. Genuine matching acknowledgement/archive interruption
continues idempotently. Scheduling eligibility itself proves no success: runtime
still reauthenticates comments, immutable selection and exact retained evidence
before any continuation effects.

Accepted owner/cycle/source/receipt schemas, durable publication-observation
recovery, honest owner-selected recipient contract, original source freshness,
one acquisition/PUT/cycle, issue122 cap 2, general cap 8 and issue119's exhausted
eight claims/history are preserved. No history, quota, retained state, operational
configuration, unrelated task or production/research behavior is changed.

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| automation/coordinator_transport.py | Supported original credential paths, fixed bounded forked keeper, remote effective identity/no-bytecode/deadline guards |
| automation/coordinator_runtime.py | Local credential preflight/held revalidation before effects; deferred optional source reads; bound scheduling state and interrupted observation recovery |
| automation/github_worker.py | DONE before reporting; exclude inert reporting candidates while preserving ordinary engineering |
| test_coordinator_runtime.py | Native SSH configuration, isolated parent-death/FD-close locks, bounds, credential preflight/race, discovery/DONE/quiet/recovery and malformed-state regressions |
| automation/COORDINATOR_RUNTIME.md | Correct exact commands, credential/lock guarantees, finite recovery and already-authorized supervisor protocol; same 20-file closure |
| Saved Task1 brief/report | Explicit correction links/erratum, preserving historical tests and original report |
| Saved Task2 brief/report; docs/PROJECT_STATE.md | Corrected handoff with implementation/validation/deployment/live facts separated |

## Acceptance criteria and evidence

| Criterion | Evidence and remaining gate |
| --- | --- |
| Exact baseline/review/scope | Actual clean branch/HEAD matched 70ad14e; PR123 metadata and review6542515755 read; Task1 brief/report/runbook and relevant repository records inspected |
| Supported SSH credential handoff | Native `/usr/bin/ssh -G` uses exact generated authentication argv with harmless temporary files, confirms accessible selected identity and known-host paths; no server/DNS connection or real key |
| Actual inherited lock lifetime | Isolated initiator is killed after its synthetic transport child proves lock FDs closed; both locks remain contended until keeper finishes that one child, then release |
| Preflight before consumption | Missing/mode/symlink/spelling/inode/owner/ACL/ancestor/same-file/empty/oversize/hardlink key fixtures and unsafe/missing known-host fixtures produce zero journal, claims, adapter, acquisition or publication; optional independent-source fetch is also excluded |
| Stable evidence and account profile | Real fixture descriptors/no-follow/postcheck replacement; short canonical .ssh parent plus safe system-ancestor and OS-account-home checks |
| Stop/idle/discovery/recovery | Real discovery with consumed and archived issue122 plus newer different-issue work; DONE/closed; no private fetch/full validation for inert commands; weak-state refusal; same genuine interrupted reconcile/ack/archive completion |
| Remote process boundary | Root/mismatched effective UID/GID rejected before chain access; fixed helper exits 124 on its synthetic remote alarm; -B explicit; existing source guards retained |
| Bounds/cleanup/privacy | Synthetic keeper pre/postcheck execution and local timeout; bounded stdout/stderr tests; no public private-payload diagnostics; no retry or extra transport connection |
| Existing engineering and coordinator behavior | Final focused and full results recorded below; unchanged accepted schemas/caps/claims/quota/isolation and retained history |
| Supported CI/live acceptance | Correction exact-head3.12/3.13 CI and independent review required; deployment/publication/genuine chat ingestion/archive NOT performed by this child |

## Tests run and results

Before the final additional journal-schema refusals, the broad focused command
passed **470 tests** (not presented as an exact-final-source run):

```sh
python3 -m unittest test_github_worker test_supervisor_policy test_supervisor_communication test_operations_publication test_coordinator_storage test_coordinator_owner test_coordinator_runtime test_coordinator_cycles test_coordinator_exports test_coordinator_integration test_coordinator -v
```

Final frozen-code runtime/native command:
`python3 -m unittest test_coordinator_runtime -v` — **44 passed**. This includes
all final journal-schema refusals, native connection-free SSH, actual orphan-lock
retention, keeper output/deadline/pre/postchecks, preflight zero effects, real
discovery/DONE/quiet polling and genuine receipt/archive recovery.

Final frozen-code repository-required full command:
`python3 -m unittest -v` — **957 run,109 errors,2 skips,zero assertion failures**
(482.618s). All 44 runtime/native cases passed in this run too. **This is not a
passing full-suite result.** The 109 errors are 84 missing `requests`, 9 missing
`bs4`, 10 unavailable `unittest.TestCase.enterContext` uses, 3 unavailable SQLite
APIs (one `sqlite_errorcode`, two `SQLITE_BUSY`) and 3 existing HTTP fixture
`RemoteDisconnected` errors. These categories/counts match the retained Task1
local baseline; no dependency/API remediation outside this task was attempted.
The two skipped cases require Linux seccomp / Linux x86-64 and are unrelated to
the new transport tests. Only this one full-suite execution was run in Task2.

All 20 runtime closure files and the regression module compile; Python3.9 grammar
checks pass. `python3 production_scoring.py --check` passes with unchanged 1909
candidates, 387 qualified (224 grandfathered, 163 new). Final diff/privacy review,
documentation links and preservation comparisons pass for the unrelated active task, decisions, accepted storage/owner/
cycle/policy/receipt modules, dependencies and supported CI workflow. All 21 frozen
source/test hashes were rechecked unchanged after both final suites.

There is no project virtual environment in this checkout. Commands use available
Python3.9.6 with `PYTHONPYCACHEPREFIX=/private/tmp/issue122-task2-pycache`.
No dependencies were installed or changed; no dependency check is newly required.
The existing supported3.12/3.13 PR workflow must pass on the parent-published
correction before supervisor acceptance. Baseline CI41194779483 belongs only to
Task1's 70ad14e and is not a result for this patch.

Development-only results: native transport 9 passed. A preliminary runtime
run executed 43 tests: 42 passed and one test-fixture origin mismatch
error; the fixture was corrected to the synthetic repository. A subsequent 11-test
native/boundary check passed, including both published/archived discovery and
ambiguous-claim quietness. These are not substituted for final frozen-code runs.
No overlapping full suites or runtime source edits during code-hash fixture runs
were performed. Final runtime/test hashes are checked after validation.

## Deployment result

**Not deployed. No live pilot or server connection.** No real key/home/private
state/root/source exploration, seedbox/SSH connection, host service/configuration,
source refresh, provider/research, media/Radarr/download/notification, permission
repair, schedule/plist, paused watch, Work, subagent, worker/runner launch, Git
publication or issue comment was performed. Only harmless native `ssh -G` and
isolated synthetic subprocesses exercised the transport boundary.

Supplied deployed launcher 229148 and accepted issue119 Task6/Task8 host facts
were not re-inspected. Installing reviewed code activates nothing. The supervisor
owns independent exact review and supported CI, bounded selective installation,
then the ALREADY AUTHORIZED one supervised partial cycle and later genuine
coordinator ingestion/owner-selected acknowledgement/verified archive. The
[runbook](../../automation/COORDINATOR_RUNTIME.md) supplies the same exact private
selection/command protocol and 20-file closure. No new engineering task or generic
approval question is required for that fixed sequence. No third execution or
recurrence is authorized.

## Unexpected findings

The scheduling fix must operate before constructing Runtime; otherwise inert
starts still fetch private pins and block unrelated discovery. It must preserve
interrupted publication-observation import without retrying failed readback, so
only a bound retained observation permits the same consumed reconcile to resume.
Optional independent export reads were moved after structural local credential
preflight; they remain original explicitly pinned evidence.

## Unresolved issues and risks

Local 3.9 dependency/API limitations do not establish a passing full suite; exact
supported CI and independent review remain acceptance gates. SSH path opening
requires the accepted stable-owner threat model; it cannot provide hostile
same-account atomicity. Structural local preflight does not verify remote login
or source freshness. No authentication/ACL/path fallback is supplied. Losing the
parent during transport leaves the opportunity consumed and the keeper safely
finishes/cleans only its child; it does not resume preparation/publication or
invent missing evidence. Pre-handoff interruption can still make the one
opportunity impossible to complete automatically. No live success is inferred
from synthetic mechanics or journal scheduling state.

Recipient authentication remains **owner-selected acknowledgement after actual
designated-chat ingestion**, not proof from JSON issuer/hash, sender readback or
an engineering terminal receipt. Actual immutable publication readback, genuine
distinct ingestion selection and verified archival are separate unrun gates.
A successful partial cycle makes no full movie-coverage claim. All eight issue119
claims and their exhausted cap remain intact; no third correction follows.

## Commit and PR reference

The existing parent alone commits/pushes/updates PR123 and posts the terminal
result. This report's containing parent revision supplies the correction's exact
code reference. The worker has not published or requested CI on its own.

## Project context updates

The saved Task2 brief/report, corrected runtime runbook and project state preserve
the handoff. Task1 brief/report carry explicit supersession links without erasing
historical results. Unrelated CODEX_TASK.md, decisions, notification guide (no
live routing change), #86/PR110, policies, accepted owner/cycle modules, histories,
production/research and operational configuration remain unchanged.
