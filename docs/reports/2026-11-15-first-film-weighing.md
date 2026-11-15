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

## Narrow dated same-listing reobservation contract

The earlier v1 contract cannot distinguish historical assertions by time alone.
This pass adds an OPTIONAL `first_assessment.reobservation`, accepted only for a
new first assessment with no direct collector IMDb/TMDb and no asserted TMDb.
Only a differing older listing-derived asserted IMDb may be considered historical
contrary evidence. Missing proof preserves the existing hard-conflict behavior.

The proof has exact fields:

- kind: `same_listing_imdb_reobservation_v1`
- source, external_id: exact stable source/listing key; the case must equal
  `outcome-` plus digest([source, 'torrent', ['external', external_id]])
- historical_original: private path/SHA256 pin, re-read under the normal guard;
  current_original_sha256 must equal the existing current source-original pin
- old_asserted_imdb: exact retained assertion
- historical_time_basis: `evidence_present_by_outcome_time`;
  historical_evidence_present_by: exact retained outcome/case clock, an upper
  bound on when evidence was available, NOT an exact HTTP fetch timestamp; this
  bound must precede current_observed_at, the direct current listing observation.
  Exact historical fetch time is explicitly unknown; no exact-time variant is added.
- historical_release_sha256/current_release_sha256 and
  historical_nfo_sha256/current_nfo_sha256: unchanged linkage, equal to the exact
  current local release-name/NFO UTF-8 hashes; neither field may be empty
- same_listing_reviewed: true; assertion_origin: `listing_derived_imdb`

Owner scope additionally binds reobservation_sha256. Main review additionally
binds same_listing_derivation_sha256 and same_listing_derivation_reviewed=true.
Both refer to the exact reobservation proof; its complete hash is also covered
by the first-assessment proof and request. The main issuer MUST independently
inspect the pinned historical/current original bytes and derive the stable
listing identity, assertion origin/field/value and its evidence-present-by outcome-time bound,
and unchanged release/NFO
linkage, as well as authenticate current source provenance, BEFORE entering the
trusted wrapper. The meaning of same_listing_derivation_reviewed=true also
requires verifying that this exact historical outcome carried the pinned evidence
before its timestamp, and that the historical/current time sources (including
clock uncertainty or an independently ordered observation chain) establish the
claimed ordering. Comparing numbers alone is not enough. If either relationship
is unverified, main must not issue the proof. This review binds the exact proof
and both timestamps. The code checks those attested facts and pins; it does not parse
arbitrary source formats or establish authenticity from hashes. A caller-created
file or Boolean is not owner authentication. If main cannot establish any fact,
it must not issue this optional scope. No real evidence was inspected here.

The current listing IMDb must match the independently verified catalogue pair,
with meaningful matching titles and same-role cast overlap. Direct collector IDs,
asserted TMDb, current source/catalogue mismatch, same-time/older observations,
missing/mismatched lineage or placeholder title/cast refuse this scope. The old
asserted IMDb and all clocks remain in the projection and report. Original
conflicting_ids remains true; a separate blocking_id_conflict=false distinguishes
this narrow reviewed historical discrepancy from a simultaneous current conflict.
The request discloses both, permits supported OR unresolved, and requires rationale
to explain the discrepancy and mention both exact IMDb tokens. Token checks cannot
prove prose quality; the explanation remains a model interpretation for human
review. No source correction intent, false-at-the-time conclusion, physical media
truth, identity or acquisition approval is inferred.

The model and report display the historical evidence-present-by outcome-time
bound, unknown exact historical fetch time, recorded case time, later directly
observed listing time and both IDs together. The ordinary producer stamps the
outcome after obtaining evidence; it does not retain the original HTTP fetch time. No schema field or answer-size allowance was
added. Old v1–v9 default request bytes and legacy conflict handling are unchanged.
Invented tests cover positive and unresolved installed outcomes, all scope limits,
meaningful corroboration, exact-ID explanation requirements, owner/main tampering
and historical byte pin mismatch. No live operation is authorized by these tests.

Final focused temporal validation: two installed outcome tests passed73.047s;
one main/owner/historical-pin negative test passed22.546s; fourteen pure and
finite-diagnostic tests passed0.767s. Exact-head CI remains the integration gate.

Final upper-bound timestamp tests: all three installed/pin-negative cases passed;
fourteen pure/diagnostic checks passed. Exact run durations are retained in the
local delivery checkpoint; supported exact-head CI gates repository integration.
