# Grab Anyway eligibility recovery brief

User request: investigate why Grab Anyway was unavailable for the pictured
The End of Oak Street (2026) 1080p FraMeSToR release and fix the issue.

Acceptance criteria:
- Establish the original rejection, identification outcome and missing action cause.
- Preserve exact original rejection reasons and source safety fields across retries.
- Retain acknowledged Telegram message receipts independently of SQLite contention.
- A recovered eligible quality rejection offers the existing alternative-release
  confirmation, with the current Radarr file snapshot; never automatically acquire.
- Mixed rejections, TV fields, unsupported sources and legacy incomplete events
  cannot become Add & Grab approvals through this recovery path.
- Explain temporary identity lookup failure in the original notification.
- Validate and deploy only this fix atop the actual production revision, preserving
  topic routing, existing approvals, prior reconciliation and other services.
- No deliberate live notifications, downloads, imports or Radarr mutations.

The old card cannot be edited without its actual Telegram receipt. Do not guess
message IDs or replay the original webhook. Record this limitation explicitly.
The unrelated cleanup task in CODEX_TASK.md is outside this request.
