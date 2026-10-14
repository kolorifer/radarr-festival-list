# Watched-state pass for the 2026-10-14 Movie List import

Status: **Assigned**

## Goal

Apply the user's completed watched classification to the newly imported Movie List cohort.

The authoritative target set is private:

- repository: `kolorifer/radarr-state`
- file: `watched-targets-2026-10-14-import.json`
- expected cohort size: **87**
- identity rule: **exact IMDb ID only**
- desired Radarr state for every target: additive `watched` tag + `monitored=false`

Do not put private watched IDs/titles into public reports.

## Semantics

`watched` is user state, not a scoring or qualification signal.

A watched Movie List title:

- remains in Radarr for information;
- remains eligible/qualified in the Movie List catalog;
- keeps `movie-list` and its managed score-band tag;
- is unmonitored so it is not acquired again;
- must not influence scoring, ranking, qualification or source logic.

The normal Movie List reconciliation already protects `monitored` on existing movies and performs tag-only updates for existing records. Preserve that behavior and add a regression test proving an existing qualified movie with `monitored=false` remains unmonitored during normal reconciliation.

## Required safety rules

Before any Radarr write:

1. Load the private 87-target cohort manifest.
2. Take a fresh live Radarr snapshot.
3. Resolve every target by exact IMDb ID to exactly one existing movie.
4. Require zero missing, duplicate or ambiguous targets before writes.
5. Verify every target belongs to the intended newly imported Movie List cohort or otherwise explain/stop before writes.
6. Produce a dry-run summary with aggregate counts only.

If any identity cannot be proven exactly, stop before mutation and report privately/local only.

## Allowed changes

For the exact target set only:

- add existing `watched` tag (create only if somehow absent);
- set `monitored=false` when currently true.

Preserve exactly:

- all unrelated tags;
- `movie-list` and managed score-band tags;
- movie files / `movieFileId` / `hasFile`;
- root folder, path, quality profile, minimum availability and metadata;
- all non-target movies.

Do not:

- remove `watched` from any movie;
- add/delete movies;
- delete/move files;
- trigger searches, release grabs, downloads, imports or acquisition commands;
- refresh import lists as part of this operation.

## Implementation constraints

Keep the write surface narrow and explicit. The current Movie List API wrapper intentionally allows tag-only editor mutations for existing movies. If monitored-state mutation needs a new code path, implement the smallest guarded operation possible:

- only `monitored: true -> false`;
- only for IDs resolved from the exact private watched manifest;
- no `false -> true` support in this task;
- no changes to any other movie field;
- verify the full movie guard before and after mutation;
- resumable/idempotent after partial application.

Do not weaken the existing general write restrictions.

## Persistent watched manifest

After a fully verified Radarr apply, merge the 87-target cohort into the private canonical `watched-targets.json` by exact IMDb ID, deduplicated. Preserve the cohort manifest as provenance.

Validate and report aggregate counts for:

- prior canonical watched count;
- cohort count;
- overlap count;
- resulting canonical watched count.

Do not publish watched identities publicly.

## Execution sequence

1. Tests for manifest validation, monitored-off guard, unrelated-field preservation, idempotence and normal-sync preservation of `monitored=false`.
2. Fresh live snapshot.
3. Dry-run with aggregate counts.
4. If clean, **apply without another approval**.
5. Reread all targets live and require:
   - every target has `watched`;
   - every target has `monitored=false`;
   - all pre-existing unrelated tags remain;
   - files/settings/metadata unchanged.
6. Run a second dry-run and require zero pending changes.
7. Merge/update private canonical `watched-targets.json` only after successful verification.
8. Refresh/publish private `radarr-current.json` immediately after apply.
9. Run/verify the normal Movie List dry-run against the post-change state and prove it does **not** try to re-monitor watched existing movies.
10. Leave the existing scheduler unchanged.

## Completion report

Public completion report: aggregate counts and safety assertions only. No private watched IDs or titles.

On success, return `docs/CODEX_TASK.md` to Idle and link the completion report.
