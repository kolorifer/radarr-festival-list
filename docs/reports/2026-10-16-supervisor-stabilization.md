# Engineering report: supervisor infrastructure stabilization

**Specification:** [User-authorized brief](2026-10-16-supervisor-stabilization-brief.md).
**Result:** implemented; deployment and live smoke verification pending.
**Repository revision:** infra/supervisor-stabilization, based on merged main 226bdbb.
**Verification date:** 2026-10-16, dedicated macOS worker host.

## What changed

The parent now publishes explicitly authorized private artifacts with destination
state checks, GitHub blob compare-and-swap and exact private readback/SHA256.
Codex writes only a local staged artifact. Private tasks refuse public repository
changes/commits and emit fixed public statuses. All task result prose stays local.

NEEDS_USER/FAILED partial work receives a private backup and fingerprint. A new
issue-owner task can authorize only the immediately preceding exact retained
snapshot; unexplained changes remain refused. No stash/reset/discard is added.
Default worker reasoning is high. Child environments exclude host tokens/SSH
agent and ignore user integrations/rules; workspace sandbox and never approval
remain. A local heartbeat distinguishes observed parent activity from RUNNING.

## Files and components changed

| Component | Purpose |
| --- | --- |
| automation/github_worker.py | Host publication, continuation, heartbeat, sanitized reporting |
| automation/supervisor_policy.py | Strict capabilities, byte/index fingerprints, child environment |
| test_github_worker.py; test_supervisor_policy.py | Existing lifecycle plus synthetic boundary regressions |
| automation/SUPERVISOR_PROTOCOL.md; automation/README.md | Responsibilities, protocol, recovery and schedule handoff |
| docs/PROJECT_STATE.md; archived brief/report | Current verified context and evidence limits |

## Architecture and observed baseline

OBSERVED LIVE: public main is 226bdbb93652073f188cff6ed3f17f979b4e783b;
PR #25 is merged from 8259f3b. The dedicated launcher is clean but still on the
issue-24 implementation branch at 8259f3b. Its installed LaunchAgent invokes the
Python runner with --repo and --once, omits --issue, and polls every 60 seconds.
Recent polls report no eligible task; idle launchctl state is not worker liveness.

OBSERVED LIVE: host gh can access both repositories with push permissions; the
state repository is private. The preserved private operation file has blob
84df3d5acb2b4df78217ac1918b99f7d8ed2a5dd (size 50149). Its contents were not
printed or altered. The retained issue-26 checkout is clean at merged main; its
existing stash and consumed [1,2] journal remain. Permanent claim refs agree with
consumption. Issue-26 terminal comments record NEEDS_USER twice.

INFERENCE: historical Keychain denial explains the earlier child/parent mismatch;
the prior conversation alone is not a fresh credential-isolation test. Fresh
child-boundary verification is part of the harmless live smoke test.

EXPECTED BY DESIGN, verified in code/tests: LaunchAgent starts the parent;
parent owns discovery, quota, local reservation, create-only claims, RUNNING,
public Git/PR/results and private publication; Codex owns local implementation.
ChatGPT supervisor wakeups require an independent saved schedule.

## Acceptance criteria and evidence

| Criterion | Result | Evidence |
| --- | --- | --- |
| Exact private path authorization/CAS/readback | TESTED | Synthetic absent/identical/divergent/racing/readback cases |
| Private/public boundary | TESTED | Worker prose canary, private-task public-change refusal, token filtering |
| Retained partial preservation | TESTED | Real Git fingerprint/index/change cases; backup contains original bytes; no stash |
| Dispatch, locks, claims, one per poll | TESTED | Existing dispatcher/lifecycle/lock regressions |
| Quota/cooldown | TESTED | Existing stale/low/failure/backoff/fresh-clears-cooldown cases |
| Authenticated quota probe | OBSERVED LIVE | Real probe after synthetic stale-entry condition refreshed telemetry; cooldown cleared |
| Launcher merged-main normalization | Pending | Deploy only after merge/checks |
| Automatic discovery/continuation/private smoke | Pending | Harmless two-task control issue required |
| Installed LaunchAgent after deployment | Pending | Reinspect runtime command and plist hash |
| Original ChatGPT supervisor schedule | Not verified | No local automation.toml entries; original cloud schedule not enumerated |

## Tests run and results

65 focused tests pass. The full 232-test suite passes with offline test-server
sockets permitted. Restricted full-suite execution hit only ten local test-server
socket denials; the complete suite is rerun with those offline fixtures allowed.
Dependencies installed in an isolated project environment; pip check passes.
The live quota probe used its fixed read-only/tool-disabled prompt, low reasoning,
and a synthetic stale-entry condition; normal live telemetry was initially fresh.
Failure/cooldown behavior remains synthetic, not a deliberately induced live auth
failure. No Radarr/seedbox/media service was contacted.

## Deployment result

Not yet deployed at this implementation checkpoint. Preserve common-Git journals,
worktrees, stash and claim refs; update only the clean launcher to merged main
while holding the existing dispatcher lock. Installed command needs no plist edit.
Rollback is a clean switch to the recorded prior revision under that lock,
preserving all new state/artifacts and without replaying consumed task numbers.

## Unexpected findings and residual risks

The old runner exposed worker prose publicly and treated every dirty retained
checkout alike. New public comments are deliberately generic; supervisors must
read private local results for diagnostic details. Snapshot coverage excludes
ignored caches. Private artifact source staging can need recovery after a child
crash; do not remove temporary staging before securing its artifact. A private
write can succeed before a later result-comment failure; reconcile under a new
task using exact readback, never reuse/delete claims. Existing pre-upgrade partial
state needs inspected baselining, not automatic retroactive authorization.

Ordinary code-task diffs still need privacy review; there is no universal private
identity detector. Exact output capability is not a generalized private-input
stager. Original ChatGPT automation activation/next run/observed wakeup still
requires account-side inspection. See the precise schedule handoff in the
[protocol](../../automation/SUPERVISOR_PROTOCOL.md).

## Commit/PR and project context

The containing commit/PR supplies the implementation reference. Project state and
archived brief/report updated. Unrelated legacy CODEX_TASK.md is intentionally
preserved and was not executed; the current user scope overrides that stale brief.
No scoring, movie records, lists, tags, downloads, import exclusions, Radarr,
seedbox, media files or service configuration were read or modified.
