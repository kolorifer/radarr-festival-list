# Issue #24 / supervisor task 1 — dispatcher-v2 brief

Source: issue #24 and its current issue-owner supervisor task, supplied to this
fresh worker. Infrastructure-only implementation and local verification;
publication belongs to the established runner.

## Agreed behavior

- Omitted `--issue` discovers open issues created by the authenticated runner
  identity, excluding PRs. Only valid issue-owner supervisor tasks qualify.
- Select at most one deterministic oldest outstanding latest READY task per poll.
  Preserve DONE, consumed/claimed-number and eight-iteration safeguards, trusted
  capabilities, fresh workers, model defaults, sandbox, atomic claims and privacy.
- Explicit `--issue N` remains an operator override. A common-Git-directory
  dispatcher flock excludes cross-issue execution, alongside per-issue locks.
- Preserve the launcher checkout when executing other issue branches.
- Keep the <=15% five-hour allowance pause. Fresh telemetry never probes. Only
  an eligible task with unusable telemetry may trigger one minimal, fresh,
  non-interactive, approval-free, read-only, network-disabled quota probe outside
  the project, containing no task/private content and preceding all consumption.
- Re-read telemetry: >15% proceeds; <=15% pauses; failure/no refresh yields a
  concise NEEDS_USER and leaves the number unconsumed. Persist a local failure
  cooldown; fresh observations naturally clear it.
- Discovery logs only safe counts, identifiers and outcomes. Dry-run has no
  claims, journal changes, locks, probes, workers, branch changes or publication.
- Inspect the installed LaunchAgent invocation read-only. Do not modify/reload
  it, change cadence/paths/log destinations, or install/start any daemon.

## Verification and boundaries

Offline tests must cover discovery/filtering/ordering, duplicate protection,
concurrency, launcher preservation, quota paths/cooldown and dry-run, plus runner
regressions. Inspect the final diff and report actual checks and limitations.
No seedbox, Radarr, media, catalog, scoring or acquisition operations, ChatGPT
Work, credentials, private task contents, destructive Git operations or unrelated
changes. No worker-created commits/pushes/PRs/comments or nested workers/runners.
The unrelated active repository task is not authorization and remains untouched.
