# Notification and exact-release approval reliability

Assigned directly by the user on 2026-10-18. Diagnose current production,
reproduce failures safely, implement narrow fixes, deploy through the existing
user-service/proxy architecture and verify the complete approved release flow.

Preserve D005/D006/D008/D009/D010: conservative identity (including the exact
10x AND 10-point duplicate rule), optional audience context, explicit approval,
searchForMovie=false, original release reference only, private capabilities and
provider-managed services. No broad malformed-year recovery or generic search.

Acceptance includes genuine resolved and unresolved notifications, useful cards,
valid live selectors, an explicitly approved exact-release add/grab with downstream
success, and replay protection. Unit tests alone do not constitute acceptance.
Read-only diagnosis is authorized. Specific deliberate live notifications and
acquisitions require approval for the movie/release. Product choices remain with
the user; unrelated cleanup and supervisor work are outside this task.

Inspect repository main and deployment independently. Retain sanitized evidence,
run focused and full tests, preflight, health and read-only checks, record limits.
The unrelated existing CODEX_TASK.md cleanup assignment is preserved.
