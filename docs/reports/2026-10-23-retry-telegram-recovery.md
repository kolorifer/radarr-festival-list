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

Tests cover receipt
ownership, success before/after binding, restart recovery, action reuse, bounded
edit failures, retry expiry/exhaustion, replay protection, superseded cases,
private permissions, exact-release confirmation, missing references, caption
limits, changed chats, uncertain actions and idempotent edits.

API reference: [Telegram message editing](https://core.telegram.org/bots/api#updating-messages).


## Test results

- Exact runtime 2320281: **664 tests passed** locally in 151.936s (two Linux-only
  skips), and on seedbox in 44.280s. This isolated actor suite intentionally does
  not include the unmerged shadow experiments.
- Targeted notification/identity retry regressions passed; the added transport
  integration uses a local fake Telegram HTTP server and captures/edits message 42.
- Both Python 3.12/3.13 CI jobs passed on review revision 118e055, run 39927465660.
- Dependency check passed. Production catalog preflight passed (1,909 candidates,
  387 qualified); configuration preflight passed. No source/catalog changes were
  included beyond the three actor implementation modules and tests/report.

## Deployment and live read-only verification

Production actor is **23202815754ba2d97a86608003ca276251f1ae9c**, isolated on the
previous verified actor 658d8f838aed7a03db7d01244254362fba99369a. The equivalent
main-based review change is in [draft PR #79](https://github.com/kolorifer/radarr-festival-list/pull/79).
The PR was not merged; unrelated catalog and shadow changes were not deployed.

Backup: `retry-telegram-backup-nqm7lgv6`, containing private configuration, actor
state and retry state. Only movie-intel was restarted. Local and public health
returned **HTTP 200**. Actor, collector and research/shadow timers are active;
collector PID and protected configuration/action/timer/pilot hashes were unchanged.
Shadow remains ab88fbd, with its original caps and pilot end date.

The new receipt table was initialized by the live retry worker. It contains zero
receipts at verification because no live test notification or old-message replay
was sent. All 19 existing retry jobs were already done; history stayed unchanged:
28 attempts, 58 provider request reservations, two provider-state rows. The action
store remained byte-for-byte unchanged. No download, Radarr mutation, provider
lookup or notification replay was triggered by deployment verification.

The first naturally occurring retryable notification will exercise the real
Telegram edit path. This remains the only live integration limitation: correctness
of actual HTTP transport was tested locally, not by sending a user-visible test.
Old warnings without receipts cannot be repaired automatically by this rollout.
Rollback restores only the previous actor code, preserving the new private tables,
current approval state and retry history; old code safely ignores the extra table.

## Project updates

Recorded D045 and updated project state. Existing unrelated cleanup brief remains
assigned. The shadow monitor's expected actor revision was updated; its read-only
scope and timing were preserved.
