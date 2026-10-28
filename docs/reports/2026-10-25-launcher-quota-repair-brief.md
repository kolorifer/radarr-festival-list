# Local launcher quota repair brief

Requested directly in the local Codex session on 2026-10-25.

Diagnose and repair the installed GitHub-to-Codex launcher for
kolorifer/radarr-festival-list. Existing issue #86 task 1 is blocked by
QUOTA_UNAVAILABLE and must remain the same task, with no claim resets.

Find the actual checkout, LaunchAgent environment and Codex executable;
reproduce the quota probe with safe diagnostics before attributing the failure.
Make the smallest verified repair preserving the <=15%-remaining pause,
state journals, lock inodes and atomic at-most-once claim protection.
Verify live quota parsing and read-only eligibility, with offline execution
boundary tests; do not launch research as part of the repair.

Do not expose credentials or private session contents. Do not change Radarr,
movie scoring, Telegram or seedbox services. Do not execute or clear the
unrelated legacy CODEX_TASK.md assignment. Report cause, changes, checks,
deployment state and whether interactive sign-in is required.
