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

Validation and production results pending.
