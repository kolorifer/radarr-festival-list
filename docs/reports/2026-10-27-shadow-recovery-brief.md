# Shadow evidence and scheduling recovery

Owner request, 2026-10-27: fix evidence extraction and budget scheduling gaps,
including unnecessary edition searches; test and deploy shadow-only, then run
another bounded pilot without downloads or notifications.

Scope: parse decorated/compact NFO container and separate audio tracks; retain
exact source-ID binding when stored release whitespace differs; report safe
listing failure reasons. Avoid interpreting AKA aliases, remaster/format labels
and container version fields as cut claims. Keep genuine unfamiliar cut labels,
source binding, rival visibility, current conflict gates and scoring unchanged.

Scheduler: one case per hourly invocation; prioritize unresolved/new versions;
checkpoint successful GET results for at most24h to resume within the same10/run,
40/day ledger instead of requiring10 unused daily requests. Retain prior good
scores with their original dates. Reuse completed version results without daily
re-fetching; new evidence versions still require investigation. Stable failures
wait one day; transient failures back off, without resetting budgets or holds.

Run a new seven-day maximum pilot, explicitly separating previous-pilot cases,
historical baseline and new proposals. Archive the previous manifest/report,
preserve caches/ledgers, leave the actor, research schedule and all acquisition
state unchanged. The existing daily research intake remains in operation; this
pilot cannot itself send notifications, mutate queues, approve identities or
download. Normal unrelated production operation is preserved.

Acceptance: offline regression/integration tests, full local/seedbox suite,
CI, exact-runtime preflight, protected-state and health checks, and bounded
shadow verification of the unresolved carryovers. Report actual requests and
remaining evidence failures separately from deployment success. No scoring
activation or indefinite recurring extension is authorized.
