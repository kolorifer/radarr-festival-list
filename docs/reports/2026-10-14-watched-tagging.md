# Engineering report: additive watched tagging

**Specification:** [Assigned brief](2026-10-14-watched-tagging-brief.md).
**Result:** Implemented, deployed and applied; all acceptance checks pass.
**Branch:** production/watched-tagging; implementation15bed93ad4beee92e3a77c52ef918722f4473d1a.
**PR:** [#9](https://github.com/kolorifer/radarr-festival-list/pull/9), merged35dcdf044a0c9b85422beae38fcd0f549be5b040.
**Verification:** 2026-10-14, deployed seedbox Python3.13.5. Subsequent documentation handoff preserves runtime bytes.

## What changed

One-time CLI reads the authoritative private watched-targets.json using the
existing state-repository credential. It validates declared count, unique exact
IMDb IDs and exactly one existing Radarr movie per target. A recorded dry-run,
fresh full-state guard and shared sync lock precede any write.
Only watched-tag creation and additive movie-editor updates to verified target
movie IDs are supported. No watched tag is removed from any movie.

After tagging, re-read/verify all movie fields except the intended tag addition,
preserve every unrelated tag and all non-target movies, require a zero-change
post-plan, then immediately publish the existing private current-state snapshot.
The manifest, target IDs/titles, before/after states and operation payloads remain
private. Public output/reporting contains aggregate counts only.
No new recurring rule/scheduler, project watch-state schema, score or qualification
change was introduced.

## Files/components

| File | Purpose |
| --- | --- |
| radarr_watched_tags.py | Exact private manifest, dry-run, closed additive write surface and verification |
| test_radarr_watched_tags.py | 18 matching/privacy/idempotence/state-preservation regressions |
| deploy/radarr-sync.py | watched-only mode reusing existing private credentials |
| deploy/WATCHED_TAGGING.md | Private execution/recovery/runbook |
| .github/workflows/movie-intel-test.yml | Implementation branch CI |
| docs/PROJECT_STATE.md, DECISIONS.md, CODEX_TASK.md | Aggregate completed/idle handoff |

## Live result

| Check | Result |
| --- | --- |
| Manifest declared/unique target count | 271 /271 |
| Initial exact matches | 271;0 missing/ambiguous |
| Already watched before apply | 0 |
| watched tag | Created, tag ID9 |
| Target movies tagged | 271 |
| Writes | 1 POST/tag;1 PUT/movie/editor with applyTags=add |
| Other writes/acquisition | 0 movie adds/deletes/search/grab/download/import-list commands |
| Monitoring/files/settings/path/metadata | Every non-tag API field unchanged for every movie |
| Unrelated tags /non-target movies | Preserved unchanged |
| Second independent live dry-run | 271 already tagged;0 remaining/missing/ambiguous |
| Private Radarr snapshot | Refreshed immediately;990 rows |
| Existing GitHub connection | Private read confirms all271 targets tagged; blob matches seedbox |
| Existing timer/unit | Hashes unchanged; active/waiting |
| Movie-intel | Same active/running PID;NRestarts0;local/public health200 |

The write audit proves what this operation issued. It does not claim to suppress
Radarr's independent scheduled background jobs. No real notification or download
test was triggered.

## Tests run

151 full unittest tests pass both before and after deployment (133 existing +18
new). New cases cover exact-ID-only matching, missing/duplicate targets, manifest
count/uniqueness, duplicate watched tag, stale recorded plans and last-minute
drift, preserved monitoring/files/settings/Overview/tags, forbidden write paths,
non-target protections, idempotence and resume after timeout/publication failure.

pip check, configuration preflight, production_scoring.py --check, git diff
--check and private-ID/credential scans pass. Frozen catalog remains1909 films,
224 grandfathered +163 new =387 qualified. CI run38600803503 passed Python3.12/3.13.
All watch-target identifiers are confined to the private repository/host state.

## Deployment and recovery

Previous deployment98485677a9b423f82b636f37210799704eb7e966 was recorded and its source,
private config and installed units backed up under
~/.local/state/movie-intel/watched-tagging/deploy-backups/20261014T164629Z.
The clean checkout switched to the validated merge with the existing sync lock
held. No service restart, daemon reload or scheduler change was required.

Fresh dry-run and apply ran in a detached process so SSH loss could not interrupt
the operation. Private before/after/operation audit is under
~/.local/state/movie-intel/watched-tagging/backups/20261014T164724Z.
Completion/verification reports stay private under the same watched-tagging state.
The refreshed current snapshot is in the private state repository.

Rollback code to98485677a9b423f82b636f37210799704eb7e966 with sync idle/lock held.
Keep the additive watched user state: code rollback does not remove tags or replay
Radarr snapshots. Reverting user annotations would require explicit instruction
and selective removal based on the private before state, never wholesale tag
replacement. No movie/file deletion is part of recovery.

## Findings and handoff

No unresolved access/identity/deployment blocker. All targets were unambiguous.
The existing daily Movie List sync treats watched as an unrelated tag and
preserves it; this task does not add an automatic watched reconciliation rule.
Project state and D019 record completion, CODEX_TASK returns idle, and the live
Telegram add/grab report and earlier research/audit evidence are retained.
