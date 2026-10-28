# Delayed tracker conflict recheck

Owner-approved [brief](2026-10-26-tracker-conflict-recheck-brief.md).
Runtime d598296e4ba3b3223e9014c993b116ada9ed723e, based on exact deployed
72a04701d110c2b6f54cfd67c25861e6bf997a4c. [Draft PR89](https://github.com/kolorifer/radarr-festival-list/pull/89)
is isolated against runtime/conflict-recheck-baseline, not unrelated main changes.

## Behavior

A selected movie with a tracker-sourced title/year/local identity/runtime or
conflicting listing-ID failure now schedules a recheck900seconds after admission.
Only the exact supported TorrentLeech URL matching the original external listing
ID qualifies. Native autobrr IMDb/TMDb assertions are not replaced. Existing
normalization and movie/source eligibility rules remain.

The existing retry worker forces a fresh listing and exact-ID TMDb resolution,
bypassing process and persistent success caches only within a context-local
recheck scope. All existing local catalog, title/year, ID and NFO runtime guards
still apply. Changed metadata is not acceptance by itself; a fully verified
result is required. An unchanged conflict ends this job for review. Temporary
transport/provider failures use existing bounded retry handling (three counted
attempts in24h, one-week expiry); empty budget/cooldown waits defer. Same-version
duplicates and restarts do not reopen a completed conflict recheck.

No additional request allowance: daily60 total,20 listing,40 TMDb, existing
provider holds/auth suspension. Therefore15minutes is the earliest nominal delay,
not a guaranteed deadline when budgets or providers are unavailable.

Original evidence remains in the durable retry job; refreshed context/listing is
retained at completion and the resulting outcome goes through existing intake.
Original Telegram receipts are captured for these cases as well as temporary
failures. The first card explains the planned recheck. Recovery edits that same
message through existing confirmation preparation; unresolved cases remain review.
No automatic Add, search, Grab or replacement is introduced. No new-message
fallback, historical replay/backfill or persistent identity exception.

## Validation

Nine synthetic regression tests cover the15minute boundary, restart/deduplication,
all accepted conflict reasons, native-ID/source/reference exclusions, cache bypass
and context reset, budget deferral, retained old evidence/new context, corrected
source IDs, unchanged runtime conflict, original rejection/message receipt and
no acquisition. Existing conflicting-ID/runtime and notification suites remain.

Full local:737 tests,151.015s,two Linux-only skips. Seedbox isolated exact runtime:
737 tests,45.707s,all passed. Python3.12 and3.13 CI run40339065262 passed on exact
runtime d598296. An initial sandboxed focused run could not bind its local mock
HTTP server; the full run with loopback permission passed. Dependency check,
1909-row catalog check and private configuration preflight passed.

## Deployment

Deployed exact tested runtime d598296e4ba3b3223e9014c993b116ada9ed723e,
replacing72a04701d110c2b6f54cfd67c25861e6bf997a4c. Private backup
conflict-recheck-backup-9nsc9fqj retained. Only movie-intel restarted. Local and
public health both200; final readback confirms expected SHA, active/running and
zero unexpected restarts. Catalog health reports1909 movies and Radarr available.

Configuration and pilot hashes, approval state and collector remained unchanged.
Retry counts remained26 jobs,35 attempts and79 requests. No historical jobs were
seeded or reset. No research/shadow units, budgets, policy or pilot extension.
No live test messages, notification replays or downloads. The passive shadow
monitor was updated to recognize this separately authorized actor revision.

The synthetic corrected-source and unchanged-conflict scenarios passed; the new
15-minute path has not yet been demonstrated by a naturally arriving live event.

## Limits

A correction later than the completed recheck still needs later evidence/review;
this is not continuous polling. Real conflicting identities and alternate-cut
runtime differences remain blocked. No automated edition-runtime exception is
introduced. Existing cards without retained receipts cannot be edited. The new
behavior is for newly admitted events; the old Begin Again/Wolverine occurrences
are not replayed as a deployment test. No deliberate live message/download test.
Rollback the code to72a04701 while preserving current private state and ledgers.
Unrelated CODEX_TASK cleanup assignment is preserved.
