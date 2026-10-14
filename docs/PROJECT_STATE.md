# Movie List project state

Last verified: 2026-10-14. Read [decisions](DECISIONS.md),
[active task](CODEX_TASK.md) and [engineering instructions](../AGENTS.md).

## Private Radarr read-only snapshot bridge

D018 implemented on production/radarr-snapshot-bridge, PR #8 merged at93a5761.
Deployed runtime is the validated merge; the subsequent documentation handoff
preserves runtime bytes. The same daily Movie List sync exports/publishes only
after successful reconciliation, with no second timer or Radarr credential store.

Private kolorifer/radarr-state/radarr-current.json has990 records. Live seedbox
publication and GitHub-connection readback are verified; all IDs/flags/tag labels
match, repeat exports are deterministic except timestamp, and generation made
zero Radarr writes. Snapshot/config/GitHub credential stay private with mode600.
One pre-existing missing IMDb ID remains null. Only schema-v1 allowlisted library
fields are exported; no Overview, paths, queue/releases or connection credentials.

133 tests (26 new), Python3.12/3.13 CI, pip check, preflight and frozen-catalog
validation pass. Existing timer/unit bytes are unchanged. movie-intel remains
active/running, same PID, zero restarts, local/public health200.
No manual reconciliation/apply or real download was triggered.
The first naturally scheduled hook run has not yet elapsed; its actual CLI
integration is tested and the deployed publisher is separately live-verified.
No access blocker remains. Keep the state repository private; token expiry can
cause stale snapshots without stopping/repeating reconciliation.

[Runbook](../deploy/RADARR_SNAPSHOT.md) ·
[Engineering report](reports/2026-10-14-radarr-snapshot-bridge.md).
Current implementation task is idle.

## D017 Radarr Movie List membership and score-band sync

Implemented on production/radarr-movie-list-sync, PR #7 merged at
a587e25ff32820cc5da6bf5bbbd07f3c2ad238b5. Source 34c0bdc passes 107 tests
(25 new), pip check, frozen-catalog validation and configuration preflight.
Main's subsequent handoff keeps runtime/scoring/catalog bytes unchanged.

Live dry-run: 387 qualified; 152 existing to tag; 235 missing; 0 unresolved.
Applied:152 existing tagged and 235 monitored records added with searchForMovie=false.
All 387 have movie-list and exactly one score band:
below225: 51; 225–249: 48; 250–299: 104; 300–399: 96; 400+: 88.
Membership tag 3; band tags 4–8. No exact-score tags/Overview changes.
Root /home/kolorifer/movies and profile 7 Ultra-HD-Remux were the single conventions
used by all 755 existing movies; they are frozen in private sync configuration.

Radarr has 990 movie records. All original 755 retain monitoring/profile/root/path/
file IDs/Overview and unrelated tags. A second live dry-run has 387 correct and
zero changes/unresolved; the installed oneshot repeats with zero writes.
No search/grab/download/import-list-refresh command was issued by this sync.
Queue remained 0 and no new grab/download history events occurred during apply.
Radarr's existing scheduled ImportListSync and normal monitored-download
bookkeeping ran independently; they are documented separately.

One unrelated existing record (Cativeiro, Radarr 675, no IMDb ID) was already
incomplete and remains untouched. All 387 qualified identities are exact/unique.

One user-systemd timer: movie-list-sync.timer, daily 03:43 UTC with up to 15min jitter,
Persistent=true. Shared private flock prevents overlapping CLI/timer runs.
Movie-intel remains active/running with the same PID and 0 restarts; health 200.

[Runbook](../deploy/RADARR_SYNC.md) ·
[Engineering/deployment report](reports/2026-10-14-radarr-movie-list-sync.md) ·
[Machine verification](reports/2026-10-14-radarr-movie-list-sync-verification.json) ·
[Applied members CSV](reports/2026-10-14-radarr-movie-list-members.csv).
The implementation task is idle. D012/D014/D016 and public feeds remain unchanged.

## D016 production implementation

Implementation branch: production/d016-qualification, based on main 696420a.
[PR #6](https://github.com/kolorifer/radarr-festival-list/pull/6) merged.
Implementation: 87873dafe2c08d8f1ce13163cb57efd15c2b7b50.
Runtime activated: 8e357b9edc90307c6af3e64f1c334527a11a5227.
The main handoff adds documentation/audit clarification without changing runtime
code, scoring inputs, frozen baseline, expected scores or generated catalog.

movie-intel.service is active/running, with the same process since activation
and NRestarts=0. Local and public HTTPS health return 200 and 1,909 movies.
Read-only Radarr status/roots/profiles, Telegram getMe/getChat and TMDb
configuration checks return 200. Autobrr notification 2 remains enabled WEBHOOK,
matches the private movie-intel target and includes PUSH_REJECTED.
No real notification/add/search/download was deliberately triggered.

82 tests pass, including 29 new regressions, on seedbox and Python 3.12/3.13 CI.
pip check and configuration preflight pass. Artifact regeneration is byte-identical;
all 1,909 score/family/rank values and the exact 224 deployed IDs/routes verify.
Privacy/doc/scope checks pass. The current task is idle.

The authoritative rule is exactly:
`qualified = grandfathered_deployed_224 OR Evidence Score >=225`.
Threshold inclusive. Frozen baseline is the 224 deployed at c7a4582; the 255
research comparator and 31 additions are historical diagnostics only.
Active routes: grandfathered_production, evidence_score_225; both may apply.
Legacy convergence/corroboration/canon never independently admit future films.

[Production data and reproduction](../production/README.md) replace movie-intel's
simulation qualifier dependency. All 1,909 frozen scores match PR #5, producing
387 qualified =224 retained +163 new. Of research31,11 naturally pass225 and 20
remain unqualified. D012 weights/Audience150/effective ceiling1000, canon
correlation and D014 anthology attribution are unchanged.

The runtime loads a validated production catalog without network scoring calls.
Unknown-movie Telegram messages show active D016 routes. A verified IMDb ID from
existing conservative TMDb resolution can join the catalog when an announcement
uses another title spelling. Approval/token/Radarr exact-release behavior remains
the deployed implementation, with automated HTTP integration coverage.

Read-only Radarr inspection found no import list consuming qualification,
research outputs or backcatalog. Existing festival lists are independent.
The D016 score promotion performed no movie additions/searches/downloads or
list refresh. D017 above separately authorizes monitored record reconciliation.
Public festival/curated/backcatalog list IDs/order remain unchanged.

## Watch annotations and data limitations

La Ciénaga and Uncle Boonmee were incorrectly watched; they are now unknown,
matching selected-to-watch without adding a visible state. Elephant was already
unknown and is regression-covered. Scores and qualification are unaffected.

IMDb coverage1909/1909; Letterboxd1900/1909. Nine gaps remain explicit.
Award-source unresolved counts: NSFC0, NYFCC0, LAFCA1, Critics Choice22,
EFA8, Gotham1. Small Axe and combined Nymphomaniac remain unallocated.
The five PR #3 TSPDT identity corrections are retained. No new enrichment,
identity resolution, formula or source interpretation was introduced.

## Live Telegram add-and-grab integration verified

On 2026-10-13 the real production path was successfully tested end to end using
an autobrr/Radarr `Unknown Movie` rejection for **Marty Supreme (2025)**.
The Telegram notification exposed the live **Add to Radarr & grab this release**
action for the exact announced TRiToN 2160p UHD BluRay Hybrid REMUX release.

Opening the action loaded the confirmation page with the resolved movie/poster,
exact release, Radarr root-folder selector and quality-profile selector. The live
test used `/home/kolorifer/movies` and `Ultra-HD-Remux`. Submission returned
**Added and sent to downloader** and reported that the exact announced release was
re-pushed with no indexer search. The user then confirmed successful completion in
the real Radarr/downloader flow.

Therefore this path is now live-verified, not merely synthetic/test-suite coverage:

`real autobrr rejection -> movie-intel webhook -> enriched Telegram notification -> approval page -> Radarr movie add -> exact release re-push -> downloader`

The single-use replay/HTTP 410 behavior was not separately re-demonstrated in this
live test; it remains covered by the automated service tests. No private tracker
URL, API key, webhook secret or action token is recorded in project documentation.
See [live integration report](reports/2026-10-13-live-add-grab-test.md).


## Research and engineering history

Research PRs remain unmerged audit history:
[identity cleanup #3](https://github.com/kolorifer/radarr-festival-list/pull/3),
[qualification calibration #4](https://github.com/kolorifer/radarr-festival-list/pull/4),
[final P225/P250 #5](https://github.com/kolorifer/radarr-festival-list/pull/5).
Validated handoff9c5a0f0; D016 decision906ff64.
Their large simulation artifacts are not production runtime/build dependencies.

[Current production brief](reports/2026-10-14-d016-production-brief.md) and
[engineering/deployment report](reports/2026-10-14-d016-production.md) record
tests, revision/PR references, deployment checks, privacy and rollback.
