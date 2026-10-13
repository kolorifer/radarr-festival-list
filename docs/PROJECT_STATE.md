# Movie List project state

Last updated: 2026-10-13. This branch contains completed research/calibration work.

## Stable architecture and production

The service architecture, discovery policy and deployment evidence are in the
[stable snapshot](https://github.com/kolorifer/radarr-festival-list/blob/7e9c32f7ac5d8c9a310e69a706731a272f23c003/docs/PROJECT_STATE.md).
Production remains clean at c7a458241b4a8a2acbd4d4f5a957d71e5198adc1.
The service is active with zero restarts and HTTP 200 health. No research scoring
change is deployed or merged into main; production feeds/qualification are fixed.

Read [decisions](DECISIONS.md) and [the current task](CODEX_TASK.md) before work.
The user/ChatGPT own product decisions; Codex executes engineering briefs.

## Current research/calibration

Research baseline: 8363f9393b9bc6961dc829b8ce01c9cd02fec641.
Scorer commit: 5ac99d98fc989533ae37fc1f04b9e475ae3e205f.
Data/artifact commit: 47d6adc6ba7ce68634f57f45313c3aa0943bbcd3.
Branch/worktree: research/audience-cap-calibration,
~/radarr-festival-list-audience-calibration.

Completed [engineering report and evidence](reports/2026-10-13-audience-caps.md).
The [comparison report](../simulations/audience-cap-comparison/comparison.md) and
[artifact index](../simulations/audience-cap-comparison/README.md) provide the
product-review handoff.

D011 specifies Audience=150 as 0.75 × (IMDb + Letterboxd), Audience=200 as their
unscaled sum. Existing per-source rating/vote calibration and the confirmed
TSPDT/Sight & Sound correlation adjustment remain fixed. European Recognition
uses twice its normalized 100-point score. Existing critics-group, Critics
Choice, and capped broad-critic evidence is reused. Trakt/TMDb do not contribute.
All other family points, inputs, qualification flags and routes match.

The frozen universe has 1,909 IDs. Final data: ReelDB 1,904; IMDb 1,908 after four
official-dataset fallbacks; Letterboxd/complete pairs 1,896. 13 Letterboxd values
and one IMDb value remain unavailable through these sources. Existing unresolved
critic-source identities and cache date gaps are explicit in coverage.json.

## Verified results

63 research tests passed; pip check passed. Full-data invariants and configured
secret/diff checks passed. Nine scoring/report artifacts regenerated through SSH
match the published results byte for byte.

Audience=150 vs 200: mean 148.32 vs 170.39, median 112.75 vs 136.46.
1,865 scores and 1,858 ordinal ranks change; 736 films cross diagnostic bands.
The 255 existing qualified films and all their routes remain unchanged.
These results do not choose a preferred cap or establish a production threshold.

## Review topics

The user and ChatGPT review rankings, distribution, completeness and dominance
examples before assigning the next task. No next product change is independently
selected. Provider/approval-flow privacy gaps in the stable deployment snapshot
remain separate operational findings.
