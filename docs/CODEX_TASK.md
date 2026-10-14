# Current Codex task

Status: **Assigned — apply watched state to the 2026-10-14 Movie List import.**

[Implementation brief](reports/2026-10-14-watched-new-import-brief.md)

Authoritative private cohort manifest:
`kolorifer/radarr-state/watched-targets-2026-10-14-import.json`

Expected cohort: 87 exact IMDb-ID targets.

Required end state for every target:
- additive `watched` tag;
- `monitored=false`;
- preserve Movie List/score-band/unrelated tags, files and settings.

Use a fresh live snapshot and exact IMDb matching. If clean, dry-run then apply without another routine approval. Verify idempotence, refresh the private Radarr snapshot, merge the cohort into the private canonical watched manifest after successful verification, and prove the normal Movie List sync does not re-monitor existing watched movies.

No movie/file deletion, search, grab, download, import-list refresh or acquisition command. Existing scheduler unchanged.

On completion, publish an aggregate-only engineering report and return this file to Idle.
