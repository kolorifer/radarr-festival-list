# Engineering report: TASK-2026-10-13-IDENTITY-INTEGRITY

**Specification:** [Agreed brief](2026-10-13-identity-integrity-brief.md), D005/D007/D012.
**Result:** Cleanup and regeneration completed; listed enrichment/source gaps remain.
Product acceptance and Evidence Score thresholds remain with the user/ChatGPT.
**Branch:** `research/data-identity-integrity`.
**PR:** [Draft #3](https://github.com/kolorifer/radarr-festival-list/pull/3), targeting research/audience-cap-calibration.
**Verification:** 2026-10-13, seedbox through SSH and GitHub Actions.

## What changed

A full audit of the cached TSPDT/backcatalog resolutions found five confirmed
false-positive IMDb identities, including the reported La Morte rouge case.
Verified source-ID overrides, explicit aliases and metadata checks now replace
fuzzy-only acceptance. Source title/year/director/runtime/country and TSPDT rank
remain available for every audited row.

| TSPDT rank | Correct source film | Wrong IMDb ID | Correct IMDb ID |
| --- | --- | --- | --- |
| 290 | Time (2020) | tt13138834 | tt11416746 |
| 338 | Birdman or (The Unexpected Virtue of Ignorance) (2014) | tt5130912 | tt2562232 |
| 509 | La Morte rouge (2006) | tt4698742 | tt0806125 |
| 603 | Spider (2002) | tt0145487 | tt0278731 |
| 897 | The Inheritance (2020) | tt7923220 | tt12913444 |

Time's former ID was a 2021 TV series; Birdman's was an unrelated short video;
La Morte rouge's was a different four-minute short; Spider was substituted with
Spider-Man; The Inheritance was substituted with Vaughn Stein's different film.
The correct identities are documented with IMDb and TMDb evidence in the
[full audit](../../simulations/data-identity-integrity/identity-audit.json).
La Morte rouge retains TSPDT #509 and 49.66 canon points.

Reviewed 994 source rows, of which 951 fall within the frozen 2000–2023 backcatalog
and have resolved records. The other 43 are outside that source-year scope.
All 951 resolved records were audited.227 were flagged as suspicious: 222 confirmed
correct, 5 corrected, 0 unresolved. Overall 946 confirmed correct, 5 corrected,
0 unresolved. Title/release-date/runtime/country/co-director differences remain
visible; identity confirmation does not rewrite source metadata or claim every
provider field has identical semantics.

Repaired 15 explicit award aliases inside the existing candidate universe. Moved
the falsely attached Gotham Best Feature evidence to the correct Birdman.
For the newly corrected Time and Spider IDs, restored the existing award-source
evidence with unchanged rules: Time gets Academy documentary nomination 30 and
Sundance documentary nomination/directing 33; Spider gets Cannes competition 10,
scaled to 20 by the already agreed European family weight. Sources are frozen at
[Kometa 8056d2d](https://github.com/Kometa-Team/IMDb-Awards/commit/8056d2d124b35cc897d1c60673d91eeaffe00dd4).
Time's awards are confirmed by the [Academy](https://www.oscars.org/oscars/ceremonies/2021)
and [Sundance](https://www.sundance.org/blogs/2020-sundance-film-festival-awards-announced-3/);
Spider's competition entry is confirmed by [Cannes](https://www.festival-cannes.com/f/spider/).

## Files and components changed

| Component | Purpose |
| --- | --- |
| film_identity.py; backcatalog.py; backcatalog_resolve.py | Deterministic identities/aliases, supporting conflict checks, source preservation |
| evidence_sources.py; evidence_sources_extra.py; phase_b_sources.py; critics_choice_experiment.py | Reuse verified mappings across research source resolution |
| identity_metadata.py; identity_integrity.py | Read-only metadata collection, full audit, explicit corrections, original-baseline repair |
| award_identity_cleanup.py | Safe in-universe aliases; explicit unresolved reasons |
| integrity_rating_enrichment.py; letterboxd_identity_enrichment.py | Missing-only provider attempts and verified public fallback, sanitized provenance |
| integrity_research_score.py | Reuse accepted scorer, regenerate data and complete before/after comparison |
| Four new test files | Identity, metadata conflict, provider denial, fallback correctness, scoped award restoration regressions |
| sources/identity-audit/*; sources/identity-overrides.json | Frozen metadata and verified identity registry |
| backcatalog*.json; audience-ratings.json; sources/evidence-families.json; sources/phase-b-institutional.json; sources/critics-choice-best-picture.json | Corrected research input state |
| simulations/data-identity-integrity/* | Machine-readable scores/audits, complete changes, comparison, frozen inputs, hashes and verification |
| .github/workflows/identity-integrity.yml; .gitattributes | Research-branch-only regeneration and generated CSV whitespace convention |
| PROJECT.md; AGENTS.md; docs state/decisions/task/reports | Durable task/result handoff and existing user authorization |

Complete changed-path inventory:

```text
.gitattributes
.github/workflows/identity-integrity.yml
AGENTS.md
PROJECT.md
audience-ratings.json
award_identity_cleanup.py
backcatalog-details.json
backcatalog.json
backcatalog.py
backcatalog_resolve.py
critics_choice_experiment.py
docs/CODEX_TASK.md
docs/DECISIONS.md
docs/PROJECT_STATE.md
docs/reports/2026-10-13-identity-integrity-brief.md
docs/reports/2026-10-13-identity-integrity.md
evidence_sources.py
evidence_sources_extra.py
film_identity.py
identity_integrity.py
identity_metadata.py
integrity_rating_enrichment.py
integrity_research_score.py
letterboxd_identity_enrichment.py
phase_b_sources.py
simulations/data-identity-integrity/README.md
simulations/data-identity-integrity/award-identity-audit.json
simulations/data-identity-integrity/before-score-150.csv
simulations/data-identity-integrity/comparison.json
simulations/data-identity-integrity/comparison.md
simulations/data-identity-integrity/evidence-score-150.csv
simulations/data-identity-integrity/evidence-score-150.json
simulations/data-identity-integrity/identity-audit.json
simulations/data-identity-integrity/identity-corrections.json
simulations/data-identity-integrity/inputs/corrected-award-evidence.json
simulations/data-identity-integrity/inputs/imdb-fallback.json
simulations/data-identity-integrity/inputs/letterboxd-fallback.json
simulations/data-identity-integrity/letterboxd-fallback-used.json
simulations/data-identity-integrity/manifest.json
simulations/data-identity-integrity/rating-enrichment.json
simulations/data-identity-integrity/score-rank-changes.csv
simulations/data-identity-integrity/validation.json
sources/critics-choice-best-picture.json
sources/evidence-families.json
sources/identity-audit/imdb-basics.json
sources/identity-audit/imdb-basics.json.gz
sources/identity-audit/tmdb.json
sources/identity-audit/tmdb.json.gz
sources/identity-overrides.json
sources/phase-b-institutional.json
test_corrected_award_evidence.py
test_film_identity.py
test_integrity_rating_enrichment.py
test_letterboxd_identity_enrichment.py
```

## Acceptance criteria and evidence

| Criterion | Result | Evidence/limit |
| --- | --- | --- |
| Known La Morte rouge case | Passed | tt0806125, rank 509; regression rejects La Porte Rouge |
| Complete frozen backcatalog audit | Passed | 951 rows;227 suspicious; classifications/metadata in JSON and Markdown |
| Conservative matching | Passed | No fuzzy-threshold acceptance; explicit overrides, aliases, director/year/runtime/common-title checks |
| Audience gaps investigated | Completed with missing data | All 13 initial gaps reviewed;7 verified fallback ratings applied across original gaps/new identities |
| Obvious award aliases | Passed within current universe | 15 fixed; remaining 32 listed without guessed IDs/universe expansion |
| Final model regeneration | Passed | Audience150 proportional 0.75; effective ceiling 1000; all other weights/canon adjustment fixed |
| Qualification/production boundary | Passed | All 255 qualifier IDs/routes preserved; production code and feeds unchanged |
| Before/after effects | Passed | All substitutions and score/rank changes; top 50/top 100; distributions |
| Reproduction/regressions | Passed | 86 full tests, pip check, ten byte-identical artifacts |

## Data completeness

| Measure/source | Before | After |
| --- | ---: | ---: |
| Candidate films | 1,909 | 1,909 |
| IMDb rating + votes available | 1,908 | 1,909 |
| Letterboxd rating + count / complete pairs | 1,896 | 1,900 |
| Incomplete Audience records | 13 | 9 |
| NSFC unresolved source records | 4 | 0 |
| LAFCA unresolved source records | 2 | 1 |
| Critics Choice unresolved source records | 29 | 22 |
| EFA unresolved source records | 11 | 8 |
| Gotham unresolved source records | 1 | 1 |
| NYFCC unresolved source records | 0 | 0 |
| Total unresolved award source records | 47 | 32 |

Official IMDb title/year/runtime metadata covers 956 old/corrected IDs; frozen
TMDb metadata contains 964 records including gap/correction investigations.
Previously valid provider ratings/counts were retained: 14,256 field records
checked across retained films. Four corrected IDs use official IMDb rating/count
fallbacks; original frozen fallbacks remain preserved. Public Letterboxd JSON-LD
ratings require the correct IMDb identity, director/year and a 5-point aggregate
with ratingCount. reviewCount is not substituted for ratingCount.

Remaining Letterboxd gaps: Endless Corridor; The Silence of Swastika;
Unpaarvayil; Mission Muh Dikhayi; Material; LaLee's Kin: The Legacy of Cotton;
Making Memories of Murder; Operation Homecoming: Writing the Wartime Experience;
Prisoner of Paradise. Exact IDs, HTTP/page/aggregate status and missing reasons
are in [the frozen fallback](../../simulations/data-identity-integrity/inputs/letterboxd-fallback.json)
and [comparison](../../simulations/data-identity-integrity/comparison.json).

ReelDB metadata and ratings endpoints both returned HTTP 403, with the existing
private Actions secret. The collector persisted the sanitized failure, stopped
after two requests, and recovered no live provider values. Therefore provider
mapping completeness and additional ratings remain unverified. Public pages
did not expose a usable aggregate/count for the nine remaining cases; this does
not prove those films have no Letterboxd ratings anywhere. Values remain missing
without renormalization. Metacritic/Rotten Tomatoes evidence for the four newly
corrected IDs also remains unavailable through ReelDB; it is not borrowed from
the incorrect films.

## Score and ranking effects

The final 1,909-film universe has four removed false IDs and four correct additions.
Correct Birdman already existed; Spider-Man remains through independent audience
discovery and loses only Spider's wrongly attributed TSPDT evidence.
Substitutions compare different works and are reported separately from retained
film deltas.

18 retained films change Evidence Score;1,208 change ordinal rank. Most rank
changes follow reordered neighbors rather than changed points.
[All movements](../../simulations/data-identity-integrity/score-rank-changes.csv)
and [complete comparison](../../simulations/data-identity-integrity/comparison.md)
are available.

| Retained film | Score before | After | Change | Rank before | After |
| --- | ---: | ---: | ---: | ---: | ---: |
| Birdman or (The Unexpected Virtue of Ignorance) | 336.92 | 440.52 | 103.6 | 145 | 65 |
| Caché | 372 | 452 | 80 | 104 | 59 |
| Mangrove | 37.04 | 84.65 | 47.61 | 1821 | 1273 |
| Lovers Rock | 100.78 | 147.77 | 46.99 | 1074 | 666 |
| Spider-Man | 147.57 | 107.23 | -40.34 | 665 | 1014 |
| Parasite | 734.21 | 769.21 | 35 | 3 | 2 |
| The Lord of the Rings: The Return of the King | 480.27 | 505.27 | 25 | 44 | 40 |
| Compartment Number 6 | 134.96 | 158.96 | 24 | 748 | 598 |

Top 50 membership: unchanged. 12 common ranks change, maximum 4 places.
Top 100: Caché and Birdman enter; Manchester by the Sea and Phantom Thread leave.
52 common ranks change, maximum 4 places. These are numerical effects; the user
and ChatGPT decide materiality. No threshold recommendation is made.

Mean 148.32 → 148.52; median 112.75 → 112.70; maximum 803.78 remains unchanged.
The fully eligible effective ceiling stays 1000. All detailed percentiles and
diagnostic-band counts are in comparison.json; bands do not change qualification.

## Tests run and results

Executed on the seedbox using the existing project virtual environment:

```sh
~/radarr-festival-list/.venv/bin/python -m unittest -v
~/radarr-festival-list/.venv/bin/python -m pip check
```

86 tests passed; no broken requirements. Includes correct La Morte rouge
override, wrong La Porte Rouge rejection, fuzzy/conflicting director/runtime
rejection, short/common-title checks,±1-year corroboration, explicit aliases,
source-rank preservation, provider 403 handling and secret-field filtering,
Letterboxd IMDb/director identity and aggregate/count parsing, and scoped
restoration of existing award evidence.

Offline reran identity_integrity.py, award_identity_cleanup.py,
letterboxd_identity_enrichment.py and integrity_research_score.py from the
published data revision. All ten audit/scoring artifacts match byte for byte;
the research working tree was clean afterward.1,909 IDs are unique; all 255
qualifier routes match baseline. Fixed scoring modules/source feeds/qualifiers
were checked byte for byte against baseline. Configured-secret and private-URL
pattern scans passed across all 54 changed paths; compressed inputs match their
expanded metadata. See
[validation.json](../../simulations/data-identity-integrity/validation.json)
for actual commands, hashes and service evidence.

[Actions run38439672908](https://github.com/kolorifer/radarr-festival-list/actions/runs/38439672908)
also passed and published the frozen data. Workflow success includes gracefully
reporting unavailable ReelDB access; it is not a successful provider integration
test. The earlier provider 403 crash was fixed and covered by regression tests.

## Deployment result

No research/scoring changes deployed; no main merge, live notification, movie
addition or download test performed. Fresh read-only SSH verification:
production checkout remains clean at
`c7a458241b4a8a2acbd4d4f5a957d71e5198adc1`;
movie-intel.service is enabled, active/running, NRestarts=0;
local and public HTTPS health both return 200.

Public service route: https://kolorifer.arcturus.usbx.me/movie-intel.
No service configuration, provider proxy, Radarr configuration or production
feeds were edited. Existing operational/privacy issues from the stable deployment
report remain separate; this task does not claim to reverify their resolution.

Research checkout: `~/radarr-festival-list-identity-integrity`.
Private original-state backup:
`~/.local/state/movie-intel/research-validation/identity-sync-20261013T173145Z`.
Final sync backup:
`~/.local/state/movie-intel/research-validation/identity-final-sync-20261013T173520Z`.
Unpublished exploratory files were preserved in the private original-state
backup. Existing deployment/calibration checkouts were preserved.

Rollback needs no production action. Review or reproduce the original research
state at4d7943b in a separate worktree. Keep current research artifacts/branch
until review; do not reset or overwrite the user's checkouts. Private backups
supply the pre-sync exploratory state if needed.

## Unexpected findings

Four additional false identities shared the title/year resolution weakness.
Correcting IMDb IDs exposed missing institutional evidence for Time and Spider;
the unchanged existing award model restores it from pinned records.
Missing provider access, rather than a proved Letterboxd absence, explains why
the remaining provider mappings cannot be fully verified.

## Unresolved issues and manual/product review

- Nine Letterboxd aggregates/counts and corrected-film ReelDB critic ratings
  remain unavailable. Restoring ReelDB access is required for further provider
  enrichment; no secret is exposed in the report.
- 32 award-source records remain unresolved in the frozen universe. Their exact
  rows/reasons are listed in award-identity-audit.json.
- LAFCA Small Axe is an anthology award. Allocating it among individual films
  requires a product decision; no arbitrary allocation was made.
- EFA Nymphomaniac Director's Cut(Vol I & II) is a combined work/cut. Do not silently
  assign it to one single-volume IMDb identity.
- Gotham Test Pattern's source year/award-year difference and absence from the
  frozen universe remain explicit; unrelated candidate inclusion needs review.
  Other unresolved source titles are outside or not safely identified within
  the current universe. This task does not choose universe expansion.
- Metadata warnings for alternate cuts/release dates/country definitions remain
  recorded. No unresolved TSPDT identity remains in this audit; that is limited
  to the cached2000–2023 resolution set, not all IMDb film data globally.
- Thresholds and production adoption require the next agreed brief.

## Commit and PR reference

- Matcher/audit/enrichment implementation: [957cc8f](https://github.com/kolorifer/radarr-festival-list/commit/957cc8fd7d0de3d863f58d1e0ebf80413f8a4540).
- Provider-denial fix/regression: [ae364a0](https://github.com/kolorifer/radarr-festival-list/commit/ae364a0a6ca77b8e0125d37248dc7a32aae86cab).
- Corrected award restoration: [87279b4](https://github.com/kolorifer/radarr-festival-list/commit/87279b4f448b1ba2d3c362d27d62ed52e7a892d3).
- Final generated data: [1451d54](https://github.com/kolorifer/radarr-festival-list/commit/1451d54d67a5cb82b1a814d640866fe30a5a088d).
- [Draft PR#3](https://github.com/kolorifer/radarr-festival-list/pull/3); no merge. This report's containing commit
  supplies the final documentation/handoff revision.

## Project context updates

PROJECT_STATE.md records final model/data/verification and remaining issues.
DECISIONS.md records the already accepted Audience150/ceiling 1000 decision and
the user's routine engineering authorization. AGENTS.md reflects that standing
authorization without removing production/test boundaries. CODEX_TASK.md is idle,
linked to this completed brief/report. The user and ChatGPT can review the report
and [artifact index](../../simulations/data-identity-integrity/README.md) before
assigning the next engineering step.
