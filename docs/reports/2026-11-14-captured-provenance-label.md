# Captured completion provenance label

**Specification:** Correct the static provenance label used by receipt-correlated
captured completion, without relaxing text validation, receipt binding, consumed
attempt guards, or answer validation. Use invented offline data only.
**Result:** Implemented; independent review and exact-head CI required.
**Verification date:** 2026-11-14.

## What changed

The real completion branch supplied `request/project` in its own provenance
label. The existing text guard rejects slashes before checking the model answer,
so even a valid response could not complete. The label now says `request and
project`. The guard and all runtime control flow remain unchanged.

Only `ai_movie_investigator/new_case.py` changes runtime behavior.
`test_captured_provenance.py` exercises valid completion, subsequent answer
rejection, and unchanged slash refusal. It consumes a genuine invented fixture
receipt, then explicitly selects the real-label branch in a test-only adapter.
It does not establish real provider authentication or host readiness.

## Acceptance evidence

Before the fix, both completion tests failed at the static label with
`unsafe_text`, including the valid-answer case. After the fix, all three new
tests and two existing receipt-binding refusal tests passed. An additional
existing activation test hit `supervised_evidence_changed_read_ctime` locally;
this six-test invocation is **not** a full pass. No guard was weakened.
Supported Python 3.12/3.13 full-suite CI is required on the exact PR head.

## Operational limits and continuation finding

No deployment, credential query, provider call, actual case read or state append
was performed. Changing the label does not repair a previously consumed case.
Completion records its start and rejection before returning this error. The
attempt receipt retains accounting and request metadata, not the answer body;
the in-process answer capability is consumed even on local completion failure.

There is no existing-contract continuation for this terminal shape. The HTTP
401 successor requires no receipt and cannot chain. Freshness refresh requires
an unstarted slot. Supplied-answer completion also rejects a consumed start.
A discarded response cannot be reconstructed from its digest. A purposeful
later request would need a separately reviewed, explicit one-shot correction
contract preserving all prior attempt, receipt, rejection and credit records,
the original prepared request/case and original source clocks. This PR does
not add that contract, replay a request, reset state or manufacture a report.

## Project context and references

This report is the completed narrow brief and implementation record; its
containing commit and PR provide exact references. Project state links here.
The unrelated assigned cleanup brief remains unchanged. Product acceptance and
any actual corrected operation remain with the supervising main chat.
