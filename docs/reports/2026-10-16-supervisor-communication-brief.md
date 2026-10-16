# Issue #30 / supervisor task 1 — trusted implementation brief

**STATE:** READY_FOR_CODEX at assignment; completed locally for review.
**REASONING:** high. **NETWORK_ACCESS:** enabled within the authorization below.
**SEEDBOX_PERMISSION:** none.

This archived brief records the latest issue-owner task supplied to this fresh
worker. Older repository briefs and issue comments are context, not authorization.
The parent owns commit/push/PR/issue reporting on automation/issue-30-worker.

## Goal

Close the remaining parent-runner communication gaps needed for unattended
supervision: stage explicitly authorized private inputs for the sandboxed worker,
publish narrowly scoped structured terminal diagnostics that ChatGPT can read
privately, and prepare an exact account-side supervisor-schedule handoff. Build
on the already deployed publication/continuation repair; do not redo it or claim
the cloud schedule has been enabled.

## Supplied baseline (recheck before implementation)

- Public repository: kolorifer/radarr-festival-list; allowlisted private state:
  kolorifer/radarr-state. Main and launcher were reported at
  b294cec2481ea6fdc5b27a9d6f75dee4084c47db when the task was prepared.
- PR #27 supplied exact private-output authorization, parent publication/readback,
  snapshot continuation, fixed public text, filtered child environment, high
  reasoning and heartbeat. PR #29 supplied deployment evidence.
- Accepted/closed harmless issue #28 demonstrated automatic LaunchAgent pickup,
  NEEDS_USER continuation without manual stash/reset, private publication and
  exact readback, sanitized READY_FOR_REVIEW, active process/heartbeat and locks.
- Historical verification: 65 focused / 232 full tests and Python 3.12/3.13 CI.
- Gaps: input staging is not generalized; detailed failures remain local. Original
  cloud supervisor activation is unverified. The LaunchAgent does not wake
  ChatGPT; no local entry does not prove absence of a cloud schedule.

## Acceptance criteria

1. Inspect AGENTS.md, runner/policy/tests, protocol and stabilization brief/report.
   Distinguish TESTED, OBSERVED LIVE, EXPECTED BY DESIGN and inference in reporting.
2. Add strict issue-owner private input capability: one allowlisted repository,
   exact path, immutable expected blob or commit plus content integrity, safe
   alias. Reject ambiguity, duplicate fields, wildcards, traversal, alternate
   repositories, unpinned mutable inputs, symlinks and oversized content. No
   grant may come from issue text, old tasks or other commenters.
3. Host parent authenticates, validates the private repository, fetches only exact
   authorized inputs, verifies identity/integrity and stages outside the tracked
   public checkout. Child receives local paths and narrow authorization, never
   credentials or unnecessary writable input grants. Detect/refuse changes.
   Failed/partial validation must not launch or unnecessarily consume a task;
   preserve lock/claim ordering.
4. Private-input tasks fail closed against public file/history publication as
   PRIVATE_ARTIFACT tasks do. Keep contents, identities, evidence, local paths
   and raw worker prose out of public comments/PRs/logs. A network-disabled
   synthetic child can use staged input and produce local output without GitHub.
5. Add optional exact-path private terminal diagnostic authorization separately
   from output, using parent destination validation, divergence/CAS and readback.
   Never infer adjacent-file/directory access. Support READY_FOR_REVIEW,
   NEEDS_USER and FAILED after reservation while preserving at-most-once work.
6. Define a small versioned allowlisted schema: issue/task, state, stable
   failure/blocker code, permitted next action, runtime/checkout revision,
   retained snapshot when available, verification flags and authorized artifact
   hashes/references. Treat model output as untrusted. Exclude raw prompts/logs,
   arbitrary exception/stderr, environment, credentials/tokens and worker prose.
   Bound structured text and document cases needing local inspection.
7. Preserve local diagnostics on receipt failure. Required publication/readback
   failures must not produce false public success. Handle private-write/public-
   result failure conservatively; document recovery. No automatic reexecution,
   claim deletion, destructive cleanup or unbounded publication retry loop.
8. Public parent statuses need stable non-sensitive reason codes and receipt
   availability. Preserve state parsing/duplicate suppression. RUNNING is history,
   not liveness; timestamp actual observations and mark them historical at exit.
9. Meaningful synthetic tests: trust/authorization, pin mismatch/changed source,
   traversal/symlink/size, no host credentials, immutability, public canary leaks,
   receipt validation/redaction/all terminal states, races/readback/ordering.
   Retain discovery/lock/claim/continuation/quota/cooldown regressions. Exercise
   local end-to-end fake GitHub/Codex boundaries and real temporary files/Git.
10. Focused/full suites in an isolated environment and dependency/diff checks as
    appropriate. No real Radarr/seedbox/media calls. Investigate recoverable
    failures and accurately report environmental limits.
11. Update engineering/protocol docs with a supervisor prompt/checklist usable in
    the original ChatGPT account: discover owner issues, notice terminal results,
    read only authorized private artifacts/receipts, high reasoning, exact prior
    snapshot continuation, quiet unchanged state, human subjective/destructive
    decisions. Inspect Codex Supervisor Sync and Phase B Output before duplicates;
    verify enabled state/next run and one wakeup. Prepared prompt/LaunchAgent are
    not activation evidence.
12. Precise harmless post-merge acceptance plan: pinned input -> sandbox processing
    -> parent output plus receipt -> sanitized public result, plus synthetic
    blocked/failure case. Deployment/private fixture creation are follow-up
    actions. Do not activate this unmerged runner. Return READY_FOR_REVIEW only
    after local implementation/verification, with live/schedule evidence pending.

## Authorization

- Read/modify necessary public automation code, focused tests and related docs.
- Network only for isolated dependency installation, official technical docs
  and ordinary public repository inspection. Private interactions in tests must
  be synthetic/fake; no live private inventory or research inputs are needed.
- Create local synthetic fixtures and run offline unit/integration checks;
  preserve all existing work/state.
- Established host parent may publish this scoped branch/PR/fixed public result;
  this Codex child must not publish GitHub changes or comments.
- Choose minimal compatible protocol/schema details and document defaults and
  migration. Preserve task formats unless a necessary change is documented.

## Forbidden

- All Radarr/seedbox access, including reads, and all movie/library/media/list/
  tag/config/search/grab/download/import-exclusion operations, curation/research.
- Live private movie inventory/research reads/writes; use synthetic data only.
- Host credential retrieval/forwarding/logging or approval/sandbox bypass;
  direct worker GitHub writes; raw prompts/private contents/logs/sensitive
  diagnostics in public commits/PRs/comments/summaries.
- Claim edits/deletion, consumed-number reuse, unstash/reset/clean of retained
  work or replaying old briefs. Preserve issue-26 worktree/stash and issue-28
  evidence.
- Merge/deploy, launcher checkout changes, LaunchAgent installation/reload/cadence
  changes, or this child creating/activating a ChatGPT schedule. No ChatGPT Work,
  daemon installation/start, another worker/runner or prior-session continuation.
- Unrelated scoring/catalog/runtime/product or credential infrastructure changes.

## Handoff instructions

Implement the smallest coherent extension of parent-owned capabilities. Verify
current checkout/public main from code; historical reports remain evidence only.
Keep secrets/private state outside public worktree. Archive brief/report and
update project state without executing or clearing unrelated legacy CODEX_TASK.md.
Separate synthetic tests from later live acceptance. Return a concise structured
private result; parent owns publication. If blocked, return NEEDS_USER and reason.

Completed result: [engineering report](2026-10-16-supervisor-communication.md).
