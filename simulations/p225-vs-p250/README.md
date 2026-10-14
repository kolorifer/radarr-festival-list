# Final P225/P250 calibration artifacts

[Draft PR #5](https://github.com/kolorifer/radarr-festival-list/pull/5) ·
[Engineering report](../../docs/reports/2026-10-14-p225-vs-p250.md) ·
[Detailed summary](summary.md).

Starting branch: research/qualification-calibration at 64d1f61a547de1e8330646a104656e1072720782.
Generated data: 9e9c528007948b1c79d328a09a08d06e4814faa1. Research only; no final threshold chosen.

## Decision evidence

| Policy | Total selected | Deployed224 retained | New | Audience-dominant new | Recent selected/new |
| --- | ---: | ---: | ---: | ---: | ---: |
| P225: deployed OR score>=225 | 387 | 224 | 163 | 3 | 61/46 |
| P250: deployed OR score>=250 | 351 | 224 | 127 | 1 | 53/38 |

The practical difference is 36 non-production films at 225–<250.
All have 106.98 or more non-Audience points; none is Audience-only or supported
by fewer than two positive independent non-Audience families.
Coco and Nobody Knows are the two additional >50% Audience cases.
Dune: Part Two qualifies under both with 58.02% Audience.

**Authority:** only the 224 deployed qualifiers at c7a4582 are grandfathered.
The 255 research set remains diagnostic. Of its 31 additions:
8 naturally qualify>=250;3 qualify 225–<250;20 qualify neither.
The three middle cases are Sound of Metal, Coco, The Salesman.
Below-threshold research membership never admits a film under either policy.

## Exact reconciliation

| Threshold | Old A total/new vs 255 | New P total/new vs 224 | Removed legacy-only | Natural research31 now counted new |
| --- | ---: | ---: | ---: | ---: |
| 225 | 407/152 | 387/163 | 20 | 11 |
| 250 | 374/119 | 351/127 | 23 | 8 |

P225:407−20=387;152+11=163.
P250:374−23=351;119+8=127.
Old A225/A250 differed by 33; P225/P250 differ by 36 because three research-only
films in 225–<250 were formerly grandfathered under both thresholds.

## Files

| Artifact | Contents |
| --- | --- |
| [summary.md](summary.md) | Policy distributions, all36 differences, shortlists, all 31 provenance, borderlines, quality checks; ends with Product review summary |
| [comparison.json](comparison.json) | All 1,909 film records/flags, policy populations, cohort/source breakdowns, history/classification and reconciliation |
| [per-film.csv](per-film.csv) | All films, all family columns, P225/P250 and deployed/research/taste/watch status |
| [P225-new.csv](P225-new.csv) | All163 P225 newcomers |
| [P250-new.csv](P250-new.csv) | All127 P250 newcomers |
| [P225-only-vs-P250.csv](P225-only-vs-P250.csv) | The36-film review cohort, sorted by frozen score/rank |
| [research-31-review.csv](research-31-review.csv) | All 31 scores/routes, natural eligibility, shortfalls, grandfathering flags and introduction reasons |
| [baseline-reconciliation.csv](baseline-reconciliation.csv) | Exact old/new totals and count equations |
| [borderline-P225.csv](borderline-P225.csv) / [borderline-P250.csv](borderline-P250.csv) | Inclusive±15 windows, all statuses and family scores |
| [210–<225](borderline-band-210-225.csv), [225–<240](borderline-band-225-240.csv), [240–<250](borderline-band-240-250.csv), [250–<265](borderline-band-250-265.csv) | Exact requested bands |
| [inputs/research31-history.json](inputs/research31-history.json) | First qualification/prior unqualified records, institutional seeds, rating observations, legacy thresholds, hashes and commit provenance |
| [manifest.json](manifest.json) | Frozen model, all input/code hashes, unchanged 1,909 IDs/scores and exact 224 routes |
| [verification.json](verification.json) | Actual tests, reproduction hashes, CSV/JSON checks and read-only service verification |

Production snapshot remains frozen at
[the prior pinned input](../qualification-calibration/inputs/deployed-qualifiers.json).
The prior255 calibration outputs remain unchanged and diagnostic only.

## Provenance and limits

All 31 institutional seeds pre-existed. Prior generated Phase B snapshots lacked
IMDb/Letterboxd ratings. Enrichment activated unchanged outside-TSPDT
convergence/corroboration rules:18 current convergence routes,13 corroboration.
No Man's Land entered at 0e0c822 after cache 4aaacb7; the other 30 at 0c3b8f7 after
cache 662de6d. Neither introduction commit is part of deployed c7's ancestry.
These were research regeneration, not score-threshold qualification or deployment.

Scores, Audience 150/ceiling 1000, source-family weights and canon correlation
are frozen. No guard, normalization, age correction or Audience-share rule added.
Canon grouping and recent>=2020/very recent>=2024 are diagnostics only.
Known taste/watch annotations do not affect scores or decisions.

No enrichment, Radarr/library query, movie add or download was performed.
Newcomer means newly eligible, not necessarily absent from the live library.
Nine Letterboxd gaps and remaining critic/award gaps persist from PR #3;
Small Axe/combined Nymphomaniac recognition remains unallocated.

## Reproduce through SSH

Checkout:`~/radarr-festival-list-p225-vs-p250`.

```sh
cd ~/radarr-festival-list-p225-vs-p250
~/radarr-festival-list/.venv/bin/python production_threshold_calibration.py
~/radarr-festival-list/.venv/bin/python -m unittest -v
~/radarr-festival-list/.venv/bin/python -m pip check
```

120 tests pass, including 15 new regressions. Fifteen generated files plus the
frozen history input match byte for byte. [Actions](https://github.com/kolorifer/radarr-festival-list/actions/runs/38520319747)
passes offline, scoped to this research branch. Production remains clean/active
at c7a4582, with zero restarts and local/public health 200.
