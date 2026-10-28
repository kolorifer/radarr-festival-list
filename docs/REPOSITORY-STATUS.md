# Repository status and review map

Snapshot: **28 October 2026**. The integration PR that contains this update
brings the deployed actor revision into the main branch history while preserving
main-only collector and documentation changes. The resulting integration commit
is not automatically deployed. The inventory and divergence figures below
describe the earlier audit snapshot, before that integration; verify current PRs,
Git revisions and service health before acting. This document does not update itself.

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

## Review map

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

## Safe path to a simpler repository

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
