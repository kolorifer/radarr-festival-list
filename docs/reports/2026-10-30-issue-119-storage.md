# Engineering report: issue #119 Task 5 coordinator enclosing storage

**Specification:** [completed Task 5 brief](2026-10-30-issue-119-storage-brief.md), latest supplied owner Task 5.
**Result:** Implemented; awaiting parent publication, independent exact-head review and supported CI. No live commissioning.
**Repository revision:** `automation/issue-119-worker`, clean starting HEAD `7094cf7042fe67a47d6c149f2af5ba22224b34fb`; parent owns publication.
**Verification date:** 2026-10-30; local Python 3.9.6, synthetic temporary fixtures.

## What changed

The sole parent can now accept one canonical opt-in storage directive, tied to
an immutable existing PRIVATE_INPUTS pin and independent exact operations-only
artifact/diagnostic capabilities. Its selection is parsed before reservation;
filesystem validation/creation happens only after a confirmed permanent claim.
Only the effective UID's exact OS-home enclosing profile can be granted. Existing
safe intermediates are prerequisites; absent is exclusive creation, explicit
reuse is exact dev/ino. No repair, adoption, alternate root or retry exists.

No-follow descriptor traversal, exact entry spelling, numeric owner/mode guards,
bounded native ACL evidence and protected-root separation precede creation/grant.
The parent retains bounded task-bound private grant evidence, fsyncs it before
mkdir/launch, adds one exact additional child grant and revalidates immediately
before launch and after completion/failure. Unsafe changes refuse artifact/READY
publication through existing terminal codes; no receipt fields were added.

Technical choices: one fixed alias/wire spelling; conservative rejection of all
allow ACL entries; Darwin-only native ACL support, other platforms fail closed.
A synthetic native fixture exposed ENOENT for an absent ACL. ENOENT alone remains
refused: the absence path requires positive extended-security support, successful
fresh descriptor security metadata and an explicit absent-ACL property query.
Apple implementation references and bounds are in SUPERVISOR_PROTOCOL.md. Native
and mocked synthetic tests establish no actual sandbox write access or live root
suitability. The stable-owner threat model remains unchanged.

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| automation/supervisor_policy.py | Strict opt-in owner task capability prerequisites |
| automation/github_worker.py | Pre-reservation selection; post-claim preparation, exact command/prompt grant, durable private evidence and checks |
| automation/coordinator_storage.py | Bounded fixed-profile filesystem and Darwin ACL guard; no CLI, transport or recovery |
| test_coordinator_storage.py | Synthetic real parent/child-command/publication integration and ACL regressions |
| automation/SUPERVISOR_PROTOCOL.md | Schema, guards, failure codes and private inspection route |
| automation/COORDINATOR_OWNER.md | Enclosing grant versus future anchored adapter base/intent boundary |
| automation/OPERATIONS_ACCEPTANCE.md | Exact-head launcher update and later harmless probe sequence |
| docs/reports/2026-10-30-issue-119-storage*.md; docs/PROJECT_STATE.md | Completed brief, report and verified handoff facts |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Latest owner opt-in and exact immutable selection | Synthetic pass | Parser and full pinned-input parent boundary; ordinary/older/untrusted tasks preserve defaults |
| Confirmed claim before root mutation | Synthetic pass | Lost/failed claim has no root, grant or terminal upload; interruption retains consumed state |
| Exclusive creation / exact safe reuse | Synthetic pass | Private empty root only; preexisting/missing/mismatch/unsafe entries refused without repair |
| Descriptor/owner/mode/ACL/spelling/separation/race checks | Synthetic pass | Temporary homes; native ACL fixture plus mocked unsafe/unsupported cases and before/after replacements |
| Exact one extra grant, child isolation and publication safeguards | Synthetic pass | Sole fake child command, filtered environment/locks/model, input/checkout immutability and refused artifact on changed storage |
| Receipt/claim/locks/quota/cap preservation | Unchanged contracts | No terminal_receipt.py, quota parser, acquisition or scheduling changes; existing regressions run below |
| Deployment and actual child write/readback | Not executed | Supervisor sequence prepared; no live access/commissioning claim |
| Supported exact-head CI and independent review | Pending | Existing Python 3.12/3.13 workflow must run on parent-published commit |

## Tests run and results

- `python3 -m unittest test_coordinator_storage -v`: **37 passed**, including the
  native Darwin ACL temporary fixture and parser-to-parent-to-child command tests.
- `python3 -m unittest test_github_worker test_supervisor_policy test_supervisor_communication test_operations_publication test_coordinator_owner -v`:
  **178 passed**; claims/cap/quota/retention, pinned inputs, receipts/readback,
  operations fingerprints and coordinator-owner regressions.
- Full `python3 -m unittest -v`: **913 run, 109 errors, 2 Linux-only skips,
  no assertion failures**. This is **not a passing full-suite result**. Errors:
  84 missing `requests` imports, 9 missing `bs4` imports, 10 unavailable
  `unittest.TestCase.enterContext` uses, 3 unavailable Python/SQLite exception or
  constant APIs, and 3 local HTTP fixture disconnects. No storage/parent assertion
  failure remains. Fresh supported exact-head CI is required.
- `PYTHONPYCACHEPREFIX=<task-specific temporary cache> python3 -m py_compile automation/github_worker.py automation/supervisor_policy.py automation/coordinator_storage.py test_coordinator_storage.py`:
  passed on Python 3.9.6.
- `python3 production_scoring.py --check`: passed, unchanged frozen counts
  (1909 candidates, 224 grandfathered, 163 new, 387 qualified).
- `git diff --check`, final diff/privacy review and preservation comparison:
  passed. CODEX_TASK.md, DECISIONS.md, terminal receipt module and plist unchanged;
  launcher quota-parser code unchanged.

No project virtual environment exists in this checkout; no dependencies were
installed or changed. The local runtime is unsupported Python 3.9.6; this does
not substitute for supported exact-head CI. All integration edges are fake, with
real temporary Git/filesystem fixtures; no Codex, GitHub mutation or remote
integration was run.

## Deployment result

Not deployed. No live private input, selected account home/root, source/key,
service, journal or seedbox was explored. No actual persistent target, adapter
state, report cycle, acquisition, notification, daemon or schedule was created or
changed. Source sharing/ACL remediation remains outside this task. The supervisor
must independently review the exact parent-published commit and CI, verify the
current clean deployed revision and preserve its quota correction while applying
only the narrow launcher update under existing locks. The planned separate owner
task probes one newly selected disposable file, retains evidence and checks exact
private readback, unchanged checkout and no replay. Installation enables nothing.

## Unexpected findings

The native temporary fixture exposed the Darwin absent-ACL distinction described
above; a stricter corroborated descriptor check handles it without treating API
failure as absence. An initial py_compile invocation could not write the system's
default cache; final compilation uses a task-specific temporary cache instead.
No HOME/TMPDIR or child boundary was changed. Initial runs before the native ACL
correction and explicit unsafe-mode fixture setup are superseded by the final
runs recorded here.

## Unresolved issues and risks

Independent review and fresh supported 3.12/3.13 CI remain required. Live filesystem
ACL support/ancestry and actual sandbox write access require the supervisor's
bounded later acceptance. Unknown platforms, permissions/ACLs or changes fail
closed; created or uncertain roots require private inspection and a new explicit
task/pin, never automatic cleanup/replay. A same-account hostile process or changes
made and reverted between observations remain outside the existing threat model.
No claim is made about source freshness/sharing, downstream access, report delivery,
original-supervisor ingestion, archival or recurrence.

## Commit and PR reference

The existing parent owns commit/push/PR and issue reporting. The containing
parent-published commit/PR supplies this report's immutable reference; this child
made no Git publication or issue comment.

## Project context updates

PROJECT_STATE.md records implementation separately from deployment, verification
and acceptance. The unrelated assigned CODEX_TASK.md is preserved byte-for-byte;
Task 5's completed brief/report are archived here instead. Decisions, movie
notification behavior/guide, scoring, retained execution history, old outboxes,
#86/PR #110 and all unrelated components remain unchanged. No follow-up task was
assigned autonomously.
