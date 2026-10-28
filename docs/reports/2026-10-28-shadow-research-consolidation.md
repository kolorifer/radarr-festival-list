# Shadow research consolidation — 2026-10-28

PRs #78, #90 and #92 form a stack ending at
`c27e493e85a1f9ee63aa71a684e3e7aa2bf0acc0`. Their standalone identity
scoring, evidence discovery, cut investigation, tests, reports, and recorded
owner decisions are retained. Research output remains a proposal and does not
change production identity decisions, download confirmation or acquisition.

The stack also changed the shared `identity_recurring_store.py` from weekly to
daily limits. That change was approved for shadow-only operation and cannot
be applied to the shared main module without altering the existing actor's
research budget. Its exact source and associated test file are preserved as
inert `.txt` snapshots in `research/identity_scoring/historical/`; main's
shared module and tests remain unchanged. No scheduler, service, flag, pilot,
or network request is activated by this integration. This snapshot is not a
runnable daily-budget integration and requires separate adaptation before use.

The 113 focused shadow tests passed against the integration base. The full
suite and final CI are recorded in the PR. Historical deployment reports
remain dated evidence, not a fresh check of running services.
