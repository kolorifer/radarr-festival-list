# Earlier shadow research versions

`historical-shadow-pr-78/` and `historical-shadow-pr-90/` retain each PR's
added or changed files at its exact original head, including superseded code,
tests, project state and decisions. These snapshots are historical data, not
current configuration, instructions, schedulers or production code. The later
working research tools and the historical daily-budget snapshot are under
`identity_scoring/`. The final #92 state and reports are preserved there and
in `docs/reports/`; its code and tests are integrated as research only.

Four additional complete historical branch trees are retained alongside these
snapshots: `historical-branch-movie-intel/` at `c7a4582`,
`historical-branch-simulation-4-multi-route/` at `67d4232`,
`historical-branch-simulation-4b-union-universe/` at `8363f93`, and
`historical-branch-audience-sensitivity/` at `f39d753`. The remote `noop`
branch has the same head as the last snapshot. These are frozen files, not
production deployment trees or enabled workflows. Every tracked file was
verified against its source Git blob.
