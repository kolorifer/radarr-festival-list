# Engineering report: private Radarr snapshot bridge

**Specification:** [Assigned brief](2026-10-14-radarr-snapshot-bridge-brief.md).
**Result:** Implemented, merged and deployed; live private publication and connector read verified.
**Branch:** production/radarr-snapshot-bridge; implementation9e69bc2, validated handofff1660ee.
**PR:** [#8](https://github.com/kolorifer/radarr-festival-list/pull/8), merged at93a5761a9fe03d9470c3ab20270c12548ff46abf.
**Verification:** 2026-10-14, seedbox Python3.13.5. Subsequent documentation handoff preserves runtime bytes.

## What changed

The existing daily reconciliation exports/publishes only after successful
post-apply validation. No new timer, Radarr integration/credential store or
network ingress was added. Publication failure is reported separately, does not
repeat reconciliation, and does not change its successful exit status.
Manual snapshot-only mode performs GET/movie and GET/tag without reconciliation.

The dedicated private repository is kolorifer/radarr-state. Its only file is
[radarr-current.json](https://github.com/kolorifer/radarr-state/blob/main/radarr-current.json).
The publisher verifies repository name/privacy, updates that one file atomically
using its existing blob SHA, and checks the resulting bytes. Redirects and raw
HTTP error logging are refused. Normal GitHub commit versions remain; there is
no extra dated-file/history feature.

No existing seedbox GitHub authentication was available. The user supplied a
repository-limited token through a hidden Terminal prompt. Token and GitHub-only
configuration are mode600 under the existing private movie-intel config directory.
Existing Radarr credentials are reused unchanged; nothing sensitive enters this
public repository.

## Files/components

| File | Purpose |
| --- | --- |
| radarr_snapshot.py | Strict allowlist, validation, read-only export/private publisher |
| radarr_movie_list_sync.py | One nonfatal hook after successful reconciliation |
| deploy/radarr-sync.py | Snapshot-only mode reusing the existing private Radarr environment |
| deploy/setup-github-state.py | Hidden token input and private GitHub configuration |
| test_radarr_snapshot.py | 26 export/privacy/publisher/integration regressions |
| deploy/RADARR_SNAPSHOT.md | Configuration, validation and rollback |
| deploy/RADARR_SYNC.md | Existing daily-sync integration documentation |
| .github/workflows/movie-intel-test.yml | Implementation branch CI |
| docs/PROJECT_STATE.md, DECISIONS.md, CODEX_TASK.md | Verified completion and idle handoff |

## Acceptance evidence

| Criterion | Result |
| --- | --- |
| Live export count | 990, exactly matching GET/movie |
| IDs, monitoring/file flags, tag labels | Verified for every exported row |
| Schema/privacy | Exact allowlist and configured-secret/path checks pass |
| Read-only snapshot generation | Four audited Radarr requests: GET/movie and GET/tag twice; zero writes |
| Reproducibility | Repeated live exports identical except generated_at |
| Local privacy | Snapshot/config/token files mode600; outside public repository |
| Seedbox publisher | Successful live update and byte-for-byte GitHub readback |
| Existing GitHub connection | Private-file fetch succeeds; blob matches seedbox snapshot |
| Scheduler/reconciliation | Existing timer/unit bytes unchanged; success/failure hook regressions pass |
| Service/health | movie-intel active/running, same PID3062372, NRestarts0; local/public HTTP200 |

Schema v1 top-level fields: schema_version, generated_at, movie_count, movies.
Each movie contains only radarr_id, title, year, imdb_id, tmdb_id, monitored,
has_file, movie_file_id, date_added, tags.
UTC timestamps; movies sorted by Radarr ID; resolved labels sorted/deduplicated.
One pre-existing unrelated missing IMDb ID remains null; no identity is guessed.
Overview, filesystem/root paths, queue/releases/download clients and connection
details/credentials are excluded. No actual library rows are committed publicly.

## Tests run

133 complete unittest tests pass (107 existing +26 new) both in the isolated
implementation and after deployment. Cases include public-repository refusal,
unexpected schema/private text, unresolved tags, duplicate IDs, read-only export,
atomic private files, blob-SHA updates, readback verification, HTTP error/redirect
privacy, and actual sync CLI success/failure/dry-run integration.
Synthetic integration tests prove a publish failure never repeats Radarr writes.

pip check, configuration preflight, production_scoring.py --check and git diff
--check pass. Frozen result remains1909 candidates,224 grandfathered,163 new,387
qualified. CI Python3.12/3.13 passed: source38579787562 and handoff38580108197.
Deployed runtime passes the full suite again; no tests trigger a real download.

## Deployment

Recorded/backed up previous deployed458755a87d890e3273d6458c760e5fb6165cdfab,
source archive, private config and installed sync units under
~/.local/state/movie-intel/radarr-snapshot/deploy-backups/20261014T142703Z.
Switched the clean checkout to the validated merge while holding the existing
private sync lock. No service restart, daemon reload or manual apply was needed.
Existing movie-list-sync.timer remains active/waiting with daily03:43UTC plus
up to15min jitter; next scheduled run observed2026-10-15 03:51:13UTC.
The installed service already invokes the updated credential launcher.

Live deployed snapshot-only publication succeeded twice, and its private file
can be fetched through the user's GitHub connection. Current private commit
1f7dfb1cc39e10dff6697888b48602814051085e;990 records.
No Radarr mutation, acquisition command, import-list refresh, real notification
or download was deliberately triggered. Existing reconciliation, production
qualification, public feeds and Telegram/add-grab behavior remain unchanged.

The first naturally scheduled run of the new hook has not yet elapsed. Hook
placement/failure behavior is regression-tested; the actual deployed exporter/
publisher is live-verified independently without invoking Radarr reconciliation.

## Rollback

With no sync running, acquire the existing private sync lock and return the clean
deployed checkout to458755a87d890e3273d6458c760e5fb6165cdfab. No Radarr backup replay
or service restart is needed for this sync-only rollback. Leave the existing
timer and current Radarr state intact. New private snapshot/GitHub configuration
may remain; old code ignores it. Recheck service and local/public health.

## Findings and remaining risks

No unresolved implementation/access blocker. One pre-existing null IMDb record
is faithfully represented. Credential expiry/API failures can leave a stale
remote snapshot while ordinary reconciliation continues; publication status is
visible in the private sync report/journal. Keep radarr-state private: sanitized
library/title/tag data is still private user data. No new product rule was added.

## Handoff

D018 records this explicitly assigned bridge. Project state and task are updated;
CODEX_TASK is idle after successful deployment. Preserve D012/D014/D016/D017,
research PRs and the live Telegram add/grab verification report.
