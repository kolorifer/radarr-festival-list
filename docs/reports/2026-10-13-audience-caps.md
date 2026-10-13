# Engineering report: TASK-2026-10-13-AUDIENCE-CAPS

**Result:** Simulation/calibration complete; provider gaps explicitly reported.
**Specification:** [Archived agreed brief](2026-10-13-audience-caps-brief.md), D011.
**Branch:** research/audience-cap-calibration.
**Research baseline:** 8363f9393b9bc6961dc829b8ce01c9cd02fec641.
**Scorer commit:** [5ac99d9](https://github.com/kolorifer/radarr-festival-list/commit/5ac99d98fc989533ae37fc1f04b9e475ae3e205f).
**Data/artifact commit:** [47d6adc](https://github.com/kolorifer/radarr-festival-list/commit/47d6adc6ba7ce68634f57f45313c3aa0943bbcd3).
**Verification:** Seedbox, 2026-10-13; Python 3.13.5 in the existing virtual environment.

## What changed

Recovered the current research implementation/data and rebuilt a valid paired
comparison of Audience=150 and Audience=200. The old comparison reads an obsolete
audience_consensus field, while the stored v10 score uses three audience
populations. The new standalone experiment uses IMDb + Letterboxd only.

The user confirmed proportional weighting (0.75 and 1.0 respectively) and
preservation of the existing Sight & Sound/TSPDT correlation adjustment.
European Recognition is weighted to 200 using twice its existing normalized
100-point score. All other family points, qualifications, routes, and input IDs
are identical between variants. No preferred cap is selected.

The existing critics family is reused, including NSFC/NYFCC/LAFCA wins, implemented
Critics Choice Best Picture evidence, and the capped Metacritic/Rotten Tomatoes
broad-critic component. No new critics-source approach was invented.

## Files and components changed

| Component | Change |
| --- | --- |
| audience_cap_simulation.py | Paired scorer, invariant checks, rankings, distributions, band crossings, audience lifts/inversions, JSON/CSV/Markdown generation. |
| audience_calibration_enrichment.py | Fixed-universe collection, safe response fields, bounded/targeted retry, cache preservation, official IMDb fallback. |
| test_audience_cap_simulation.py | Regression coverage for fixed weights, correlation, missing data, ties, deltas, bands, frozen qualification, and invalid comparisons. |
| test_audience_calibration_enrichment.py | Coverage for ID matching, budgets, targeted retry, rate limits, cache preservation and secret-safe output. |
| audience-ratings.json | Completed feasible ReelDB enrichment on this isolated branch. |
| .github/workflows/audience-cap-enrichment.yml | Branch-scoped use of the existing repository secret; research-only collection and artifact publication. |
| simulations/audience-cap-comparison/ | Full variant JSON/CSV, comparison JSON/CSV/Markdown, manifest, coverage, IMDb fallback, collection history and validation evidence. |
| AGENTS.md, PROJECT.md, docs/ | Persistent engineering instructions, accepted experiment, state, active-task closure, brief/report templates and completed handoff. |
| .gitignore | Ignore virtual environments, Python cache and private .env files. |

Existing production feed files, qualification logic, and legacy scoring modules
are unchanged. The previous temporary comparison and v10 artifact remain
recoverable and were not treated as results for this experiment.

## Data completeness

The same fixed union of 1,909 unique IMDb IDs is used in both runs. The union
contains backcatalog, institutional, frozen qualification, evidence snapshot,
and audience-discovery candidates.

| Measure | Initial | Final |
| --- | --- | --- |
| ReelDB cached IDs within the universe | 1,619 | 1,904 |
| Complete IMDb + Letterboxd pairs | 1,614 | 1,896 |
| IMDb available after official fallback | 1,619 | 1,908 |
| Letterboxd available | 1,614 | 1,896 |
| Incomplete audience pairs | 295 | 13 |
| Frozen qualified films | 255 | 255 |

The first collection made 291 requests: 289 successes, one timeout, and one
HTTP 404. The targeted retry resolved the timeout (Memoir of a Snail), with one
additional successful request. Five candidate IDs are known ReelDB HTTP 404s.
Official [IMDb title.ratings data](https://data.imdb.com/non-commercial-datasets/)
filled four remaining IMDb records. ReelDB access follows its
[documented ratings endpoint](https://reeldb.io/).

Remaining: 13 candidate records lack Letterboxd values through the configured
provider; one of those also has no IMDb value in the provider/official dataset.
Every affected title/ID and reason is listed in coverage.json. Missing
components contribute zero without renormalization and are labeled incomplete;
valid low ratings/low vote counts are a separate case.

Existing critics metadata retains unresolved source rows: NSFC 4, LAFCA 2,
Critics Choice 29 (NYFCC 0). The broad-critic cache provides usable Metacritic
data for 1,614 films and Rotten Tomatoes critic data for 1,679. These limits
remain fixed between runs. Cached ReelDB records lack historical collection
timestamps; new request dates do not establish the age of every cached rating.

## Acceptance criteria and evidence

| Criterion | Result | Evidence |
| --- | --- | --- |
| Same universe/input data | Passed | 1,909 IDs; shared universe/evidence hashes in both variants and manifest. |
| Only audience weighting differs | Passed | Every per-film non-audience point map matches; score delta equals 0.25 × component sum within rounding. |
| Preserve qualification/routes | Passed | Exact equality to the frozen qualifier snapshot; 255 qualified films in both. |
| Preserve existing canon correlation | Passed | Existing modifier reused; unit and full-data invariants verified. |
| Explicit availability/provenance | Passed with reported gaps | coverage.json, fallback source/digest, and request history. |
| Full requested comparison | Passed | Tops, movers, deltas, bands, distributions, lift and dominance/inversion examples in comparison.md/json. |
| No product-cap choice or production rollout | Passed | preferred_cap is null; unchanged deployed source/service. |

## Tests run and results

On the seedbox, using the existing Python virtual environment:

- python -m unittest -v: 63 research tests passed (46 inherited, 17 new).
- python -m pip check: No broken requirements found; no dependency changes.
- Actual artifact invariants: ID uniqueness, input hashes, family ceilings,
  exact non-audience equality, qualification/routes, total component sums,
  expected deltas, and distribution totals passed.
- Nine generated scoring/report artifacts were regenerated through SSH from the
  published frozen inputs and matched byte for byte, including both JSON/CSV
  variants and comparison outputs.
- Configured-secret absence, changed-file scope, relative documentation links
  and git diff --check were verified before the final handoff.
- Both isolated enrichment/publication Actions runs completed successfully.

The prior deployment's 53 service tests are earlier evidence; the 63 tests above
are the current research suite. The experiment sends no live notifications and
adds/downloads no movies.

## Simulation outputs and observations

See the [comparison report](../../simulations/audience-cap-comparison/comparison.md)
and [artifact index](../../simulations/audience-cap-comparison/README.md).

| Metric | Audience=150 | Audience=200 |
| --- | --- | --- |
| Mean score | 148.32 | 170.39 |
| Median score | 112.75 | 136.46 |
| Highest score | 803.78 | 841.86 |
| Films at or above 300 | 183 | 233 |
| Films at or above 600 | 15 | 22 |

Increasing the audience weight changes 1,865 scores and 1,858 ordinal ranks.
736 films cross at least one existing diagnostic band. Those bands do not
change qualification.

Brokeback Mountain ranks first in both. Boyhood and Parasite exchange second
and third. For a concrete audience-sensitive inversion, Dune: Part Two rises
from 284 to 232 and overtakes The Assassin, which moves from 204 to 247 despite
having more non-audience points. This is evidence for review, not a verdict
about either film or either cap.

## Deployment result

No scoring change is deployed or merged into main. Production remains clean at
c7a458241b4a8a2acbd4d4f5a957d71e5198adc1. movie-intel.service remains active/running
with zero restarts; loopback health returns HTTP 200. Production feed files,
private configuration, and qualification policy are preserved.

Research code/data are kept in the separate seedbox worktree:
~/radarr-festival-list-audience-calibration. GitHub publishes research artifacts
using the existing private secret inside Actions. Final simulation and
reproduction/invariant checks run through SSH.

## Unexpected findings

The old 150-vs-200 script no longer matches the current score schema. The latest
stored score also includes three-population audience, canon correlation,
Critics Choice evidence and broad critics; those inherited details needed
explicit recovery. ReelDB enrichment previously ended on HTTP 429, and the new
collection encountered one transient timeout that was resolved.

## Unresolved issues and risks

- 13 Letterboxd values and one IMDb value remain unavailable through the current
  provider/dataset. No values or alternate movie identities were guessed.
- Critics-source identity gaps, incomplete broad-critic coverage, and missing
  cache dates limit interpretation of individual films.
- Strong audience evidence can dominate sparse recorded non-audience evidence;
  that does not prove the film lacks critical/institutional recognition.
- Absolute diagnostic score-band crossings are not production qualification.
  A preferred audience weight/threshold remains a separate product decision.

## Commit and PR reference

The scorer and artifact commits are linked above. The containing handoff commit
and research PR provide the final documentation revision. Review the
[branch comparison](https://github.com/kolorifer/radarr-festival-list/compare/simulation-4b-union-universe...research/audience-cap-calibration).
No merge or deployment is performed.

## Project context updates

D011 records the agreed experiment and clarification replies. PROJECT_STATE.md
records the results and data gaps. CODEX_TASK.md is idle and links this completed
report/brief. The user and ChatGPT can now review the evidence and select the
next explicitly scoped change.
