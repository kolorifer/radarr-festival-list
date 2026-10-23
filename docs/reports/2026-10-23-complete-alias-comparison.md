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

Pending full checks. Regression tests cover a complete winner, close/incomplete
rivals, missing facts, omitted search candidates, pagination, absent alias
support, actual IMDb conflicts, unverified mapping, NFO/source conflicts,
sequel differences, and historical review reasons/asserted IDs.

Retained evidence will be re-evaluated without provider requests, retaining its
original evidence timestamp and request accounting. This is a policy evaluation
of already collected evidence, not a new tracker refresh.
