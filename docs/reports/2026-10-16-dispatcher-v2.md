# Engineering report: issue #24 dispatcher-v2

**Specification:** [Completed brief](2026-10-16-dispatcher-v2-brief.md), issue #24,
issue-owner supervisor task 1.
**Result:** Implemented locally; ready for supervisor review.
**Repository revision:** automation/issue-24-worker, starting at 08ab5ca.
**Verification date:** 2026-10-16, local macOS, Python 3.9.

## What changed

The runner now discovers eligible owner-created open issues when `--issue` is
omitted. It paginates GitHub issues, excludes PRs/non-owner/closed issues,
validates the latest trusted task per issue, filters DONE/consumed/claimed and
max-eight issues, and chooses the oldest outstanding valid task by comment ID
(issue number breaks ties). One task runs per poll. Explicit issue selection
retains the existing issue-owner trust policy. Duplicate protocol fields and
invalid reasoning overrides fail before consumption.

A common-Git-directory dispatcher flock covers discovery and explicit overrides;
per-issue locks and atomic GitHub claim refs remain. Workers inherit both locks.
For other issue branches, retained per-issue Git worktrees preserve the launcher
checkout and upgraded dispatcher even on blocked/failed workers with partial
changes. Dirty retained worktrees stop before quota checks/claims. Worktrees are
retained for inspection rather than deleted or reset.

Unusable five-hour telemetry triggers one fresh quota-only Codex invocation in
an empty temporary directory before reservation/claim. It uses read-only sandbox,
approval policy never, disabled sandbox network/web search/shell tools/snapshots,
zero project instruction bytes, ignored user config/rules, GPT-6.1 Sol / Low,
and a fixed generic prompt. No raw stdout/stderr is retained or published. Model
transport still contacts Codex; network-disabled refers to agent execution.
Session persistence permits quota events. A 60-second timeout and clone-wide
30-minute cooldown cover failed/no-refresh probes and interruptions. Fresh
telemetry clears cooldown, even before expiry. Successful probes re-read quota:
>15% proceeds, <=15% pauses without consuming; failure reports generic NEEDS_USER.

Dry-run prints safe selection identifiers, never task prompts, and creates no
claim/journal/lock/probe/worker/worktree/publication. Git optional index writes
are disabled for dry-run. Normal logs show candidate counts, selection, quota
outcomes, invalid/exhausted candidates and lock contention.

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| automation/github_worker.py | Discovery, global locking, retained execution worktrees, safe quota refresh/backoff, private observability |
| test_github_worker.py | Existing regressions plus dispatcher, quota and real local Git worktree coverage |
| automation/README.md | Discovery, quota, lock/worktree lifecycle, CLI prerequisites, LaunchAgent compatibility |
| docs/reports/2026-10-16-dispatcher-v2-brief.md | Completed scoped specification |
| docs/reports/2026-10-16-dispatcher-v2.md | Engineering evidence and limitations |
| docs/PROJECT_STATE.md | Infrastructure implementation/verification state |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Discovery/explicit compatibility and oldest single selection | Passed offline | CLI parsing; paginated synthetic issue sets; selection independent of issue order; restart/next-poll tests |
| Closed/DONE/non-owner/PR/malformed/untrusted/max/claimed/consumed excluded | Passed offline | Focused dispatcher and existing protocol/lifecycle tests |
| Global exclusion and per-issue/atomic protections | Passed offline | Explicit-vs-discovery lock contention; inherited descriptors; existing kernel-lock/crash/claim regressions |
| Launcher preserved across other issue branches | Passed locally | Real temporary Git repositories with older issue-branch content; success/blocked/exception; retained dirty work and clean launcher verified |
| Fresh high/low quota skips probe | Passed offline | >15% launches, <=15% pauses; no probe |
| Missing/stale probe success/low/failure/no refresh/cooldown | Passed offline | Synthetic subprocess and telemetry; claim ordering, timeout/nonzero failure, cross-issue backoff, expiry and fresh-observation clearing |
| No eligible task or dry-run causes no quota probe | Passed offline | No process/claim/publication or journal/branch creation; safe stdout |
| Installed LaunchAgent invocation | Verified read-only | Actual runner ProgramArguments include --once and omit --issue; no edit required |
| Privacy/scope | Verified diff | No credentials, raw telemetry/logs, private task contents, absolute local paths or unrelated runtime changes |

## Tests run and results

- `python3 -m unittest test_github_worker -v`: 52 tests passed.
- `python3 -m unittest -v`: 219 tests ran; 218 passed, one error in
  `test_watch_annotation_does_not_score`: missing local dependency `bs4`.
  No project virtual environment is present; dependencies were not changed.
- Installed Codex CLI help/parser accepted the probe command shape. Official
  [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
  checked for shell-tool, instruction-loading and web-search controls.
- `git diff --check` and Python compilation (temporary bytecode cache): passed.

All Codex worker/quota executions in the focused tests use synthetic test doubles;
no live quota-refresh success or end-to-end live dispatch is claimed. Git worktree tests use only temporary local repositories and stub fetches.

## Deployment result

No deployment or LaunchAgent installation/reload/change was performed. Installed
invocation is already compatible with discovery; cadence, paths and log targets
were not changed. The upgraded source still needs runner publication and
supervisor activation/acceptance. No seedbox, Radarr or media operations occurred.

## Unexpected findings

The checkout has no project virtual environment and its default Python lacks
Beautiful Soup. The broader suite's single dependency error is outside this
standard-library runner change. Dry-run previously printed task prompts; this
was removed to satisfy the requested privacy boundary.

## Unresolved issues and risks

- Live authenticated quota refresh and unattended dispatch remain unverified;
  offline tests and installed CLI parsing establish behavior but not account or
  provider availability. Unsupported CLI/config/auth failures fail closed with
  cooldown and leave the task unconsumed.
- Retained worktrees consume local disk and need operator inspection if dirty;
  automatic cleanup/reset is deliberately absent.
- Dirty launcher checkouts still stop dispatch, preserving the existing safety
  precondition. Existing unrelated task instructions are unchanged.
- Product acceptance and activation are pending supervisor review.

## Commit and PR reference

The established runner owns commit, push, PR and issue reporting after this
worker returns. No commit/PR/comment was created by the worker; the containing
runner-created commit/PR will supply the final reference.

## Project context updates

Completed brief/report archived together and project state updated. The unrelated
active task in CODEX_TASK.md is preserved, as explicitly required by the current
task boundary. No product/scoring decision changed; DECISIONS.md is unchanged.
