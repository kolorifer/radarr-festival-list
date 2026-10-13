# Implementation brief: TASK-2026-10-13-AUDIENCE-CAPS

**Status:** In progress.
**Agreed with:** User + ChatGPT; user brief and clarification replies, 2026-10-13.
**Base:** simulation-4b-union-universe at 8363f9393b9bc6961dc829b8ce01c9cd02fec641.
**Branch:** research/audience-cap-calibration.
**Relevant decisions:** D001, D002, D005, D006, D007, D009, D011.

## Objective

Provide calibration evidence to decide later between Audience=150 and
Audience=200. Codex must not choose a preferred cap.

## Desired behavior

Recover current scoring/data. Complete feasible IMDb/Letterboxd/ReelDB
enrichment or explicitly report unavailable data. Freeze one candidate universe.
Run audience_cap_150 and audience_cap_200 on it, using the user-confirmed
0.75 × (IMDb + Letterboxd) and unscaled sum respectively.
Preserve existing per-source calibration and canon correlation in both runs.

Produce full machine-readable score tables and a report with top films, ranking
movers, score changes, diagnostic band crossings, distributions, material
audience lifts, and cases where audience appears to dominate other evidence.

## Scope and constraints

Simulation only. TSPDT 100, Sight & Sound 100 before existing correlation,
BBC 100, NYT 100, US Institutional 100, European Recognition 200,
Independent Cinema 100, Audience 150/200. Reuse the implemented critics family
with its existing 100-point ceiling and broad-critic component.
European 200 uses 2 × its existing normalized 100-point family score.
All non-audience weights/points, qualifications and routes match between runs.
No production qualification/feed changes, deployment, or merge into main.
No private values in artifacts or logs.

## Acceptance criteria

- Same unique IDs, input hashes and qualifications in both variants.
- Only audience weighting changes; per-film delta equals 0.25 × the shared
  IMDb + Letterboxd component sum, within documented rounding.
- Explicit source coverage, provenance, inherited modifiers and missing data.
- Full JSON/CSV tables and Markdown/JSON comparison cover every requested
  diagnostic without a preferred-cap recommendation.

## Testing requirements

Test calibration reuse, missing versus weak evidence, deterministic ranking,
family ceilings, canon correlation, identical non-audience points, expected
deltas, bands and distribution totals. Test ID matching, request budgets,
partial-cache preservation, rate limits and secret-safe output. Run the full
unittest suite on the seedbox. Verify generated artifacts and production state.

## Deployment and verification expectations

Keep checkouts and simulation execution on the seedbox. An isolated Actions
enrichment job may use the existing repository ReelDB secret and write research
ratings only; do not transfer the key out of Actions. Final scoring and checks
run through SSH. Publish a reviewable research branch/PR and artifacts.
No scoring change is deployed.

## Ambiguities and assumptions

Resolved by user: proportional weighting; preserve existing canon correlation.
A missing ReelDB key will be handled through the existing Actions secret where
available, otherwise reported. Reuse existing diagnostic band boundaries;
do not reinterpret them as qualification tiers.

## Progress and implementation status

Recovered latest research baseline and fixed 1,909-film union. Implementing
enrichment and paired scoring. Final completeness, tests and artifacts pending.
Archive this brief/report on completion and clear the active task.

## Required engineering report

Branch/commit, files changed, completeness, tests/results, simulation outputs,
unexpected findings, unresolved issues, artifact links/paths, and confirmation
that production scoring was neither merged nor deployed.
