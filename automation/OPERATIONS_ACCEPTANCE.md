# Harmless operations-only acceptance after review

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
