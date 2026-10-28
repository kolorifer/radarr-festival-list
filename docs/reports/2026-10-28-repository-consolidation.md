# Repository consolidation — 28 October 2026

## Scope and result

The main baseline before this documentation update is
`6c8129d7042a444920a2400054774955a06ad48e`. The complete disposition table,
including the original ten open PRs and the independently discovered branches,
is in [Repository status](../REPOSITORY-STATUS.md). The merge of this status
update advances main, so use the GitHub main branch or `git rev-parse origin/main`
for its exact current revision. No branch or local checkout was deleted.

- #99 preserves all public #88 research files and the original #16 public audit.
  Their changed content was compared against the source heads after merge.
- #100 integrates the local launcher quota repair, preserving fail-closed quota
  handling, locking and reservation tests. It was not installed or run as a worker.
- #101 preserves the final isolated identity and cut research. The separate
  daily recurring-budget version changes a shared module, so its exact original
  source and tests remain inert historical files; the current shared weekly
  budget remains unchanged. #103 also preserves the intermediate #78/#90
  changed files, and #102 preserves their final project-state history.
- #102 preserves the #1–#5 historical handoff and research trees and the
  issues 55–56 incident report and tests. #103 additionally preserves earlier
  movie-intel, simulation and audience-sensitivity branch trees. Snapshot files
  were checked against the source Git blob IDs; original historical task files
  and nested workflows are archival, not active assignments or workflows.
- The decision formerly labeled D036 in the shadow branch is distinguished as
  Shadow D036 because main already uses D036 for watched notifications. The
  original branch records remain unchanged in the snapshots.

The original ten PRs were closed as superseded after their identified unique
content was verified on main. None was closed merely because it was a draft.
The original branches remain. The latest PR and branch state should still be
checked before future changes; repository status does not update itself.

## Verification

Python 3.12: 780 current-tree tests for #99, 786 for #100, 899 for the final
#101 head, and 907 for #102 passed, with two platform skips each. Focused
research tests: 52 worker, 113 shadow, 120 historical-tree and eight adapted
incident tests passed; worker artifact byte checks also passed. Python 3.12 and
3.13 CI passed on the exact final heads of #99, #100, #101, #102 and #103.
The first sandboxed 780-test run had 44 errors from denied local HTTP sockets;
it was rerun successfully with local loopback access. Documentation and diff
checks passed. #103 added inert snapshots; its CI tested the current tree.

Two earlier CI runs had SQLite `database is locked` errors in concurrent
collector tests. The store defaults to a 250 ms SQLite lock timeout, a plausible
source of backpressure but not an established root cause. A local stress run of
both affected tests (200 executions) passed; the intermittent issue remains
unresolved. Tests were not weakened and no runtime timeout was changed.

## Deployment and outstanding decisions

No production, Radarr, Telegram, downloader, service or shadow-worker access was
performed. The last actor verification was historical: `46cccea3a119ca080e35f6cf071bd0351eba037a`,
healthy at that time. Main contains additional changes and is not asserted to
be deployed. Shadow scoring and cut results remain research, with no automatic
identity or acquisition authority. Source rights/access for the score research,
product acceptance, and any future shadow adaptation or deployment remain
separate decisions. The unrelated `docs/CODEX_TASK.md` assignment was preserved.
