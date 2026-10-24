# Grab Anyway confirmation and completed-attempt reconciliation

Status: **Complete**. [Validation, deployment and reconciliation report](2026-10-24-grab-confirmation.md).

Owner request, 2026-10-24: investigate and fix uncertain status handling, deploy
safely, and reconcile the completed first attempt without downloading it again.

Scope: tolerate delayed/temporarily unavailable exact-hash readback after one
submission; retain durable no-retry barriers and safe private diagnostics. Verify
with synthetic transports and full suites. Deploy only these changes on the
actual production baseline, preserving unrelated actor/collector/research state.
Reconcile the existing The End of Oak Street alternative only after matching the
existing client torrent to Radarr import and current-file evidence. No new torrent
submission, source fetch, library changes or notification test is authorized.

Acceptance: delayed visibility and lost acknowledgements can become queued with
exact hash/category proof; unresolved or conflicting evidence remains uncertain;
no second add under any retry path; existing receipts migrate without deletion;
health/config/catalog checks pass; the completed receipt is audited as imported
and its old capability retired, with all other approval state preserved.
