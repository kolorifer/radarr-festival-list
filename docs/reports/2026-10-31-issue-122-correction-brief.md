# Issue122 Task2 — final scoped correction brief

Source: issue-owner supervisor Task2, the SECOND AND FINAL authorized engineering
execution. Independently read review [6542515755](https://github.com/kolorifer/radarr-festival-list/issues/122#issuecomment-6542515755)
and PR [123](https://github.com/kolorifer/radarr-festival-list/pull/123). Initial
checkout verified clean `automation/issue-122-worker` at
`70ad14ebf23c1f68e79a6a073056c0d29303e465`. Task1 is terminal; its accepted
supported CI41194779483 is baseline evidence, not validation of this correction.
Supplied deployed launcher remains229148; no operational state is inspected.

Implement/test/document only the independently reproduced findings:

1. Replace OpenSSH-inaccessible credential descriptor paths with the already
   selected canonical original paths. Never read/copy/hash/stage private-key
   bytes or use an agent/ambient config/weakened authentication. Hold/revalidate
   descriptors, namespace, ownership/modes/ACLs and device/inode before/after
   use. State the accepted stable-owner threat model honestly; path opening is
   not atomic protection against hostile same-account swap-and-restore.
2. Preserve both actual dispatcher locks after initiating-parent death and SSH
   FD closure using only a bounded fixed transport keeper supervising one SSH
   child. No external command protocol, worker, daemon, retry or scheduler. Test
   native `/usr/bin/ssh -G` with harmless files and isolated orphan-lock lifetime.
3. Complete deterministic local credential and ancestor preflight before any
   journal/claim/evidence/adapter/reservation effects. Unsafe/missing/replaced/
   linked/mode/ACL/identity inputs consume nothing and make no source/publication
   call. Preserve exact OS-account home derivation for short SSH-parent paths.
   Remote checks remain after the one durable acquisition grant.
4. Honor closed/latest-trusted DONE before reporting selection. Exclude consumed
   starts, inert reconciles and completed archive acknowledgements before private
   fetch/validation, allowing other eligible issues to progress. Preserve fresh
   matching continuations and exact interrupted receipt/archive recovery; weak or
   malformed local state grants no work. No retry acquisition/PUT or second cycle.
5. Before source path access, require actual non-root effective UID/GID to match
   the explicit selected numeric account. Use explicit no-bytecode Python and an
   independent bounded remote deadline. Preserve the same two exports and all
   original-byte/clock/no-follow/spelling/identity/owner/mode/ACL/hardlink/size/race
   checks. No source writes, refresh, provider/research or DB operations.
6. Preserve all Task1 schemas/functionality, durable publication observation,
   honest owner-selected genuine recipient contract, accepted Grant.home fix,
   issue119's eight claims/cap and current phase history, issue122 limit2 and
   general limit8, all claims/quotas/locks/isolation/grants/retained evidence.
   Update the exact runbook and saved handoff; leave unrelated CODEX_TASK.md,
   decisions, #86/PR110, production/research/services/plist/watch untouched.
7. Freeze runtime code before final validation. Run meaningful native/synthetic
   checks and relevant parent/policy/storage/receipt/coordinator regressions, then
   one full unittest suite. Preserve native3.9 compatibility; no dependencies are
   installed. Report local failures accurately. Parent-published exact-head
   supported3.12/3.13 CI remains required before supervisor acceptance.

Only implementation/tests/docs are authorized for this child. No seedbox access
(including reads/SSH), real key/home/private/source/root exploration, live server
connection, deployment, pilot, Work, subagent/worker/runner launch, Git publication
or issue comments. The existing parent alone commits/pushes/updates PR123/reports.
After independent exact review/CI, the supervisor carries the already authorized
bounded deployment, ONE partial cycle, actual distinct coordinator ingestion and
owner-selected acknowledgement/archive. Those fixed operations require no new
engineering task or generic approval. No third execution/successor/reset/recurrence
or full movie-coverage claim is authorized.

Handoff: [engineering report](2026-10-31-issue-122-correction.md) and
[exact runtime/deployment/command runbook](../../automation/COORDINATOR_RUNTIME.md).

Completion: scoped correction implemented and handed off for exact review. Final
native runtime44 passed; one full suite957/109 errors/two skips/no assertion
failures (not a pass); detailed actual validation and remaining CI/live gates are
in the linked report. No operational access or worker publication occurred.
