# Main and production integration: engineering report

**Specification:** [brief](2026-10-28-main-production-integration-brief.md).
**Status:** integration candidate under validation; no deployment.

Main parent includes [status-map PR #95](https://github.com/kolorifer/radarr-festival-list/pull/95).
The second merge parent is deployed actor revision `46cccea3a119ca080e35f6cf071bd0351eba037a`.
Conflicts in actor identity, retry and acquisition files were resolved to the
production implementation after inspecting the main-side differences; main-only
collector, selected intake, occurrence reconciliation, tests, feed data and docs
remain. The deployed actor source was retained across the overlapping runtime files,
with one additional retry-display correction described below; nine collector/selection/admin files and their tests differ from
that actor checkout because main contains separate collector work.

The integration retains main's D022–D035 and newer historical reports, plus
production's watched label decision and remembered/short-title decision records.
The runbook preserves main's retirement of per-film identity exceptions and daily
budget guidance, while adding production's topic routing and verified identity
cache sections. Example environment keeps main's generic NFO flag and production
routing/cache settings. Old superseded status entries were not copied over the
current main status map; final deployment reports were retained from their PRs.

Focused identity, source-revalidation, watched-notification, retry and approval
suite: 59 tests passed. Scoring check passed (1,909 candidates, 387 qualified);
pip check passed. Full integrated suite: 776 local tests OK (two skips), 776 seedbox tests passed.
An independent static review found no actionable actor/collector interface defect;
it identified outdated runbook and notification-guide descriptions, corrected
in this integration. The first Python 3.12 CI run hit `database is locked` in
`test_concurrent_distinct_events`; Python 3.13 passed. Seedbox and local tests passed.
The subsequent documentation-only head `8fb34f4` passed both CI versions. This
failure is retained as evidence rather than silently omitted. Independent review
also identified three post-runtime reports omitted from the first integration;
they were added without changing runtime code.
No production service, state, configuration, PR disposition or research activation
was changed. This integration commit is not a deployed revision; a deployment
requires separate approval and preflight.

## Follow-up from independent review

Review identified that a successful retry rebuilt the notification without
Radarr's watched status and existing-file edition context. This behavior was
already present in the deployed actor. The integration now reads optional,
identity-checked Radarr display context when preparing a retry notification and
uses the same logic for the original notification. No Radarr write is performed.
The correction is not deployed; focused watched/retry/edition tests pass (48 tests).
The full suite must be rerun for this code change before merge.
