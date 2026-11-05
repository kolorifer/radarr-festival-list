# Supervised failure reason and phase

The command now classifies a finite literal set of static refusal reasons across
its fixed transport, protocol, parent, authority, storage and validation modules.
It emits only an allowlisted reason and category; arbitrary exception messages
become `unexpected_exception`. Existing specific categories retain precedence.
A coverage test checks the static sites in the selected modules so new fixed
refusals cannot silently lose classification. Nearby unused sites are harmless
allowlist entries, not additional authority or an execution trace.

An ephemeral context records the last observed bounded phase, from preflight
through wire setup, DNS/connect/TLS, HTTP response/body, parsing, receipt and
completion. A phase denotes entry into that stage, not successful completion or
provider charging. After a slot starts, a failure appends a small
`supervised_diagnostic` to the existing held root transaction, with slot, time,
phase, reason and category. No error payload is stored. Failed diagnostic writes
are swallowed while the original exception is re-raised; incomplete history
still fails closed. HTTP cleanup similarly cannot obscure a primary refusal; a close failure on
an otherwise successful response fails closed with a static reason.
No diagnostic controls admission, erases consumption or releases reservations.

Validation uses the real fixed HTTP method, HTTPConnection/HTTPResponse framing,
TLS context, deadline, parser and receipt path with finite invented socket I/O.
Cases cover successful completion, incomplete/unexpected/schema/usage/malformed
responses, missing request ID, rejection, header/body limits/truncation, DNS,
TLS roots and timer prerequisites, secondary close failure, failed diagnostic
append, unknown exceptions, restart refusal and installed `-m` output without
leaks. The prior recovery fixture explicitly constructs the historical
pre-diagnostics shape; no actual historical journal is changed.

Local baseline run: 53/55 existing focused tests passed; two installed renewal/
recovery fixture setups failed at the unchanged `supervised_evidence_changed`
guard. Preserve these observations; cause was not established and the guard was
not loosened or retried to green. The six new diagnostic tests passed, including
fifteen negative raw-HTTP/prerequisite cases, one complete response and two
installed-module scenarios. Independent review caught success-path close-error swallowing; it was corrected
to refuse safely while preserving any primary exception. The updated run passed
five of six tests (including all fifteen negative variants); the installed unknown-
exception fixture stopped before its prompt at the unchanged evidence-change
guard. The earlier successful no-leak run remains evidence, not a claim that this
metadata issue is fixed. Supported exact-head CI results are recorded in the PR.

No live request, actual key input, deployment, real-state modification, new slot
or budget change occurred. The historical failed request remains unexplained.
The separate active cleanup brief and all production behavior are preserved.
