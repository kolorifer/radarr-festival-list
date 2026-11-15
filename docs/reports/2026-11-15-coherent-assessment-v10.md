# Coherent assessment v10

## Agreed scope

Correct the assessment itself using public code and invented fixtures. Preserve
all prior builders, assertions, timestamps, consumed outcomes and reservations.
No real case, credential, provider, collector, deployment or production operation.
The unrelated cleanup task in CODEX_TASK.md remains assigned and untouched.

## Assessment behavior

`build_film_assessment` emits one coherent policy instead of appending conflicting
clauses from earlier prompts. Genuine current listing/catalogue ID and title
conflicts remain hard blockers. An explicitly reviewed dated same-listing IMDb
discrepancy stays visible as historical contrary evidence, with an outcome-time
upper bound and unknown original fetch time. A retained producer flag or this
historical discrepancy alone is not an automatic veto. The model weighs current
support and contrary evidence; both supported and unresolved outcomes remain.

When either cast or directors provides meaningful same-role corroboration, missing
the other people subfield cannot be classified as missing people evidence. The
schema and validator enforce this; a different material ambiguity can still be
explained. No verdict is manually rewritten, score introduced or named-film rule
added. Matching identifiers alone remain insufficient.

At most two strongest material blockers each have support_considered and
material_conflict clauses of up to400 characters, instead of up to six pairs of
140. Rationale600 and uncertainty300 remain. This allocation permits complete
sentences while fitting the unchanged32768-byte envelope, including non-BMP text.
Both the report copy and durable completion copy use the same v10 limit.
Independently validated safe prose is temporarily substituted for legacy text
validation, then restored, preserving ordinary punctuation and slash comparisons.

The finite explanation check requires a terminal sentence mark, refuses dangling
clause endings, category-only text and identical support/conflict clauses. It has
no word-count threshold and accepts short complete sentences. It cannot prove
English grammar or evidence reasoning quality; all explanations remain model
interpretations for human review. Temporal rationale must mention both exact IDs.
If its unsafe text is withheld, the required explanation is absent: the attempt
consumes its reservation and refuses completion, rather than fabricating a report.

## Exact entry contract

The existing trusted normalized authority gains mutually exclusive `assessment`:

- kind: `snapshot_film_assessment_v10`
- mode: `first` or `reassessment`
- model_profile: unchanged exact Mini profile
- model_evidence_sha256 and request_sha256: exact selected evidence and v10 request
- optional reobservation: unchanged reviewed temporal contract from PR197
- prior: required only for reassessment, exact fields listed below

Owner scope kind is `snapshot_film_assessment_scope_v10`, with existing case_id,
version, max_calls=1, disclosure_allowed=true, production_allowed=false,
model_profile_sha256 and mode; reassessment adds prior_slot. Temporal scope also
binds reobservation_sha256. Main review binds assessment_sha256 and, when relevant,
the same reviewed temporal derivation fields as PR197. No CLI/ambient activation.
The resulting grant contract_version is `film_assessment_v10`.

Prior fields: slot, start_sha256, grant_sha256, completion_sha256, report_sha256,
retained_reply_sha256, attempt_sha256, receipt_sha256, credit_sha256, credit_count,
request_sha256, projection_sha256, local_context_sha256, summary. Summary exactly
retains slot/status/candidate/report_sha256 and prior rationale/uncertainty handling.
Only a completed, receipt-correlated, unsent v9 FIRST assessment is eligible; no
v9 reassessment or v10 parent. The immediate last attempt must be that parent;
exact old authority/artifacts/request/result/receipt and15-cent reservation are
validated. One child only; old attempts and all charges remain immutable.

A fresh same-case/version inventory and same-source/catalogue reread may update
only freshness clocks and their exact pins. Substantive projection facts, source
assertions, title/cast/IDs/NFO/runtime and historical outcome time stay identical;
local context bytes stay identical. The existing temporal proof may update only
its current observation time/current original hash. Main must authenticate all
new evidence and independently verify chronology under the unchanged admission
rules. Current freshness is checked normally; expired evidence is never reused.

The same Mini model/profile,15-cent reservation, standing ledger, deadlines,
body bounds, isolated wrapper, Keychain route and send-once gates apply. The
private report labels v10 and retains the exact prior summary when reassessing.

## Validation and delivery

Focused invented matrix covers temporal support with missing directors, genuine
current ID conflict, unrelated title, inadequate support, meaningful unresolved
outcomes, prose retention, maximum envelope, frozen v9 bytes and refresh drift.
Installed fake-wire tests cover new-case and refreshed reassessment, durable
161–400-character explanations, mixed ledger/old attempt preservation, duplicate
refusal and native/network tripwires. Wrong prior pins and unsafe temporal prose
fail closed; no report is invented. Exact results are retained in the delivery
checkpoint. Independent review and exact Python3.12/3.13 full CI gate merge;
a distinct47-file code-only runtime follows zero-diff verification. Actual
issuance and live use remain with main under separately verified authority.

Initial full focused integration:4 tests passed160.589s. Pure assessment plus
finite-diagnostic coverage:6 passed0.688s. A targeted installed reassessment
checks the exact400-character durable-retention boundary before freeze.

Final exact400-character installed boundary test passed49.818s after the modest
sentence-ending adjustment; six pure/diagnostic checks passed0.606s.
