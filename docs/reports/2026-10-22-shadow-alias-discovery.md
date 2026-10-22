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

Six new tests cover query deduplication, empty search with
IMDb candidate, absent IDs, incomplete/oversized searches, misleading aliases and
sequel distinctions. Existing independent10/run40/day shadow caps remain intact.


## Tests and deployment result

Implementation **0f8446d**, draftPR78 (not merged). All722 tests passed locally
(two Linux-only skips,154.089s) and seedbox(46.406s); CI Python3.12/3.13 passed
run39833512551. Installed scorer/refresh hashes match the tested sources.

Shadow unit now uses isolated `~/.local/share/identity-scoring-shadow/0f8446d`.
Prior unit/state backed up privately at
`~/.local/state/identity-scoring-shadow-backup-qn5d0gh8`. Rollback restores only
that unit and reloads/restarts the timer; do not restore old request budgets.
Actor remains658d8f838aed7a03db7d01244254362fba99369a. Actor source/config/actions,
original research timer and pilot deadline hashes unchanged; health200 and actor,
collector/research timer active. Shadow timer restored. No actor restart, queue
updates, notification or download calls. Existing daily research776986f unchanged.

## Live shadow findings

- **ChinaIII:** both separate alias searches return one candidate, the same
  TMDb10619. Fresh tracker IMDb mapping agrees. Score75: title30, year20, IMDb25;
  margin75 against the sole-candidate zero baseline. Still `review` because the
  catalog does not corroborate the exact transliterated source alias under the
  conservative alias check. Its1863-character NFO layout also produces no parsed
  runtime/audio-language points. Five metadata GETs, within unchanged caps.
- **ChinaII:** new arithmetic applied to retained evidence yields75 versus old15,
  restoring title30 instead of-30. This is not fresh verification. The old worker
  had retried it minutes earlier; preserved one-hour delay prevents an immediate
  retry. The next eligible hourly refresh will exercise new discovery. Historical
  identity conflict remains review-required even if future arithmetic passes.
- **The Beast:** due refresh still stops at the three-candidate capacity limit;
  no fresh score. This deployment does not implement broad-search narrowing.
- Genealogies retained fresh100 unchanged. Four new pilot cases, eight historical
  snapshots; two have fresh results, including review-blocked ChinaIII.

## Remaining limitations and follow-up

Search alias recognition is broader than catalog alias metadata: both queries
can retrieve the same movie without both names appearing in its details. We
conservatively show that discrepancy for review, not automatically trust a search
engine's fuzzy association. Supporting further transliteration variants or new
NFO layouts remains separate follow-up. No movie-specific rule was added.

Weights70 threshold/15 margin, conflict guards, request caps10/run40/day,
failure delay1hour and originalOctober27 deadline unchanged. ChinaII fresh result
is pending the existing timer, monitored by the standing read-only automation.

PROJECT_STATE and D040 updated. Unrelated CODEX_TASK cleanup brief preserved;
this report archives the approved implementation brief and results.
