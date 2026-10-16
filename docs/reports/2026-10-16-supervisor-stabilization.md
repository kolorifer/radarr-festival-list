# Engineering report: supervisor infrastructure stabilization

**Specification:** [User-authorized brief](2026-10-16-supervisor-stabilization-brief.md).
**Result:** implemented, merged and deployed; harmless live acceptance loop observed.
Original cloud ChatGPT supervisor wakeup remains unverified.
**Repository revision:** [PR #27](https://github.com/kolorifer/radarr-festival-list/pull/27),
implementation 869f4a5, merged/deployed runtime e56ff969a9c621b6e02083604408f53e3f322d55.
Final evidence is a documentation-only follow-up from merged main.
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

INITIAL OBSERVED LIVE: public main was 226bdbb93652073f188cff6ed3f17f979b4e783b;
PR #25 is merged from 8259f3b. The dedicated launcher was clean but still on the
issue-24 implementation branch at 8259f3b. Its installed LaunchAgent invokes the
Python runner with --repo and --once, omits --issue, and polls every 60 seconds.
Recent polls report no eligible task; idle launchctl state is not worker liveness.

OBSERVED LIVE: host gh can access both repositories with push permissions; the
state repository is private. The preserved private operation file has blob
84df3d5acb2b4df78217ac1918b99f7d8ed2a5dd (size 50149). Its contents were not
printed or altered. The retained issue-26 checkout is clean at its original merged-main revision 226bdbb; its
existing stash and consumed [1,2] journal remain. Permanent claim refs agree with
consumption. Issue-26 terminal comments record NEEDS_USER twice.

OBSERVED LIVE: the fresh sandboxed child reported GH_TOKEN/GITHUB_TOKEN and
SSH_AUTH_SOCK absent and its bounded gh identity call failed. Parent private
publication succeeded separately. No credential contents were retrieved or printed.
INFERENCE: this is consistent with the historical Keychain/sandbox mismatch; a
network-disabled failed identity call alone does not isolate Keychain denial as
its unique cause. The enforced environment/config/sandbox boundary is separately
tested; no claim of a hostile same-account credential-exfiltration audit is made.

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
| Launcher merged-main normalization | OBSERVED LIVE | main at merged e56ff96; retained worktree/stash/plist unchanged |
| Automatic discovery/continuation/private smoke | OBSERVED LIVE | Issue #28 tasks 1/2; exact backup-to-private readback; public READY_FOR_REVIEW |
| Installed LaunchAgent after deployment | OBSERVED LIVE | --once, no --issue, 60s; unchanged plist SHA256; exit 0 after smoke |
| Original ChatGPT supervisor schedule | Not verified | No local automation.toml entries; original cloud schedule not enumerated |

## Tests run and results

65 focused tests pass; GitHub CI Python 3.12/3.13 both pass. The full 232-test suite passes with offline test-server
sockets permitted. Restricted full-suite execution hit only ten local test-server
socket denials; the complete suite passed when those offline fixtures were allowed.
Dependencies installed in an isolated project environment; pip check passes.
The live quota probe used its fixed read-only/tool-disabled prompt, low reasoning,
and a synthetic stale-entry condition; normal live telemetry was initially fresh.
Failure/cooldown behavior remains synthetic, not a deliberately induced live auth
failure. No Radarr/seedbox/media service was contacted.

## Deployment result

OBSERVED LIVE: launcher switched from the stale implementation branch to merged
main under the clone-wide dispatcher lock. Existing issue-26 HEAD/clean state,
stash ref, journals and permanent claims were preserved. Installed plist SHA256
remained 3fc18b1ab766e9b3430be4ad31adc1b173974d5316bc5b5ba96c45e4695e34de;
no plist edit, reload, service installation or cadence change was needed.

[Issue #28](https://github.com/kolorifer/radarr-festival-list/issues/28) is a purely
synthetic acceptance test. Task 1 was posted at 17:32:01 Europe/Warsaw, picked up
17:33:04 and ended deliberate NEEDS_USER at 17:33:37. The private tar and retained
file matched exact synthetic bytes. A new high-reasoning task authorized its exact
snapshot. Automatic pickup at 17:35:02 continued without stash/reset, copied the
marker into approved staging and reconciled only the untracked synthetic fixture.
During execution a fresh heartbeat and PID with PPID 1 were observed; both global
and issue locks rejected second acquisition. This is process evidence beyond
RUNNING. One distinct LaunchAgent poll executed each task.

The parent published only the authorized private operations path, commit
65d0f94c742620c11f28ffd7d8d5b9a69a15b63e at 17:35:46, then posted sanitized
[READY_FOR_REVIEW](https://github.com/kolorifer/radarr-festival-list/issues/28#issuecomment-6218974396)
at 17:35:48. Independent readback exactly matched the original backup and durable
staged copy: blob 79800a5cf54ad49a9556ff6bcb35b824f7068044, SHA256
7ae3a2ae19a9436feb8c7e86db53cf3182b28bd1a0dfadbc18f9ae94dc9ac6c5.
A further live-destination divergence check refused before PUT; the verification
harness additionally prohibited any PUT. The smoke checkout is clean; the original
partial backup and unrelated existing stash remain intact. No empty smoke PR was
needed. Public result checks found no artifact content or local paths.

Claim refs issue-28-claim-1 and -2 both point to deployed e56ff96; consumed journal
is [1,2]. After execution heartbeat is inactive, LaunchAgent exit code is 0.
The pre-existing private research artifact still has the original blob/size.
Rollback: hold the dispatcher lock and switch the clean launcher to the recorded
prior runtime; preserve all new state/artifacts and never replay consumed numbers.
The evidence-only follow-up changes no runtime bytes and is deployed from main.

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
requires account-side inspection. A hard process kill before terminal snapshot
recording also requires inspected recovery; at-most-once claims are not retried. See the precise schedule handoff in the
[protocol](../../automation/SUPERVISOR_PROTOCOL.md).

## Commit/PR and project context

The containing commit/PR supplies the implementation reference. Project state and
archived brief/report updated. Unrelated legacy CODEX_TASK.md is intentionally
preserved and was not executed; the current user scope overrides that stale brief.
No scoring, movie records, lists, tags, downloads, import exclusions, Radarr,
seedbox, media files or service configuration were read or modified.
