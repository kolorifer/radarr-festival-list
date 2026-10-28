# Repository status and review map

## Actor identity fixes — 28 October 2026, 19:22 UTC

The running actor is now **`d7487700ee8bb6eed86adefeca365945ecccc001`**,
a minimal patch on `46cccea3`. [PR #107](https://github.com/kolorifer/radarr-festival-list/pull/107)
contains the equivalent patch for main: contextual five-letter typos, NFO Length
parsing and owner-approved bounded runtime variation. Both reviewed occurrences
are verified; health is 200 and the actor has zero restarts. The collector-only
update below and the separate shadow runtime were preserved. The main-only retry
display improvement from #96 is still not part of this actor deployment.
[Validation and deployment report](reports/2026-10-28-contextual-typos-runtime.md).

## Collector-only deployment — 28 October 2026

PR #105 merged at `55f22402be9a4001f913677587aade203f49ac3f`. Only its
`identity_triage_store.py` was deployed at 18:47 UTC. The actor remains clean at
`46cccea3a119ca080e35f6cf071bd0351eba037a`, without a restart; shadow runtime
`4db4e38` and its active timer/configuration are unchanged. Collector and actor
health, database integrity, 77 host tests and confined synthetic concurrency
checks passed. No production POST, download or Telegram test was triggered.
See the [deployment report](reports/2026-10-28-collector-sqlite-deployment.md).

## Consolidation snapshot — 28 October 2026

The validated main baseline before this status update is `6c8129d7042a444920a2400054774955a06ad48e`.
The status-update merge itself advances `main`; use `git rev-parse origin/main`
or the repository's GitHub branch view for its current revision. The running
actor was last verified at `46cccea3a119ca080e35f6cf071bd0351eba037a` in the
previous session; its current state has not been checked during consolidation.
Main is not a deployment claim. The separate shadow worker has not been
rechecked. No deployment or live acquisition was performed during this work.

| Original PR or branch | Contribution and disposition |
| --- | --- |
| #1 | Handoff instructions, archive, templates and original deployment report retained as a historical snapshot; closed after #102. |
| #2 | Audience-cap comparison, code, tests and frozen outputs retained by #102; no production cap selected. |
| #3 | Identity-integrity research, corrections, tests and original data retained by #102; no production identity policy changed. |
| #4 | Qualification calibration, policies, tests and artifacts retained by #102; no threshold chosen. |
| #5 | P225/P250 comparison, source tree, tests and frozen results retained by #102; no threshold chosen. |
| #16 | Original public legacy audit preserved alongside the later second pass by #99; detailed private evidence was not accessed. |
| #78 | Offline and shadow identity scoring, tests, reports and decisions preserved by #101; earlier files preserved by #103. |
| #90 | Cut discovery research and tests preserved by #101; its earlier files preserved by #103. Depends on #78. |
| #92 | Shadow evidence recovery and bounded scheduling code and reports preserved by #101/#102. Depends on #90. The shared daily-budget implementation is retained as inert source, not applied to the live recurring store. |
| #88 | All three Live Movie Score worker packets and their public reports preserved by #99; rating/source permissions and product choices remain unresolved. |
| `automation/launcher-quota-repair` | Validated account-provided quota windows and associated tests merged by #100; no worker was launched here. |
| `investigation/issues55-56-readonly` | Incident reports and synthetic tests preserved by #102; one test updated for later research-only routing. |
| `movie-intel`, simulation and audience-sensitivity branches | Frozen historical branch trees retained by #103; `noop` shares the audience-sensitivity head. |
| #79, #82–#85, #87, #89, #91 | Previously closed as superseded after deployed runtime changes and later reports were accounted for in #96/#97. |

The original ten open PRs were closed as superseded only after their identified
content was retained on `main`; the original branches remain available. The
integration PRs above target `main`. Research snapshots preserve earlier code,
outputs and decisions as historical material, with no scheduler or workflow
activated. Full details and limits are in the
[consolidation report](reports/2026-10-28-repository-consolidation.md).

The collector SQLite contention identified during consolidation is now addressed
by a bounded per-Store writer queue; the regression fails on the old code and
passes on the fix. External-lock and overload backpressure remain explicit.
It was initially merged without deployment; the later collector-only activation
is recorded above. See the
[implementation and regression report](reports/2026-10-28-collector-locks.md).

---

## Historical status map — prior to this consolidation

The following section is retained as dated context. Its branch heads and PR
states are historical, not the current inventory.


Snapshot: **28 October 2026**. The integration PR that contains this update
brings the deployed actor revision into the main branch history while preserving
main-only collector and documentation changes. The resulting integration commit
is not automatically deployed. The inventory and divergence figures below
describe the earlier audit snapshot, before that integration; verify current PRs,
Git revisions and service health before acting. This document does not update itself.

## Current review state — 28 October 2026

[PR #96](https://github.com/kolorifer/radarr-festival-list/pull/96) merged the
production actor lineage into `main` at `ee8c29e`. Its independently reviewed
retry-display improvement is in `main` but **not deployed**; the running actor
remains `46cccea`. Main also retains its own collector and other changes, so the
integration commit is not identical to the production checkout. A deployment
requires its own decision and validation.

Eight duplicate deployed-work PRs were closed as superseded after their runtime
changes and later reports were accounted for: #79, #82, #83, #84, #85, #87,
#89 and #91. The remaining open work at this snapshot is:

- **Shadow identity and cut research:** [#78](https://github.com/kolorifer/radarr-festival-list/pull/78),
  [#90](https://github.com/kolorifer/radarr-festival-list/pull/90), and
  [#92](https://github.com/kolorifer/radarr-festival-list/pull/92), all draft.
  Their research findings are separate from production identity policy.
- **Worker outputs awaiting disposition:** [#88](https://github.com/kolorifer/radarr-festival-list/pull/88)
  and [#16](https://github.com/kolorifer/radarr-festival-list/pull/16), ready for review.
- **Earlier handoff and research drafts:** [#1–#5](https://github.com/kolorifer/radarr-festival-list/pulls),
  which require individual review before closing or merging.

Two separate CI runs encountered SQLite lock timeouts in concurrent collector
store tests; reruns passed. This deserves investigation and does not prove that
concurrent intake can never encounter backpressure. See the
[integration report](reports/2026-10-28-main-production-integration.md).

The audit map below records the earlier 18-PR snapshot; its open/closed states
are historical. Use the live GitHub PR list for current status.

## What is running?

The `movie-intel` production actor was verified at
`46cccea3a119ca080e35f6cf071bd0351eba037a`; its checkout was clean, the service
active, restart count zero and local health HTTP 200 with 1,909 catalog movies.
This revision includes the verified short-title typo improvement, watched-tag
presentation, tracker-conflict recheck and the earlier Grab Anyway improvements.
It does not imply that every open PR head, its subsequent documentation, or any
research branch is deployed.

The last deployment evidence for the separate shadow research worker is recorded
in [PR #92](https://github.com/kolorifer/radarr-festival-list/pull/92). Its
runtime and current operational status were **not rechecked** for this snapshot.
Shadow results are research, not production identity or download decisions.

## Why are deployment and GitHub different?

`main` was `8458c8de538b98e96deb48a280d940adba21b949` at the snapshot; it is not
the deployed actor revision. Since their common ancestor, each branch contains
commits the other does not (74 on `main`, 32 on the production lineage). Some
changes may be equivalent under different commits: these counts are not a count
of missing features. A read-only merge simulation reported conflicts, including
`movie_intel_service.py`, `identity_retry.py`, `tmdb_resolver.py` and
`alternative_grab.py`. Do not deploy `main`, overwrite either tree with the
other, or blindly merge them to reconcile this status.

A PR can be open even when its runtime code was deployed. Several PRs target
`runtime/*-baseline` branches to isolate already-deployed changes; a merge into
one of those branches is **not** a merge into `main`. For example,
[PR #94](https://github.com/kolorifer/radarr-festival-list/pull/94) is merged
into `runtime/short-title-typos-baseline`; its runtime is deployed, but this
merge alone did not bring the change into `main`.

## Historical review map (before integration cleanup)

| PRs | Purpose | State at snapshot |
| --- | --- | --- |
| [#91](https://github.com/kolorifer/radarr-festival-list/pull/91) | Watched-tag notification presentation | Open, ready; runtime commit is an ancestor of the deployed actor. |
| [#89](https://github.com/kolorifer/radarr-festival-list/pull/89) | Recheck tracker identity conflicts | Open, draft; deployed actor includes its runtime commit; PR head includes later changes. |
| [#87](https://github.com/kolorifer/radarr-festival-list/pull/87) | Source and runtime identity safeguards | Open, ready; deployed actor includes the runtime change. |
| [#85](https://github.com/kolorifer/radarr-festival-list/pull/85), [#84](https://github.com/kolorifer/radarr-festival-list/pull/84), [#83](https://github.com/kolorifer/radarr-festival-list/pull/83) | Retry presentation, remembered identities and Grab Anyway recovery | Open, ready; runtime changes are in the deployed actor lineage. |
| [#82](https://github.com/kolorifer/radarr-festival-list/pull/82), [#79](https://github.com/kolorifer/radarr-festival-list/pull/79) | Topic routing and retry message updates | Open, drafts; production includes their corresponding runtime changes. |
| [#92](https://github.com/kolorifer/radarr-festival-list/pull/92), [#90](https://github.com/kolorifer/radarr-festival-list/pull/90), [#78](https://github.com/kolorifer/radarr-festival-list/pull/78) | Evidence research and cut discovery | Open, drafts; PR descriptions record shadow deployments. They do not authorize activating scoring for production. |
| [#88](https://github.com/kolorifer/radarr-festival-list/pull/88), [#16](https://github.com/kolorifer/radarr-festival-list/pull/16) | Worker-loop outputs | Open, ready; inspect the issue and private evidence before deciding disposition. Deployment is not established here. |
| [#1–#5](https://github.com/kolorifer/radarr-festival-list/pulls) | Earlier handoff and research branches | Open, drafts; historical work requiring individual disposition. |

There were 18 open PRs when this snapshot was made, before any PR for this status
map. “Ready” and “draft” are GitHub states, not independent code approvals.

## Historical integration plan

1. Independently review the deployed actor changes against current `main`,
   preserving both main-only work and the verified production behavior.
2. Prepare a single integration PR on top of current `main`, resolve each
   conflict deliberately, and test the resulting tree. Track which existing
   runtime PRs are included by code/content, not merely by commit ancestry.
3. After review and verification, merge that integration PR. Only then reconcile
   individual PRs and branches according to their actual content. Preserve the
   separate shadow research until its disposition is agreed.
4. Update this map and deployment report whenever a merge or deployment changes
   either revision. Deploy only a separately verified runtime revision.

This is a review and integration plan, not an authorization to activate research,
change acquisition policy, delete branches or modify production state.
