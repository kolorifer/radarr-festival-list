# Movie List project state

Last updated: 2026-10-13. This branch contains research/calibration work.

## Stable architecture and deployment

The service architecture, accepted discovery policy and deployment evidence are
preserved in the [stable project-state snapshot](https://github.com/kolorifer/radarr-festival-list/blob/7e9c32f7ac5d8c9a310e69a706731a272f23c003/docs/PROJECT_STATE.md).
Production movie-intel remains at c7a458241b4a8a2acbd4d4f5a957d71e5198adc1.
This branch does not replace production feeds or qualification routes.

Read [DECISIONS.md](DECISIONS.md) and [CODEX_TASK.md](CODEX_TASK.md) before work.
The user and ChatGPT own product/design decisions; Codex executes engineering.

## Recovered research state

Baseline: simulation-4b-union-universe at
8363f9393b9bc6961dc829b8ce01c9cd02fec641. The older audience-sensitivity-temp
comparison reads the obsolete audience_consensus field. The current stored v10
score uses IMDb + Letterboxd + Trakt, correlated canon evidence, and broad
critic evidence merged into Critics Groups Consensus.

The fixed union contains 1,909 IMDb IDs from backcatalog, institutional,
qualification, evidence-family and audience-discovery snapshots. Initially
ReelDB covers 1,619 of those IDs; 290 are absent. Five additional in-universe
records lack usable Letterboxd data. The earlier collector ended on HTTP 429.
Cached data has no collection timestamps.

## Active calibration

D011 defines Audience=150 as 0.75 × (IMDb + Letterboxd), and Audience=200 as
their unscaled sum. Existing rating/vote calibration and canon correlation are
preserved. Trakt and TMDb do not contribute to this pair. European Recognition
is weighted to 200 from its existing normalized 100-point family score.
Other family points and frozen qualification remain identical between runs.

Implementation/enrichment is in progress in an isolated seedbox worktree.
Unavailable evidence will be explicit. The experiment will publish two full
machine-readable tables and a comparison with provenance and completeness.
