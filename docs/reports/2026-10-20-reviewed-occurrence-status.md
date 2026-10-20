# Reviewed occurrence versus automatic identification

## Approved brief

Implement the owner's distinction between a completed human review of one
occurrence and an identity that can be resolved automatically in future. Mark the
current Madame Bovary case reviewed as the 1949 film, preserving the tracker's
conflicting evidence. Require fresh evidence and a choice next time, including
when the same torrent returns. Test and deploy without downloads or permanent
exceptions. Unrelated catalog/cleanup work is out of scope.

## Implementation

The collector has an append-only `selection_reviews` workflow receipt, bound to
an exact current case version, its latest outcome event and its accepted delivery
cursor. It stores the reviewed target IDs/year for audit only. No matcher, action
or acquisition module reads it. The operator-only `review-occurrence` admin
command requires an exact current version and explicit target IDs/year; it cannot
create an approval capability or change the source assertions.

The projection is `reviewed_occurrence`, distinct from `verified` and `routine`.
Reports exclude it from unresolved age/count interpretation and research export;
the digest recognizes it without sending a completion notification. The underlying
conflict and historical research remain. Display text says the review is for this
occurrence only and gives no download approval.

Any new accepted delivery for that source invalidates closure, including an
identical filename/outcome or a selected-filter event. Exact transport redelivery
is deduplicated and does not reopen. Subsequent case versions include the new
occurrence binding, preventing reuse of the prior research version. A delayed new
event or maintenance refresh may conservatively reopen the case; this favors
fresh review over accidentally persisting an exception. This is workflow state,
not a verified identity, a learned rule or an identity override.

## Verification and deployment

PR [#77](https://github.com/kolorifer/radarr-festival-list/pull/77) merged as
`8003775a1d01a28214a8cca93bd4e2d5a20092eb`. Collector selection is from tested
`d8cce25a058bea729e360c26e804b0be05473bf1`; actor/report compatibility runtime is
`658d8f838aed7a03db7d01244254362fba99369a`, based on the previous isolated runtime.
Unrelated main catalog changes were not deployed. The installed selected-only
intake was verified byte-identical to the tested main version and preserved.

Nine new regressions cover closure versus verification, exact redelivery, new
identical outcomes, new selected-filter observations, delayed observations, stale
review races (including unchanged material), report/digest behavior and other
releases. Final local suite: 679 tests, two Linux-only skips. Seedbox main: 679
passed; isolated runtime: 649 passed. CI Python 3.12 and 3.13 passed. The initial
sandboxed local run could not bind loopback HTTP test fixtures; the full rerun
with that permission passed. Dependency/config/catalog preflight passed.

A private copy of the actual collector database proved closure and reopening for
Madame Bovary with unchanged source evidence, including a new research version.
Copied digest state proved zero sends. Deployment backed up code, configuration
and private state, restarted the collector and actor, and restored the research
timer. Collector Landlock ABI 6 and selected-only mode remained active with zero
storage failures; local/public actor health returned 200 with 1,909 movies.
Unchanged files/configuration were hash-checked; research network isolation and
budgets were not changed.

Live read-only evidence verification still returns `needs_review / year_conflict`
and offers the independently verified 1949 target (IMDb tt0041615 / TMDb 45184).
The evidence packet contains 279 description characters, 1,409 NFO characters,
three screenshot references and three candidate choices. No web choice or
acquisition token was created by verification.

The explicit owner review was recorded against the exact current occurrence and
delivery cursor. Collector and report now show `reviewed_occurrence`, retaining
`year_conflict` as the underlying reason. Historical source events and the entire
research ledger are unchanged; existing actions, helper receipts and protected
files are unchanged. One suppressed digest receipt prevents a maintenance alert;
all previous delivery records remain intact. The prior persistent approval is
still revoked. Installed handoff validation accepts the resulting live snapshot,
and the report matches current collector versions. Actor, collector and daily
research timer are active.

Only **2018: Everyone Is a Hero (2023)** remains unresolved (`listing_id_invalid`).
No downloads, Radarr writes, notifications or notification replays were triggered.
Product acceptance beyond the explicitly approved occurrence remains for the owner.

## Limits

Closure is an operator action after explicit owner review. This change does not
automatically close cases when a web choice is submitted. Existing web choices
remain expiring and require separate download confirmation. Source events without
stable transport identity may cause conservative extra review; genuinely lost
upstream events cannot be detected by the collector. No recurrence schedule,
research budget, tracker credential or network-isolation change is introduced.
