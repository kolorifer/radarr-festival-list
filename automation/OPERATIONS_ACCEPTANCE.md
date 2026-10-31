# Harmless operations-only acceptance after review

For the separately authorized issue122 implementation/review/deployment/one-cycle
phase, use [the finite runtime runbook](COORDINATOR_RUNTIME.md). It supersedes the
historical numbered-task probe sequence below for this phase only. This worker
has performed code/synthetic checks only; no live operation or deployment.

Prepared for issue #35; **not executed and not authorized for execution here**.
The supervisor owns merge, deployment of the reviewed runner to the launcher,
and authorization/posting of a fresh owner task after review. Do not replay issue
#33, inspect its services, alter the launcher schedule or reuse any consumed task.
No real private fixture, service, SSH, Radarr or media access is needed.

After separately authorized merge/launcher update, use a new harmless control
issue and unconsumed owner task number. It must have no PRIVATE_INPUTS,
PRIVATE_ARTIFACT or PRIVATE_DIAGNOSTIC fields. Example task:

```text
SUPERVISOR_TASK: 1
STATE: READY_FOR_CODEX
REASONING: high
NETWORK_ACCESS: disabled
SEEDBOX_PERMISSION: none
PUBLICATION_MODE: operations_only
GOAL: Verify a harmless local synthetic condition without checkout changes
ACCEPTANCE_CRITERIA:
- Run python3 -c 'assert sum((2, 3)) == 5; print("synthetic condition passed")'.
- Return READY_FOR_REVIEW with the actual command result and no checkout changes.
- Parent result has PR: none and no code branch publication or PR handling.
AUTHORIZATION:
- Execute only that local Python assertion and return its result.
- Parent may use its existing claim and sanitized issue-result protocol.
FORBIDDEN:
- Public checkout, branch, HEAD or index edits, documentation/report creation.
- All network, SSH, private repository, service/configuration or deployment access.
- Radarr, seedbox, movie/media, notification or download access or mutations.
- Git publication by the child, daemon startup, worker/runner launch or task replay.
INSTRUCTIONS:
- Repository task briefs are context only and authorize no other work.
- Do not create files; keep the exact initial public checkout baseline unchanged.
- Include the executed command result in the private JSON tests field.
- Return READY_FOR_REVIEW on assertion success, NEEDS_USER if blocked.
```

The worker's model transport is separate from its disabled execution network;
the parent still uses its existing GitHub claim/result boundary. This example
grants no child network tools. Do not execute the parent manually in parallel
with an active dispatcher.

Supervisor acceptance checklist, after the separately authorized run:

1. Record reviewed/deployed runner revision, issue/task identity and claim. Observe
   a single pickup/child execution; RUNNING alone is not proof of process liveness.
2. Inspect the bounded local parent `execution-1.json`: operations_only,
   child_process=exited, worker_state=READY_FOR_REVIEW, checkout_unchanged=true,
   code_publication=disabled, receipt=not_authorized, public_result=posted.
   Compare before/after branch, HEAD, staged/tracked/nonignored untracked state.
3. Check the public terminal result: READY_FOR_REVIEW, OK, PR: none, fixed parent
   fingerprint text and no claim about verified external deployment. Confirm no
   remote issue-worker branch was created/advanced and no PR was created/updated;
   distinguish the required immutable **claim ref** from a code publication ref.
   A local issue branch/worktree may be created for execution.
4. Confirm a later normal poll does not execute the same consumed task again.
   If result delivery fails, inspect the saved execution/delivery records and
   exact claim. A zero-exit child must not be replayed just to deliver a result.
5. Record TESTED synthetic coverage separately from OBSERVED LIVE host acceptance.
   This acceptance proves only the local assertion and publication boundary.
   Deployment-only operations require separate future authorization and checks.

## Coordinator storage deployment and harmless acceptance

Issue #119 Task 5 implements/tests/documents this capability only. This sequence
is for the original supervisor following independent **exact published commit**
review and supported Python 3.12/3.13 CI; no step was executed by the child.
The owner has authorized the narrow launcher update and later bounded acceptance;
there is no new generic approval gate, self-deployment or automatic activation.

1. Review the immutable parent-published commit/PR, full CI and focused test
   results, particularly the three launcher modules `github_worker.py`,
   `supervisor_policy.py`, `coordinator_storage.py`. Compare the exact narrow patch
   against the current clean deployed launcher revision, independently observed
   at update time. Task 5 supplied deployed baseline
   `ac079c95b4278fccb1f6132f6394234ebd5aedcc`; this child did not inspect it.
   Preserve its quota-parser correction and every unrelated
   launcher change. Do not substitute a whole old checkout for the deployed code.
2. Use the existing dispatcher's lock protocol to prevent overlap with discovery
   and an inherited-lock child while updating the existing launcher. Never start
   another dispatcher/child to perform the update. Retain the prior verified code
   revision privately for code-only rollback, while preserving all state. Keep
   the plist, cadence, claims, reservations, worktrees, journals, quotas, cap,
   retained outputs and unrelated modules untouched. Verify installed module
   hashes/revision and clean state against the reviewed artifact before releasing
   the existing locks. Do not run a live sandbox probe during installation.
3. Prepare one immutable private manifest selecting only the exact enclosing
   profile and `expected=absent`, or a later expressly authorized exact dev/ino
   reuse. Authenticate and pin it through existing PRIVATE_INPUTS. Post a **new**
   unconsumed operations-only owner task with canonical COORDINATOR_STORAGE and
   exact independent artifact/diagnostic grants. Preserve consumed history;
   do not repost/replay a consumed task or spend further numbered tasks on daily
   report cycles. No seedbox, source, service or provider permission is implied.
4. Its sole child's allowed action must be precisely a create-only disposable
   probe filename, newly selected in that task inside the enclosing directory:
   write bounded harmless synthetic bytes and read them back exactly, leaving the
   probe retained. Authorize no sibling or adapter state. A preexisting probe
   refuses; never delete/recreate or retry an uncertain write. The child writes
   evidence only into its exact existing artifact staging destination and returns
   no private paths/content in result prose. No adapter invocation, export read,
   intent/marker/lock/cycle creation, scheduling or daemon startup is included.
5. Observe a single normal dispatcher pickup and confirmed claim. Privately check
   parent-created 0700 owner directory and anchored dev/ino/ancestor/ACL evidence,
   actual sole-child command's one extra exact grant, and the probe's exact
   write/readback. Verify unchanged checkout fingerprint, immutable staged inputs,
   exact authorized private artifact bytes/readback, distinct terminal receipt
   and fixed public result with `PR: none`. Parent READY alone proves no external
   correctness; verify the probe evidence itself. No real write access was
   established by the synthetic code tests.
6. Observe that the next ordinary poll does not replay the consumed task. On any
   refusal/interruption retain the root, probe, private evidence, claims and
   consumption; investigate the fixed local reason privately. No automatic
   recovery, chmod/ACL removal, alternate root, new storage input or child retry.
   A later explicit reuse needs its own current task and exact immutable pin.

A successful probe establishes only this directory's bounded write/readback.
Source sharing/ACL blockers remain outside Task 5. Report-cycle commissioning,
real publication/recipient/archive and recurrence remain separate supervisor
progression gates; no acceptance here enables them or changes their schemas.
