# Qualification calibration artifacts

[Engineering report](../../docs/reports/2026-10-13-qualification-calibration.md) ·
[Detailed analysis](summary.md) · [Draft PR #4](https://github.com/kolorifer/radarr-festival-list/pull/4).

Fixed cleaned PR #3 baseline: 762d6af242c84e26e2007d2a175b08c7e9c3b2a8. Final generated data: f93c21dc006686b2209ca3e3c5acbb6406376b9b.
Audience=150, ceiling=1000, other weights and canon correlation unchanged.
No score, identity or qualification route changed. No final policy/threshold chosen.

**Baseline correction:** the requested frozen comparator contains 255 films.
The deployed c7a4582 lookup contains 224, all included in the 255 with identical
routes. Every New/Retained/Lost number here uses the requested 255 comparator.
Earlier descriptions calling it production-qualified were inaccurate.
[Verification](verification.json) lists the 31 research-only entries and shared
metadata differences. The [deployed snapshot](inputs/deployed-qualifiers.json)
is diagnostic only; production remains unchanged.

## Score-only thresholds

Overlap is agreement with the frozen comparator, not validated quality precision.

| Threshold | Total | New | Retained | Lost | Overlap |
| --- | ---: | ---: | ---: | ---: | ---: |
| 100 | 1080 | 825 | 255 | 0 | 23.61% |
| 125 | 836 | 583 | 253 | 2 | 30.26% |
| 150 | 654 | 408 | 246 | 9 | 37.61% |
| 175 | 510 | 279 | 231 | 24 | 45.29% |
| 200 | 415 | 208 | 207 | 48 | 49.88% |
| 225 | 336 | 152 | 184 | 71 | 54.76% |
| 250 | 288 | 119 | 169 | 86 | 58.68% |
| 300 | 184 | 54 | 130 | 125 | 70.65% |
| 350 | 129 | 27 | 102 | 153 | 79.07% |
| 400 | 88 | 8 | 80 | 175 | 90.91% |

## Numerical review options

| Policy | Threshold | Total | New | Lost | New Audience>50% | Recent new |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A_keep_existing | 250 | 374 | 119 | 0 | 1 | 35 |
| A_keep_existing | 300 | 309 | 54 | 0 | 0 | 17 |
| E_low_evidence_guard | 125 | 787 | 536 | 4 | 133 | 104 |
| D_audience_half | 200 | 381 | 199 | 73 | 0 | 47 |

A250/A300 preserve all baseline films and control expansion.
E125 offers broader guarded discovery: >=1 non-audience family, and Audience<=50%
when only one family contributes. It still admits 133 audience-dominant new films.
D200 removes dominance but loses 73 baseline films; it is the costly replacement
comparator. No final policy or threshold is selected.

## Artifacts

| File | Contents |
| --- | --- |
| [summary.md](summary.md) | Bands/percentiles, all policy tables, examples, trade-offs and interpretation |
| [calibration.json](calibration.json) | All 1,909 films and 60 flags; complete selected/new/lost IDs; years, family composition, cohorts, sensitivity, examples |
| [per-film-policies.csv](per-film-policies.csv) | One film per row, all policy decisions, points/families/coverage/taste/watch context |
| [threshold-summary.csv](threshold-summary.csv) | All ten requested score-only thresholds |
| [policy-comparison.csv](policy-comparison.csv) | All 60 combinations and retention/overlap/dominance/recent/taste metrics |
| [score-only-losses.csv](score-only-losses.csv) | Every baseline loss under each score-only threshold |
| [candidates/](candidates/) | Complete shortlist new/lost/borderline lists |
| [manifest.json](manifest.json) | Frozen input, code/config hashes, IDs and fixed model |
| [verification.json](verification.json) | Actual tests, hashes, cross-format verification and baseline discrepancy |
| [inputs/deployed-qualifiers.json](inputs/deployed-qualifiers.json) | Pinned 224-film diagnostic snapshot from c7a4582 |

Candidate lists:

- A250: [new](candidates/A_keep_existing_250-new.csv), [lost](candidates/A_keep_existing_250-lost.csv), [borderline](candidates/A_keep_existing_250-borderline.csv).
- A300: [new](candidates/A_keep_existing_300-new.csv), [lost](candidates/A_keep_existing_300-lost.csv), [borderline](candidates/A_keep_existing_300-borderline.csv).
- E125: [new](candidates/E_low_evidence_guard_125-new.csv), [lost](candidates/E_low_evidence_guard_125-lost.csv), [borderline](candidates/E_low_evidence_guard_125-borderline.csv).
- D200: [new](candidates/D_audience_half_200-new.csv), [lost](candidates/D_audience_half_200-lost.csv), [borderline](candidates/D_audience_half_200-borderline.csv).

All four share the highest-scoring newcomers: Anatomy of a Fall, Anora,
The Favourite, Tár, One Battle After Another. They are review examples, not
automatic acquisition instructions.

## Definitions and limits

Positive points define contributing families. TSPDT/Sight & Sound count as one
canon family for B/C/E, following existing hybrid research; raw counts also appear.
Small broad-critic points can count as a Critics Groups family. Family count
does not establish strength. B/C/E add no filtering at >=200 in this dataset.
At >=300 the 150-point Audience cap makes the 50% share guard redundant.

Existing taste has 13 positive signals and 33 watched annotations, all already
qualified in the baseline. It cannot validate new-film preference precision.
None of those annotations affects scores or gates; unknown films are unlabelled.

Nine Letterboxd gaps remain at observed scores 0–45.74. None can reach 125 even
at the maximum missing component; at most four could cross 100. Thus these gaps
cannot affect the shortlisted options under that bound. Missing award/critic
evidence is not bounded here. ReelDB HTTP 403 and 32 unresolved award-source records
remain from PR #3. No enrichment API calls in this task. Small Axe/combined
Nymphomaniac awards remain unallocated under D014.

Recent means 2020 onward; borderline means within ten score points, diagnostics
only. Current Radarr library/addability and release availability were not queried.

## Reproduce through SSH

Checkout: `~/radarr-festival-list-qualification-calibration`.

```sh
cd ~/radarr-festival-list-qualification-calibration
~/radarr-festival-list/.venv/bin/python qualification_calibration.py
~/radarr-festival-list/.venv/bin/python -m unittest -v
~/radarr-festival-list/.venv/bin/python -m pip check
```

19 generated artifacts and the pinned deployed input match byte for byte.
105 tests pass, including 19 new regressions; pip check passes.
[Actions verification](https://github.com/kolorifer/radarr-festival-list/actions/runs/38444911888) is offline and branch-scoped.
No deployment, merge to main or Radarr behavior change occurred.
