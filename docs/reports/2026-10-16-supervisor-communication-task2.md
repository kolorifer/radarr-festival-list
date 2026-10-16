# Engineering report: issue #30 / task 2 — retention and claim ownership

**Specification:** [Archived trusted task](2026-10-16-supervisor-communication-task2-brief.md).
**Result:** both review findings implemented and locally verified; READY_FOR_REVIEW.
**Repository revision:** automation/issue-30-worker, initial clean HEAD and remote
branch both cde534ae5e34da13a4de6ac44484cfa3c01a61ae. PR #31 remains parent-owned.
**Verification date:** 2026-10-16, isolated local Python 3.9.6 on macOS.

## What changed

Retention now names the validated execution checkout independently of the
temporary self.repo launcher context. Snapshot, file listing, tar contents and
index patch all use that checkout. Failure recovery preserves a current-task
capture rather than replacing its metadata against an older backup. This also
preserves the original NEEDS_USER state when receipt failure later makes the
public outcome FAILED. With no established execution checkout, recovery does
not manufacture a snapshot or tar from the launcher; checkout revision and
retained snapshot are unavailable rather than substitutes from main.

An atomic claim create must return successfully before terminal publication is
allowed. Both definite conflicts and ambiguous responses keep the preexisting
local consumed reservation and one bounded claim-failure-N.json record with
fixed code/ownership/consumed fields. They do not call terminal, create receipt
delivery journals, write any task-private destination, post RUNNING or publish an
authoritative WORKER_RESULT. No public claim warning is emitted, avoiding changes
to supervisor parsing. A terminal guard also rejects accidental unowned calls.
The historical version-1 CLAIM_FAILED receipt code remains readable, but is no
longer generated remotely by this runner.

No retries, claim deletion, new scheduling, new schema, permission expansion or
changes to private input/CAS/readback policy were introduced.

## Files and components changed

| Component | Change and purpose |
| --- | --- |
| automation/github_worker.py | Explicit execution checkout for retention; preserve prior capture; confirmed ownership gate and local-only claim failure |
| test_supervisor_communication.py | Separate real Git worktree lifecycle, backup/index and continuation checks, two-host claim interleavings and lost responses |
| test_github_worker.py; test_supervisor_policy.py | Unit fixtures explicitly establish ownership when starting after claim; claim conflict asserts no public result |
| automation/SUPERVISOR_PROTOCOL.md | Corrected retention/ownership recovery and historical receipt compatibility |
| automation/SUPERVISOR_HANDOFF.md | Owner-supplied current-chat ACTIVE heartbeat, pending wakeup/original schedule evidence |
| docs/PROJECT_STATE.md; task-1 report; this brief/report | Current scoped handoff, preserving earlier evidence and unrelated task |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Exact baseline and preserved work | Verified read-only | Clean initial branch; git ls-remote origin refs/heads/automation/issue-30-worker returned the exact requested commit |
| Child plus receipt failure retains issue checkout | TESTED | Main launcher differs from older issue branch; tracked staged/unstaged and untracked bytes, recomputed snapshot, complete tar contents and index patch all match the issue checkout |
| Authorized continuation without stash/reset | TESTED | NEW task 2 validates task-1 snapshot, enters a real issue-worktree child with identical bytes/index and leaves task-1 backup unchanged; no stash created |
| Success/blocked receipt failures | TESTED | Successful private child captures FAILED from issue checkout; blocked child preserves original NEEDS_USER retention and partial work while public receipt failure reports FAILED |
| Checkout never established | TESTED | Failed worktree creation plus receipt PUT failure launches no child and produces no retained baseline/tar; intended receipt snapshot and checkout revision are null |
| Cross-host claim conflict/ambiguity | TESTED | Independent temporary Git clones both discover before claim; winner's receipt destination remains absent through loser's attempt; only acknowledged owner publishes |
| Lost successful claim response | TESTED | Remote ref is created but response is lost; neither host executes/publishes, both keep consumed journals, later polls do not retry |
| Public/private and existing safeguards | TESTED | Focused regression suite includes pinning, immutability, credential filtering, canary redaction, CAS/readback, locks, quota/cooldown and duplicate protection |
| New live runner behavior | Pending | No merge/deployment or live fixtures/services authorized or accessed |
| Schedule context | Owner-supplied status only | Current Work/Codex chat hourly heartbeat creation returned ACTIVE; scheduled wakeup unobserved and original cloud ChatGPT schedules unverified |

The two-host race is a deterministic interleaving, not a timing-dependent stress
test: both hosts first discover the absent claim, the first server create succeeds,
then the second host attempts claim before the first receives its success or
publishes anything. It tests both HTTP conflict and timeout of that losing
attempt, and the separate case where the successful create's response is lost.
All claims, APIs, Codex transport and private destinations are synthetic. Real
temporary Git/files/backups and a harmless Python subprocess exercise local
boundaries; no production launcher or retained issue state is inspected.

## Tests run and results

Reused the existing isolated /private/tmp/issue30-venv (Python 3.9.6); dependency
declarations unchanged. Actual test commands/results:

- `/private/tmp/issue30-venv/bin/python -m unittest test_github_worker test_supervisor_policy test_supervisor_communication -v` — **105 passed**.
- `/private/tmp/issue30-venv/bin/python -m unittest -v` — **272 passed**, including offline local HTTP fixtures; no skips or failures.
- `/private/tmp/issue30-venv/bin/python -m pip check` — **passed**, no broken requirements.
- Final documentation/link review, `git diff --check` and complete diff inspection — **passed**.

The earlier task-1 97/264 counts and historical issue-28 live acceptance are
preserved as earlier evidence, not substituted for these fresh checks.

## Deployment result

Not authorized or performed. No merge, GitHub publication, live private fixture
creation/access, service/media/seedbox/Radarr operation, launcher/LaunchAgent
change or daemon start. No schedule tools or ChatGPT Work were used. Network
was limited to ordinary read-only public branch inspection. The parent owns
commit/push/PR/public reporting; review and later scoped live acceptance remain.

## Unexpected findings

The earlier synthetic integration fixture placed its launcher directly on the
issue branch, masking the restore-context bug. New regressions keep main and
issue worktrees distinct, with different HEAD/content, and exercise the real
execute lifecycle rather than substituting execute_in_checkout.

## Unresolved issues and risks

- A lost successful claim response intentionally leaves a permanently consumed
  task with no executing/publishing owner. A ref at the same SHA cannot prove
  host identity. Inspect exact claim/local journals and use a NEW task if needed;
  do not retry the old number or delete/reclaim the ref.
- Receipt PUT may succeed before readback fails; existing conservative public
  FAILED/unavailable and bounded delivery journals still apply. A previously
  captured NEEDS_USER snapshot remains usable only through exact NEW-task
  authorization and unchanged-state validation.
- These changes prevent newly corrupted retention; they do not repair preexisting
  mismatched snapshots/backups. Existing unexpected dirty/damaged state requires
  inspection; no bypass, reset, cleanup or invented continuation was added.
- Local tests establish parent behavior at fake boundaries. Deployed CLI staging,
  private publication/readback and account-side scheduled wakeup remain pending
  live acceptance. The owner's ACTIVE creation result is not a wakeup observation.

## Commit and PR reference

Review correction for [PR #31](https://github.com/kolorifer/radarr-festival-list/pull/31)
on the supplied baseline. This child made no commit, push, PR update or comment;
the host parent supplies the eventual containing commit and publication evidence.

## Project context updates

State, protocol and schedule handoff reflect this scoped correction. The task-1
report links forward without rewriting earlier test/live evidence. This archived
brief/report completes only supervisor task 2; unrelated CODEX_TASK.md and product
decisions remain unchanged. No further implementation task is inferred.
