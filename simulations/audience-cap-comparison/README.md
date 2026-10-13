# Audience-cap comparison artifacts

Start with [comparison.md](comparison.md). It covers top ranks, movers, deltas,
bands, distributions, audience lifts and potential dominance/inversions.
No preferred cap is selected.

| Artifact | Purpose |
| --- | --- |
| [audience_cap_150.json](audience_cap_150.json) / [CSV](audience_cap_150.csv) | Complete 1,909-film Audience=150 table. |
| [audience_cap_200.json](audience_cap_200.json) / [CSV](audience_cap_200.csv) | Same universe with Audience=200. |
| [comparison.json](comparison.json) / [CSV](comparison.csv) | Full movements, score changes, crossings and diagnostics. |
| [manifest.json](manifest.json) | Frozen IDs, source/input hashes and fixed weights. |
| [coverage.json](coverage.json) | Per-film availability, provider gaps and inherited critics-source status. |
| [inputs/imdb-fallback.json](inputs/imdb-fallback.json) | Official IMDb fallback data, retrieval date and dataset digest. |
| [enrichment-attempts/01.json](enrichment-attempts/01.json) / [retry](enrichment-status.json) | Initial collection and targeted timeout retry. |
| [validation.json](validation.json) | Tests, invariants, privacy/scope checks and byte-identical reproduction evidence. |

The scorer runs offline against these frozen files. On the seedbox, from
~/radarr-festival-list-audience-calibration, use
~/radarr-festival-list/.venv/bin/python audience_cap_simulation.py.
The full suite is ~/radarr-festival-list/.venv/bin/python -m unittest -v.

[Completed implementation brief/report](../../docs/reports/2026-10-13-audience-caps.md)
records scope, assumptions, tests and remaining limits.
