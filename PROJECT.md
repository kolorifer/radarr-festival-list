# Movie List shared context

Read [project state](docs/PROJECT_STATE.md), [decisions](docs/DECISIONS.md),
[current task](docs/CODEX_TASK.md) and [engineering instructions](AGENTS.md).

D016: qualified = frozen deployed224 OR Evidence Score >=225 (inclusive).
D012 score weights/Audience150/ceiling1000 and D014 attribution are final.
Production data is owned by [production/](production/README.md); research PRs
#3/#4/#5 remain historical evidence. Movie-intel uses the production catalog.
Qualification informs Telegram. D017 synchronizes membership/score-band tags and
adds missing monitored Radarr records with search disabled.
The unknown-movie exact-release approval flow remains available.
See [Radarr sync runbook](deploy/RADARR_SYNC.md).
