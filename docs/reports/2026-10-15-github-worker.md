# Engineering report: issue #11 / supervisor task 1

**Specification:** [archived brief](2026-10-15-github-worker-brief.md), issue body and task comment.
**Result:** implemented; awaiting supervisor review.
**Repository revision:** automation/issue-11-worker; containing commit/PR supplies the final reference.
**Verification date:** 2026-10-15, local macOS restricted workspace.

## What changed

Added an issue-driven runner that launches each task in a fresh GPT-6.1 Sol /
Medium `codex exec` process, with no resume, transcript history or ChatGPT Work.
GitHub issue comments supply the task and durable result. The runner owns scoped
commit/push/PR publication after the implementation worker returns its tests and
summary. Dry-run prints a sample eligible prompt without mutation; once polls
and executes at most one task; continuous polling is also available.

Task claims use a create-only GitHub ref plus a pre-launch durable local journal.
This makes cross-machine claims atomic and prevents replay even after ambiguous
failures or interrupted workers. Kernel flock protects linked worktrees and
stale locks; its descriptor is inherited by the worker. Up to eight consumed
iterations are allowed per issue. Quota metadata comes from primary 300-minute
Codex telemetry, never context history. <=15% remaining pauses without consuming
the task; missing/expired telemetry stops launch with NEEDS_USER.

## Files and components changed

| Component | Purpose |
| --- | --- |
| automation/github_worker.py | Runner, protocol, quota, locks, journal and GitHub publication |
| test_github_worker.py | 28 offline protocol, failure, quota, locking and publication tests |
| automation/README.md | Auth, preview/start/stop, protocol, crash recovery and operational limits |
| automation/com.example.github-codex-worker.plist | Inert macOS example, never installed or started |
| docs/reports/2026-10-15-github-worker-brief.md | Archived authorized task |
| docs/PROJECT_STATE.md | Separate implementation/review/deployment facts |

## Acceptance criteria and evidence

| Criterion | Result / evidence |
| --- | --- |
| Fresh process and default Medium | Command contract test pins gpt-6.1-sol, medium, workspace-write and never approvals |
| Dry-run, once, sample prompt | Offline lifecycle tests; no real Codex or GitHub call in tests |
| At-most-once and atomic claims | Restart, interrupted worker, remote claim and claim-conflict tests |
| Lock and stale recovery | Real local flock exclusion and killed-child recovery tests |
| Eight iterations | Eighth permitted / ninth rejected test |
| <=15% quota pause | Synthetic boundary, stale/expired/malformed/context-ignore tests |
| Commit/push/one PR/result | Simulated create/update publication tests; blocked worker never publishes |
| Setup and inactive daemon example | CLI help, documentation and plist syntax checked |
| No unrelated behavior change | Published diff limited to automation/tests/documentation |

## Tests run and results

- `PYTHONPYCACHEPREFIX=/private/tmp/issue11-pycache python3 -m unittest test_github_worker -v`: 28 passed.
- Full `python3 -m unittest -v`: 195 run, 184 passed, 11 environment errors.
  Ten existing HTTP tests cannot bind loopback sockets in this sandbox; one
  existing scoring test cannot import the unavailable beautifulsoup4 dependency.
  The unmodified baseline has the same 11 errors (167 tests, 156 passed).
- `python3 production_scoring.py --check`: 1,909 candidates, 224 grandfathered,
  163 new, 387 qualified; passed.
- `plutil -lint automation/com.example.github-codex-worker.plist`: passed.
- CLI `--help`, scoped diff review and `git diff --check`: passed.

GitHub's existing pull-request workflow runs the full suite and frozen catalog
check with installed requirements on Python 3.12 and 3.13. Its result is reported
on the PR/issue separately from local sandbox evidence.

## Deployment result

No deployment or daemon activation. No Radarr/seedbox/media access or mutations.
No previous Codex session used or resumed. No live nested worker run was started.
Local gh is unavailable and shell GitHub DNS is blocked; the authorized branch,
commit and PR are published through the authenticated GitHub connector instead.
The runner itself uses gh when operated in the documented authenticated clone.

## Unexpected findings

The bootstrap directory contained only deployment notes, with no checkout or
partial worker files. GitHub branches contained no partial worker implementation.
Retrieved the upstream ffccdd3 snapshot into an isolated local repository; existing
codex-health helper informed telemetry parsing. Large catalog blobs were fetched
separately for local tests; publication preserves all upstream data bytes.
The upstream active task file describes unrelated media work: it is preserved,
not executed or cleared. The issue prompt explicitly overrides unrelated briefs.

## Unresolved issues and risks

Live gh/Codex integration requires an authenticated, network-enabled local clone;
this workspace verifies it with synthetic integrations. A consumed number never
retries, even if interrupted before useful work; supervisor must inspect partial
work and issue a new number. Do not delete permanent claim refs. Logs/diffs stay
private under the common Git directory. Task scope is enforced through the
trusted supervisor, prompt and workspace sandbox, not a service-specific network
firewall. Use a dedicated clone/account context without media credentials.

## Commit and PR reference / context updates

The containing commit and PR are the implementation reference; WORKER_RESULT: 1
in issue #11 records the final SHA, PR and validation result. Updated project
state and archived this brief/report. Preserved unrelated CODEX_TASK.md and all
existing movie/scoring/production files. Supervisor review and optional manual
runner installation remain separate from implementation completion.
