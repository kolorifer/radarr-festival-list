# Engineering report: standard retry notification and poster

**Specification:** [accepted brief](2026-10-25-retry-presentation-brief.md).
**Result:** implemented, deployed, and the requested existing card updated.
**Deployed revision:** `ea062d865f56cfb33a0b284cafeb11feb37a1b2b`.
**Review:** [PR #85](https://github.com/kolorifer/radarr-festival-list/pull/85), open against the isolated runtime baseline.
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

34 focused tests passed. Full local suite: **717 tests passed, two skips**,
137.598 seconds. Full isolated seedbox suite: **717 tests passed**, 45.612 seconds.
[Python 3.12/3.13 CI passed](https://github.com/kolorifer/radarr-festival-list/actions/runs/40201044909).
Local/seedbox pip check and production scoring checks passed (1,909 candidates,
224 grandfathered, 163 new, 387 qualified). Configuration/diff checks passed.
No acquisition behavior changed.

## Deployment, limitations and handoff

Activated at **15:13 CET on 2026-10-25**. Clean deployed checkout; movie-intel
active/running with zero restarts. Local/public health 200 with 1,909 movies.
All 19 preexisting approvals and acquisition receipts were unchanged, as were
protected configuration and the identity collector. Private backup/audit:
`~/.local/state/retry-presentation-20261025`.

The exact Late Night Trains card was edited using its retained Telegram receipt
and existing pending approval. Telegram acknowledged the same message/chat, a
poster, the exact requested catalog sentence, removal of the old instruction,
and the same approval button. The caption is 485 UTF-16 units. The approval store
was byte-for-byte unchanged; no new message, movie addition or download occurred.
The retry record now retains the updated prepared presentation and caption-kind
receipt. The before/intended/ack/result audit is private under `card-update/`.

Ordinary actor retries do not revisit already edited cards; only this specific
user-requested existing card was updated. The final documentation commit is not
deployed. Code rollback preserves current actions, cache and updated receipt state.
Telegram image fetching can fail; errors remain bounded and do not recreate
approvals. No movie addition, torrent download or import is authorized here.
The unrelated cleanup task and open runtime-stack work are preserved.
