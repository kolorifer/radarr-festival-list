# Reconcile stale investigation statuses

## Approved brief

After identity-rule changes, refresh affected investigation cases without sending
notifications or starting downloads. Reconcile Bruce and Madame Bovary, preserve
history and existing acquisition/research safeguards. Leave unrelated cleanup work
and identities unchanged.

## Implementation

Added a generic operator maintenance helper and deployment gate. Prepared outcomes
must match the existing case fingerprint and complete normalized source metadata.
Transient failures cannot replace meaningful prior results. Report refresh is
bounded to explicitly named cases and refuses unrelated projection drift.

Silent maintenance receipts suppress only the precise affected digest versions,
using an honest `suppressed` state. Previously sent/uncertain records are retained;
future changed evidence and unrelated notifications are not suppressed. No new
scheduler, matching exception, research call or acquisition path is introduced.

The live actor runtime stays pinned; this maintenance helper is executed separately
with the installed collector and actor modules. An isolated database-copy proof
precedes actual observer ingestion and report publication. Pause the actor/digest
and scan timer during publication, then restore their prior operation and health.

## Verification and result

Local full suite651 tests passed,2 Linux-only skips. Four helper tests also passed
on the seedbox. Both Python3.12/3.13 CI jobs passed. PR
[#75](https://github.com/kolorifer/radarr-festival-list/pull/75) merged as
`2dfedf96f517b7004c84d6cead1af12620d353d5` (implementation `08e2a93`).

Live reconciliation completed:

- Bruce Almiighty: old `title_conflict/review_only` replaced by a fresh
  `external_id_verified/verified` result under the generic typo rule.
- Madame Bovary: historical `external_id_verified/verified` replaced by a fresh
  `year_conflict/eligible` result, meaning investigation/review is required.
- Both collector projection and private review report agree. Their complete source
  fingerprints and normalized metadata matched before publishing. Old evidence,
  decisions, events, request history and proposals were retained.
- Exactly two new digest records are marked `suppressed`. Every pre-existing
  delivery record stayed byte-for-byte equivalent at the row level; no messages
  were sent. An isolated copy proved the entire refreshed report produces zero
  immediate sends before publication; live readback confirmed only silent receipts.
- Actions, downloader receipts, private configuration, installed collector/worker/
  handoff modules and the complete research ledger were unchanged. Collector PID
  stayed unchanged. Actor and scan timer were briefly paused for atomic publication,
  then restored active. Local/public health200. No notifications or downloads.
- Production actor remains **`3a6c2cc9e2613a60719ba7030e5968895d14d7f2`**.
  No runtime matcher change or new scheduled job was needed; maintenance used the
  tested helper privately with existing installed modules.

Unexpected findings: autobrr no longer retained the exact old Bruce row, so its
private saved evidence was used, requiring exact normalized source equivalence.
The first isolated proof also detected a new natural **Audition** verified case
since the previous report and stopped before any live mutation. That verified,
never-notified row was represented in the report before re-running the proof;
no unrelated unresolved case or notification was suppressed. All backups and
prepared events remain private for audit.

## Limitations

This is a mandatory deployment procedure, not a new recurring scanner. It requires
retained exact source evidence and an explicit affected-case scope. Missing source
evidence, concurrent case changes or temporary lookup failures are reported rather
than guessed. Research proposal history is retained and stale evidence is labelled;
the ordinary bounded worker may produce future updates on its normal schedule.

## Owner-requested Aberfan skip

The owner subsequently chose to skip Aberfan: The Village That Fought Back(2026),
stating it is not wanted in the library and autobrr filters were independently
changed. This is a preference/disposition, not proof of absence from IMDb and not
an identity correction.

Applied the existing `skipped_routine` outcome to the exact retained case through
the collector, with normalized source matching, a private owner-decision record,
backups and an isolated-copy proof. The collector/report now classify it as
`routine/skipped_routine`, excluding it from unresolved review and eligible research
export. Original evidence and the awaiting-evidence research history are preserved.
One precise digest version is silently suppressed; no message or download occurred.
A new naturally verified Frankenstein row was included in the refreshed report;
no unrelated unresolved cases were altered. Actions, receipts, configuration,
research ledger and collector PID stayed unchanged; services restored and health200.
Runtime remains `3a6c2cc`; no code change or full-suite rerun was needed for this
operator disposition. No autobrr or Radarr setting was changed. A future newly
admitted occurrence is still governed by ordinary rules and the owner's filters.
