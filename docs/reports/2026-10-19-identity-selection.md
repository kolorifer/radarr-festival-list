# Engineering report: issue 53 passive identity eligibility

**Specification:** [approved issue 53](https://github.com/kolorifer/radarr-festival-list/issues/53), [archived brief](2026-10-19-identity-selection-brief.md).
**Result:** implemented and passively deployed; production output review pending.
**Repository:** [PR 54](https://github.com/kolorifer/radarr-festival-list/pull/54), separate from merged PR 52. Phase 2 is not merged.
**Verification:** 2026-10-19, local Python 3.12, seedbox Python 3.13, CI both versions.

## What changed

Explicit movie-intel resolution outcomes now flow through a capability-free,
bounded observer into a private durable retry spool and the existing collector.
Intake and a new eligibility projection commit atomically. Research remains off.
Only a known identification failure with strong source-release correlation enters
the pending export; missing IDs and generic `unknown_movie` do not qualify.

Routes distinguish verified, routine, unassessed, eligible missing crosswalk/no
exact match, review-only title/year/ambiguous conflicts, retry-later provider/auth
failures, quarantine and unmatched outcomes. Stable source plus torrent identity
is required; supporting title/year/name and IDs must agree. Name-only matches
remain uncertain. Versions retain original provenance and contradictions; repeated
UUIDs/material do not produce duplicate admissions, old events cannot supersede
newer ones, and same-time conflicting evidence quarantines. Four original seed
cases keep their richer reviewed history and are excluded from re-import.

An authenticated narrow export provides Stage 2-compatible manifests without
giving the worker access to Stage 1 or actor credentials. This is a pending
eligibility queue, not a new researcher run. The closed pilot is never reopened.

## Files and components

| Component | Change |
| --- | --- |
| `movie_intel_service.py` | Preserve explicit resolver reason, start optional observer; existing notification/approval behavior unchanged |
| `identity_triage_observer.py`, `identity_outcome_outbox.py` | Sanitize, bounded asynchronous admission, durable retry with stable UUID, aggregate gap/error metrics |
| `identity_selection.py`, `identity_triage_store.py` | Additive atomic projection, fail-closed routing, evidence versions, strong correlation and deduplication |
| `identity_triage_intake.py`, `identity_triage_service.py` | Allowlisted outcome assertions/reasons, authenticated private export |
| Tests and deployment runbook | Regression, outage/replay/privacy gates and rollback/coverage instructions |

## Phase 1 acceptance

PR 52 head `14f42cc4593677b44c1b9b3d547f99a56aa539ba` had passing CI,
clean mergeability and no outstanding review feedback. Its final runtime
`2de1ba88d2a8be6fcbd87e0db2a15a089a0baa4a` had 481 passing seedbox/CI tests
and 479 local passes plus two Linux-only skips; the head added documentation only.
Fresh read-only health, installed hashes, configuration, binding and process checks
confirmed the disabled worker and closed 19-request ledger. PR 52 merged as
`fba7a0767cc94c5f77613880d893c82502bf567b`; issue 51 is closed. Neither actor
nor collector was restarted or upgraded as part of that merge.

## Tests and technical verification

- Final runtime `28d65ed5a6ec26825386b9be1bb7d52a27c2acef`: full suite **510
  tests**; seedbox and both CI versions pass all 510; local 508 pass, two Linux-only
  checks skipped. Local duration 147.283s; seedbox 34.971s.
- Both CI jobs passed at that exact revision:
  [run 39215626038](https://github.com/kolorifer/radarr-festival-list/actions/runs/39215626038).
- Dependency checks, frozen scoring (1,909 candidates; 387 qualified) and offline
  production configuration preflight passed. No dependency change.
- Regression coverage includes verified Snowman/Hamnet/Not Not Jazz exclusion,
  routine rejections, missing IDs, genuine missing crosswalk/no exact match,
  review-only conflicts, provider/auth failure, TV/malformed data, conflicting
  IDs/sources, same-title distinct releases, regenerated UUIDs, material changes,
  out-of-order and same-time conflicts, atomic rollback, concurrency and legacy
  outcomes without chronology.
- Reliability tests cover queue saturation without foreground HTTP, real loopback
  transport outage/recovery, spool restart, commit-before-ACK replay, duplicate
  ACK, SQLITE_BUSY/FULL, private permissions, export credential separation and
  stripping capabilities from malformed resolver assertions before persistence.
- Frozen production inbox migration preserved all eight original tables exactly,
  passed integrity checks, retained all four seeds and exported zero eligible
  cases. Old collector code successfully reopened the additive migrated copy:
  rollback does not require restoring an old database.
- Collector Landlock module, socket and effective system-call unit remained
  unchanged. Fresh installed startup passed ABI6 protected-directory/proc/new
  socket/metadata denial probes. Worker files match the previously proven installed
  metadata-only boundary; that worker was not activated again. Linux syscall
  regression checks passed in the fresh full suite.

## Deployment

Actor checkout and all five installed collector modules are pinned to tested
**`28d65ed5a6ec26825386b9be1bb7d52a27c2acef`**, from unmerged PR 54.
The collector rollout also explicitly deploys PR 52's fixed-reason storage
failure diagnostics; merging PR 52 alone did not deploy them.

Private configuration/code and triage-only backups were saved before rollout.
The observer reuses the existing outcome key; no new credential, privilege or
network permission was introduced. Exact autobrr notifier/filter/API-key rows
are unchanged. All actor environment settings except the observer flag/path,
and both reviewed bindings, are unchanged. No acquisition state was restored.

The inherited collector socket remained active during its short code restart.
The actor had no established request connection at the restart check; restart to
local health took **12.321 seconds**. Local and public health returned 200; both
services are active with NRestarts=0. The isolated collector's startup gate passed.
The new spool is private (directory 700, database 600).

The research worker remains installed at **`2de1ba88d2a8be6fcbd87e0db2a15a089a0baa4a`**,
inactive, with empty provider token, no recurring schedule and closed pilot. All
worker files and every pilot database table match the baseline. Requests remain
**19 total, zero new research GETs**. No deliberate notification, approval-token,
Radarr, movie-addition, download or search test was performed.

Rollback: disable the observer flag and restart movie-intel; restore the prior
actor commit/configuration and collector modules if necessary. Keep additive
triage tables and private committed spool. Never restore stale acquisition state.
The rollback compatibility check passed; production rollback was not needed.

## Measured intake and coverage

The predeployment frozen inbox held **564 distinct source releases**, 568 evidence
versions, 421 provisional groups, four seeds and **zero recorded identity
outcomes**. It contained 114 live accepted announcements plus retained intake.
All 564 were therefore *unassessed by this projection*, not newly failed movies.

At deployment there were **565 source releases**, 569 evidence versions, 422
provisional groups and **115 live accepted movie announcements**. The 260 rejected
release.new inputs are intake rejections, not confirmed movie-identification
failures or a measured delivery-loss count.

Final passive snapshot at 270.9 seconds after deployment: **566 source releases**
and **116 live accepted announcements**, including one new natural announcement
after deployment. The collector continues accepting real traffic. Zero outcome events, zero assessed release cases,
zero new eligible/review-only/verified/unmatched cases, zero new or duplicate
admission versions, zero pending spool messages and zero known observer errors.
**Four previously investigated unresolved movies remain; zero additional genuine
failures have been demonstrated.** A zero queue with zero fresh outcomes is not
an identification success rate. A natural positive live outcome is still needed
to verify real publisher-to-actor-to-selection correlation; its positive behavior
is currently demonstrated by isolated integration tests only.

Historical collector storage warning count was one before restart (cause still
unknown). After the checked rollout the process counter is zero; this does not
erase the historical warning. New failures now have fixed diagnostic reason codes.

## Limitations and recommendations for review

- Actor persistence is asynchronous. Committed spool messages have at-least-once
  delivery; the 32-item memory window may lose messages on crash/saturation.
  Known failures are counted/logged; crash-window loss is unknown, not zero.
  Publisher delivery also lacks an outbox. Complete announcement coverage is not
  established, and no automatic historical backfill was performed.
- Source releases that never enter movie-intel's rejection path remain unassessed.
  Weak or absent source IDs withhold automatic admission. Counts are conservative
  **release identity cases**, not deduplicated canonical film counts.
- No fresh natural outcome had arrived at initial readback. The original four
  cases already have proposals; their history must not be overwritten or rerun
  merely because a schedule is introduced.
- Future approved research still needs a controlled private manifest transfer and
  a fresh bounded run/ledger. The authenticated export is limited to ten cases;
  pagination/large-backlog draining is not implemented. The worker never receives
  the collector key or direct database access.
- **Recommendation, not activated:** start with a weekly run only when new or
  materially changed eligible cases exist, capped at **5 cases / 25 GETs per week**
  (and at most 5 GETs per case). Skip unchanged closed attempts and provider-outage
  cases. Review a week of passive outcomes before increasing frequency. Current
  zero-assessed data cannot justify daily research or estimate demand reliably.
- Recurring research, automatic corrections, broader tracker access and Stage 3
  remain reserved for further approval. PR 54 remains separately reviewable.

## Project context

This report and the archived issue 53 brief record implementation and deployment;
project state links them and separates the current pins from historical reports.
The unrelated Rambo/cleanup assignment in `CODEX_TASK.md` was preserved. No new
product decision or scheduled task was created.
