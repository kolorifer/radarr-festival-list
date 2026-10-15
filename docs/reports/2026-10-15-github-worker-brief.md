# Bootstrap brief: issue #11 / SUPERVISOR_TASK 1

Source of truth: [control issue](https://github.com/kolorifer/radarr-festival-list/issues/11)
and [supervisor task 1](https://github.com/kolorifer/radarr-festival-list/issues/11#issuecomment-6199401413).

Implement a small auditable macOS runner using Python/shell, GitHub CLI and fresh
`codex exec` processes. Normal ChatGPT supervises through GitHub; no ChatGPT Work
in the loop. Default GPT-6.1 Sol / Medium reasoning. Include --dry-run, --once,
polling, concise prompts, atomic task claims, locking/stale-lock recovery,
at-most-once task numbers, maximum eight iterations and <=15% remaining 5h-quota
pause using synthetic-tested Codex telemetry parsing. Commit/push scoped code,
create/update a stable PR and report WORKER_RESULT: 1 to the issue.

Authorization covers repository files, tests, branch/commit/push/PR, and issue
state/result comments. No Radarr, seedbox, media, deployment, destructive Git,
ChatGPT Work, or persistent daemon activation. Setup/start/stop docs and an inert
LaunchAgent example are required. Inspect partial work and the scoped diff before
commit. Existing movie-list behavior and unrelated active briefs stay intact.

Status: implemented for supervisor review. See [engineering report](2026-10-15-github-worker.md).
