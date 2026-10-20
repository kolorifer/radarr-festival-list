# Passive evidence-scoring shadow pilot — 2026-10-20

## Authorized scope

The owner approved running the proposed scorer in shadow mode on real examples
before deciding about production identification. Keep the existing weights,
threshold70 and margin15. No automatic identities, queue reconciliation,
notifications, download actions or extra provider requests are authorized here.

## Implementation

A separate `research.identity_scoring.shadow` process reads existing research
proposal databases using SQLite read-only/query-only connections. It never loads
actor/provider clients or configuration. A Python audit hook rejects socket use.
It writes only a private atomic comparison report. Hourly observations last seven
days; a fixed-date timer and an explicit processing deadline bound the pilot.
The actor, collector and research schedules and request budgets are unchanged.

Up to1000 retained proposal rows are inspected, newest first per database.
Duplicate source/version/result snapshots collapse into one row; the same case
with changed evidence remains a separate observation. Reports distinguish results
created before the pilot from new results during it. Repeated runs are idempotent
for unchanged inputs. Invalid/oversized records are reported as unscorable.

The adapter retains all retrieved movie rivals, including undetailed search
results, so missing rival fields cannot create a falsely large winning margin.
A crosswalk is verified only by a successful unique IMDb find response matching
the detail ID with no TV result. Research labels and human choices earn no points.

## Coverage and interpretation

This is a **passive research-evidence diagnostic**, not complete parallel matching
of every autobrr release. Successful actor identifications, failures never admitted
to research, and queued cases without a completed research result are not scored.
The existing daily research worker controls when new evidence becomes available.

Stored projections lack exact listing/NFO filename binding, original source audio
language, and complete candidate pagination. These missing integrity checks remain
blocked. `arithmetic_pass` means only that the available score and conservative
margin pass the numerical proposal; it is NOT a proposed authorized identity.
The guarded decision remains review when proof is absent. Source runtime retained
in original facts can contribute arithmetic, but is explicitly unbound.
A future complete shadow adapter will need retained provenance and candidate
coverage before this can support a decision to enable automatic scoring.

Reviewed fixture replay remains available separately; those nine development
examples must not be counted as newly observed traffic or production accuracy.
This pilot cannot establish a false-positive rate without human-reviewed labels.

## Verification and deployment

Pending final test and deployment results below. No change to production matching
is part of this installation. Rollback is disabling/removing only the new shadow
timer; retained private reports can remain for review.
