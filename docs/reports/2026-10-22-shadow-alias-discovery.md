# Shadow alias discovery

## Brief and implementation

Implement the approved generic AKA search/score flow for ChinaII/III, in shadow
only. No actor changes, downloads, notifications, threshold changes or new budget.

Exactly two names separated by explicit aka/a.k.a. are searched separately.
Every complete response is combined with tracker IMDb-derived movie candidates;
IDs are deduplicated before details. Empty title results no longer erase a direct
IMDb candidate. Pagination, more than3 combined candidates or an empty combined
set stop safely. No ranking-based truncation or year-based discarding of rivals.

Score uses the best supported alias, but every declared alias must be corroborated
by this candidate's catalog titles (case/word normalization). Inconsistent sequel
numbers block review even if an alias matches. This conservative requirement can
leave transliterations without catalog aliases for review. Single-name scoring
and weights are unchanged. Existing production conflicts remain hard review.

## Validation/deployment

Pending full checks. Six new tests cover query deduplication, empty search with
IMDb candidate, absent IDs, incomplete/oversized searches, misleading aliases and
sequel distinctions. Existing independent10/run40/day shadow caps remain intact.
