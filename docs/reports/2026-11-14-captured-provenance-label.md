# Captured completion provenance label

**Specification:** Correct the static provenance label used by receipt-correlated
captured completion, without relaxing text validation, receipt binding or answer validation. Add one
explicit main-approved successor after the exact known local completion defect,
preserving the consumed attempt and every previous record. Use invented offline data only.
**Result:** Implemented; independent review and exact-head CI required.
**Verification date:** 2026-11-14.

## What changed

The real completion branch supplied `request/project` in its own provenance
label. The existing text guard rejects slashes before checking the model answer,
so even a valid response could not complete. The label now says `request and
project`. The guard and all runtime control flow remain unchanged.

`ai_movie_investigator/new_case.py` also implements the exact correction consent
and locked lineage checks. `supervised_credit.py` and
`supervised_authorization.py` bind the successor to a distinct reservation
namespace while keeping the identical wire request and existing credit limits.
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
The connected 401 → credential continuation → unstarted freshness → old-label
rejection → corrected successor test passed independently of the initial set.
A later nine-test invocation passed eight (including that complete lineage)
and hit the same existing read-ctime refusal in one negative fixture. No
local full-pass claim is made. Supported Python 3.12/3.13 full-suite CI is
required on the exact PR head.

## Operational limits and continuation finding

No deployment, credential query, provider call, actual case read or state append
was performed. Changing the label does not repair a previously consumed case.
Completion records its start and rejection before returning this error. The
attempt receipt retains accounting and request metadata, not the answer body;
the in-process answer capability is consumed even on local completion failure.

The existing HTTP 401 and unstarted-freshness contracts do not admit this
terminal shape. The narrow correction contract now adds exactly one new slot
and debit after a terminal `captured_result_validation` / `unsafe_text` /
`validation_refused`, an existing transport receipt, and the exact old
receipt-correlated provenance in one completion-start/rejection pair. It never
reconstructs or supplies the discarded answer, and cannot establish whether
that lost answer would have passed later validation.

The main-issued proof binds the original root, case and credit prefixes, prior
slot, current corrected module digest, finite purpose, main reference and
expiry. The same approved wrapper verifies the complete runtime installation.
Each pre-send recheck revalidates the proof and exact lineage under the existing
root/case locks. Prior attempt, receipt, rejection and reservations remain
immutable. The new request is identical; no case/source clock is refreshed.
A correction cannot chain, run twice, admit a supplied answer or ignore a
changed case. Original 401 then freshness history is supported explicitly.

## Main-only preparation API (not live authority)

After independently verifying the merged installed runtime and the actual
terminal evidence, main constructs a canonical private JSON proof with fields:
`kind`, `prior_slot`, `root_prefix_sha256`, `case_prefix_sha256`,
`credit_prefix_sha256`, `corrected_module_sha256`, `main_reference`, `purpose`,
`reviewed`, `issued_at`, `expires_at`.
`kind` is `captured_static_provenance_correction_v1`; `purpose` is
`one_corrected_captured_assessment_after_static_provenance_defect`;
`reviewed` must be true. The evidence owner reference includes the main reference
and proof digest. Proof expiry must cover the exact account-evidence expiry.
The proof is not a new approval request and does not itself authenticate an
issuer; the existing independently accepted main wrapper remains the trust
boundary.

Under the existing root then case transactions, prepare
`captured_completion_correction_consent(root, root_events, history, events,
request_hash, evidence, prior_slot=..., correction={path, sha256})`.
Pin that canonical consent in the existing approved captured wrapper. Call
`authorize_captured` once, then the existing `run-captured-keychain` for the
returned distinct slot. No `refresh_captured`, copied state, retry or fallback
is part of this correction. Actual invocation stays with main.

## Project context and references

This report is the completed narrow brief and implementation record; its
containing commit and PR provide exact references. Project state links here.
The unrelated assigned cleanup brief remains unchanged. Product acceptance and
any actual corrected operation remain with the supervising main chat.
