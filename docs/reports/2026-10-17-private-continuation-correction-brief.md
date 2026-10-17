# Implementation brief: issue #35 / supervisor task 2

Source of authority: latest issue-owner SUPERVISOR_TASK 2, READY_FOR_CODEX,
REASONING high. This review correction supersedes task 1's application of exact
checkout immutability to default private tasks. Repository briefs for other work
are not authorization.

## Goal and reproduced finding

Correct PR #36 before merge, starting from clean reviewed commit
580eb8e777a71f6a270950aa4e9cff76a891bb6b on automation/issue-35-worker.
Task 1's `execute_in_checkout()` finally block rejects any changed fingerprint
for operations or private tasks. An exact default-mode private CONTINUE_FROM can
legitimately reconcile expressly authorized retained partial files, finish clean
with unchanged HEAD, and publish privately. The new check rejects that established
workflow, including the contract previously exercised by issue #28.

Supervisor reproduction used synthetic IntegrationTests/BoundaryRunner: retain
an untracked marker for task 1 NEEDS_USER, set consumed=[1], then run task 2 with
pinned synthetic input/output/diagnostic grants and exact CONTINUE_FROM, omitting
PUBLICATION_MODE. A fake child removes the authorized marker and emits output.
Reviewed 580eb8e returns PUBLIC_CHANGE_REFUSED despite the clean finish; baseline
1bbd8d91a5e24440d4aec870dea08f4ad72641e6 returns OK. No retained live state changed.

## Required behavior and acceptance

- Restrict exact fingerprint immutability to explicit operations_only tasks.
  Preserve default private exact immediately preceding continuation authorization,
  partial-work backups, clean final checkout and unchanged HEAD before private
  publication. Preserve input immutability and public publication restrictions.
- Any stronger default-mode check must allow expressly authorized reconciliation;
  do not require both an unchanged dirty baseline and a clean finish.
- Add separate launcher/issue-worktree regression with a real synthetic retained
  partial file, exact next-task continuation, authorized cleanup, successful private
  artifact/receipt and readback, preserved backup, sanitized reporting, zero code
  publication, and no stash/reset. External boundaries must all be synthetic.
- Keep operations-only refusal of that same reconciliation, acceptance of an
  unchanged explicitly retained baseline, and no code publication. Keep ordinary
  code publication and failure/race/privacy coverage.
- Align prompts and protocol documentation without changing old test semantics
  merely to accept the regression. Run focused/full suites in isolation and diff
  checks. Archive this brief/report and update project state; distinguish local
  synthetic verification from pending live acceptance.

## Authorization and prohibitions

Only scoped runner/policy/tests and related engineering/protocol documentation
may change. Network is permitted only for public repositories/docs and necessary
isolated dependencies. Preserve task-1 boundaries and unrelated work. The host
parent owns commits/push/PR/issue reporting; this child performs no publication.

No Radarr, seedbox (including SSH/reads), media, live service/configuration access,
issue #33 deployment retry or resolver checks, real private inventory/research,
credential access/exposure, direct GitHub writes, merge/deployment, launcher/
LaunchAgent/schedule changes, claim deletion/reuse, stash/reset/clean, retained
state bypass, other workers/runners, session resumption or ChatGPT Work. Do not
enable operations_only for this implementation task. No daemon installation/start.

## Completion

Return READY_FOR_REVIEW after local verification with actual tests and concise
results/limitations; use NEEDS_USER only if blocked. Supervisor reviews and owns
subsequent publication and acceptance. No next task is inferred.
