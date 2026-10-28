# Delayed tracker conflict recheck

Owner requested a generic recheck about15 minutes after a conflict with tracker
metadata, following two observed listings whose later descriptions differed.
Implement and deploy atop the current actor72a04701, preserving other authorized
work. No movie-specific exceptions, relaxed conflict rules or download behavior.

- Admit only exact TorrentLeech listing references with conflicting identity
  evidence and no native autobrr IMDb/TMDb assertion to overwrite.
- Reuse the actor retry worker and its daily60 total /20 listing /40 TMDb limits.
- Force fresh tracker and exact-ID TMDb validation after900seconds; cache hits
  must not disguise a recheck. Respect authentication holds and provider cooldowns.
- Stop after a completed recheck that still conflicts. Transport failures use the
  existing bounded retries/expiry; zero-request budget waits remain deferrals.
- Preserve original observations, new outcome and original Telegram receipts.
  Existing message edits and separate explicit acquisition confirmation remain.
- No historical webhook replay, backfill, live notification test or download.
- Test delay, restart/deduplication, fresh-cache bypass, corrected and unchanged
  evidence, budget exhaustion, native-ID exclusions and original-message binding.
- Do not activate shadow scoring or alter its pilot, budgets or research schedule.
- Preserve the unrelated cleanup assignment in CODEX_TASK.md.
