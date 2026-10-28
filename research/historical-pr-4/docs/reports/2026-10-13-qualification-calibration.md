# Engineering report: TASK-2026-10-13-QUALIFICATION-CALIBRATION

**Specification:** [Agreed brief](2026-10-13-qualification-calibration-brief.md);
D012 model and D014 anthology/combined-work rule.
**Result:** Research calibration complete for product review; no final policy.
**Branch/PR:** research/qualification-calibration,
[draft #4](https://github.com/kolorifer/radarr-festival-list/pull/4), targeting research/data-identity-integrity.
**Verification date:** 2026-10-13, seedbox SSH and Actions.
**Baseline:** [762d6af](https://github.com/kolorifer/radarr-festival-list/commit/762d6af242c84e26e2007d2a175b08c7e9c3b2a8), cleaned PR #3.
**Final generated data:** [f93c21d](https://github.com/kolorifer/radarr-festival-list/commit/f93c21dc006686b2209ca3e3c5acbb6406376b9b).

## What changed

Added an offline simulator applying ten requested thresholds and six policies
to the exact 1,909-film finalized score artifact: 60 combinations. Audience=150,
effective ceiling=1000, remaining weights and canon correlation remain fixed.
Scores, identities and all 255 comparison qualification routes are unchanged.

It emits complete per-film decisions, distributions by qualification/Audience
coverage, years, family count/composition, overlap/retention, dominance, missing
data bounds, examples and complete shortlist admission/borderline/loss lists.
Taste/watch annotations are a sanity-check lens only. No award allocation occurs.

## Baseline discrepancy and terminology correction

The requested cleaned PR #3 comparator has 255 records. Fresh production checks
show 224 qualified records at c7a4582. All 224 belong to the 255 and have identical
routes; 31 additional research records are absent from the deployed qualifier
snapshot. Six shared rows differ in auxiliary evidence/source metadata.

Earlier handoff descriptions calling 255 production-qualified were inaccurate.
The service's WorkingDirectory and loader point to the deployed checkout;
read-only build_index() confirms 224. Its qualifier file is pinned as a diagnostic
input with SHA-256, without changing production.

Every primary Current/Retained/Lost/New number below uses the explicitly requested
255 comparator. [Verification](../../simulations/qualification-calibration/verification.json)
lists all 31 differences. Future implementation needs an explicit decision about
those research-only baseline additions; this task does not promote them.

## Files/components changed

| Component | Purpose |
| --- | --- |
| qualification_calibration.py | Frozen inputs, predicates, distributions/examples, deterministic generation |
| qualification-calibration-config.json | Grid, diagnostic definitions and four numerical review options |
| test_qualification_calibration.py | 19 policy/input invariants and regressions |
| .github/workflows/qualification-calibration.yml | Offline research branch tests and artifact-only generation |
| simulations/qualification-calibration/* | JSON/CSV/Markdown, candidate lists, hashes and verification |
| PROJECT.md; docs state/task/decisions/reports | D014, durable handoff and corrected baseline terminology |

Complete changed paths:

```text
.github/workflows/qualification-calibration.yml
PROJECT.md
docs/CODEX_TASK.md
docs/DECISIONS.md
docs/PROJECT_STATE.md
docs/reports/2026-10-13-identity-integrity.md
docs/reports/2026-10-13-qualification-calibration-brief.md
docs/reports/2026-10-13-qualification-calibration.md
qualification-calibration-config.json
qualification_calibration.py
simulations/qualification-calibration/README.md
simulations/qualification-calibration/calibration.json
simulations/qualification-calibration/candidates/A_keep_existing_250-borderline.csv
simulations/qualification-calibration/candidates/A_keep_existing_250-lost.csv
simulations/qualification-calibration/candidates/A_keep_existing_250-new.csv
simulations/qualification-calibration/candidates/A_keep_existing_300-borderline.csv
simulations/qualification-calibration/candidates/A_keep_existing_300-lost.csv
simulations/qualification-calibration/candidates/A_keep_existing_300-new.csv
simulations/qualification-calibration/candidates/D_audience_half_200-borderline.csv
simulations/qualification-calibration/candidates/D_audience_half_200-lost.csv
simulations/qualification-calibration/candidates/D_audience_half_200-new.csv
simulations/qualification-calibration/candidates/E_low_evidence_guard_125-borderline.csv
simulations/qualification-calibration/candidates/E_low_evidence_guard_125-lost.csv
simulations/qualification-calibration/candidates/E_low_evidence_guard_125-new.csv
simulations/qualification-calibration/inputs/deployed-qualifiers.json
simulations/qualification-calibration/manifest.json
simulations/qualification-calibration/per-film-policies.csv
simulations/qualification-calibration/policy-comparison.csv
simulations/qualification-calibration/score-only-losses.csv
simulations/qualification-calibration/summary.md
simulations/qualification-calibration/threshold-summary.csv
simulations/qualification-calibration/verification.json
test_qualification_calibration.py
```

## Score-only threshold summary

Overlap is selected baseline films / all selected. It is agreement, not validated
quality precision. Retention uses the 255 frozen baseline.

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

[Threshold CSV](../../simulations/qualification-calibration/threshold-summary.csv) ·
[Complete score-only losses](../../simulations/qualification-calibration/score-only-losses.csv).

## Hybrid policies

Positive point contribution defines a contributing family. TSPDT/Sight & Sound
count together as independent canon, matching existing hybrid research.
Raw scoring-family counts are also available.

- A: existing qualification OR score>=threshold.
- B: score>=threshold AND >=2 independent non-audience families.
- C: score>=threshold AND >=1 independent non-audience family.
- D: score>=threshold AND Audience<=50%; exact 50% ties pass.
- E: score>=threshold AND >=1 family; when only one family contributes,
  Audience<=50%. With two or more, E does not impose that share guard.

[All 60 policy rows](../../simulations/qualification-calibration/policy-comparison.csv)
and [JSON](../../simulations/qualification-calibration/calibration.json) contain
every selection/new/loss ID, year/composition distributions and missing-data
sensitivity. Guard losses and score losses are reported separately.

## Recommendation section: numerical options for review

These four operating points compare different objectives. They are not a quality
ranking or a selected production policy.

| Option | Threshold | Total | New | Lost | New Audience>50% | Recent new |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A_keep_existing | 250 | 374 | 119 | 0 | 1 | 35 |
| A_keep_existing | 300 | 309 | 54 | 0 | 0 | 17 |
| E_low_evidence_guard | 125 | 787 | 536 | 4 | 133 | 104 |
| D_audience_half | 200 | 381 | 199 | 73 | 0 | 47 |

- **A250:** moderate expansion with 119 additions and no baseline losses;
  35 recent additions. One new audience-dominant case remains, Dune: Part Two:
  score 252.05, Audience 146.25, non-audience 105.80.
- **A300:** smaller expansion, 54 new with no losses or new audience dominance;
  17 recent additions. It excludes more borderline discoveries. Score-only 300
  would instead lose 125 baseline films; legacy retention is the material difference.
- **E125:** broad guarded discovery, 536 additions/four baseline losses, all
  13 known positives retained. It removes audience-only/weak single-family cases,
  but admits 133 new multi-family audience-dominant films and creates high volume.
  The Blind Side and Bohemian Rhapsody are explicit single-family review cases.
- **D200:** evidence-led replacement comparator, 199 new with no audience
  dominance, but 73 baseline losses: 48 below 200 plus 25 share-guard losses.
  The share guard removes only nine prospective new admissions. This is a costly
  option for retention, useful if an Audience-share ceiling matters.

E at 125 selects 787 versus 827 for C and 779 for B. Relative to score-only 836,
E filters 49: 47 previously unqualified and two baseline guard losses; two additional
baseline films fail the score. It retains some strong single-family evidence that
B rejects. B/C/E add no filtering at >=200 in this frozen universe.

At >=300, D also matches score-only: a 150-point Audience cap cannot exceed 50% of
a score over 300, and exact ties pass. Complete redundant outputs remain included.

## Examples and taste lens

All four options share these highest-scoring newcomers:

| Film | Year | Score | Audience | Non-audience |
| --- | ---: | ---: | ---: | ---: |
| Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 |
| Anora | 2024 | 499.51 | 79.91 | 419.6 |
| The Favourite | 2018 | 479.03 | 95.19 | 383.84 |
| Tár | 2022 | 455.62 | 85.67 | 369.95 |
| One Battle After Another | 2025 | 439.72 | 104.72 | 335 |

Examples at the decision edges:

- A250 admits I'm Not There 250.44, The Wonders 251.34, Honeyland 251.56;
  Hedwig and the Angry Inch 248.83 and District 9 248.65 remain below the gate.
- A300 admits On Body and Soul 301.01 and Beasts of the Southern Wild 301.31;
  Dune 299.36 misses. Already-qualified Holy Motors 299.17 remains through A.
- E125 admits The Descent 125.05, rejects audience-only Dangal 125.19 and
  single-family audience-dominant Om Shanti Om 125.17.
- D200 admits The Station Agent 200.53 and You Were Never Really Here 200.67;
  Jojo Rabbit 200.39 fails the share guard. Current baseline exclusions include
  Howl's Moving Castle 262.96, Kill Bill: Vol. 1 262.75, Interstellar 255.52.

Strong non-audience / weak Audience examples: Goodbye to Language (279.43/14.65),
The Assassin (266.41/21.96), Titane (265.69/28.84). Full points and gate decisions
are retained. “Surprising” examples are deterministic thin-evidence/high-share or
baseline-loss diagnostics, not independent aesthetic judgments.

13 positive signals and 33 watched annotations all belong to the baseline.
Positive minimum score 240.12; all four options retain all 13. This small
positive-only sample cannot validate new admissions or estimate preference
precision. No score/gate training or negative labels.
D200 excludes three known-watched films: The Swamp, A.I. Artificial Intelligence,
Platform. Watched does not mean liked/disliked; monitoring context remains separate.

## Distribution and data sensitivity

| Cohort | Count | Mean | Median | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| all | 1909 | 148.52 | 112.7 | 0 | 803.78 |
| audience_complete | 1900 | 149.13 | 113.5 | 0 | 803.78 |
| audience_incomplete | 9 | 19.66 | 8.04 | 0 | 45.74 |
| currently_qualified | 255 | 338.46 | 301.78 | 108.67 | 803.78 |
| currently_unqualified | 1654 | 119.24 | 99.71 | 0 | 571.43 |

All-score p10=53.08, p25=74.09, p50=112.70, p75=184.48, p90=296.80,
p95=388.85, p99=570.71. Detailed 25-point bands through 400, cohort percentiles
and family counts are in the [summary](../../simulations/qualification-calibration/summary.md).
Every policy has years and major family-composition counts. Recent means 2020
onward; older means 2000–2019. These labels are diagnostics, not gates.

311 films have only positive Audience points; three have no positive points.
900 have Audience>50%, including 49 baseline films. Small broad-critic points count
as the existing Critics Groups family; family count does not ensure evidence
strength. Independent family counts 0–7 are 314, 458, 529, 361, 152, 57, 27, 11.

All nine incomplete rows score 0–45.74; none is within ten points of a tested
threshold. With missing Letterboxd bounded at 75, only four could cross 100 and
none can reach 125. These nine gaps cannot affect the shortlist under that bound.
No ratings inferred. Other missing critic/award evidence is not bounded.
Extra Audience can also trigger D/E rejection while increasing total score.

## Tests and verification

105 full research tests pass, including 19 new regressions; pip check passes.
Tests cover inclusive thresholds, frozen universe/model/routes, canon counting,
zero-point families, subset/monotonic relationships, Audience-only rejection,
exact/rounded 50% boundaries, conditional E behavior, taste/watch independence,
unknown policies and the distinct deployed diagnostic.

```sh
~/radarr-festival-list/.venv/bin/python -m unittest -v
~/radarr-festival-list/.venv/bin/python -m pip check
~/radarr-festival-list/.venv/bin/python qualification_calibration.py
```

From published f93c21d, all 19 generated artifacts plus the pinned deployed input
match byte for byte through SSH. CSV/JSON agree for all 60 policies and 1,909 rows.
All selected/new/lost counts reconcile; 15 immutable input hashes verify.
Configured-secret scans pass; research tree is clean after generation.
[Actions 38444911888](https://github.com/kolorifer/radarr-festival-list/actions/runs/38444911888) passes.
[Verification record](../../simulations/qualification-calibration/verification.json)
contains hashes and actual service evidence.

## Deployment result and rollback

No production code/configuration change, merge to main, deployment, Radarr API
query/behavior change, notification, movie addition or download.
Read-only verification: production clean at c7a458241b4a8a2acbd4d4f5a957d71e5198adc1;
service active/running with NRestarts=0; local/public health 200.
Deployed lookup has 224 qualified entries, distinct from 255 comparison records.

Checkout:`~/radarr-festival-list-qualification-calibration`.
Original production/identity checkouts remain preserved. Private preview backup:
`~/.local/state/movie-intel/research-validation/qualification-preview-20261013T181227Z`.
No production rollback needed. Review the prior baseline in a separate worktree
at 762d6af; preserve current artifacts and user work.

## Unexpected findings and product/manual review

- Resolve the 255/224 distinction before future behavior changes; no implicit
  promotion of 31 research-only baseline films.
- High-scoring unqualified examples include Anatomy of a Fall, Anora, The Favourite,
  Tár. Unqualified is a frozen-rule label, not proof of low quality.
- Family guards become redundant and can count small critic fragments.
  No hidden minimum-family weight was invented.
- D's global Audience ceiling removes familiar films; E retains multi-family
  dominance. Both costs are explicit.
- Taste is positive-only and entirely baseline-qualified; human review of new
  admissions and exclusions remains required.
- Nine Letterboxd gaps, ReelDB HTTP 403, corrected-film critic gaps and 32 award-source
  gaps remain from PR #3. No new provider enrichment claim.
- D014 prohibits arbitrary Small Axe/combined Nymphomaniac allocation.
- Historical-poll eligibility differs by year. Absolute scores are not
  renormalized; recent coverage is reported without changing the model.
- Simulated qualification does not establish live Radarr addability/library
  membership or release availability. Those were not queried.
- User/ChatGPT choose the final policy and threshold in a subsequent brief.

## Commits and context handoff

Implementation:[ee50fa9](https://github.com/kolorifer/radarr-festival-list/commit/ee50fa96f5b63986793187598f991d793dfbb70d);
baseline diagnostic:[7861c96](https://github.com/kolorifer/radarr-festival-list/commit/7861c963623ec096d21a11ae442488300f4ef8f6);
final data:[f93c21d](https://github.com/kolorifer/radarr-festival-list/commit/f93c21dc006686b2209ca3e3c5acbb6406376b9b).
[Draft PR #4](https://github.com/kolorifer/radarr-festival-list/pull/4); containing report commit supplies the final handoff revision.

Project state/task updated, D014 recorded, brief archived, previous integrity
report annotated with the corrected baseline terminology. Active task is idle.
Review [artifact index](../../simulations/qualification-calibration/README.md)
and [detailed summary](../../simulations/qualification-calibration/summary.md)
before assigning the next engineering step.
