# Issue #35 — supervisor task 1: operations-only publication

Source: latest issue-owner supervisor task supplied to this fresh implementation
worker. STATE: READY_FOR_CODEX; REASONING: high; NETWORK_ACCESS: enabled;
SEEDBOX_PERMISSION: none. This implementation is an ordinary **code task**;
operations_only must not be enabled on it. Repository briefs authorize no other
work. Runner owns commit/push/PR/issue reporting on automation/issue-35-worker.

## Goal and verified context supplied by the supervisor

Add explicit operations-only publication to the host runner so successful
authorized operations do not fall through into code commit/push/PR handling.
Issue #33 task 5 returned READY_FOR_REVIEW locally, followed by public FAILED /
PUBLIC_CODE_PUBLICATION_FAILED. The runner unconditionally publishes code after
READY without private input/output. The user reports functional deployment
completed and explicitly needs no retry: treat it as complete, never replay it
or inspect its services. No deployment or service operation is authorized here.

Public main supplied: 92afda3004af075c165886b6705b9f79f219706d. Launcher supplied:
clean main at a7017dd7525bc50fd719883ed5cfaccdedf603ca, behind product commits;
do not modify it. Preserve PR #31 retention, claim, private-input and receipt fixes.

## Acceptance criteria

1. Inspect AGENTS.md, runner/policy/receipt code, tests and supervisor protocol.
   Start at current main and preserve unrelated work. Add a narrow explicit
   PUBLICATION_MODE: operations_only directive; omission retains code publication.
   Reject unknown/duplicate/malformed directives and grants outside the latest
   trusted issue-owner task. Never infer it from prose, no diff, state or keywords.
2. Publication only: no network, SSH, service, filesystem or deployment grant.
   Preserve authorization/prohibitions, claims, locks, quota, reasoning, child
   credential filtering and at-most-once boundaries.
3. Operations-only never runs parent git add/commit/push or PR list/create/edit,
   even with earlier branch commits. PR: none and truthful fixed public checks/
   summary. Private artifacts/diagnostics stay independently authorized at exact
   destinations with unchanged CAS/readback; preserve input/output restrictions.
4. Capture exact checkout baseline immediately before child execution; verify
   afterward, including child failure. Detect branch/HEAD, staged, tracked and
   nonignored untracked changes; retain differences and emit a sanitized stable
   failure without code publication. Accept unchanged exact explicitly authorized
   retained continuation. No stash/reset/clean or adopting new changes as baseline.
   Document ignored-cache limits. This mode does not permit editing/reconciling
   the public checkout; future remote deployments need explicit separate scope.
5. Distinguish success, intentional NEEDS_USER, genuine child failure, checkout
   refusal, artifact/receipt failure and public-result failure. Persist a small
   local parent execution/publication outcome so delivery failure does not imply
   operations should rerun. Worker claims do not prove deployment. Public text
   states parent observations only. No retry or claim deletion/reuse. Keep receipt
   compatibility or document a minimal versioned change if necessary.
6. Meaningful synthetic regressions with separate launcher/issue worktrees:
   publication skipped on success and with earlier commits; blocked/failed results;
   changed checkout refused/preserved; unchanged retained baseline accepted; strict
   trust/parser; ordinary code publication; private canary isolation, artifact/
   receipt ordering; no reexecution after public-result failure. No real remotes,
   services or private inventories in tests.
7. Focused/full project tests in isolation, diff/dependency checks as appropriate.
   Update protocol/examples, engineering report/project state; leave unrelated
   legacy CODEX_TASK.md unexecuted. Separate TESTED, OBSERVED LIVE, EXPECTED BY
   DESIGN and inference.
8. Prepare a harmless post-merge local synthetic assertion task, READY with no
   checkout changes and no branch/PR publication. Real side effects require future
   authorization. Merge, launcher deployment and live smoke are supervisor follow-up.

## Authorization

Modify only necessary runner/policy/receipt code, synthetic tests and related
public infrastructure documentation. Network only for public repository inspection,
official technical documentation and necessary isolated dependency installation.
Use synthetic local fixtures for all operational/private boundaries. The established
host parent may publish this implementation branch/PR and sanitized terminal result;
the child must not publish Git/GitHub changes or post comments.

## Forbidden

No Radarr, seedbox (including SSH/reads), movie/media, live service/configuration,
library/list/tag/search/grab/download/import-exclusion access or mutations. No
repetition of issue #33 deployment or resolver checks. No host credential retrieval,
forwarding or logging; direct worker GitHub writes; real private inventory/research;
raw prompts/logs/private evidence in public output. No merge, deployment, launcher/
LaunchAgent/schedule changes; claim deletion/reuse; destructive cleanup, stash/reset
or retained-state bypass. Preserve worktrees/backups/stashes. No ChatGPT Work,
daemon startup, additional worker/runner, or prior-session resume/history access.

## Handoff

Smallest coherent extension with clear authorization boundary. Archive this brief
and an engineering report. READY_FOR_REVIEW only after local scoped checks; parent
owns publication. Report remaining live acceptance separately. Subsequent tasks
retain REASONING: high unless explicitly justified otherwise. The unrelated active
task document remains unchanged; this archived brief is completed by its
[engineering report](2026-10-17-operations-publication.md).
