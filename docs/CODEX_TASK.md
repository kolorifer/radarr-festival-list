# Current Codex task

Status: **Idle — Radarr read-only snapshot bridge completed and deployed.**

[Engineering/deployment report](reports/2026-10-14-radarr-snapshot-bridge.md)

PR #8 merged; private radarr-current.json contains990 current movies and is readable
through the user's GitHub connection. The deployed seedbox publisher is verified.
133 tests and CI pass; zero snapshot-generation Radarr writes. Existing daily
timer, qualification and Telegram/add-grab flow remain unchanged.

No implementation task is currently assigned.
