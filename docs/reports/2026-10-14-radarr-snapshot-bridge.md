# Engineering report: private Radarr snapshot bridge

**Specification:** [Assigned brief](2026-10-14-radarr-snapshot-bridge-brief.md).
**Result:** Implemented and tested; deployment/publication pending private seedbox GitHub credential.
**Branch:** production/radarr-snapshot-bridge, based on main65d1b8b.
**Implementation:** 9e69bc2937d02dd1e7eef56af689c089e1bff58e.
**Draft PR:** [#8](https://github.com/kolorifer/radarr-festival-list/pull/8).
**Verification:** 2026-10-14, existing seedbox Python 3.13.5.

## What changed

A strict allowlist exports current Radarr movies and resolved tag labels. The
existing reconciliation calls it only after successful post-apply validation.
Publication failure is recorded separately and does not retry reconciliation or
change its successful exit status. The existing timer/service and Radarr write
surface are unchanged. Manual snapshot-only mode performs just GET/movie and
GET/tag, without running reconciliation.

GitHub publication is confined to kolorifer/radarr-state, verifies that repository
is private, atomically updates radarr-current.json with its prior blob SHA, and
checks the read-back bytes. Redirects and raw HTTP error logging are refused.
One current file is overwritten; GitHub retains normal commit versions, without
additional dated snapshot files or a separate history feature.

## Files/components

| File | Purpose |
| --- | --- |
| radarr_snapshot.py | Allowlist, validation, read-only export and private publisher |
| radarr_movie_list_sync.py | One nonfatal hook after successful reconciliation |
| deploy/radarr-sync.py | Snapshot-only mode using existing private Radarr environment |
| deploy/setup-github-state.py | Hidden token input; private GitHub configuration |
| test_radarr_snapshot.py | 26 privacy/export/publisher/integration regressions |
| deploy/RADARR_SNAPSHOT.md | Configuration, validation and rollback |
| deploy/RADARR_SYNC.md | Existing sync integration documentation |
| .github/workflows/movie-intel-test.yml | Implementation branch CI coverage |

## Tests and acceptance evidence

133 complete unittest tests pass (107 existing +26 new). pip check, deployment
preflight, production_scoring.py --check and git diff --check pass.
Frozen scoring remains 1,909 candidates,224 grandfathered,163 new,387 selected.

Live read-only verification exported 990 movies, exactly matching GET/movie.
Every row's monitoring/file flags, IDs and resolved labels match the source.
Two exports of unchanged Radarr state are identical except generated_at.
Four recorded requests: GET/movie and GET/tag twice; zero Radarr writes.
Local snapshot has mode600, outside every repository. Private verification stays
under ~/.local/state/movie-intel/radarr-snapshot/verification.json.
Strict schema and configured-secret/path screening passed.
One existing missing IMDb ID remains null; it is not guessed.

Top-level fields: schema_version, generated_at, movie_count, movies.
Movie fields: radarr_id, title, year, imdb_id, tmdb_id, monitored, has_file,
movie_file_id, date_added, tags. No Overview, filesystem/root paths, queue,
releases, downloader details or server/credential fields are exported.

The existing GitHub connection can access kolorifer/radarr-state; its visibility
was independently verified private. The initial sanitized file was published through the GitHub connection at
8a4fca6891e985b8fdf9ff6709159e22a5ec0881. Connector fetch returned identical
bytes and all990 rows. Seedbox publisher authentication remains pending.
PR #8 CI run38579787562 passed on Python3.12 and3.13.

## Deployment and remaining access

Current deployed checkout remains 458755a. No service or timer was changed or
restarted, and no reconciliation/apply was run for this task.
The seedbox has no pre-existing GitHub credential/helper/key. Daily publishing
requires a repository-limited Contents read/write token entered privately through
deploy/setup-github-state.py. The repository connector itself cannot supply a
credential to an unattended seedbox process.

After private credentials are available: test seedbox snapshot-only --publish,
reverify connector file access/content, merge validated implementation, back up current
revision and private sync configuration, switch the clean deployed checkout,
verify unchanged scheduler and movie-intel health. Do not manually trigger an
apply or a real download to validate snapshot export.

Rollback uses recorded previous revision458755a; no Radarr restoration is needed
because snapshot generation makes no writes. Leave current private Radarr state
and existing daily timer intact.

## Unexpected findings / risks

One unrelated existing Radarr record has no IMDb ID, faithfully represented null.
The snapshot's allowed library/title/tag data is private user data even after
sanitization; never make the destination repository public.
GitHub credential expiry/API failures leave the prior remote snapshot stale while
ordinary reconciliation continues. Failed publication is visible in its private
sync report/journal. No production scoring, feeds or Telegram behavior changes.

## Handoff

Keep docs/CODEX_TASK.md active until deployment and private-file connector
verification are complete. Preserve the live Telegram add/grab report and research
PRs. This report will be updated with actual deployed/PR revisions and publication
verification before declaring completion.
