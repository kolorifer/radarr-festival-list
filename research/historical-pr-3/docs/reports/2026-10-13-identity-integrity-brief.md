# TASK-2026-10-13-IDENTITY-INTEGRITY: agreed brief

Source: user/ChatGPT instructions, 2026-10-13. Completed engineering result:
[report](2026-10-13-identity-integrity.md). Decisions: D005, D007, D012.

## Objective

Audit and repair identity/matching quality in the 1,909-film research dataset
before discussing Evidence Score thresholds. Known false positive: TSPDT
La Morte rouge (2006), Víctor Erice, rank 509 was incorrectly resolved to
La Porte Rouge (2007), tt4698742. Correct IMDb identity: tt0806125.

## Desired behavior and scope

1. Repair the known case, preserving source title/year/director/runtime/country/rank.
2. Audit the complete cached TSPDT/backcatalog resolution set, especially fuzzy
   titles, ±1-year matches, alternate/translated titles, short/common titles, and
   director/runtime/country conflicts. Classify suspicious matches as confirmed
   correct, corrected, or unresolved/manual review.
3. Use verified IDs and explicit aliases. A fuzzy similarity threshold alone
   must not establish identity; conflicting supporting metadata must reject it.
4. Review all 13 incomplete Audience records (one also lacking IMDb). Investigate
   provider/mapping failures, recover reliable values, and document remaining
   missing values without inventing ratings.
5. Repair straightforward NSFC/LAFCA/Critics Choice and EFA/Gotham alias gaps
   conservatively, using explicit mappings inside the existing candidate universe.
6. Regenerate the final agreed research model and compare before/after identities,
   audience coverage, award gaps, scores/ranks/distribution, and top 50/top 100.

## Fixed model and constraints

Audience = 0.75 × the existing calibrated IMDb + Letterboxd component sum, capped
at 150. Effective fully eligible Evidence Score ceiling 1000. All other family
weights and the existing TSPDT/Sight & Sound correlation adjustment remain fixed.
Qualification logic and frozen qualifier routes are unchanged. Critics-group
consensus reuses the already implemented sources; no new source/weight is invented.

Research-only dedicated branch/PR. No production scoring deployment, merge into
main, qualification change, unrelated candidate expansion, real notification,
movie addition, or download test. Preserve existing seedbox checkouts/work.
Credentials and private URLs remain outside public artifacts.

## Acceptance and testing

Full record audit; explicit identity corrections and all suspicious/manual cases;
before/after Audience and critics-source counts; machine-readable research
scores and all rank/score changes; top 50/top 100 membership/order comparison;
provenance/frozen inputs and reproducible outputs.

Regressions must resolve La Morte rouge to tt0806125, reject La Porte Rouge as a
substitute, and reject different films with metadata conflicts. Run the full
unittest suite and appropriate dependency checks. Report actual verification,
unavailable enrichment, deployment boundary, branch/commits/files, and artifact
paths. The user/ChatGPT decide thresholds after reviewing the engineering result.
