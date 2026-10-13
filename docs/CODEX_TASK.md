# TASK-2026-10-13-QUALIFICATION-CALIBRATION
Status: Active. Source: current user/ChatGPT brief.
Branch: research/qualification-calibration.
Baseline: PR #3, 762d6af242c84e26e2007d2a175b08c7e9c3b2a8.

## Objective and fixed inputs

Research-only qualification/recommendation calibration on the cleaned 1,909-film
universe. Read the final Audience150 Evidence Score as implemented, preserving
all points, weights, canon correlation and effective ceiling1000. Preserve the
255 current production-qualified IDs and every frozen route for comparison.
Do not deploy, change production code/Radarr behavior or merge into main.

Anthology/combined-work awards remain unallocated to components unless the
awarding body explicitly attributes recognition to that component. No arbitrary
Small Axe or combined Nymphomaniac allocation.

## Analysis and simulations

Analyze bands/percentiles by baseline qualification, Audience completeness,
contributing families, years and overlap. Simulate score-only at100,125,150,175,
200,225,250,300,350,400. Simulate every threshold under:
A existing qualification OR score; B score AND >=2 non-audience families;
C score AND >=1 non-audience family; D score AND Audience<=50% of total.
Test a simple E low-evidence/high-audience guard if informative, without retuning
scores. Explain each definition and numerical trade-off.

For each policy/threshold report selected/new/lost/overlap, years, family
composition, audience-only/dominant cases and incomplete rows near thresholds.
Use existing positive taste/watch signals only as a sanity-check lens; no
training, score/gate change or negative labels inferred from unknown films.

Technical interpretations: family contribution requires positive points; combine
TSPDT/Sight&Sound into canon for B/C/E as existing hybrid research does, and also
expose raw scoring-family counts. D uses published point values, including exact
50% ties. E tests the existing2-family/50% boundaries conditionally: >=1 family,
and if fewer than2, Audience<=50%. Recent means2020 onward; borderline means
within10 score points, used only for diagnostics. Missing Audience upper bounds
are potential sensitivity, not invented ratings. Publish these assumptions.

## Artifacts, examples and acceptance

Produce Markdown summary, full machine-readable JSON, per-film CSV across all
tested policies, threshold/policy tables, full candidate lists for2–4 numerically
promising policies, and every score-only baseline loss. Include top new films,
nearest above/below, surprising inclusions/exclusions, audience-dominant versus
critical-strong examples and recent/older coverage. Shortlist2–4 options and
trade-offs; choose no final policy/threshold.

Run full research unittest suite, add policy invariant regressions and verify
byte-identical deterministic regeneration. Audit frozen input/route invariants
and production separation. Report branch/commits/draft PR, tests, numerical
summary, examples, artifacts, findings and manual/product review cases. Preserve
all existing work; use the seedbox worktree and GitHub as durable handoff.
