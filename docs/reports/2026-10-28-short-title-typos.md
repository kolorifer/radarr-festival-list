# Engineering report: short-title typo matching

**Specification:** [brief](2026-10-28-short-title-typos-brief.md).
**Status:** implemented and deployed; [PR #94](https://github.com/kolorifer/radarr-festival-list/pull/94) merged into its isolated baseline branch.

## Change

Remove the eight-letter whole-title gate from the existing exact-source tracker
typo matcher. Both differing words must remain at least six letters, alphabetic,
and differ by exactly one insertion, deletion, substitution or adjacent swap.
Unique IMDb/TMDb crosswalk, matching year, source restrictions, local conflicts,
runtime evidence and separate download approval are unchanged. No fuzzy title
search is used to identify a movie. Five-letter words and numeric/Roman-numeral
changes stay blocked; very short titles need review. Carrue -> Carrie is accepted
only with the existing verified source and ID constraints.

## Verification and deployment

- Focused suite: 19 tests pass. Full local suite: 746 tests OK, two Linux-only
  skips; final isolated seedbox suite: all 746 pass. Both Python 3.12 and 3.13
  [CI jobs](https://github.com/kolorifer/radarr-festival-list/actions/runs/40715885389)
  passed. Server dependency, scoring and actual private-config preflight passed.
- Deployed tested revision `46cccea3a119ca080e35f6cf071bd0351eba037a` at
  16:28 Warsaw time, October 28. Clean checkout, local/public health 200,
  1,909 movies, active/running, zero restarts. Ten existing approvals, acquisition
  receipts, protected configuration and collector state preserved. Private backup:
  `~/.local/state/short-title-typos-20261028`.
- Deployed resolver reproduced Carrue to Carrie with a synthetic unique IMDb/TMDb
  mapping. The actual historical Carrue listing currently fails exact heading
  verification, so a live source-to-result success is **not** claimed. This rule
  does not relax the exact-heading guard or replay past notifications.
- No live notification, historical replay, movie addition or download occurred.
  Existing rollback restores the previous code while preserving current state.
  The unrelated cleanup assignment remains unchanged.

## Product acceptance

On 2026-10-28 the user accepted finalization without waiting for a live
end-to-end example, given the rarity of this case. The historical listing
heading mismatch and absence of a live success remain documented above.
