# Expired unstarted captured authorization freshness

## Agreed scope

Permit one explicit freshness refresh of the latest captured slot only while it
is allocated but never started. Preserve the original allocation, case, request,
source clocks, prior failed attempts, credit history and per-request limit. No
new slot, automatic loop, credential mode, provider operation or guard relaxation.

## Implementation

`captured_freshness_consent` prepares exact authority against the locked root and
case. `refresh_captured` appends one `supervised_captured_freshness_authorized`
record after validating the original expired grant, empty attempt, unchanged
credit prefix and exact owner access-fix artifact. New evidence must retain the
account/project and original credit grant, with fresh balance and policy checks.
The access-fix artifact's bytes and identity are checked again before credential
use and throughout the connected send. The original two allocation records stay
unchanged; the parser resolves the effective selection for the existing runner.
A prior 401 successor keeps its original failed attempt, reservation and case
start; its fresh authority remains single-use and cannot authorize another slot.

## Validation and limitations

Focused invented checks cover exact same-slot completion, prior-401 continuation,
unchanged history/credit before send, one resulting receipt/report, duplicate
refresh refusal, changed request/account/owner-fix/case refusal, and already-started
work refusal. Unit fixture private reads are explicitly invented. The installed
child uses the actual complete runtime manifest and actual filesystem guards,
with only a fake credential, fake HTTP and simulated clock; external I/O has a
tripwire. A hosted ACL refusal is reported separately from successful execution.

Initial local guarded tests stopped at the existing read-ctime guard; no guard
was weakened and no failed run is counted as an installed success. Full supported
Python 3.12/3.13 CI and independent installed validation remain acceptance gates.
No broad local suite or dependency changes were performed.

## Operational boundary

No real state or credential operation was performed by this change. Visible
Keychain settings alone cannot substantiate `material_access_fix_verified`.
The main supervisor must supply an exact truthful access-fix artifact, fresh
account evidence, review and activation pins before the one append and existing
same-slot run. This contract cannot substitute owner-chosen hidden manual entry
for a verified Keychain access correction; that is a separate scope decision.
An interrupted refresh may leave the exact refreshed slot unstarted; only its
existing valid selection can resume. It cannot be refreshed again or extended
past expiry automatically. No live report is claimed by fake-wire tests.
