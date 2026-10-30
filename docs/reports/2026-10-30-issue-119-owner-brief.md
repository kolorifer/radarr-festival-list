# Issue #119 Task 2 — owner commissioning adapter brief

**Authority:** issue-owner supervisor Task 2, public comment 6528285463.
**Date:** 2026-10-30. **Mode:** code only; all inputs synthetic.
**Baseline:** accepted PR #118 merge `c66be2f1e794a1c8bfa4406b7e82e70a98daca25`.
**Branch:** parent-created `automation/issue-119-worker`.

Implement a small explicit standalone owner library/CLI, without dispatcher hooks,
that durably binds external acquisition intent before transport; verifies original
fixed movie-export bytes; calls the accepted format-2 cycle/handoff; stages one
exact create-only parent publication payload after the uncertain boundary; and
wraps independently selected offline receipt import and safe archive. Reuse
accepted validators, security checks, material comparison and lifecycle schemas.

Required configuration includes canonical explicit private base/intake/cycle/
evidence/receipt/output identities, stable runtime/owner/cycle IDs, one original
clock, fixed source selector, create-only destination and distinct named recipient.
No authority comes from staged JSON, environment or worker prose. No-follow
identity/ancestor guards, durable create-only intent, immutable byte bindings,
nonblocking concurrency, finite bounds and fail-closed replay are required.

Acceptance requires synthetic end-to-end actual-reader/CLI rehearsal, intent-
before-transport ordering, replay/change/concurrency/alias/overlap/corruption
checks, honest missing/stale/future/incompatible exports, preserved independent
findings/proposal versions, exact uncertain handoff, readback-only lost-response
reconciliation, rejected incorrect/unselected receipts and idempotent archive.
Run focused and accepted coordinator/export/integration tests, applicable parent/
policy/receipt checks, full available-runtime unittest, compilation, dependency
preflight, frozen scoring and diff verification. Report unsupported-runtime and
dependency errors accurately; later parent exact-head 3.12/3.13 CI, independent
review and scoped merge are mandatory.

Task 1's accepted assessment (review 6528253227) is context: current symlinked
source spelling, unproven fresh exports/producer handoff, missing verified private
roots and external owner/recipient contracts. Preserve unknowns; never import its
private selectors or retroactively diagnose the historical source rejection.

Forbidden: seedbox/SSH, private inputs/repos/credentials, live transport/publication/
recipient issuance, providers/research/refresh, Radarr/media/Telegram actions,
deployment, schedules/services/daemons, additional executors, engineering claim/
lock/quota/cap/schema edits, issue #113 roots/history, #86/PR #110, unrelated
`CODEX_TASK.md`, production/scoring changes, migration/deletion or Git publication.
The parent alone owns commit/push/PR/result publication. No active repository task
is replaced. Save this brief/report and update only related runbook/project facts.

**Completion:** implementation and synthetic validation are recorded in the
[engineering report](2026-10-30-issue-119-owner.md). Live commissioning and product
acceptance remain outside this assignment.
