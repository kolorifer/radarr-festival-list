# Engineering report: issue #30 / task 1 — supervisor communication

**Specification:** [Archived trusted task](2026-10-16-supervisor-communication-brief.md).
**Result:** implemented and locally verified; READY_FOR_REVIEW. Live deployment,
private fixture creation, sandbox acceptance and cloud schedule activation pending.
**Repository revision:** automation/issue-30-worker, based on
b294cec2481ea6fdc5b27a9d6f75dee4084c47db. Parent owns commit/push/PR/comments.
**Verification date:** 2026-10-16, isolated local Python 3.9.6 environment on macOS.

## What changed

The existing parent-owned capability architecture now stages exact pinned private
inputs before reservation. Each owner capability requires repository, exact path,
full commit, full blob, SHA256 and safe local alias. Both immutable commit and
blob are deliberately required: commit/path/tree mode rejects symlinks, while
blob and independently recomputed SHA256 verify the actual content. This is a
minimal stricter protocol choice within the assigned pinning requirement.

Up to eight inputs of 900000 bytes each are verified in bounded memory, then
staged outside the public checkout with mode500 directory/mode400 files and no
input --add-dir grant. Directory/file identities, modes, timestamps, size,
entries and contents are checked before reservation, before launch and after
child completion/failure. Private-input tasks cannot publish public files/history
or PRs. Existing PRIVATE_ARTIFACT and continuation boundaries remain in use.

PRIVATE_DIAGNOSTIC separately authorizes one exact operations/ JSON destination.
The parent generates a version-1 allowlisted receipt for terminal states after
reservation, including claim/child failures, using the existing private destination
validation/CAS/readback publisher. No worker prose, arbitrary diagnostics or raw
exception text enters the receipt or public status. Required receipt failure
produces public FAILED, preserves local records and makes no automatic retry.
Public comments add stable reason/receipt-availability fields; RUNNING includes a
claim timestamp and explicitly describes history rather than process liveness.

Omitted capabilities preserve denied defaults; existing task/result states,
discovery, duplicate suppression, locks, quota/cooldown and continuation formats
remain compatible. JSON duplicate-key rejection now also closes ambiguity in
existing publication/continuation directives. Private publisher metadata now
checks exact full repository identity as well as private/main properties.

## Files and components changed

| Component | Purpose |
| --- | --- |
| automation/supervisor_policy.py | Strict input/diagnostic capabilities, shared bounds/path/hash validation, duplicate JSON rejection |
| automation/github_worker.py | Parent input staging/immutability, terminal/delivery journals, required receipt publication, stable public codes |
| automation/terminal_receipt.py | Versioned schema and explicit code/action/field allowlists |
| test_supervisor_communication.py | 32 new synthetic authorization, integrity, leakage, lifecycle and delivery tests |
| test_supervisor_policy.py | Existing fake metadata/publication receipts updated to the stricter verified contract |
| automation/SUPERVISOR_PROTOCOL.md; automation/README.md | Protocol/defaults/recovery and verification instructions |
| automation/SUPERVISOR_HANDOFF.md | Exact original-account prompt/checklist and later harmless live plan |
| docs/PROJECT_STATE.md; archived brief/report | Scoped handoff; unrelated legacy task preserved |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Baseline and required records inspected | TESTED / observed read-only | Clean initial checkout and public main both b294cec; AGENTS/state/decisions/legacy task/deploy docs, runner/policy/tests/protocol and stabilization records read |
| Strict owner trust and immutable input grants | TESTED | Latest owner only; old/other tasks cannot grant; duplicate JSON/fields, wildcards/traversal/repos/aliases/pins rejected |
| Before-claim staging/integrity and no partial launch | TESTED | Metadata, commit/tree/blob/SHA256/size; changed source/pins, symlink modes, partial multi-input validation fail before claim/consumption |
| Read-only inputs and child credentials | TESTED | Mode/identity/hash/entry checks, local links/directory replacement, post-failure mutation; filtered environment and only output writable grant |
| Private/public separation | TESTED | Canary in input/output/result/exception; no public identity/path/prose, add/commit/push/PR; file and history changes refused |
| Structured receipt, all terminal states | TESTED | READY, NEEDS_USER, FAILED, claim/RUNNING-post failures; schema/extra field/code rejection; raw worker prose excluded |
| CAS/readback/order/recovery | TESTED | Existing publisher absent/identical/divergent/CAS races/readback; new receipt divergence/write failure/readback failure; private artifact -> receipt -> public order; lost public result never reexecutes/rewrites receipt |
| Existing lifecycle regressions | TESTED | All 65 preceding focused tests retained/passing, including locks/claims/continuation/discovery/quota/cooldown |
| Offline integration | TESTED | Real temporary Git checkout/backups, actual Python subprocess reading staged input and writing deterministic output, fake GitHub/Codex APIs and CAS |
| Exact schedule handoff/live plan | Prepared; EXPECTED BY DESIGN | Original-account prompt, inspect named existing schedules, enabled/next-run/observed wakeup checklist, successful/blocked/failure harmless plans |
| New live staging/receipts/schedule | Pending | Not deployed or activated; no live private APIs, real Codex child or schedules accessed |

OBSERVED LIVE (limited to ordinary public repository inspection): read-only
`git ls-remote origin refs/heads/main` returned b294cec, matching the supplied
baseline and initial local HEAD. The launcher, LaunchAgent, issue-26 retained
work, issue-28 evidence and private repositories were not accessed or changed.
Their earlier observed-live acceptance remains historical evidence in
[the stabilization report](2026-10-16-supervisor-stabilization.md), not a new
observation by this worker. No inference of cloud schedule absence is made.

EXPECTED BY DESIGN: the host gh boundary authenticates, resolves pinned private
inputs and publishes exact artifacts/receipts; the deployed CLI sandbox can read
staged aliases without a writable input grant. Synthetic tests verify command
configuration and parent behavior. The subprocess integration disables network
in its fixture and asserts Codex network=false, but does not run a real Codex
OS sandbox or prove a hostile same-account credential boundary. Those live CLI
properties require the subsequent harmless acceptance step. INFERENCE: the
existing parent separation should support the new staging/receipt loop; local
tests alone do not establish account-side scheduled wakeup or production behavior.

## Tests run and results

An isolated `/private/tmp/issue30-venv` was created using Python 3.9.6; existing
requirements were installed there. No dependency declarations changed.

- `/private/tmp/issue30-venv/bin/python -m unittest test_github_worker test_supervisor_policy test_supervisor_communication -v`
  — **97 passed**.
- `/private/tmp/issue30-venv/bin/python -m unittest -v`
  — **264 passed**, including offline local HTTP fixtures. No skipped
  tests or socket failures in the final run.
- `/private/tmp/issue30-venv/bin/python -m pip check`
  — **passed**, no broken requirements. Pip emitted only its non-writable-cache
  warning; installation succeeded without using that cache.
- `git diff --check` and changed-file/link/privacy/scope inspection — passed.

The initial full/focused runs had one recoverable test-fixture error each:
macOS refused rename of the mode500 directory used to simulate replacement.
The fixture now chmods its own synthetic directory before replacement. The
isolated replacement case then passed, followed by the complete passing runs
above. Runtime behavior was not relaxed. Prior baseline 65/232 and Python
3.12/3.13 CI are historical; this child did not run new CI or those interpreters.

## Deployment result

Not authorized and not performed. No unmerged runner, daemon, LaunchAgent,
launcher update or cloud schedule was started/installed/changed. No GitHub writes,
private repository reads, Radarr/seedbox/media services, inventories or research
were used. Network activity was limited to public main inspection and isolated
dependency installation. All private interactions in tests used synthetic fakes.

The [handoff](../../automation/SUPERVISOR_HANDOFF.md) specifies a separate reviewed
merge/deployment/fixture authorization, ordinary automatic pickup, pinned input
processing with network=false, output/receipt readback and sanitized public result,
plus deliberate synthetic blocked/failure cases. It also requires original-account
inspection of Codex Supervisor Sync and Phase B Output before any duplicate,
enabled/next-run verification and one actual scheduled wakeup.

## Unexpected findings

Contents API responses alone are insufficient to rule out symlinks because a
target may be returned as a file. Exact non-recursive Git tree mode checks are
therefore required in addition to content/hash verification. No recursive private
inventory or other file contents are requested. Full metadata identity checks
and strict JSON duplicate-key validation strengthen existing boundaries without
changing their destination allowlist or claim ordering.

## Unresolved issues and risks

- Live private staging/CLI read permissions, new receipt readback and cloud
  schedule enabled/next-run/wakeup remain pending. Review is not live acceptance.
- A receipt PUT may succeed before readback fails: public FAILED/unavailable takes
  precedence over an unverified intended READY receipt. A verified private receipt
  may precede an ambiguous public POST failure. Local delivery records preserve
  this boundary; no automatic receipt rewrite, second public terminal attempt,
  claim deletion or task reexecution occurs. Inspect exact destinations/claims,
  then authorize a NEW task with exact expected blobs and snapshot if needed.
- Codes identify parent-observed boundaries, not root causes. Raw test failure
  detail, exact blocker questions, credential problems and damaged snapshots still
  require local inspection. Action categories do not grant new capabilities.
- Mode400/500 and before/after identity/hash checks detect changes; they are not
  a hostile same-OS-account isolation guarantee. Temporary staging and private
  worker logs/backups remain local; OS cleanup, hard kill or state-disk failure
  can require inspected recovery. Inputs receive no unnecessary writable grant.
- Ordinary code-task diffs still need privacy/scope review. Private-input/output
  tasks instead categorically refuse public publication. Ignored caches remain
  outside the existing continuation fingerprint; no automatic cleanup was added.

## Commit and PR reference

No child commit/push/PR/comment performed. The established parent will publish
this review-ready working tree and supply commit/PR references. No merge assumed.

## Project context updates

Project state records local implementation/testing separately from later live
acceptance. This brief/report archives the completed scoped assignment. The
unrelated legacy docs/CODEX_TASK.md and existing decisions remain unchanged per
the trusted task; no curation/runtime/product work was inferred or executed.
User/supervisor review and subsequent explicitly authorized live steps remain.
