# Engineering report: Grab Anyway eligibility recovery

**Specification:** [completed brief](2026-10-25-grab-eligibility-recovery-brief.md).
**Result:** implemented and deployed; PR review and live recovery observation pending.
**Runtime revision:** `99d81d8e89f7fac5a0545fc1303ea8dd278846f2`.
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
| Deployment | Passed | Clean running revision, health 200, zero restarts, state preserved |

## Tests run and results

Focused synthetic suite: 29 tests passed, including local mock Telegram transport.
Final full local suite: 686 tests, passed with two skips (154.935 seconds).
Final full seedbox suite: 686 tests, all passed (44.998 seconds).
Python 3.12 and 3.13 [CI passed](https://github.com/kolorifer/radarr-festival-list/actions/runs/40191146259).
Local and seedbox pip check passed. Production scoring reproduction passed:
1,909 candidates, 224 grandfathered, 163 new, 387 qualified. Seedbox deployment
configuration preflight passed. Diff whitespace check passed.

An earlier local run failed the newly added receipt-wrapper test because its
temporary home lacked `.local/state`; the fixture was corrected and the full
suite rerun successfully. All notification tests used synthetic local transports.

## Deployment result

Activated `99d81d8e89f7fac5a0545fc1303ea8dd278846f2` at 12:02 UTC on
2026-10-25. Clean checkout; movie-intel active/running, NRestarts=0. Local and
public HTTPS health both returned 200 with 1,909 catalog movies. All 34 preexisting
approvals and acquisition receipts were unchanged. Protected private
configuration and identity collector PID/state were unchanged. Backups are in
the private host directory `~/.local/state/grab-eligibility-20261025`.

Production contains unmerged runtime work from PRs #79 and #82; this isolated
fix uses the actual running baseline without replacing it with main or merging
unrelated work. PR #83 remains open for review against that baseline.
Rollback: stop only movie-intel, restore code to `25eae80`, restart and verify
health; preserve current private state and never restore old action snapshots.
New spool files are ignored by the older code and retained for recovery.

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

[PR #83](https://github.com/kolorifer/radarr-festival-list/pull/83), open for review.
Implementation/deployed commit: `99d81d8e89f7fac5a0545fc1303ea8dd278846f2`.
The subsequent report commit changes documentation only and is not deployed.

## Project context updates

Brief and report saved here; project state updated. The unrelated active cleanup
assignment is preserved. No scoring, film-cut policy or approval policy changed.
