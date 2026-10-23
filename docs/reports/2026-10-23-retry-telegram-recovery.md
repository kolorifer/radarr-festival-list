# Original Telegram message updates after identification retries

## Approved brief

Update the original Telegram notification when identification retries succeed or
end, with the appropriate confirmation/review action. Test and deploy safely,
preserve explicit download confirmation and trigger no downloads. Isolate this
actor change from the unmerged shadow-scoring experiments and unrelated catalog
changes. Preserve the unrelated active cleanup brief.

## Implementation

Bot responses now supply private, thread-local receipts containing only chat ID,
message ID and text/caption kind. Webhook fields cannot supply message ownership.
Retryable notifications bind their first successful receipt to the same version
as the existing retry job and retain the exact original release privately.
Payload/reference fields are allowlisted and never put in notification text.
A duplicate webhook cannot replace the original receipt/reference.

Terminal outcomes are queued atomically with retry completion, including maximum
attempts and seven-day expiry. A durable edit worker prepares one action/text,
then edits the captured text or photo caption. Preparation is reused across edit
failures/restarts. The worker attempts at most five edit batches with backoff;
lost ACKs can safely repeat the same edit. It never sends a new message as a
fallback. Private receipt/context storage is limited to eight days/10,000 rows.
This one-day grace allows seven-day retry expiry to be reported.

Verified success uses the existing exact-release pending action and confirmation
page. No Radarr add/search/grab or downloader submission is called. Missing source
reference/configuration means identification may succeed without an action.
Identity conflicts get a review button only where the existing evidence-review
flow supports it. Exhausted/unverified cases get no download button. Expired,
consumed or uncertain actions are not recreated or re-offered during edit retry.
Changed chat configuration blocks editing an old chat. Split/supplemental messages
have stale buttons removed and point to the first message's updated result.

## Limitations

Historical notifications have no saved message IDs and cannot safely be edited
retroactively. The two already recovered examples therefore stay unchanged; no
IDs are guessed and no notification replay is performed. The new behavior applies
to captured future retryable notifications. There remains a narrow crash window
between Telegram accepting a send and local receipt persistence, as with any
external send/receipt transaction; failures are logged without sensitive data.
Telegram refusal/deletion or prolonged outage can exhaust the five edit attempts.
No live test notification is sent; real transport serialization is tested against
a local fake Telegram server.

## Verification/deployment

Pending full test gates and guarded runtime deployment. Tests cover receipt
ownership, success before/after binding, restart recovery, action reuse, bounded
edit failures, retry expiry/exhaustion, replay protection, superseded cases,
private permissions, exact-release confirmation, missing references, caption
limits, changed chats, uncertain actions and idempotent edits.

API reference: [Telegram message editing](https://core.telegram.org/bots/api#updating-messages).
