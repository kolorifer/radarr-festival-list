# Captured final prose retention and bounded correction

**Scope:** One offline connected correction pass. Preserve generic text/privacy,
source, schema, citation, identity, receipt, credit and no-replay boundaries.
No actual account, case, evidence, credential, provider or production operation.

## Diagnosis

`output_schema()` describes rationale and uncertainty as strings. The captured
prompt asks for concise explanations of at most 600 characters. Neither tells
the model that ordinary slashes, question marks or credential-related words
are forbidden. `validate_final` applies `contracts.text(..., 600)`, which uses
the stricter movie-title `safe_text` policy. Its finite rejection origins are:

- Non-string, empty/blank or longer than the field limit.
- Unicode category C characters, including controls and unpaired surrogates.
- Reserved punctuation (`<`, `>`, backslash, `?`, `=`, `@`), URLs, magnet and
  www syntax, credential syntax, and opaque ASCII runs of at least 48.
- The additional envelope prohibition of slash/backslash and whole credential
  words, including secret, passkey, password, cookie, bearer and api_key.

In `_complete_locked`, other `unsafe_text` origins are the retained packet's
validated title/evidence text during admission, and provenance `chat_reference`.
The fixed connected provenance now passes. The renderer/redactor does not call
`text`; it replaces known local references and imposes a 4096-byte draft limit.
No historical answer or offending field is inferred from a generic refusal.
The transport receipt does not retain the discarded answer.

## Connected fix

After original schema and binding checks, a separate captured-answer copy
withholds an entire rationale or uncertainty field that fails existing text
policy. A fixed marker explicitly says the model explanation is withheld; no
replacement reasoning is invented. Finite `prose_handling` field/predicate
markers distinguish retained prose from empty, length, Unicode-control,
credential-label/syntax, opaque-reference, path/URL, reserved-punctuation and
other-policy withholding. A single local renderer fallback can withhold prose
for `draft_byte_limit` (for example, valid 600-character Unicode strings).
If the remaining draft is still too large, the existing refusal remains.

All existing candidate, citation, decision, freshness and schema checks still
run. The generic validator and other completion routes are unchanged. The
original in-memory answer remains the receipt-bound object; `reply_hash`
identifies it. `retained_reply_hash` identifies the safe copy. Both
`new_case_completed.report.assessment` and `supervised_completed.answer` retain
that same safe copy. Unsafe field text is not placed in flags, rejection records
or draft text. An unsent report with withheld prose is a validated structured
review proposal, not proof that its original explanation passed validation.
Passing text is not guaranteed secret-free: this preserves the existing finite
policy, not a universal secret detector.

The public prompt/schema is intentionally unchanged so an already prepared
request is not silently rewritten. Tests exercise that exact contract.

## One new main-issued successor

`captured_prose_correction_consent` admits only an already consumed
`completion_correction` with the accepted plain-language provenance, one further
completion-start/rejection pair, exact transport receipt, no success and terminal
`captured_result_validation` / `unsafe_text` / `validation_refused`. Its proof
kind is `captured_prose_retention_correction_v1`; fixed purpose is
`one_corrected_captured_assessment_with_explicit_prose_withholding`.
The existing proof schema binds the current module digest, main reference,
root/case/credit prefixes and expiry. Original source clocks and prepared
request/case remain identical. A distinct attempt and debit preserve every
prior failure, receipt and credit record. Only one typed prose successor is
allowed; it cannot chain, replay, recover supplied answers, or renew itself.
Actual issuance and execution remain with main, not this code review.

## Validation and limitations

Four connected/component prose tests passed locally. The first full lineage
attempt in Documents stopped at existing `supervised_evidence_changed_read_ctime`
during fixture setup; no guard was relaxed. In an isolated public-code temporary
checkout, all six then-current tests passed (6.038 seconds), including the
complete invented HTTP401 → credential continuation → freshness → static-label
rejection → completion-correction plain-prose rejection → prose-correction unsent
report. They checked preserved prefixes/attempts/debits, exact original request
and clocks, both retained answers, and duplicate/supplied-answer refusal.
The additional bounded Unicode draft test and genuine installed-module successor
test passed together (6.669 seconds) from an isolated public-code checkout.
The installed successor uses the existing CLI, nonempty manifest and invented
file/credential/HTTP adapters, checks both durable answers and their hashes,
and proves one send plus restart refusal with zero external-I/O tripwires.
This does not verify actual host privacy guards or credentials. Independent review and Python 3.12/3.13 CI gate repository merge.
No test establishes actual private storage, credential or provider success.

## Handoff

This report archives the agreed brief and implementation scope. Project state
links here; the unrelated active cleanup brief is preserved. The containing PR
identifies exact source/checks. No deployment or actual assessment is performed.
