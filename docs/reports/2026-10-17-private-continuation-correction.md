# Engineering report: issue #35 / supervisor task 2

**Specification:** [trusted review brief](2026-10-17-private-continuation-correction-brief.md).
**Result:** implemented and locally verified; READY_FOR_REVIEW.
**Repository revision:** automation/issue-35-worker; verified initial clean HEAD
580eb8e777a71f6a270950aa4e9cff76a891bb6b, the reviewed PR #36 commit.
**Verification date:** 2026-10-17, isolated local Python 3.9.6 environment with
synthetic launcher/issue Git worktrees and fake external transports.

## What changed

Task 1 incorrectly applied exact checkout fingerprint immutability to default
private input/output tasks. Exact immediately preceding CONTINUE_FROM could
authorize removing a retained partial file, yet a clean unchanged-HEAD finish
still failed PUBLIC_CHANGE_REFUSED because it differed from the dirty baseline.

The finally block still records the actual before/after comparison, including
child failure, but exact fingerprint enforcement applies only to explicit
operations_only tasks. Default private tasks retain the established clean final
public checkout and unchanged HEAD checks before private artifact publication.
Input immutability, exact continuation validation, backups, claim ownership,
private CAS/readback, sanitized results and all code-publication gates remain.
Receipt schema v1 is unchanged. Its historical public_checkout_unchanged flag
continues to mean the mode's public-checkout policy passed; the local execution
record independently records exact fingerprint equality, which may be false
after successful default private reconciliation.

Prompts now distinguish default private reconciliation from operations-only exact
baseline preservation, avoiding a clean-finish instruction on an operations-only
dirty retained baseline. The existing private failed-child regression again
expects CHILD_FAILED, matching pre-PR #36 behavior. Its backup/continuation
assertions remain; operations-only changes still take PUBLIC_CHANGE_REFUSED
priority and preserve the separate child-failure observation.

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| automation/github_worker.py | Restrict exact immutability enforcement; clarify mode-specific private prompts. |
| test_operations_publication.py | Paired real-file reconciliation regressions and parent stash/reset/clean guard. |
| test_supervisor_communication.py | Restore baseline private-child failure expectation; retain backup/continuation checks. |
| automation/SUPERVISOR_PROTOCOL.md, automation/README.md | Explain default reconciliation versus explicit operations-only immutability. |
| docs/PROJECT_STATE.md, archived brief and this report | Record review correction and verification limits. |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Default private continuation/reconciliation restored | Passed targeted tests | Separate launcher/older issue branch, real untracked synthetic marker, task 1 NEEDS_USER retention, consumed=[1], exact task 2 continuation and pinned input/output/diagnostic grants, no publication directive. Authorized marker removal finishes clean with unchanged HEAD. |
| Private artifact/receipt success and zero code publication | Passed targeted tests | Artifact bytes verified; artifact and receipt readbacks precede sanitized public result; all verification flags true; code publication disabled and no parent add/commit/push/PR. |
| Preserve partial work/backups and exact authorization | Passed targeted tests | Original tar bytes and index patch unchanged; marker bytes still in backup. Existing snapshot/path/previous-task validation remains intact; no stash/reset/clean performed. |
| Operations-only refuses same reconciliation | Passed targeted tests | Identical setup/removal plus explicit mode gives PUBLIC_CHANGE_REFUSED despite clean unchanged-HEAD finish; no artifact/code publication. Existing unchanged dirty retained baseline tests preserved. |
| Ordinary publication, input immutability, failure/race/privacy | Passed | 138 focused / 316 full tests; existing default code publication and input/history/file refusal, failed-child retention and claim race coverage retained. |
| Documentation/prompt consistency and diff checks | Passed | Mode distinctions documented and checked in paired prompt assertions; final diff/scope and 51 local documentation link targets verified. Historical task-1 report preserved and superseded in project state. |

## Tests run and results

Environment: existing /private/tmp/issue35-venv, Python 3.9.6,
include-system-site-packages=false. No dependencies or dependency manifests
changed and no installation was needed.

- Before correction, paired synthetic regression run: 2 tests, default private
  case errored at the exact fingerprint refusal, operations-only refusal passed
  (8.657s). This locally reproduces the reviewed regression.
- After correction, paired regressions plus the prior separate-launcher
  failed-child/receipt/backup continuation regression: **3 passed**, 14.992s.
- `/private/tmp/issue35-venv/bin/python -m unittest -v test_operations_publication test_github_worker test_supervisor_policy test_supervisor_communication`:
  **138 passed**, no skips, 151.165s.
- `/private/tmp/issue35-venv/bin/python -m unittest -v`:
  **316 passed**, no skips, 161.668s.
- `python -m pip check` in that environment: **No broken requirements found**.
- `git diff --check`: passed; final tracked diff and both new documents inspected.
  Link validation: **51 local link targets across 5 documents passed**.

Focused and full run logs remain local temporary artifacts under /private/tmp;
all final runs exited zero. Runtime code/tests were unchanged between the
targeted passing run and these final suites.

Only synthetic temporary Git repositories, fake GitHub/Codex transports and local
test fixtures are used. Test child execution never launches a real worker or
runner; the existing fixture's external-child case is an isolated local Python
process. No actual private repositories, inventories or credentials are accessed.

## Deployment result

Not authorized and not performed. No merge, deployment, launcher/LaunchAgent/
schedule changes, daemon installation/start, live service/configuration access,
Radarr/seedbox/SSH/media access, issue #33 retry/resolver checks, ChatGPT Work,
real notification, Git publication or GitHub writes by this child. No network
requests were needed for implementation or dependency setup. Test loopback
fixtures are synthetic; they are not live acceptance.

## Unexpected findings

The regression also changed default private child-failure precedence from
CHILD_FAILED to PUBLIC_CHANGE_REFUSED. Restoring the default contract restores
the prior exception type and reason; the existing test still exercises retained
staged/unstaged/untracked work, receipt failure and an actual next-task child.
There is no new recovery path, claim retry or retained-state bypass.

## Unresolved issues and risks

Local synthetic behavior is TESTED; OBSERVED LIVE: none for this correction.
Merge, launcher deployment, live acceptance and product acceptance remain pending
supervisor review and separate authorization. Existing fingerprint limitations
(ignored caches, external state and changes reverted between observations) and
ambiguous delivery/readback failure limits remain as documented in the protocol.
No result here establishes a deployed runtime or external operational state.

## Commit and PR reference

Correction targets [PR #36](https://github.com/kolorifer/radarr-festival-list/pull/36)
at reviewed 580eb8e. No commits, pushes, PR updates or issue comments by this
worker. The parent owns publication; the containing correction commit/PR will
supply the final reference.

## Project context updates

Archived the completed review brief and this report; updated project state with
the corrected compatibility distinction and actual final verification. No product
decision changed, so DECISIONS.md is unchanged. The unrelated legacy CODEX_TASK.md
was read for context, not executed or modified. No next task is inferred.
