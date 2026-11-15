# General first normalized-case assessment

## Scope and implementation

An unconsumed normalized case can enter the accepted v9 Mini film-weighing
pipeline directly, without manufacturing obsolete failures or reassessments.
No per-film rule, per-slot configuration or new execution framework is introduced.
Captured-case admission and all legacy request bytes remain unchanged. This task
uses public code and invented fixtures only; main owns private evidence/live use.

The existing trusted normalized wrapper accepts one mutually exclusive
`first_assessment` field with exact fields:

- `kind`: `snapshot_first_weighing_v1`
- `model_profile`: unchanged exact `MINI_PROFILE`
- `model_evidence_sha256`: digest of selected fresh account/model evidence
- `request_sha256`: digest of `build_film_weighing(projection, first=True)` request

Owner scope is `snapshot_first_weighing_scope_v1`, with the existing case_id,
version, max_calls=1, disclosure_allowed=true, production_allowed=false, plus
model_profile_sha256. It has no prior_slot. Main review adds
first_assessment_sha256 to its existing exact artifact/disclosure bindings.
Authority still binds root identity/prefix/count, same project/account, source,
catalogue, original evidence, output identity and exact runtime. No CLI or
ambient flag grants access. `proposal` returns film_weighing_v9 plus this proof.

Only the first request says “first assessment”; the existing v9 reassessment
bytes are frozen. The same validator, Mini policy,15-cent reservation, body/time
bounds, Keychain/session route, receipt correlation and private HTML writer apply.
Reports label this `first_mini_film_weighing` without inventing a prior assessment.
The existing consumed-case check grants no lineage exemption: even a changed
version of an already consumed case cannot use this route. Failed requests retain
their reservations; duplicate execution cannot call native/provider IO again.

## Validation and delivery gates

Four invented integration tests passed97.996s before the first-only prompt wording
change: installed real-wrapper supported and genuine conflicting-ID unresolved
outcomes after an existing completed v9 case; scope/request/model evidence and
consumed-case refusals; malformed answer burns once. Native/network tripwires,
exact old attempt bytes and append-only mixed Nano/Mini history are checked.
The final prompt-specific four-test rerun passed96.717s. Independent review and exact Python3.12/3.13
full CI gate merge. Frozen v9 request bytes are checked explicitly. A separate
47-file code-only runtime is prepared only after merge and zero-diff verification.
No credential/provider/private case/collector/deployment operation occurred.
The model snapshot still needs independently verified actual availability and
fresh authorization before use; no fallback or generic activation is added.
Unrelated CODEX_TASK cleanup remains assigned and untouched.

## Temporal-ID contract limitation — do not send a predetermined assessment

The current contract cannot prove that a newer listing observation corrects an
older assertion on the same listing. `selected_listing_facts_v1` has case/version,
observation time and IMDb, but no immutable listing key or typed correction
relationship. The attestation's source_linkage_verified Boolean and original-byte
hashes do not identify which historical field was superseded or establish that
the source changed it. The current source record has no TMDb field; a changed IMDb or catalogue crosswalk
alone cannot supersede an earlier asserted TMDb value. Newer observation time alone proves neither correction
nor currentness. Therefore this change does not discard historical IDs or relax
the existing conflict guard. An invented regression preserves the older asserted
ID and blocks a positive branch even when listing observation is later.

Minimal additional versioned provenance needed before a temporal treatment:

- Stable same-listing identity, independently reviewed and bound to both retained
  historical and current source originals (opaque key/hash kept local).
- Exact historical assertion field/value and observation timestamp, bound to
  the normalized case/version and old original evidence hash.
- Exact current source field/value, observation timestamp and original evidence
  hash, with explicit typed supersession relation and reviewer verification of
  source origin and same-listing continuity. Mere later timestamp is insufficient.
- Exact fresh catalogue/crosswalk evidence hash and time. Any disagreement between
  current source and catalogue remains a hard conflict; history stays disclosed
  as dated contrary evidence and the report must explain any accepted supersession.

This requires a separately reviewed typed evidence extension; none is inferred
from untyped prose or the chosen movie. Main must resolve this evidence limitation
before invoking the new entry for a case that depends on superseding old IDs.
