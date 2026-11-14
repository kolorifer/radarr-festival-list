# Captured assessment after an explicit credential correction

## Agreed scope

An owner-confirmed credential update and explicit request to continue may select
one new assessment after a captured attempt stopped with terminal HTTP 401.
Keep the same prepared occurrence and wire request; preserve the failed attempt,
all reservations and original evidence clocks. No automatic retry, chained
continuation, copied ledger, supplied-answer completion or production change.

## Implementation

The exact captured authority can contain a single continuation binding to the
prior slot, grant, attempt rows, terminal diagnostic and case-history prefix.
The root and case locks protect validation and allocation. The prior result must
be `responses_http_401`, `http_response_received`, `transport_refused`, without
cleanup uncertainty, receipt or completion. Its original debit remains reserved.
A changed owner reference and explicit material-credential-correction attestation
are required; their truth comes from the accepted supervisor wrapper, not JSON
self-authentication. Fresh account evidence and exact activation remain required.

The exception permits only the original generation start plus the new bound
start. The actual receipt-correlated completion path accepts that exact pair.
Ordinary consumed requests still refuse. A successor cannot itself be continued.
The successor debit has an authority-scoped reservation identity and retains the
unchanged wire-request hash; ordinary duplicate reservations stay forbidden.

## Validation and operational boundary

Focused invented tests cover full connected completion, preserved history and
debits, receipt/uncertain-result refusal, mismatched authority, no second
continuation, no supplied-answer fallback, and an installed isolated module with
fake native credential/socket I/O and the real private-file reader. Supported
Python 3.12/3.13 full CI and independent exact-change review gate merge.

An early local fixture run encountered `supervised_evidence_changed_read_ctime`;
those failures were not accepted as continuation coverage. The fixture now
asserts the actual first 401 and uses the genuine private reader. Runtime guards
were not relaxed. No broad local suite or dependency repair was performed.

No actual credential, provider, account, ledger or collector operation is part
of this code change. Main independently verifies the concrete runtime and
owner-bound wrapper before a separate live assessment. HTTP 401 does not prove
zero billing, and reserved amounts are not actual-charge evidence.

Local real-guard run: 5/8 passed, including connected successor completion and
no chained correction; three stopped at the existing ctime guard before their
intended checks. The installed-module test did not reach its child process in
that run. These are recorded failures, not an installed-path pass.

First supported CI run: Python 3.12 ran 1,987 tests, with one failure: the new
installed subprocess correctly refused a hosted ancestor POSIX ACL. Python 3.13
was cancelled by the matrix failure. No evidence-reader or ACL bypass was added.
The installed fixture now verifies this host refusal before any allocation when
an ACL is present; on a guard-compatible host it must complete via the installed
module. A real guarded Mac installed success is separately required before live
handoff acceptance; a hosted refusal is not labelled an installed success.

Independent Mac review also caught a fixture-only manifest binding: the inherited
parent mock affected install_runtime’s return value. The installed test now
binds the actual written runtime-files.json, as the existing installed fixture
does. Product runtime and closure verification are unchanged.
