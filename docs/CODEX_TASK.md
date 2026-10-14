# Current Codex task

Status: **Assigned — implement Radarr read-only snapshot bridge.**

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
