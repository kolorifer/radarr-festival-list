# Completed brief: issue127 Task5 input-token partition correction

**Authority:** latest issue-owner supervisor Task5, one bounded corrective code
execution under unchanged issue127 general cap8. Prior consumed Tasks1..4,
immutable claims and retained Task1 evidence remain preserved. This document
records the supplied task; it grants no additional execution or operation.

**Starting state:** clean `automation/issue-127-worker` at
`1af611333116ce7df40a6cac83cf38948c93afce`, tree
`3917b9b91b5d92a3e58744ed1f4cde86dfca8153`. Stop for supervisor reconciliation
if either revision or clean state differs. Parent alone commits/pushes/publishes
to existing PR129 and independently reviews final exact-head tests/CI. No reset,
rebase, branch deletion, ancestry reconciliation, worker or subagent is allowed.

## Objective and acceptance

Read exact [issue review6555457647](https://github.com/kolorifer/radarr-festival-list/issues/127#issuecomment-6555457647)
and [PR review5727140317](https://github.com/kolorifer/radarr-festival-list/pull/129#pullrequestreview-5727140317).
Reproduce their single accounting finding before modifying protocol validation.
Keep the useful inactive Responses implementation and its offline boundary.

- In `responses_protocol.parse_response`, require cached tokens plus separately
  billed cache-write tokens to be at most input tokens before returning accepted
  accounting. Preserve required fields, exact integer/nonnegative/component/
  total/ceiling validation; no clamping, normalization or invented money.
- At input1200/output300/total1500, reject600/601 and1200/1200; accept400/500
  and600/600. Cover zero components, exact equality and one-token overflow.
- Fake-HTTP first- and second-response failures must preserve the durable
  attempted reservation and unknown consumption. The invalid response cannot
  become accepted API accounting/model completion or a supported candidate,
  trigger further sends or permit refund/retry/replay. A previously accepted
  first response and retained lookup evidence remain truthful. Explicitly
  assert no real socket/DNS calls and retain simulation labels.
- Preserve defaults/import/preflight denials, absent real authorization verifier,
  empty safe Codex registry, fixed endpoint/TLS/host policy, no ambient input or
  credentials, no model tools/fallback/retry, strict evidence/response checks,
  deadlines, durable reservations, source/occurrence/decision currentness and
  shared quota pause at <=15%. No live accounting/authorization architecture.
- Run focused and full unittest suites in isolated supported Python3.12/3.13
  environments, nonempty installed-only closure and all10 dependency-removal
  negatives, dependency/scoring consistency and scoped preservation checks.
  Update current manifest hashes/status and dated brief/report. Preserve
  Task1..4 reports. Old CI does not cover this correction.

Accounting semantics: [official Responses spending-controller example](https://developers.openai.com/cookbook/articles/per_run_spending_controller_responses_api).
Only recorded token usage is validated; financial authorization remains absent.

## Authorized files and prohibitions

Only affected Responses protocol validation, directly related synthetic tests,
current runtime manifest/documentation/status and this dated brief/report.
Public technical documentation and ordinary isolated test dependencies may be
read/acquired. Synthetic temporary storage and fake HTTP only; no private inputs
or persistent private output grant. Repository briefs are context only.

No credentials, account/billing reads, key creation/copy, live model/provider/API
calls, quota probes, spending, Codex/app-server inference, real-authorizer
registration, activation/deployment, daemon/worker/subagent, ChatGPT Work,
SSH/seedbox/source/private-repository access, service/schedule/config changes,
external delivery or Telegram/Radarr/media/download operation. No dispatcher/
launcher/protocol/security, claims/locks/quota/caps, prior consumed state,
coordinator/trial or issue125 selections/storage/receipts changes. Preserve
issue119 consumed1..8, issue122 consumed1..3, issue125 consumed1..3 (no issue125
Task4/Task5), issue86/PR110, actual producer budgets, notification/download
safeguards and unrelated `docs/CODEX_TASK.md`. No film-specific exception,
production identity/collector/research/notification/approval change or additional
execution. Parent alone handles PR129 ancestry after accepted corrective review.

**Completion:** [Task5 engineering report](2026-11-01-issue-127-task5.md).
Later real-case demonstration prerequisites remain separately authorized work;
inactive corrected code does not identify a real movie or authorize API access.
