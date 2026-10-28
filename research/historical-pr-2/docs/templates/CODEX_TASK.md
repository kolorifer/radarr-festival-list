# Implementation brief: <task ID and title>

**Status:** <draft / ready / in progress / blocked / implemented>
**Agreed with:** <user + ChatGPT; date and discussion/issue reference>
**Repository/base revision:** <repository, branch and inspected commit>
**Relevant decisions:** <IDs and rationale links>
**Engineering owner:** Codex

Replace docs/CODEX_TASK.md with the agreed brief. A draft is a proposal; ready
means its scope is agreed. Preserve already given authorization. Do not put
credentials, private tracker URLs, webhook secrets, or approval tokens here.

## Objective

<The concrete problem and intended outcome. Include the agreed reason for
changing it, or reference the decision record that contains that reasoning.>

## Desired behavior

<Describe the before/after behavior, triggers, representative inputs/outputs,
error and ambiguity behavior, and interactions that must remain stable.>

## Scope and constraints

<Components in scope; exclusions; unchanged scoring/feed policy; privacy,
provider and source-control constraints; known deployment restrictions.>

## Acceptance criteria

- [ ] <Observable criterion with an example or verification method.>
- [ ] <Compatibility/error-path criterion.>

## Testing requirements

<Required test commands and cases; what must be mocked; regression checks;
which integration tests are allowed; limits on live side effects.>

## Deployment and verification expectations

<Implement-only, staging, or a specifically authorized deployment target. State
the required preflight, service/health/read-only integration checks, rollback
expectations and post-deployment observation. Name any deliberate notification,
movie or exact release approved for a live test; keep its private links off Git.>

## Ambiguities and assumptions

<Open questions; conservative assumptions the user accepted; any blocking
information or access. Do not let unresolved items silently become new policy.>

## Progress and implementation status

<Last update; completed/remaining work; test/deployment evidence; blockers.
Keep this current across interruptions. On completion, archive the agreed brief
with its report and clear the active task rather than assigning a new priority.>

## Required engineering report

Report what changed, files/components changed, tests/results, deployment result,
unexpected findings, unresolved issues/risks, and commit/PR references. Map the
acceptance criteria to evidence and explain any deviation from the agreed brief.
