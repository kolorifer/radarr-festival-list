# Current Codex task

Status: **Implemented/tested — waiting for private seedbox GitHub credential before deployment.**

[Implementation brief](reports/2026-10-14-radarr-snapshot-bridge-brief.md)

Goal: reuse the existing deployed Radarr sync and its private credentials to publish one sanitized `radarr-current.json` into a private GitHub repository, preferably `kolorifer/radarr-state`.

Constraints:

- no new Radarr scheduler;
- no new Radarr credential store;
- no Radarr writes for snapshot generation;
- never publish Radarr URL/API key, filesystem paths, download-client data or other secrets;
- do not put the snapshot in this public repository;
- overwrite one current-state file only; no history initially;
- preserve the deployed Movie List reconciliation behavior unchanged.

Implement, test, deploy on the seedbox, verify the live snapshot, and confirm whether the user's existing GitHub integration can read the private repository. If private-repo creation or connector authorization requires a user action, stop only for that single concrete action.

After successful deployment, return this file to idle and link the completion report.

## Current verified progress

- Branch production/radarr-snapshot-bridge; [draft PR #8](https://github.com/kolorifer/radarr-festival-list/pull/8).
- 133 tests and Python3.12/3.13 CI pass; frozen production catalog unchanged.
- Live read-only export990 rows; all IDs/flags/tag labels verified, zero Radarr writes.
- Private radarr-state created/authorized; initial radarr-current.json published and
  fetched identically through the GitHub connection.
- Deployment still458755a; existing timer/movie-intel remain active unchanged.
- Missing access: repository-limited Contents read/write token on seedbox.
  Enter through deploy/setup-github-state.py hidden Terminal prompt; never chat.
- Next: verify seedbox publication, merge/deploy, health/scheduler checks and idle handoff.

[Implementation/access report](reports/2026-10-14-radarr-snapshot-bridge.md).
