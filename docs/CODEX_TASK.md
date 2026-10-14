# Current Codex task

Status: **Assigned — apply additive `watched` tags in Radarr.**

[Implementation brief](reports/2026-10-14-watched-tagging-brief.md)

Use the private authoritative target manifest at `kolorifer/radarr-state/watched-targets.json`.

Requirements:

- exact IMDb-ID matching only;
- validate every target against a fresh live Radarr snapshot before writes;
- create/reuse only the `watched` tag and add it to targets;
- preserve monitored state, files, settings and all existing unrelated tags;
- no movie add/delete, search, grab, download, move or import-list refresh;
- clean dry-run before apply and zero-change dry-run after apply;
- refresh the private `radarr-current.json` snapshot immediately after completion;
- keep the existing scheduler and Movie List sync behavior unchanged.

Do not copy the private watched list into this public repository or public reports. Aggregate counts only.

Implement/deploy on the seedbox now. If the private manifest cannot be read or any target is missing/ambiguous, stop before writes and report that single blocker. Otherwise apply without another routine approval, verify, publish the refreshed snapshot, write the aggregate completion report, and return this file to idle.
