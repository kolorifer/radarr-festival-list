# Movie List project state

Last verified: 2026-10-14. Read [decisions](DECISIONS.md),
[active task](CODEX_TASK.md) and [engineering instructions](../AGENTS.md).

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
No bulk additions, searches, downloads or list refresh are part of this rollout.
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
