# Movie List Project — Shared Context

Build a free, maintainable movie-discovery and Radarr-assistance system that
favors worthwhile discovery over indiscriminate volume.

The repository is the persistent handoff between the user, ChatGPT and Codex:

| Document | Purpose |
| --- | --- |
| [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) | Current architecture, stable behavior, verification and known gaps. |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Accepted product/architecture decisions and their rationale. |
| [docs/CODEX_TASK.md](docs/CODEX_TASK.md) | Currently assigned engineering task only. |
| [AGENTS.md](AGENTS.md) | Instructions engineering sessions read before work. |
| [Implementation brief template](docs/templates/CODEX_TASK.md) | Objective, desired behavior, constraints, acceptance criteria, tests and deployment expectations. |
| [Engineering report template](docs/templates/ENGINEERING_REPORT.md) | Changes, files/components, tests/results, deployment, findings, issues/risks and commit/PR reference. |
| [Latest completed brief/report](docs/reports/2026-10-13-handoff.md) | Workflow-documentation result for review. |
| [deploy/README.md](deploy/README.md) | Technical deployment procedure. |
| [Original project context](docs/archive/PROJECT-before-handoff.md) | Historical design/research reasoning, retained for context. |

The user and ChatGPT discuss, design and analyze. Codex executes the agreed
engineering specification and reports the result. The user and ChatGPT then
review behavior/output and decide the next iteration.

Read current state, relevant decisions and the active brief before starting.
Preserve agreed design reasoning and record verified facts; do not infer product
policy from an implementation convenience or treat a historical task as current.
