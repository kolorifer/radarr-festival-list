# Film identity separate from edition: v12

## Agreed correction and outcome

A main-reported completed v11 assessment still treated edition uncertainty and an
unsupported producer conflict label as film-identity blockers. This correction is
versioned; old request builders, validations, receipts, reports and charges remain
reproducible. No private case, response, source, account or ledger was inspected.

`build_film_identity` discloses admissible identity aspect/reason pairs and separate
limitations. Its response schema excludes runtime-description and NFO blockers.
`validate_film_identity` rejects negative identity results based only on runtime,
cut/physical-file uncertainty, an unsupported collector conflict flag, or missing
collector resolved outputs when the observed source/catalogue pair is bound.
It never rewrites a rejected result into a positive verdict. Negative schema
variants remain available; local admissibility is an independent evidence guard.

Current concrete ID/title conflicts remain hard guards. Supported identity needs
observed title/year/people corroboration plus existing exact citations; exact IMDb
or matching duration alone is insufficient. A different supplied year and partial
people lists without overlap remain admissible ambiguity to weigh. Unknown festival
years and partial cast lists do not prove another film and introduce no numeric
threshold or automatic veto. The projection lacks person-list completeness or
release-year-event identity, so it cannot honestly turn those partial comparisons
into a proved conflict. Real conflicting observations and missing evidence remain
visible; no facts, qualifiers, score, tolerance or named-film exception are added.
Free-text semantic correctness still needs the main review.

Edition/runtime differences, publisher-claim limitations, missing collector outputs,
unsupported producer flags and unapproved acquisition are computed locally into
`separate_limitations` for either verdict. The model is not asked to reproduce a
fixed list, avoiding needless post-receipt format failures. The existing automatic
report shows the actual model result, source link, original issue, full comparisons,
unchanged safe explanation, publisher claim and a separate limitations section.
Nothing establishes physical edition, production identity or acquisition approval.

## One completed-v11 successor

New `assessment.kind=snapshot_film_identity_v12`, `mode=reassessment` uses the same
Mini profile and exact request/evidence pins. Owner scope kind is
`snapshot_film_identity_scope_v12`, with prior slot and
`same_case_reobservation_allowed=true`; main review adds
`same_case_reobservation_reviewed=true` and binds the complete assessment hash.
No v12 first-mode or repeated v12 successor exists.

`assessment.prior` binds `slot`, `start_sha256`, `grant_sha256`,
`completion_sha256`, `report_sha256`, `retained_reply_sha256`, `attempt_sha256`,
`receipt_sha256`, `credit_sha256`, `credit_count`, `request_sha256`,
`projection_sha256`, `local_context_sha256`, prior `version`,
`collector_observed_at`, and the existing exact prior-result `summary` (slot,
status, candidate, report hash and rationale/uncertainty retention states).

The complete v11 answer is validated under its original contract and observations;
its genuine receipt/report and15-cent reservation remain. Exactly one immediate
child is allowed. If v11 was itself the correction of a failed first v10, that
exact two-ancestor chain is revalidated using the retained v11 context and a bounded
v12 descendant; no broad replay exemption is created. Root/account/project,
append-only history, locks, budget and existing one-operation issuance remain.

## Actual same-case re-observation, never fabricated freshness

The existing fresh-snapshot guard and source/catalogue observation windows remain.
A stale historical snapshot cannot be made current by editing its generation time.
Main must actually obtain and verify the newly pinned export/observations; this
code verifies selected bytes and attestations, not the truth of a remote clock.
Still-fresh unchanged evidence may remain selected without claiming a refresh.

Main reported that a genuinely new export can retain the same stable case identity
while the outcome time, version and provenance digest advance. The v12 comparison
selects both exact prior/current case and item from hash-bound validated snapshots.
Every case field except `version`/`observed_at`, and every item field except
`observed_at`/the strictly validated provenance time+digest, must match exactly.
This includes first-observed time, source identifiers, title/year, route/reason,
correlation, description/NFO digests and all other selected item facts. A changed
version requires strictly later observation time; unchanged version requires the
same event time. Changed snapshot hash requires later actual generation time.

Source facts can bind the actual new selected version with identical substantive
values. The existing substantive projection refresh comparison allows only clock
and attested-original/evidence-pin advancement; changed source/catalogue hashes
require later observation clocks. Local release/NFO bytes remain exact. Publisher
claim fields and source URL remain exact; changed publisher artifact/provenance
requires later observed time. All expiry and full operation-window checks remain.
A new case, changed selected facts, refreshed old timestamp, new first enrollment,
changed substantive publisher claim or extra successor is not permitted.

The original same-listing historical assertion bound remains the prior event bound;
advancing a collector event does not relabel that bound as a new direct source fetch.
The report retains both collector versions/times and the previous report, and does
not claim live queue currentness. Main owns actual source verification and issuance.

## Validation and operational boundary

Invented tests cover supported film identity despite runtime/edition/flag limitations,
unsupported negative refusal, true ID/title negatives, insufficient non-ID evidence,
year/person ambiguity, immutable v11 request bytes and selected case/item drift.
Installed-wrapper tests use fake HTTP through actual parsing/receipt/report paths,
including failedv10→completedv11→v12, real selected version advancement, preserved
history/debits, and duplicate/restart refusal with external-I/O tripwires.
Independent exact-head review and full Python3.12/3.13 CI gate merge. No broad local
suite/dependency repair, live provider call, credential access, private source,
worker/claim/task/schedule change, production change or issued wrapper occurs here.
Unrelated `docs/CODEX_TASK.md` cleanup work remains untouched.
