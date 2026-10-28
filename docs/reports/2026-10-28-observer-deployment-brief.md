# Deploy only PR #108's observer fix

User request: deploy only the observer timeout and diagnostics fix from PR #108,
preserve actor and shadow configuration, keep monitoring and verify health without
triggering downloads or Telegram messages.

Apply the tested observer module to the verified current actor baseline. Preserve
all other actor code, the separately installed collector SQLite fix, configuration,
units/timers, budgets and durable private state. Run host preflight and tests in
separate staging directories, retain private rollback evidence and restart only
the actor. Verify local/public actor and authenticated collector health with GETs,
compare protected state and inspect only sanitized journal categories. Do not
replay webhooks, submit production events, call acquisition actions, send test
notifications or deploy unrelated main changes. Retain the existing 24-hour
monitor's schedule and fixed deadline. The unrelated cleanup task remains assigned.
