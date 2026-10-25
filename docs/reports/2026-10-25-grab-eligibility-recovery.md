# Engineering report: Grab Anyway eligibility recovery

**Specification:** [completed brief](2026-10-25-grab-eligibility-recovery-brief.md).
**Result:** implemented; validation and deployment pending.
**Baseline:** production `25eae809e63f734689a0ce2243c8140e2657b8d0`.
**Verification date:** 2026-10-25.

## What changed

The 11:30:15 CET announcement was rejected solely because the existing file was
Remux-2160p v1. Its exact-listing metadata lookup failed temporarily; withholding
an approval before identity verification was correct. At approximately 11:45 CET,
automatic retry verified the movie, but the original Telegram receipt had not
been retained. Therefore the original card could not be edited.

Separately, the retry binding code fabricated an Unknown Movie rejection instead
of retaining the real action/reasons. That could select the wrong confirmation
flow on recovery. Bindings now preserve original event/action/rejections and
source guard fields; legacy incomplete bindings cannot create approvals.

Acknowledged message receipts are atomically written to an owner-only bounded
spool before a retry database transaction. The existing worker imports them and
edits only the original message. Database failure retains the file for retry.
No receipt is accepted from webhook-provided message IDs. Diagnostics distinguish
storage, validation and unexpected runtime failure without exposing payloads.
The initial card explains temporary identity lookup failure explicitly.

## Files and components changed

| Component | Purpose |
| --- | --- |
| retry_telegram.py | Preserve original event; durable receipt spool; fail closed on legacy bindings |
| movie_intel_service.py | Queue receipts independently of SQLite; clearer unavailable message |
| test_retry_telegram.py | Recovery, restart/contention, original-event and no-acquisition regressions |

## Acceptance criteria and evidence

| Criterion | Result | Evidence |
| --- | --- | --- |
| Exact release investigation | Passed | Read-only autobrr event, retry completion and sanitized journal |
| Current eligibility | Passed | Original source + recovered identity + live Radarr read; create_action mocked, no writes |
| Quality recovery | Passed focused tests | Alternative action retains original rejection/source and current file snapshot |
| Negative safeguards | Passed focused tests | Mixed reasons, season field and legacy payload create no acquisition approval |
| Receipt retention | Passed focused tests | Queue without opening SQLite; failed flush persists; restart retains original message |
| No acquisition | Passed focused tests | ensure_movie and push_release are never invoked |
| Deployment | Pending | See final deployment result |

## Tests run and results

Focused synthetic suite: 29 tests passed, including local mock Telegram transport.
Full local/seedbox suite and preflight results will be recorded after completion.

## Deployment result

Pending. Production contains unmerged runtime work from PRs #79 and #82; this
isolated fix is based on the exact running revision, without replacing it with
main or merging unrelated work.

## Unexpected findings

The historical receipt-saving exception was reduced to a generic log code.
Its exact cause is unverified. SQLite contention is a plausible failure mode,
not a proven diagnosis. The durable spool removes SQLite from receipt capture
and adds useful failure classification.

## Unresolved issues and risks

The old card has no retained Telegram message ID; it cannot safely be repaired
in place. No IDs were guessed and no replacement notification was sent. Current
eligibility was verified read-only, but no live recovery notification or download
was exercised. The spool is bounded at 1,000 files; storage/capacity failures
remain fail-closed and logged. A crash before Telegram acknowledges delivery or
before a receipt reaches durable storage cannot be eliminated by this change.

## Commit and PR reference

The containing implementation commit/PR records this change against the isolated
production baseline. Deployment and final evidence will be appended separately.

## Project context updates

Brief and report saved here; project state updated. The unrelated active cleanup
assignment is preserved. No scoring, film-cut policy or approval policy changed.
