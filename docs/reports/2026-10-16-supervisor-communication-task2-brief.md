# Issue #30 / supervisor task 2 — review correction brief

**Assignment:** READY_FOR_CODEX; completed locally, READY_FOR_REVIEW.
REASONING: high; NETWORK_ACCESS: enabled only
within the infrastructure task; SEEDBOX_PERMISSION: none.
**Baseline:** automation/issue-30-worker at
cde534ae5e34da13a4de6ac44484cfa3c01a61ae, PR #31. Preserve task-1 implementation.
**Result:** [Engineering report](2026-10-16-supervisor-communication-task2.md).

## Goal and findings

Correct two high-priority supervisor findings before merge:

1. A failing child captures the issue checkout, then execute restores the launcher.
   If diagnostic publication also fails, terminal calls preserve_failure again,
   replacing retained metadata with a launcher snapshot while the original backup
   remains. Preserve exact execution-checkout retention and any existing capture.
2. A failed atomic claim currently enters terminal and can publish an authorized
   diagnostic without acquiring ownership. A losing host can preempt the winner's
   absent destination. Conflicts and ambiguous responses must preserve local
   consumed state and bounded diagnostics, without private outputs/receipts or
   authoritative WORKER_RESULT. Any public warning must be non-authoritative and
   parser-compatible. Do not delete claims or automatically rerun.

## Acceptance criteria

- Use actual separate main launcher and issue worktrees for child-failure plus
  receipt-failure regressions. Verify exact checkout/fingerprint, matching tar and
  index backup, and successful authorized next-task continuation without stash/reset.
- Cover successful/blocked child receipt failures and checkout failures; a checkout
  that never existed cannot have an invented usable continuation.
- Exercise two independent runner instances discovering one unclaimed task,
  existing-claim conflict and ambiguous network responses. Only the confirmed
  owner may publish; preserve at-most-once execution and bounded attempts.
- Preserve pinned-input integrity, credential/public-private boundaries, sanitized
  errors, CAS/readback, locks, quota and retained prior evidence.
- Run focused and full project tests in an isolated environment with synthetic
  offline boundaries; inspect the final diff and update protocol/report/state.
- Distinguish local TESTED evidence from pending live acceptance. Record the
  owner's correction: an hourly heartbeat in the current Work/Codex chat was
  enabled and creation returned ACTIVE; no scheduled wakeup is observed and
  original cloud ChatGPT schedules remain unverified.

## Authorization and prohibitions

Code/test/documentation only, using synthetic fixtures. Network scope remains
task 1's public repository inspection, isolated dependencies and official docs.
The host parent owns commit/push/PR and sanitized issue reporting. No direct
worker GitHub writes or publication; no merge/deployment, launcher/LaunchAgent
changes, live private fixture creation, credentials access, schedule access or
changes, ChatGPT Work use, daemon/worker/runner launch, Radarr/seedbox/media reads
or mutations, inventories, research or subjective curation. Do not resume/fork
other sessions or read prior conversations. No stash/reset/clean, claim deletion,
consumption reuse or bypass of unexpected dirty state. Existing unrelated task
briefs cannot authorize other work; preserve the legacy CODEX_TASK.md.
