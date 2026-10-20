# Bounded retries for missing TMDb mappings

## Approved scope

Owner requested bounded retries for missing TMDb mappings, including retained
Insomnia (1997), while keeping conflicting identities such as Madame Bovary
(1949) blocked. Test/deploy without downloads or notification replay.

## Implementation

`identity_retry.py` admits `tmdb_mapping_missing` to its existing temporary
metadata failure set. No new search/identity policy or per-film exception. The
existing 15-minute initial delay, subsequent 1-hour/6-hour waits, maximum three
attempts, daily60 GET budget (20listing/40TMDb), provider holds/pacing, one-week
source expiry and version deduplication remain unchanged. Exhaustion goes to
review. A year/identity/title conflict, ambiguous/nonmovie mapping or invalid
source is not admitted; if discovered during retry it ends retries immediately.

`test_identity_automation.py` adds recovery without action/notification,
three-attempt exhaustion across restart, duplicate suppression and stopping on
all conflict classes. The existing non-retryable regression now explicitly covers
year conflicts like Madame Bovary. Existing budget/cooldown/expiry tests remain.

## Retained-case admission

Insomnia's original collector evidence was matched exactly to retained autobrr
release metadata, source fingerprint and original observation time. It had only
the missing-mapping outcome and no prior retry job. The one authorized operator
admission preserves its original one-week expiry and elapsed initial delay,
uses the normal durable queue/budget, and does not replay a webhook or handler.
No bulk history reopening, ledger reset or notification backfill.

## Verification and deployment

Implementation `be08a06`, PR70. Isolated runtime
`c2ae4e12e67486d4651db863e5132213715246f6` based on verified live `c025aad`.
Targeted retry tests21 passed. Full seedbox tests596 passed; both CI versions
passed. Local full suite613 tests passed with two Linux-only skips. PR70 merged
as `c061989dd2c43d3d588237a51472b6cdbd3cd9b2`.

Production clean at `c2ae4e12e67486d4651db863e5132213715246f6`. Private state/config
backup taken; dependency/catalog/config preflight passed. Only movie-intel
restarted; local/public health200 with1909 movies. Actor/collector active with
NRestarts0, collector PID unchanged, daily timer active. Protected configuration,
collector/research/helper files, approval state and downloader receipts unchanged.
No code rollback was needed; no state was restored.

Insomnia recovered naturally on its first queued attempt: `done` /
`external_id_verified`, using one listing and two TMDb GETs under the live durable
budget. The collector received the verified outcome alongside its historical
missing-mapping outcome. Original source expiry preserved. No Insomnia approval
created or changed, and no webhook/notification replay. Existing request and
attempt history retained. Madame Bovary remains `needs_review` / `year_conflict`
with no retry job. No downloads triggered. Runbook, project state and D029 record
the completed change; the unrelated active task was preserved.

## Limits

Persistent missing mappings still require review after bounded attempts; provider
holds/budget waits can defer recovery. The existing daily report/digest cadence
controls when updated review status is visible. Old Telegram messages are not
edited or resent; metadata retries never create acquisition approvals. Madame
Bovary's mismatched tracker identity remains blocked. Generic-only identification,
all existing Radarr/Grab safeguards and the unrelated active cleanup brief remain.
