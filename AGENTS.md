# Movie List engineering instructions

## Responsibilities and context

The user and ChatGPT own product design, architecture, recommendation logic,
behavior changes, priorities, and analysis of outputs. Codex implements, debugs,
tests, deploys, and technically verifies agreed work.

Before starting a task, read:

1. [Project state](docs/PROJECT_STATE.md).
2. Relevant records in [Decisions](docs/DECISIONS.md).
3. The current [implementation task](docs/CODEX_TASK.md).
4. [Deployment instructions](deploy/README.md) for service or deployment work,
   and any more specific instructions for the files being changed.

Inspect the actual branch, commit, working tree, and deployment state. Repository
facts and current user instructions take precedence over stale chat summaries.
Historical reports and archived briefs are context, not new work assignments.

## Execute the agreed specification

- Implement the objective, desired behavior, constraints, acceptance criteria,
  testing requirements, and deployment expectations in the agreed brief.
- A clear current user instruction is sufficient authorization to write or
  update the task brief and execute its engineering scope. Do not make the user
  restate an already agreed task or approve it again solely because a document
  is idle or has not caught up.
- The user grants standing authorization for routine repository reads/edits,
  scripts, tests, Git operations, SSH, service/log inspection, API queries and
  non-destructive debugging required by an agreed task. Carry that scope through
  implementation and verification; do not ask for command-by-command approval.
  Ask only before destructive/difficult-to-reverse work, important data deletion,
  production behavior outside the brief, meaningful external cost, missing
  credentials/access, or an uncovered product/design decision.
- Choose routine technical details needed for implementation; explain material
  tradeoffs in the engineering report.
- Prefer a conservative interpretation when the specification is ambiguous.
  Flag the ambiguity and record assumptions. Continue independent work; ask only
  for information or access needed to resolve a blocking ambiguity.
- Do not invent scoring weights, thresholds, recommendation gates, automatic
  download behavior, new product priorities, or a substantial architectural
  change. Surface proposals for the user and ChatGPT to decide.
- Preserve existing changes. Keep deployment checkouts at their verified commit;
  use an isolated branch/worktree when another change is not to be deployed yet.

## Project constraints

- Preserve the production festival feed, scoring policy, and research/production
  separation unless the agreed brief explicitly changes them.
- Do not reinstall provider-managed Radarr, assume Docker control, overwrite
  unrelated services, or merge/deploy beyond the scope explicitly authorized by the user.
- Keep service credentials in private host configuration and action data in
  private state. Never put credentials, tracker URLs, passkeys, webhook secrets,
  or approval tokens in chat, logs, commits, examples, or public artifacts.
  Generate missing secrets directly into private configuration without printing.
- Obtain the user's approval for the specific real notification/movie/release
  before deliberately sending a live test notification or testing movie addition
  or download. Respect existing authorized production operation.
- Inspect downstream and provider logging before making privacy claims about a
  release push. An approval for a test does not remove the secret-handling
  constraint.

## Validation and handoff

Use the task's required checks. For Python runtime changes, run the relevant
tests and the full `python -m unittest -v` suite in the project virtual
environment; run `python -m pip check` when dependencies change. For deployment,
follow the preflight, health, service, and read-only integration checks in the
runbook. Documentation-only work needs documentation/diff verification; do not
claim a runtime test was rerun when citing an earlier result.

After implementation:

1. Record what changed, files/components changed, tests and results, deployment
   result, unexpected findings, unresolved issues/risks, and commit/PR references.
   Use [the report template](docs/templates/ENGINEERING_REPORT.md).
2. Save the completed brief and report under `docs/reports/` so the next chat can
   recover both the requested behavior and its engineering result.
3. Update project state with verified facts, separating implementation,
   deployment, technical verification, and product acceptance.
4. Update decisions only to reflect an explicitly agreed decision, retaining its
   rationale and marking any replaced decision as superseded.
5. Finish or clear the active task in `docs/CODEX_TASK.md`, linking its report.
   Leave it idle when no implementation task is assigned; do not turn open
   questions into an independently chosen next task.
6. Return the structured engineering report to the user. The user and ChatGPT
   review behavior/output and agree the next iteration.

These documents preserve the handoff; they do not create an automatic channel
between unrelated chat threads. Start a new discussion with repository access or
the relevant file links and revision.

## User-facing movie notifications guide

Keep `docs/MOVIE-NOTIFICATIONS-GUIDE.md` current whenever a verified change affects movie notification routing, identification, investigation, confirmation actions or their safeguards. Write in plain language, distinguish live behavior from shadow experiments, and never include private credentials or tracker links. Preserve unrelated assigned tasks.
