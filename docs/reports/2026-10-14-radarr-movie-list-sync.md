# Radarr Movie List membership and score-band sync

Status: **Implemented, merged, deployed and reconciled**, 2026-10-14.
[Assigned brief](2026-10-14-radarr-movie-list-sync-brief.md) ·
[Verification JSON](2026-10-14-radarr-movie-list-sync-verification.json) ·
[Applied members CSV](2026-10-14-radarr-movie-list-members.csv) ·
[PR #7](https://github.com/kolorifer/radarr-festival-list/pull/7).

## Result

All **387** D016-qualified films now have **movie-list + exactly one score band**
in Radarr. **152 existing movies tagged; 235 missing records added.**
New records are monitored with searchForMovie=false.
Second live dry-run: 387 already correct; 0 updates/additions/removals/unresolved.
The installed scheduler launcher repeated successfully with 0 writes.

The 235 are movies absent from Radarr, distinct from the 163 Evidence Score admissions
in D016. Existing 225 qualification/224 grandfathering/1,909 scores are unchanged.

## Implementation and revisions

Branch: production/radarr-movie-list-sync; base main a4c9066.
Initial implementation835e16f; final code34c0bdc9da80353107267c84f2d69e732bb0d07a.
PR #7 merged/runtime installed at a587e25ff32820cc5da6bf5bbbd07f3c2ad238b5.
Previous seedbox revision b8e2634eb71b83494b144237767ac68364775fcc.
A subsequent handoff commit contains completed docs/artifacts with identical
runtime and scoring bytes; the final checkout revision is recorded on the PR.

Files: radarr_movie_list_sync.py, test_radarr_movie_list_sync.py,
deploy/radarr-sync.py, movie-list-sync.service/.timer, RADARR_SYNC.md,
CI workflow and project/task/decision/report documentation.

The sync uses exact IMDb lookup and a second TMDb lookup with agreeing IDs.
Ambiguities are skipped/reported; no fuzzy title/year admission is used.
Apply validates live state against its recorded plan. Existing changes use only
movie/editor tag add/remove; the write surface refuses full tag replacement,
non-tag editor fields, command endpoints and deletions.
Private snapshots, operation journals and a process-wide file lock support
safe repeated execution and partial-failure recovery.

## Dry-run, apply and tags

| Measure | Count |
|---|---:|
| Qualified catalog |387|
| Already correctly tagged before |0|
| Existing needing tags |152|
| Missing, exact identity verified |235|
| Unresolved/ambiguous qualified IDs |0|
| Managed-tag removals |0|
| Existing movies before/after |755 /990|
| Second dry-run changes |0|

Created all six managed tags; none existed before:

| Tag | ID | Applied qualified count |
|---|---:|---:|
| movie-list |3|387|
| ml-below-225 |4|51|
| ml-225-249 |5|48|
| ml-250-299 |6|104|
| ml-300-399 |7|96|
| ml-400-plus |8|88|

Score boundaries use full numeric values, inclusive 225/250/300/400.
Grandfathered below225 receive ml-below-225. No exact-score tags were created.

Root /home/kolorifer/movies; profile 7 Ultra-HD-Remux.
All755 preexisting movies used exactly that root/profile, making the conventions
unambiguous. Private ~/.config/movie-intel/radarr-sync.json (600) records them.
Existing movie roots/profiles/monitoring were never changed.

Verified examples: Paddington 2(score 224.22, newly added,3+4);
Brokeback Mountain(803.78,newly added,3+8); Boyhood(748.89,newly added,3+8);
Amour(679.91,newly added,3+8); Florida Project244.45, Sound of Metal242.93,
Coco241.70 and The Salesman240.81 were existing and now have 3+5.
All identities and per-film results are in the CSV.

## Tests and proof

**107 full tests passed, 25 new.**
Unit and real local HTTP tests cover zero-write dry-run, idempotence, unrelated-tag
preservation, stale-band replacement, exact boundaries, grandfathered below225,
monitored additions/search-disabled, exact identity conflicts/ambiguities,
managed-only removal, live-state drift, closed API writes and resumable timeouts.
D016 frozen387 and existing Telegram/add-grab tests remain green.

Seedbox full suite, pip check, production_scoring.py --check and config preflight
passed. Python 3.12/3.13 [PR CI](https://github.com/kolorifer/radarr-festival-list/actions/runs/38566311723)
and [branch CI](https://github.com/kolorifer/radarr-festival-list/actions/runs/38566304944)
passed. Privacy/diff/documentation checks passed.

Private before/after comparison verified **all original 755** monitoring, profiles,
roots/paths, file IDs, Overview and unrelated tags. All 235 new records have
monitored=true, correct root/profile and both managed tags.
All nonempty Radarr IMDb IDs are unique; every qualified ID is present once.

The exact write audit contains only:
6 POST/tag; 152 PUT/movie/editor; 235 POST/movie.
Every movie POST has searchForMovie=false. No /command, release push, delete,
file move or import-list refresh request is emitted.
Queue0 before/after; no new grab/download history events during apply.

Radarr's normal RefreshMonitoredDownloads/ProcessMonitoredDownloads and one
ImportListSync ran during the window. The import-list command's trigger was
**scheduled**, verified read-only. These are existing background work, not sync
requests. They are recorded separately from the approved-write audit.

The live post-apply plan and independent second dry-run both show387 correct,
zero remaining changes and zero unresolved. The scheduled wrapper also shows
zero new additions/tag updates/removals.

## Scheduler and service

Exactly one user timer, movie-list-sync.timer:
daily 03:43 UTC plus up to 15min randomized delay; Persistent=true.
No existing catalog-refresh scheduler hook was available; no duplicate sync
timer or cron entry existed. The shared private flock prevents overlap.
The oneshot reads existing private credentials, current catalog and sync config.

Unit syntax verification passed. Timer active/waiting; installed oneshot
Result=success, ExecMainStatus=0.
Movie-intel was not restarted: same PID 3062372, active/running, NRestarts=0.
Existing Telegram approval/exact-release flow and public feeds remain unchanged.

## Unexpected findings and unresolved issues

One preexisting unrelated Radarr record, Cativeiro (Radarr 675/TMDb 1493187), lacks an
IMDb ID. It existed before this task, has no Movie List ownership and was preserved.
It is not a qualified-film lookup failure and does not block reconciliation.
No product choice or qualified identity remains unresolved.

Normal background job names include 'Downloads'; those bookkeeping names alone
do not show a grab/download. Queue/history and the sync's exact write audit
establish zero acquisition from this run.
No scores, identity mappings, watched annotations or source interpretation changed.

## Backups and rollback

Full private Radarr before/after/plan/journal snapshots:
~/.local/state/movie-intel/radarr-sync/backups/20261014T124727Z.
Predeployment code/config:
~/.local/state/movie-intel/radarr-sync/predeployment.
Public reports contain selected identities/counts only, not private API payloads,
credentials, tracker URLs or complete unrelated-library state.

Prepared syntax-checked rollback, **not executed**:

Run over SSH on the seedbox, using the private before snapshot:

```sh
python3 ~/.local/state/movie-intel/radarr-sync/predeployment/rollback.py \
  --before ~/.local/state/movie-intel/radarr-sync/backups/20261014T124727Z/before.json
```

Disable the timer first (the script does so), wait for any running oneshot to finish,
restore only managed tags using add/remove, and return code to b8e2634.
Current unrelated tags/settings/files and private action/cache state are preserved.
Added movie records remain; no movie/file deletion is part of rollback.
No rollback was needed.
