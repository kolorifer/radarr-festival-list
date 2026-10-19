# Engineering report: changed-case Telegram digest

**Specification:** [Approved brief](2026-10-19-identity-digest-brief.md).
**Result:** Implementation complete; final testing and live enablement pending.
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
Final full-suite, CI and deployment evidence will be recorded after gates pass.

## Deployment result

Pending. Production remains pinned to the previously verified version until
preflight and seedbox tests pass. Private configuration/state backup and rollback
preserve delivery reservations and existing action state.

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
remains untouched. Final commit/PR and deployed status will be added after checks.
