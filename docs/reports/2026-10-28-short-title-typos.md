# Engineering report: short-title typo matching

**Specification:** [brief](2026-10-28-short-title-typos-brief.md).
**Status:** implementation under validation; deployment pending.

## Change

Remove the eight-letter whole-title gate from the existing exact-source tracker
typo matcher. Both differing words must remain at least six letters, alphabetic,
and differ by exactly one insertion, deletion, substitution or adjacent swap.
Unique IMDb/TMDb crosswalk, matching year, source restrictions, local conflicts,
runtime evidence and separate download approval are unchanged. No fuzzy title
search is used to identify a movie. Five-letter words and numeric/Roman-numeral
changes stay blocked; very short titles need review. Carrue -> Carrie is accepted
only with the existing verified source and ID constraints.

Tests, deployment and live read-only verification pending. No live notification,
historical replay, movie addition or download is part of this task. The unrelated
cleanup assignment remains unchanged.
