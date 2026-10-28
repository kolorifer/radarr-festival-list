# Data identity cleanup artifacts

Research-only result on `research/data-identity-integrity`.
[Engineering report](../../docs/reports/2026-10-13-identity-integrity.md) ·
[Agreed brief](../../docs/reports/2026-10-13-identity-integrity-brief.md) ·
[Draft PR #3](https://github.com/kolorifer/radarr-festival-list/pull/3).

Final generated data commit: [1451d54](https://github.com/kolorifer/radarr-festival-list/commit/1451d54d67a5cb82b1a814d640866fe30a5a088d).
Baseline: [4d7943b](https://github.com/kolorifer/radarr-festival-list/commit/4d7943b6f4a2cff3b4ddc38fb8ff096747efc3bf).
Audience=150, proportional 0.75 weighting; effective ceiling 1000; remaining
weights/canon correlation/qualification unchanged.

## Read first

[Before/after comparison](comparison.md) summarizes all suspicious identities,
award gaps, score/rank movements, top 50/top 100 and distribution.
[Comparison JSON](comparison.json) contains complete machine-readable changes.

| Artifact | Contents |
| --- | --- |
| [evidence-score-150.json](evidence-score-150.json) | All 1,909 final film records, family points, coverage, provenance, ranks, unchanged qualification/routes |
| [evidence-score-150.csv](evidence-score-150.csv) | Final ranked dataset |
| [before-score-150.csv](before-score-150.csv) | Historical Audience150 baseline |
| [score-rank-changes.csv](score-rank-changes.csv) | Every ID in the before/after union, including identity additions/removals |
| [identity-audit.json](identity-audit.json) | All 951 cached TSPDT records and metadata,227 flagged records, classifications |
| [identity-corrections.json](identity-corrections.json) | Five explicit wrong/correct IMDb pairs with source rank |
| [award-identity-audit.json](award-identity-audit.json) | All 47 initial unresolved source rows:15 corrected,32 unresolved |
| [manifest.json](manifest.json) | Frozen universe IDs, additions/removals, code/input hashes and fixed weights |
| [validation.json](validation.json) | Actual86-test, dependency, reproduction and production boundary checks |
| [rating-enrichment.json](rating-enrichment.json) | Sanitized ReelDB attempts: metadata and ratings HTTP 403; no live ratings recovered |
| [letterboxd-fallback-used.json](letterboxd-fallback-used.json) | Seven verified public Letterboxd fallbacks applied |
| [inputs/imdb-fallback.json](inputs/imdb-fallback.json) | Preserved historical fallbacks plus official IMDb ratings for four corrected IDs |
| [inputs/letterboxd-fallback.json](inputs/letterboxd-fallback.json) | Frozen IMDb/director/year-verified Letterboxd ratings and remaining page statuses |
| [inputs/corrected-award-evidence.json](inputs/corrected-award-evidence.json) | Pinned existing award source records for new corrected identities |

Frozen title/director/runtime/country/alias metadata and verified registry:
[sources/identity-audit](../../sources/identity-audit) and
[identity-overrides.json](../../sources/identity-overrides.json).
Expanded JSON is readable; compressed copies supply identical CI inputs.

## Coverage and limits

IMDb 1908 → 1909; Letterboxd/complete pairs 1896 → 1900. Nine Letterboxd values remain
missing. Public page retrieval did not expose a usable published aggregate/count
for these cases; this does not establish global absence of ratings. ReelDB's
current HTTP 403 prevents further provider/mapping verification and recovery of
Metacritic/Rotten Tomatoes for the four newly corrected IDs. Missing values stay
missing, contributing zero under the existing model without renormalization.

NSFC 4 → 0; LAFCA 2 → 1; Critics Choice 29 → 22; EFA 11 → 8; Gotham 1 → 1; NYFCC 0 → 0.
Remaining source records and exact reasons are in the award audit. Small Axe's
anthology and Nymphomaniac's combined director's cut require product/manual
interpretation; unrelated films outside this frozen universe are not admitted.

Different-film substitutions are separate from same-film score deltas. Spider-Man
retains its legitimate audience-discovery membership but loses Spider's TSPDT
evidence; Birdman's source evidence merges into its already present correct ID.

## Offline reproduction through SSH

Checkout and all application work remain on the seedbox:
`~/radarr-festival-list-identity-integrity`.
From that directory, use the existing project virtual environment:

```sh
~/radarr-festival-list/.venv/bin/python identity_integrity.py
~/radarr-festival-list/.venv/bin/python award_identity_cleanup.py
~/radarr-festival-list/.venv/bin/python letterboxd_identity_enrichment.py
~/radarr-festival-list/.venv/bin/python integrity_research_score.py
~/radarr-festival-list/.venv/bin/python -m unittest -v
~/radarr-festival-list/.venv/bin/python -m pip check
```

These commands use committed/frozen inputs and reproduce all ten audit/scoring
artifacts byte for byte. Avoid live enrichment when reproducing this revision:
it would create a new source observation. Historical150/200 comparison artifacts
and legacy research outputs remain historical; this directory is the final
accepted Audience150 model with corrected identity/data.

[Actions verification](https://github.com/kolorifer/radarr-festival-list/actions/runs/38439672908) regenerates the
research branch only. Workflow success does not mean ReelDB access succeeded.
No production threshold, merge or deployment has occurred.
