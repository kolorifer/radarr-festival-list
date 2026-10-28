# Collector-only SQLite deployment

User request: deploy only the collector SQLite fix already merged in PR #105,
preserve the current actor and shadow configuration, and verify health and
concurrent intake without triggering downloads or Telegram messages.

Scope: replace only the installed `identity_triage_store.py` with the tested
file from merge `55f22402be9a4001f913677587aade203f49ac3f`. Preserve the other
collector modules, configuration, units, SQLite schema and current state. Restart
only the collector, with its existing mandatory confinement. Keep the actor
checkout/process and shadow runtime/pilot/timer unchanged.

Acceptance: private backups, baseline/fixed regression evidence on the host,
actual-service confined preflight, authenticated collector health/metrics, actor
health, database integrity and configuration/hash comparisons. Exercise concurrent
HTTP intake with synthetic data in a separate confined collector and store; send
no production POST requests. Preserve the unrelated active cleanup brief.
