# Radarr Movie List membership + score-band sync brief

Status: **Assigned for implementation.**

## Product decision

The production D016 catalog remains authoritative. Radarr should now reflect current Movie List qualification directly.

For every currently qualified film in `production/movie-catalog.json`:

- ensure the Radarr movie has the membership tag `movie-list`;
- ensure it has exactly one managed score-band tag based on current `overall_score`;
- if it is missing from Radarr, add it as monitored with the same two managed tags;
- do **not** trigger an automatic movie search/download during this sync.

Existing Radarr movies that are in the qualified catalog must be tagged retroactively. Existing unrelated tags, root folders, quality profiles, monitoring state and files must be preserved.

The exact numeric Evidence Score remains authoritative in the production catalog. Do **not** create one tag per exact score and do **not** overwrite Radarr `Overview`/description metadata.

## Managed tags

Membership:

- `movie-list`

Exactly one score band for every qualified movie:

- `ml-below-225` for qualified grandfathered films with score <225;
- `ml-225-249` for 225 <= score <250;
- `ml-250-299` for 250 <= score <300;
- `ml-300-399` for 300 <= score <400;
- `ml-400-plus` for score >=400.

Use the full production `overall_score` for boundaries, not a rounded integer display value.

These names are managed by this project. If a qualified movie already has a stale managed score-band tag, replace only the managed band tag with the correct one. Preserve all unrelated Radarr tags.

If a non-grandfathered film ceases to qualify in a future production catalog, remove `movie-list` and any managed `ml-*` score-band tag from that existing Radarr movie, but do not delete it, unmonitor it, change its profile/root, remove files, or search it. Grandfathered D016 members remain qualified by definition.

## Initial reconciliation behavior

Implement a deterministic, idempotent Radarr sync command with at least:

- dry-run mode with zero writes;
- apply mode;
- machine-readable summary/report output;
- safe repeated execution.

Before the first production write, run the dry-run against the live Radarr instance and record:

- qualified catalog total (expected 387 with the current frozen catalog);
- already in Radarr and already correctly tagged;
- already in Radarr but needing membership and/or band tags;
- qualified films missing from Radarr and eligible to be added;
- lookup failures/identity ambiguities;
- any previously managed movies that now require managed-tag removal;
- exact tag create/reuse plan;
- root folder / quality profile intended for newly added movies.

If identity resolution is ambiguous, skip that movie and report it. Prefer exact IMDb identity; use Radarr's IMDb lookup and verify the returned IMDb/TMDb identity before adding. Do not guess by fuzzy title/year matching.

After a clean dry-run, apply the reconciliation without waiting for another routine approval, provided all safety invariants below hold. Stop before writes and report if the dry-run reveals an unresolved product/configuration choice, especially an ambiguous root folder or quality profile for new movies.

## Adding missing movies

For missing qualified movies:

- add to Radarr as monitored;
- `searchForMovie` / equivalent must be false;
- attach `movie-list` and the current score-band tag;
- do not issue a general search command after add;
- do not trigger downloader activity;
- preserve the existing Telegram exact-release approval flow separately.

Determine the root folder and quality profile from the user's existing live Radarr conventions/configuration. Reuse a single unambiguous existing convention rather than inventing a new one. If there are conflicting plausible profiles/root choices, stop before the add phase and report the exact choice required. Never modify profile/root on movies already present in Radarr.

## Updating existing movies

Use Radarr's supported movie/tag API. For existing matching movies:

- add `movie-list` without replacing unrelated tags;
- remove only stale managed score-band tags;
- add the one correct managed score-band tag;
- preserve all other fields;
- do not move files.

Use bulk operations where safe, but batch writes and verify returned state. A partial failure must be resumable/idempotent.

## Ongoing synchronization

Make the sync reusable for future catalog changes. Integrate it with the existing operational model using one safe scheduler/path only:

- preferably hook it to the canonical production catalog refresh/deployment path if such a path already exists;
- otherwise install a lightweight periodic reconciliation (for example daily) using the existing user-level service/timer conventions.

Do not create duplicate schedulers. Report the exact mechanism and cadence selected.

A future catalog refresh should therefore:

- add/tag newly qualified movies;
- update score-band tags when scores cross a band;
- remove only this project's managed tags from films that cease to qualify;
- never automatically delete movies or trigger searches/downloads.

## Exact score presentation

The exact Evidence Score remains in `production/movie-catalog.json` and may continue to be used by Movie List/Telegram/reporting surfaces.

Do not:

- create `score-233.08` / one-tag-per-score tags;
- modify Radarr `Overview`/description to inject our score;
- use Radarr metadata fields that can be overwritten by metadata refresh as project storage.

## Safety invariants

The initial apply is authorized to add missing qualified movies and modify managed tags, but **not** to trigger acquisition.

Must remain zero during this task unless required to create/update the Radarr movie records themselves:

- automatic movie searches;
- release grabs/download pushes;
- import-list refreshes solely to force acquisition;
- movie deletions;
- file deletions/moves;
- quality-profile changes on existing movies;
- root-folder changes on existing movies;
- monitoring-state changes on existing movies;
- unrelated tag removal.

Preserve provider-managed Radarr boundaries and all secret-handling rules.

## Required tests

Add regressions for at least:

1. dry-run performs no writes;
2. repeated apply is idempotent;
3. qualified existing movie receives `movie-list` while unrelated tags survive;
4. stale managed score band is replaced and only one managed band remains;
5. exact band boundaries: <225, 225, 250, 300, 400;
6. grandfathered score <225 receives `ml-below-225`;
7. qualified missing movie is added monitored with `searchForMovie=false` and correct tags;
8. ambiguous/failed IMDb lookup is skipped, not guessed;
9. non-qualified formerly managed movie loses only project-managed tags;
10. no movie delete/file move/search/download command is emitted;
11. current frozen catalog still yields 387 qualified and every qualified film maps to exactly one score band;
12. Telegram/add-grab and D016 scoring tests remain green.

Mock Radarr API operations for unit/integration tests. Do not create a real download to prove the sync.

## Deployment / first live run

Implement from current `main` after D016 (`b8e2634...` or later).

Create a dedicated implementation branch and PR. Run complete CI plus seedbox tests/preflight.

For the first live execution:

1. back up/record current revision and relevant Radarr tag/movie state needed for rollback;
2. perform live dry-run and preserve a redacted summary artifact;
3. verify the expected write plan and configuration invariants;
4. apply membership/band tagging and add missing qualified movies with search disabled;
5. run the sync again in dry-run mode and require zero remaining changes, except explicitly documented unresolved lookup failures;
6. verify no unexpected queue/download/search activity;
7. verify representative existing, newly-added, grandfathered-below225 and high-score movies in Radarr;
8. install/activate the selected ongoing sync mechanism only after the one-shot reconciliation is proven idempotent.

If the planned add count or live state differs materially from the dry-run between steps, stop and reconcile before continuing.

## Documentation / completion report

Update:

- `docs/DECISIONS.md` with implementation status for this decision;
- `docs/PROJECT_STATE.md` with the Radarr sync behavior and live reconciliation counts;
- `docs/CODEX_TASK.md` to idle after successful completion;
- create an engineering/deployment report and machine-readable verification summary.

Completion report must include:

- branch / PR / merge / deployed revision;
- tests and CI;
- dry-run counts;
- number of existing Radarr movies tagged;
- number of missing qualified movies added;
- number of unresolved/ambiguous movies, with identities only (no secrets);
- score-band distribution actually applied;
- created/reused Radarr tag IDs/names;
- root/profile used for new additions and why it was unambiguous;
- proof `searchForMovie=false` / zero acquisition commands;
- second dry-run showing idempotence;
- ongoing sync mechanism/cadence;
- rollback plan/result;
- confirmation unrelated tags/settings/files were preserved.
