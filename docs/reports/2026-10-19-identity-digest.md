# Engineering report: changed-case Telegram digest

**Specification:** [Approved brief](2026-10-19-identity-digest-brief.md).
**Result:** Implemented, enabled and live delivery verified; corrections still require review.
**Runtime:** `8846f5195d4094a337726d1f7829659ecdeb8f85`; [PR59](https://github.com/kolorifer/radarr-festival-list/pull/59).
**Verification date:** 2026-10-19.

## What changed

An actor-owned background sender reads the complete private research report and
sends new/materially changed review cases through the existing Telegram bot/chat/
topic. Current review cases are sent once on first enablement; unchanged cases,
observation timestamps, unassessed releases and unchanged historical seeds do not
create repeated messages. Previously reported cases can report recovery.

The message includes title/year, fixed reason/research status and current,
explicitly unverified TMDb candidate IDs. Stale proposals are labelled. Every
message requires review; no action buttons, tokens, links or identity writes.
Existing metadata/research budgets, sandbox boundaries and Radarr/Grab paths remain
unchanged. The research worker never gains Telegram credentials.

## Files and components changed

| Component | Purpose |
| --- | --- |
| identity_telegram_digest.py | Private durable reservations, safe projection, bounded sender |
| movie_intel_service.py | Start sender after listener binding using existing Telegram transport |
| deployment_config.py | Validate default-off enable switch |
| test_identity_telegram_digest.py | Dedup, crash/ambiguity, throttling, privacy, capacity, concurrency |
| deploy/README.md | Enable, inspect uncertainty and disable/rollback procedure |

## Acceptance and technical evidence

Focused tests cover changed evidence/proposals, restart suppression, timestamps,
complete-report consumption, stale candidates, explicit 429 cooldown, concurrent
reservation, locked storage, private files, disabled mode and bounded plain text.
Seedbox full suite: 560 tests pass; CI Python 3.12/3.13 both pass. Focused
digest suite: 14 tests pass. Local full suite: 558 pass and two Linux-only skips.
Dependency check, offline enabled configuration, frozen scoring and diff checks
pass: 1909 candidates, 224 grandfathered, 163 new, 387 qualified.

## Deployment result

Production is clean and pinned to verified runtime `8846f5195d4094a337726d1f7829659ecdeb8f85`.
Only movie-intel restarted, with the enable flag set in existing private config.
Configuration/action/outcome/retry backups remain private. All protected collector,
worker, helper, timer and reviewed-binding hashes remain unchanged; collector PID
unchanged. Local/public health return 200 with 1909 movies, actor/collector active
with NRestarts=0, daily research timer active.

Telegram acknowledged one plain-text digest covering the two current review cases:
Aberfan (unverified movie candidate TMDb 1796471) and 2018 Everyone Is A Hero
(listing ID quarantine). Two case versions are durably marked sent, zero uncertain
or retry deliveries. Reopening the ledger and processing the same complete report
produced zero sends. Research remains at one case/two GETs, unchanged by deployment.
No metadata replay, identity correction, approval token, Radarr operation or
acquisition was performed for this rollout. Normal production events continue.

Disable with the flag and restart only movie-intel. Rollback to prior runtime
`4c55f2a29314fa18c5131c4199aa9bf53966bd35` and saved environment if necessary;
preserve the digest ledger and current action state. No worker rollback is needed.

## Unexpected findings

The first unattended daily research scan succeeded with no changed cases or
additional research GETs. New normal production events arrived afterward; some
outcome deliveries retried. This digest does not change that delivery pipeline.

## Remaining limitations

Telegram sendMessage has no idempotency key. Reservation precedes the request;
uncertain acknowledgements/crashes are retained for manual inspection, not blindly
retried. Only explicit 429 rejection is automatically retried, respecting a longer
provider delay. Journal counts expose uncertainty but are not a separate alert
channel. Latest-state polling can coalesce intermediate changes. Daily research
cadence and upstream intake gaps still govern report coverage. Reports older than
48 hours fail closed. Telegram receipt is technical delivery, not user review.
Identity corrections remain a separate approved engineering task.

## Project context

The approved brief and runbook are saved. The unrelated CODEX_TASK cleanup task
remains untouched. The deployment is pinned to tested runtime; report-only follow-up commits and
unrelated automated catalog updates are not deployed. Final merge status is
available on PR59. Prior decision/sign-off text in historical reports is superseded
by this approved digest brief and D022.
