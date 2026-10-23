# Complete candidate comparisons for alias ambiguity

## Approved brief

Allow a complete candidate comparison to resolve alias ambiguity in shadow,
while keeping actual conflicting IDs blocked. Test and deploy without downloads
or notifications. Preserve the unrelated active cleanup task in CODEX_TASK.md.

## Implementation

The pure scorer may clear only `source_alias_not_corroborated` when both complete
alias queries include the winner and every returned candidate is retained and
fully scored across all five attributes. The winner must have an exact catalog
title, matching year, matching checked tracker IMDb and verified crosswalk,
bound NFO, positive runtime and film-audio evidence, and the existing threshold
and margin over rivals' upper scores. Any other block prevents this refinement.
All rivals remain visible. No changes to weights, limits or production matching.

The refresh layer clears a historical `needs_review/title_conflict` only after
this specific complete-comparison resolution succeeds. Unknown review reasons
and other conflict categories remain blocked. Asserted IMDb and TMDb IDs are
checked independently, including when another gate already withheld selection.

## Validation and deployment

Regression tests cover a complete winner, close/incomplete
rivals, missing facts, omitted search candidates, pagination, absent alias
support, actual IMDb conflicts, unverified mapping, NFO/source conflicts,
sequel differences, and historical review reasons/asserted IDs.

Retained evidence will be re-evaluated without provider requests, retaining its
original evidence timestamp and request accounting. This is a policy evaluation
of already collected evidence, not a new tracker refresh.


## Components and checks

- `research/identity_scoring/scorer.py`: comparison-based alias resolution,
  with an explicit audit marker; all numeric scoring stays unchanged.
- `research/identity_scoring/refresh.py`: narrowly clears resolved historical
  title conflicts; every retained source IMDb/TMDb assertion is checked.
- `test_fresh_identity_scoring.py`: four additional test methods with adversarial
  subcases, including contradictory assertions from two retained sources.

Final runtime revision: **6659b9f** (initial implementation 44c3e01).
The isolated seedbox suite passed all 736 tests in 46.442s; both Python 3.12/3.13
CI jobs passed in run 39911709706. Targeted fresh-scoring tests passed 34/34.
The first sandboxed local run could not bind test sockets; it was rerun with
loopback permissions rather than treating those environment errors as passes.
The preceding 44c3e01 revision passed 736 local tests in 128.681s, with two
Linux-only skips; final-revision local and deployment results follow below.

## Limitations

The refinement deliberately requires all five attributes for every compared
candidate. Incomplete detail data, absent IMDb mapping, close rivals or paginated
searches remain review-only. Genuine source-ID conflicts and other review
reasons cannot be bypassed by a high score. Shadow proposals still do not enable
production identification or download actions. Existing caps, pilot end date
and explicit download confirmation are unchanged.


## Verified deployment result — 2026-10-23

Final local suite: **736 tests passed**, two Linux-only skips, 126.831s.
Deployed shadow **6659b9f** from the exact tested archive; source hashes matched.
Private backup: `identity-scoring-shadow-backup-bmtlb3re`. Only the shadow unit
was switched, and its timer resumed. Actor remains
**658d8f838aed7a03db7d01244254362fba99369a**; actor, collector and research timer
health passed, local HTTP health returned 200. Protected actor/configuration,
action-state, pilot and request-budget hashes were unchanged. No actor restart,
research trigger, provider request, notification or download was performed.

The retained China II evidence was re-evaluated under the new rule, after
read-only verification that the exact occurrence and its asserted IMDb identity
were unchanged. It now **would identify TMDb 10618 / IMDb tt0105839**, score
**99.446903**, margin **111.344224**, with all four candidates still visible and
no remaining shadow blockers. Its original evidence timestamp and eight-request
collection count were preserved; this deployment used **zero new GETs**.
The deployment re-evaluation is recorded separately as policy revision/time.

China III remains would-identify 10619 at 98.660714. Genealogies remains its
retained 100-point proposal. The Beast remains review-only at 100 because
candidate discovery is incomplete and unresolved rivals retain a zero margin;
its existing conflict review guard also remains. Production records and queues
were not changed. None of these shadow outcomes grants download authorization.

The policy change is in existing draft [PR #78](https://github.com/kolorifer/radarr-festival-list/pull/78),
not merged or promoted to production. D043 and project state were updated;
the unrelated active cleanup brief was preserved. The existing passive monitor
was updated to avoid repeating the old China II blockers. Pilot end remains
2026-10-27 at 19:12 Europe/Warsaw. Rollback remains switching only the shadow
unit to its prior tested archive, preserving all ledgers and action history.
