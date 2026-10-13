# TASK-2026-10-13-IDENTITY-INTEGRITY
Status: Active. Source: current user instruction.
Branch: research/data-identity-integrity. Baseline: 4d7943b6f4a2cff3b4ddc38fb8ff096747efc3bf.

Audit the complete cached TSPDT/backcatalog identity set; repair confirmed false
positives, classify suspicious rows, review all 13 incomplete audience records,
and resolve obvious NSFC/LAFCA/Critics Choice/EFA/Gotham identity aliases.
Known mandatory correction: La Morte rouge (2006), Víctor Erice, TSPDT #509,
IMDb tt0806125 replaces the incorrect La Porte Rouge (2007), tt4698742.

Use explicit verified IDs/aliases and supporting metadata. Fuzzy similarity alone
cannot establish identity; conflicts must reject a candidate. Keep unresolved
cases explicit and retain source title/year/rank/director/runtime/country.

Regenerate the research dataset using the agreed Audience=150 model:
0.75 × (IMDb + Letterboxd), effective ceiling 1000, all remaining weights and
existing canon correlation unchanged. Preserve qualification rules and frozen
qualifier routes. Identity substitutions must be explicitly documented rather
than preserving a demonstrably wrong ID merely to retain the original 1909 IDs.
Do not add unrelated candidates or broaden source eligibility.

Acceptance: full audit with confirmed/corrected/manual statuses; before/after
audience and critics-source coverage; all score/rank changes and top50/top100
effects; deterministic machine-readable artifacts with provenance; regression
tests for La Morte rouge and conflicting metadata; full unittest suite.
No guessed ratings, no preferred thresholds, no production merge/deployment or
live notifications/downloads. Publish dedicated review PR and engineering report.
