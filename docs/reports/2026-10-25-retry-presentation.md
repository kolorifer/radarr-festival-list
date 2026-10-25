# Engineering report: standard retry notification and poster

**Specification:** [accepted brief](2026-10-25-retry-presentation-brief.md).
**Result:** implemented; final tests/deployment/live card update pending.
**Runtime baseline:** `89b1b72092e247c86e5a23b4ad25e0fd4e42f278`.

## Change

Successful identification retries now use the normal movie formatter, including
links, ratings/facts, the local catalog status and the exact original release and
rejection. The special “Open the confirmation page…” explanation is removed.
A retained poster is added through editMessageMedia on the original message ID;
no new notification is sent. The approval token is preserved. Unavailable/used
capabilities remain removed; unresolved, exhausted and legacy incomplete events
retain their previous safe handling.

Telegram supports replacing text with media through
[editMessageMedia](https://core.telegram.org/bots/api#editmessagemedia).
A repeated successful edit with a lost acknowledgement remains idempotent.
Oversized captions use bounded plain text rather than cutting HTML markup.
If a poster edit fails, the existing bounded retry worker retains the prepared
message and action; it does not send a duplicate notification or acquire anything.

## Components and validation

movie_intel_service.py: normal retry rendering and in-place photo edits.
test_retry_telegram.py: standard catalog text/poster, existing message ID/token,
no-send behavior, repeated edit acknowledgement, caption bounds and real local
HTTP serialization.

34 focused tests passed. Full local/seedbox/CI results pending. No acquisition
behavior was changed. The live card update will reuse only its retained receipt
and existing pending approval, with a private before/after audit.

## Deployment, limitations and handoff

Pending. The ordinary actor retries do not revisit already edited cards; only the
specific Late Night Trains card requested by the user will be updated manually.
Telegram image fetching can fail; errors remain bounded and do not recreate
approvals. No movie addition, torrent download or import is authorized here.
The unrelated cleanup task and open runtime-stack work are preserved.
