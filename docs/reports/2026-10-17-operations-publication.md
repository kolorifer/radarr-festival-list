# Engineering report: issue #35 / supervisor task 1

**Specification:** [archived trusted brief](2026-10-17-operations-publication-brief.md).
**Result:** implemented and locally verified; READY_FOR_REVIEW.
**Repository revision:** automation/issue-35-worker, starting HEAD and local
origin/main both 92afda3004af075c165886b6705b9f79f219706d; initial checkout clean.
**Verification date:** 2026-10-17, isolated local Python 3.9.6 environment and
synthetic launcher/issue worktrees. No live operational verification.

## What changed

Successful operations previously entered code publication whenever no private
input/output capability was present. The latest trusted issue-owner task may now
explicitly select PUBLICATION_MODE: operations_only. Missing mode, or explicit
code, retains the normal code workflow. Unknown, duplicate and noncanonical
directives fail before claim/execution. No prose, issue body, stranger comment,
old task, worker state or empty diff supplies the mode.

Operations-only never enters parent add/commit/push/PR handling, even with existing
branch commits. It grants no operational authority and forbids edits/reconciliation
of this public checkout. Existing authorization, prohibitions, child credential
filtering, sandbox, locks, quota, high reasoning and permanent claims remain in
force. An existing operations checkout is never fast-forwarded; a remote branch
ahead of it fails before the child. Initial local issue-worktree creation remains
part of the existing execution setup.

The parent validates its entry baseline and compares the exact immediate pre-child
snapshot afterward, including child exceptions. Operations/private tasks refuse
unexpected branch, HEAD, staged, tracked, deletion, symlink or nonignored untracked
changes with PUBLIC_CHANGE_REFUSED and retain them. An explicitly bound unchanged
retained baseline can remain dirty in operations mode, including with private
inputs/output. This permits no new checkout changes or public publication. Other
private tasks retain their clean-finish restriction and gain exact comparison.
Detached HEAD is now fingerprintable for failure retention; normal branch
fingerprint bytes and receipt schema v1 remain compatible.

Parent-generated local execution-N.json records process exit separately from
parsed worker claims and publication/delivery. A delivery failure cannot erase an
observed normal child exit. It adds no recovery loop or destination grant. Public
operations results use PR: none and fixed fingerprint/reason text; they expressly
avoid claiming external state verification. Private artifact and diagnostic grants
remain independent with existing exact CAS/readback and ordering.

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| automation/supervisor_policy.py | Strict owner-bound publication parser; detached fingerprint support. |
| automation/github_worker.py | Publication gate, exact baseline checks, local outcome record and fixed public operations text. |
| test_operations_publication.py | 31 new synthetic regressions using separate launcher and issue worktrees. |
| test_supervisor_communication.py | Assert refusal plus failed-child observation for combined failure; make fake receipt assertion task-aware. |
| automation/SUPERVISOR_PROTOCOL.md, automation/README.md | Directive, authority boundary, compatibility, local-record semantics and recovery limits. |
| automation/OPERATIONS_ACCEPTANCE.md | Prepared harmless post-merge task and supervisor acceptance checklist. |
| docs/PROJECT_STATE.md, this report and archived brief | Scoped handoff; unrelated CODEX_TASK.md unchanged. |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Explicit trusted mode; absence preserves code publication | Implemented | Strict parser/latest-owner tests and synthetic ordinary add/commit/push/PR path. |
| Publication only; existing safety boundaries | Implemented | No new authority, credentials, network/SSH grants, claim/lock/quota/reasoning changes. Existing boundary suites retained. |
| No operations code/PR commands, including prior commits | Implemented | Synthetic parent command guards reject all add/commit/push/merge/PR calls; earlier-commit branch case and remote-advance refusal. |
| Exact checkout detection and retained continuation | Implemented | Tracked/untracked/index/HEAD/branch/detach/deletion, failed-child and pre-child-drift cases; dirty unchanged retained/private baseline accepted. |
| Distinct execution/delivery failures; no automatic rerun | Implemented | READY, NEEDS_USER, failed child, invalid result, checkout/input refusal, artifact/receipt readback and ambiguous public result cases; durable child outcome; repeated poll skips consumed task. |
| Private grants, isolation and ordering | Implemented | Synthetic canaries, filtered environment and actual local Python child; no private fixture/inventory access. Artifact/readback precedes receipt/readback and public result. |
| Focused/full tests and diff/dependency checks | Passed | 136 focused / 314 full tests; pip check and final diff/documentation verification pass. |
| Harmless post-merge plan | Prepared | Local assertion only; no public checkout edits, branch publication, PR or real deployment. |

## Tests run and results

TESTED with /private/tmp/issue35-venv/bin/python (Python 3.9.6):

- `python -m unittest -v test_operations_publication test_github_worker test_supervisor_policy test_supervisor_communication`: **136 passed**, no skips, 141.191s.
- `python -m unittest -v`: **314 passed**, no skips, 149.842s.
- Targeted rerun of private retained continuation, detached HEAD retention and
  public-result failure: **3 passed**, 10.868s, before the final suites above.
- `python -m pip check`: **No broken requirements found**.
- `git diff --check`: passed; final scoped diff and new-file/whitespace inspection
  passed. Five local links in the new brief/report/acceptance and protocol resolve.

Installed existing requirements.txt into that isolated environment; no dependency
manifest changes. Tests use temporary Git repositories, synthetic GitHub/Codex
transports and loopback-only service fixtures. No real operational boundary was
called. Detailed test logs are local temporary artifacts, not public deliverables.

## Deployment result

Not authorized and not performed. No merge, launcher/LaunchAgent/schedule change,
live smoke, Radarr/seedbox/media/service/private-inventory access, real notification
or repeat of issue #33 deployment/live resolver checks. The supervisor's statement that
the earlier deployment completed and needs no retry is supplied context, not a
fresh worker observation. This task remains an ordinary code task; parent owns its
commit/push/PR/result reporting.

## Unexpected findings

Exact checks now prioritize checkout refusal when a child both fails and changes
public files; the local execution record separately preserves that child failure.
The existing private failure/continuation regression was updated accordingly;
retention, matching backup/index patch and next-task continuation still apply.
Detached HEAD previously prevented snapshot creation; quiet symbolic-ref now uses
a stable detached marker for retention. The new task-2 private continuation test
also exposed a task-1-only assumption in the fake receipt transport; corrected
only the synthetic fixture to inspect the claimed task's delivery record.

## Unresolved issues and risks

TESTED evidence is local/synthetic. OBSERVED LIVE: none for this change. EXPECTED
BY DESIGN: the reviewed runner will skip publication for a later explicitly
authorized operations task. Host launcher deployment and harmless live acceptance
remain supervisor follow-up after review; product acceptance is pending.

Fingerprints omit ignored caches, Git metadata beyond branch/HEAD/index entries,
external state and changes reverted between observations; they are not protection
against a hostile same-account process. Unsupported/unreadable entries fail closed.
The child result proves no deployment state. A crash can leave running/started/
unconfirmed local phases, and a successful public POST is not readback-verified.
An artifact or receipt PUT may have succeeded before a failed readback. Preserve
all claims/worktrees/backups and reconcile only within separately authorized scope;
never infer that completed operations need replay merely to deliver results.

## Commit and PR reference

This worker made no commits, pushes, PRs or issue comments. The established parent
owns publication; the containing implementation commit/PR will supply references.

## Project context updates

Archived this scoped brief/report and updated project state. No decisions changed:
the trusted task explicitly specifies this publication boundary. The unrelated
legacy CODEX_TASK.md was neither executed nor changed; no new task inferred.
Review code, tests, protocol and prepared acceptance plan before any separately
authorized launcher deployment or live acceptance.
