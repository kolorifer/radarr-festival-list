# Daily identity retries and clearer review digest

Owner authorized removing the week-long retry bottleneck, clearer Telegram copy,
safe deployment, review before identity corrections and no test downloads.

The actor's extra metadata retries previously shared ten GET reservations per
rolling week, five per provider. A handful of temporary errors consumed that
allowance. They now share 60 per rolling 24 hours: at most 20 tracker listing GETs
and 40 TMDb GETs. Original request reservations remain durable and count if still
inside the new window. Existing pacing, provider Retry-After/auth suspension,
three attempted lookups per case per 24 hours, source expiry and no-acquisition
retry boundaries remain unchanged. Deeper research's separate weekly budget and
schedule are unchanged.

A one-time transactional migration advances only pending, unexpired jobs blocked
by the old request budget. It staggers their wake-ups by one minute. It never
reopens review/completed cases or active leases, resets request/attempt history,
extends source expiry or removes provider suspensions. The normal request gate
still checks current capacity/cooldowns before any network call. This avoids a
startup retry storm and makes rollback possible without restoring old state.

The digest explains temporary lookup failures, missing source IDs, title
conflicts and proposals in plain language. A temporary failure is not presented
as a confirmed identity mismatch. Candidate matches remain explicitly unverified;
every correction requires review. Existing material-version keys are preserved,
so wording changes alone do not resend historical messages. No test digest will
be deliberately sent; future natural case changes use the new wording.

## Validation and deployment

PR66 merged as `27d98149062fec71fb03813389082058cd79b639` after Python 3.12/3.13 CI passed on `5402dff`. Local full suite: 616 tests, two Linux-only skips. Exact isolated runtime: 599 tests, all passed on the seedbox.

Production is pinned to **`09c3ab44767c2182fbf23b1214da74c336949fbc`**, based on verified `5e27584`. Only retry/digest modules and their tests changed; those files match the merged implementation. Dependencies/config/catalog preflight passed. Local/public health200, catalog1,909, actor and collector active with NRestarts=0. Protected configuration/research/timer hashes and collector PID remained unchanged. Approval and downloader receipt stores were preserved; no download or correction was triggered.

Private-copy verification preserved all existing request/attempt/provider rows while moving only the five pending budget waits to +60/+120/+180/+240/+300 seconds. All 65 report-case material delivery keys matched the previous implementation. The live rollout preserved old request reservations and source expiry; digest stayed at nine sent records with no wording-only replay. Backups and rollout evidence are retained privately under `~/.local/state/daily-retry-rollout/`.

## Live recovery results

All five naturally scheduled cases completed with `external_id_verified` within the staggered five-minute rollout window: **Toby, Contagion, Rooster Cogburn, Legend of the White Dragon, Making the Shining**. No retry was forced manually. They consumed 15 additional GET reservations (five listing, ten TMDb); the rolling-day totals at postflight were eight listing and thirteen TMDb, below 20/40 limits.

These are successful ordinary source/TMDb identity verifications, not newly approved correction rules. No correction configuration changed. Existing approval capabilities for the five films were compared against the private pre-rollout backup and were unchanged; no new capability was created by retry. Final local/public health remained200, digest remained nine sent, and production SHA was rechecked. No live download occurred.

A postflight assertion initially assumed no prior capabilities existed for these titles; that assumption was too broad. Verification was corrected to compare their actual pre-rollout state, proving no new or changed approvals without deleting or rewriting existing ones.

## Limitations and operator notes

Daily bounds are additional retry traffic only; ordinary webhook enrichment and the separate deeper-research budget are unchanged. A repeated provider outage, rate limit or authentication suspension can still delay recovery. Three attempted lookups per case per day remain bounded; persistent failures go to review. No policy guarantees that every movie will resolve or be offered for acquisition.

The digest is driven by the existing daily research report and five-minute actor poll. Retry outcomes enter the collector immediately, but digest reporting can wait for the next scheduled report. Old Telegram messages are not rewritten. The new wording appears on future material changes and explicitly keeps corrections subject to review.

Rollback is code-only to `5e27584`, preserving current requests, attempts, provider holds, migration marker, approvals and receipts. Never restore earlier ledgers to obtain capacity. The one-time migration does not rerun on every restart. The unrelated active `docs/CODEX_TASK.md` assignment was left intact.
