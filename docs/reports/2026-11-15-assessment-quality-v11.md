# Assessment explanation quality v11

## Agreed bounded correction

A main-reported v10 first assessment recorded its provider receipt, then refused
`snapshot_assessment_justification`. No answer or report was retained. That composite
reason does not identify which punctuation, fragment, label or identical-clause
predicate failed. Neither the answer nor its wording can be recovered from a receipt.
This work uses public source and invented fixtures only; it does not inspect the
actual case, original response, account, credentials or ledger.

## Result and compatibility

`build_film_quality` and `validate_film_quality` introduce a distinct v11 request and
validation contract. Existing v10 request bytes and validation behavior are frozen,
with a retained invented request fixture. Schema validity, bounded sanitized prose,
current ID/title conflicts, exact citations, temporal both-ID explanation, observed
support, missing/different observation requirements and privacy withholding remain.
The new contract does not force a supported result. Safe label-only, fragmentary or
identical support/conflict wording is retained with finite advisory predicates under
`result.explanation_quality`; no semantic correctness is inferred from these checks.
PR199's factual summary, unchanged model interpretation and comparisons remain.
The renderer displays caveats and clearly distinguishes the failed predecessor
from the distinct new assessment. No arbitrary raw remote text is logged.

Actual v11 missing-observation and corroborated-people refusals now have separate
finite codes (`snapshot_quality_no_missing_observation` and
`snapshot_quality_people_corroborated`). Existing finite schema, binding, privacy,
ID, title, citation and temporal diagnostics continue. The historical composite
v10 diagnostic is not retroactively reinterpreted.

## Explicit issuer contract

The existing `assessment` field supports exact kind `snapshot_film_quality_v11`,
unchanged Mini model profile, exact model-evidence/request hashes, and mode `first`
or `correction`. The corresponding owner scope kind is
`snapshot_film_quality_scope_v11`; it binds the same case/version, one call,
explicit disclosure, no production, model profile, mode and optional reobservation.
The main review binds `assessment_sha256` and any existing temporal derivation.
A first operation retains the consumed-case guard and cannot reuse this failed case.

A correction additionally binds owner `prior_slot` and exact `assessment.prior`:

- `slot`, `start_sha256`, `grant_sha256`, `terminal_sha256`;
- `attempt_sha256`, `receipt_sha256`, `request_sha256`;
- `credit_sha256`, `credit_count`, `projection_sha256`, `local_context_sha256`.

Only an immediate failed **first v10** predecessor qualifies: exactly one
`snapshot_refused` diagnostic at `receipt_recorded`, reason
`snapshot_assessment_justification`, no cleanup uncertainty and no completion.
The exact three-row attempt receipt and original 15-cent Mini reservation must
remain. The predecessor authority and all original artifacts are hash checked;
case, projection, local context, source/catalogue/original artifact pins and temporal
proof must be unchanged. Account/project and root identity must match. No source
refresh exception is introduced. Normal freshness and operation-window checks
still apply; expired evidence is not silently refreshed or replayed.

Only one immediate next slot can be authorized and sent, under existing locks and
append-only root/credit history. Old bytes and debit remain. This is a newly issued
operation, not a reset, refund, recovery, automatic retry or loop. No v11 predecessor
or completed v10 predecessor qualifies. Main alone may issue a wrapper after review;
this engineering change issues none. Existing completed-v9-to-v10 reassessment
semantics remain unchanged.

## Optional reviewed publisher-edition context

The original selected projection has listing-description runtime minutes, NFO
runtime milliseconds/kind and catalogue runtime minutes; none is an independently
observed publisher-edition claim. Main subsequently authorized a small optional
append-only observation in this v11 change. `assessment.publisher_edition` is an
exact `{path, sha256}` pin for a canonical typed artifact with fields:

`kind=publisher_edition_observation_v1`, `case_id`, `version`, bounded `title`,
`year`, `edition_label`, `publisher`, integer `runtime_minutes`, `observed_at`,
`expires_at`, `provenance_sha256`, private `source_url`, `source_reviewed=true`,
`title_year_linkage_reviewed=true`.

The title must equal the selected catalogue title after trim/casefold, and year
must equal its theatrical year or one of its supplied festival years. Runtime
uses the existing1..1440minute source bound, not a matching tolerance. Main must
verify actual primary-publisher provenance, the title/year linkage and times before
issuing; code verifies pins/shape/attestations, not external truth. Owner scope adds
`publisher_edition_sha256`; main review adds the same hash and
`publisher_source_reviewed=true`, `publisher_title_year_linkage_reviewed=true`.

The bounded text/privacy filter applies to every disclosed free-text field. The
source URL stays out of projection/request text and appears only as escaped local
report text, never fetched. The complete artifact hash binds even that local URL.
The projection/request/report bind the normalized claim and its observed/expiry,
provenance and artifact hashes. Artifact identity/bytes and freshness are checked
on authorization, send and completion; the expiry must cover the normal operation
window. Missing optional context preserves ordinary behavior.

The failed-v10 proof compares the unchanged base projection separately from this
newly authorized optional claim. It cannot replace original source/catalogue/local
pins. All original comparisons remain, and no new computed numeric tolerance or
forced verdict is introduced. The model may consider publisher-stated edition
runtime as context, while the report explicitly says this is not measurement or
identification of the torrent or physical file. Physical edition and approval
remain unknown. No actual private publisher source or case was provided here.

## Validation and boundaries

Focused invented tests cover preserved v10 request bytes/refusal semantics,
quality-caveat retention, supported and unresolved outcomes, safety/schema/current
ID/title/citation/temporal guards, failed-v10 lineage, wrong proof pins, consumed
first-mode reuse and duplicate refusal. Installed-only tests use the actual wrapper,
fake HTTP and credential substitutes with independent external-I/O tripwires; they
check original attempt bytes, history prefixes, exactly one new reservation and a
rendered report. These fixtures do not prove real model reasoning quality.

Independent exact-head review and Python3.12/3.13 full CI gate merge. A distinct
code-only runtime may be prepared after accepted merge/zero-diff verification.
No live issuance, provider call, credential access, private source read, deployment,
collector restart, production activation, worker or claim change is part of this task.
Unrelated `docs/CODEX_TASK.md` cleanup assignment is preserved.
