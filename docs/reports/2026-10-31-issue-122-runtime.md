# Engineering report: issue122 Task1 finite reporting runtime

Task3 historical correction: live review6543043459 disproved the20-file closure
claim below. The original tests/results remain historical facts, not installed
closure or live acceptance. The owner separately authorized one final correction
in6543142163, superseding the earlier two-execution/no-third limit only for
issue122. See the [Task3 brief](2026-10-31-issue-122-recovery-brief.md),
[report](2026-10-31-issue-122-recovery.md) and current runtime runbook. No claim,
clock, source opportunity or other issue's cap/history is reset.

Task2 correction notice: independent review6542515755 reproduced failures in the
Task1 SSH FD handoff/lock lifetime, preflight ordering and dispatcher eligibility.
The final scoped [Task2 brief](2026-10-31-issue-122-correction-brief.md) and
[correction report](2026-10-31-issue-122-correction.md) supersede the operational
claims below about inherited SSH FDs, local credential preflight and quiet polling.
This Task1 report remains historical evidence of its original implementation and
tests; its earlier supported CI is not acceptance of the correction or live route.

**Specification:** [completed brief](2026-10-31-issue-122-runtime-brief.md), latest
owner supervisor Task1 supplied to this fresh worker on 2026-10-31.
**Result:** implemented; synthetic validation recorded below; independent exact
revision review and supported CI required before deployment/live acceptance.
**Repository revision:** clean starting `automation/issue-122-worker`,
`cc6b90755ba8b71e743517e618a2496163b59815`; parent owns publication/commit/PR.
**Verification date:** 2026-10-31; local macOS Python3.9.6, synthetic fixtures only.

## What changed

The sole dispatcher's ordinary poll recognizes a narrow, canonical, authenticated
issue122 owner command. No command preserves existing behavior. There is one
finite reporting acquisition/publication opportunity and only matching explicit
readback or genuine acknowledgement/archive continuations. No subprocess Codex,
new runner, task reservation, schedule, Work integration or automatic successor.

Full immutable private pins bind the phase/operation, public reviewed commit,
exact local deployment HEAD and runtime file hashes, existing commissioned root
device/inode, separate existing private parent staging, fixed SSH source/key /
known-host selectors, exact absent report destination and distinct successor chat.
Private selection/schema/code/root guards precede the operational claim. Durable
local consumption precedes one separate create-only cross-host operation claim;
only confirmed claim creation and accepted owner.reserve's first durable grant
permit the one source acquisition. No old root/state is adopted or repaired.

The fixed reviewed Linux Python helper reads only original snapshot/review-report
bytes using descriptor spelling/owner/mode/identity/ACL/race/size checks. One SSH
invocation has strict authentication, no ambient SSH config/agent/proxy/password/
forwarding/multiplexing, inherited dispatcher locks and bounded time/stdout/stderr.
The parent retains original transport/file/acquisition metadata privately. Failed
or ambiguous transport cannot retry; unavailable/stale/incompatible movies remain
honest partial findings. Explicitly pinned independent engineering/parent exports
remain useful, including issue119 tasks1..8 and separately selected current phase.
No providers, source refresh, source DBs or quality evidence are invented.

Accepted seal/prepare/handoff bind original clocks/bytes and consume uncertain
before exposure. Parent publishes one exact <=512KiB create-only report with one
PUT, then authenticates byte-exact readback against immutable commit/tree/blob /
SHA256. A lost response only permits selected reads, never another PUT. Cycle
publication receipts are separate from engineering terminal/private receipt history.

After actual designated-chat fetch/verification/inspection, a later unedited
owner comment selects an immutable acknowledgement with exact original attempt,
recipient/chat, report/hash/destination, publication, ingestion reference and time.
Only that authenticated selection can construct/import the distinct accepted
recipient receipt. Both receipts are mandatory for exact verified/fsynced archive.
Completed replay is inert. The guarantee is **owner-attested selection following
real designated coordinator ingestion**, not cryptographic proof that a GitHub
account uniquely identifies a chat. Synthetic tests provide no live ingestion.

Routine implementation choices: immutable public reviewed_revision is separate
from exact local deployed_revision because selective installation can create a
Mac-only commit; the operation claim targets the authenticated public commit.
The staging/SSH parents reuse accepted no-follow/ACL guards with the actual
OS-account home profile, rather than deriving home from arbitrary path lengths.
New explicit engineering directives can supersede older operational commands
without resetting phase state; issue122 still permits at most two engineering
executions. Existing eight-execution rules remain unchanged elsewhere.

## Files and components changed

| Component | Change |
| --- | --- |
| automation/github_worker.py | Lazy current-owner operational selection and ordinary poll integration; issue122 two-execution ceiling; engineering route preserved |
| automation/coordinator_runtime.py | Strict pin/comment/code/storage/request validation, durable finite claim/state, accepted lifecycle orchestration, one-write publisher, selected acknowledgement/archive |
| automation/coordinator_transport.py | Fixed read-only source helper, strict SSH argv/FD/environment boundary and bounded process capture |
| test_coordinator_runtime.py | Synthetic real-parent poll/authentication/pins/guards/crash/receipt/archive and fixed-helper regression coverage |
| automation/COORDINATOR_RUNTIME.md | Exact schemas/comments, selective deployment closure, fixed pilot contract, failure/recovery/limits and honest recipient guarantee |
| Existing supervisor/owner/cycle/pilot/acceptance guides | Current runbook cross-links; historical reports preserved |
| docs/PROJECT_STATE.md and this report/brief | Current engineering handoff, separate implementation/deployment/live facts |

## Acceptance criteria and evidence

| Criterion | Result/evidence |
| --- | --- |
| Current checkout/docs/narrow interfaces | Read repository records and relevant runtime/tests; clean supplied baseline verified; no prior session/history or private operational evidence read |
| Opt-in sole-parent path and finite claim | Synthetic real poll, current-owner reauthentication, strict private tree/blob pins, exact installed revision/hashes, separate claim, interruptions and no repeat acquisition/PUT |
| Commissioned storage reuse/new adapter | Existing root identities and accepted OS-account no-follow/mode/ACL/overlap guards; no reuse/adoption of old adapter; synthetic missing/link/identity/permission/ACL cases |
| Original fixed source acquisition | Actual helper fixture reads, strict argv compilation, metadata/race/UID/ACL/hardlink/size checks, bounded synthetic subprocesses; no live SSH |
| Partial evidence, one publication/readback | Real accepted prepare/handoff, stale movie fixtures retaining selected phase and eight-task parent history; lost PUT followed by readback-only reconciliation |
| Genuine selection/receipts/archive | Fake owner/chat identities exercise mechanics, rejecting forged/trusted flags, wrong chat/recipient/hash/attempt/time/conflicts; no archive before both receipts; exact restart/archive |
| Existing engineering preservation | Focused parent/policy/storage/receipt/coordinator regressions; no accepted schema/policy/credential filtering/executor changes; issue119 history/cap unchanged |
| Runtime compatibility | Actual synthetic paths on3.9.6; supported exact-head3.12/3.13 CI remains required, not run by this child |
| Deployment/live success | NOT verified; supervisor-owned later exact review/deployment/one cycle/actual ingestion/archive gates |

## Tests run and results

Final frozen-code focused validation: **423 tests passed**, including all **30
new runtime/helper cases**. Actual command (with the bytecode prefix below):

```sh
python3 -m unittest test_github_worker test_supervisor_policy test_supervisor_communication test_coordinator_storage test_coordinator_owner test_coordinator_runtime test_coordinator_cycles test_coordinator_exports test_coordinator_integration test_coordinator -v
```

Final frozen-code full run: `python3 -m unittest -v` executed **943 tests** with
**109 environment errors, two skips, no assertion failures**. All30 new runtime /
helper cases passed in this run too. This is **not a passing full-suite result**.
The109 errors comprise84 missing requests,9 missing bs4,10 unavailable
unittest.enterContext, three unavailable SQLite APIs, and three existing HTTP
fixture disconnects. Exact-head supported Python3.12/3.13 CI remains mandatory.

No dependency installation or real host/private probe occurred. There is no local
project virtual environment; commands use the available Python3.9.6 with
`PYTHONPYCACHEPREFIX=/private/tmp/issue122-pycache` to keep bytecode in the allowed
temporary directory. No dependencies changed, so pip check was not required.

Earlier development checks: parent/policy/storage/owner subset142 passed;
runtime23 passed; helper5 passed. An earlier full run executed938 tests with109
environment errors and two skips, no assertion failures. Error categories were
84 missing requests,9 missing bs4,10 unavailable unittest.enterContext, three
unavailable sqlite APIs and three existing HTTP fixture errors. This was NOT a
passing full-suite result. Concurrent source edits during intermediate runtime
runs correctly triggered deployed-hash refusal; final verification uses frozen
code and is reported separately below. No intermediate result is live acceptance.

All20 runtime closure files and the new test module compile on3.9.6; Python3.9
grammar validation also passes. `python3 production_scoring.py --check` passes (1909 candidates,
387 qualified,224 grandfathered,163 new); no scoring file changed. Diff checks
and preservation review cover new files as well as tracked edits.

## Deployment result

**Not deployed; no live cycle run.** No SSH, real private root/source/home/key
inspection, source refresh, host/service operation, provider call, media/Radarr /
notification action, permission repair or schedule/plist change occurred. No
credential was copied, printed or committed. No worker publication, issue comment,
Git commit/push/PR, successor issue, subagent or extra runner was performed.
Supplied launcher229148 and Task6/Task8 operational facts were not re-observed.

[The exact review/deployment/pilot runbook](../../automation/COORDINATOR_RUNTIME.md)
lets the supervisor install only the dependency-closed reviewed runtime blobs atop
clean launcher229148 under existing locks, verify without activation, and issue
the already authorized canonical start/reconcile/ack commands through normal poll.
No third engineering task is part of that sequence. Parent owns Git publication;
supervisor owns independent exact-revision review, CI, bounded install and live
acceptance. Recurrence remains outside the phase.

## Unexpected findings

Selective deployment's local clean commit may not exist in GitHub; using it as a
GitHub ref target would make a valid install unusable. Public reviewed commit and
local deployed identity are therefore independently pinned. Accepted storage's
fixed-suffix home derivation is inappropriate for arbitrary staging/SSH parents;
the runtime explicitly uses the fixed OS-account profile for those checks.
Neither finding changes product policy or permits operational access in this child.

## Unresolved issues and risks

Full local suite is limited by the existing3.9/dependency environment; exact-head
supported CI and independent review are mandatory. Linux source descriptor ACLs
must be positively absent; unsupported evidence refuses. Only exact regular
private keys and literal DNS/IPv4 endpoints are supported. No permission repair,
agent/certificate/IPv6 fallback, ambient alias or source discovery is supplied.

Crash before a usable handoff/write intent can consume the only opportunity and
leave no safe automatic completion. Ambiguous remote claims never establish
ownership. Preserve history and inspect the fixed failure; do not create another
cycle or retry transport/PUT. Finite bounds and original freshness thresholds
remain unchanged. A partial cycle never establishes full movie coverage.
Owner-selected receipt authenticity depends on the supervisor actually obtaining
and retaining genuine designated-chat ingestion evidence; JSON cannot prove it.

## Commit and PR reference

Parent-owned publication is pending. The containing parent commit/PR will provide
the exact code reference; this child did not perform Git publication or CI actions.

## Project context updates

This brief/report and the new runtime runbook preserve the requested behavior and
engineering result. Project state records implementation and synthetic checks
separately from deployment, technical live verification and product acceptance.
Unrelated `docs/CODEX_TASK.md`, decisions, historical reports, notification guide
(no verified live routing change), #86/PR110 and production/research code remain
untouched. No open question has been turned into a new engineering task.
