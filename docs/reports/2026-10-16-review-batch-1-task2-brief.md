# Issue #20 / supervisor task 2: reconcile approved batch

The latest issue-owner supervisor task authorizes only reconciliation and
completion of the existing private 15-target operation at
`kolorifer/radarr-state/operations/2026-10-16-review-batch-1.md`.
Task 1 ended FAILED after partial mutation; current live Radarr state is
authoritative. Repository task briefs authorize no additional work.

Read all 15 targets before any mutation. Leave already satisfied states alone;
never re-add an absent movie. Complete only missing approved actions with exact
Radarr/IMDb/TMDb/title/year identity and original safeguards intact. Skip any
identity mismatch, file, watched/protected state or unexpected protection.
Removal means the Radarr entry only, with media deletion disabled. Preserve the
single keep target and apply only missing existing watched-tag/unmonitored state.

Verify final state and unrelated-state sanity; retain exact original/current/final
per-target evidence privately. Expected complete result: 14 removal targets
absent, preserved target present/watched/unmonitored, zero media deletions and
zero unrelated mutations. Safely blocked partial completion is acceptable.
Public results must contain aggregate counts only.

No unrelated seedbox access or mutations, safeguard bypass, media deletion,
daemon installation/start, ChatGPT Work, other workers, Git publication or issue
comments. The runner owns branch publication and reporting.

Result: [engineering report](2026-10-16-review-batch-1-task2.md).
