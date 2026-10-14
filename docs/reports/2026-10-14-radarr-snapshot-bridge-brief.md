# Radarr read-only snapshot bridge brief

Status: **Assigned for implementation.**

## Goal

Let ChatGPT inspect the user's current Radarr state for discussion and analysis without giving ChatGPT direct Radarr credentials or adding a second Radarr integration.

Reuse the already deployed Radarr Movie List sync and its existing private `RADARR_URL` / `RADARR_API_KEY` environment. Do not create a new Radarr scheduler, credential store, or network ingress.

## Architecture

After the existing daily Radarr reconciliation finishes successfully, export one sanitized current-state JSON snapshot and publish it to a **private GitHub repository** owned by the user, preferably `kolorifer/radarr-state`.

Initial design should keep only one file:

- `radarr-current.json`

No history is required initially. Overwrite the same file on each successful refresh.

If creating the private repository from the seedbox/Codex environment is not permitted, stop and ask the user for only that one manual action. Do not fall back to committing the snapshot to the public `radarr-festival-list` repository.

## Snapshot schema

Top-level object:

```json
{
  "schema_version": 1,
  "generated_at": "UTC ISO-8601 timestamp",
  "movie_count": 0,
  "movies": []
}
```

Each movie should contain only fields useful for read-only library discussion:

```json
{
  "radarr_id": 123,
  "title": "Example",
  "year": 2024,
  "imdb_id": "tt1234567",
  "tmdb_id": 12345,
  "monitored": true,
  "has_file": false,
  "movie_file_id": 0,
  "date_added": "UTC ISO-8601 timestamp",
  "tags": ["movie-list", "ml-250-299"]
}
```

Resolve tag IDs to tag labels in the export. Stable sort by Radarr ID or IMDb ID so diffs are deterministic.

## Privacy / safety boundary

The snapshot MUST NOT contain:

- Radarr URL or API key;
- any other secret/token/credential;
- filesystem paths or root-folder paths;
- download-client information;
- release/download queue data;
- IP addresses, hostnames, usernames or provider details;
- movie overview text or unrelated large metadata blobs.

This task is read-only with respect to Radarr. No new Radarr write endpoint may be added for snapshot generation.

Do not change any movie's monitored state, tags, files, quality profile, root folder, or metadata as part of this task.

## Integration

Piggyback on the existing deployed daily `movie-list-sync` path rather than adding another timer. Generate/publish the snapshot only after a successful reconciliation. A failed snapshot publish must not cause Radarr mutation or repeated reconciliation loops.

Use the seedbox's existing GitHub authentication if it already safely permits writing to the private repo. Do not print credentials to logs or add PATs/secrets to the public repository.

Atomic publication is preferred: write a temporary file locally, validate JSON/schema, then replace/push the target state.

## Validation

Before completion:

1. Generate a live snapshot from current Radarr.
2. Verify movie count equals the live `/movie` count used by the existing sync.
3. Verify representative movies preserve current `monitored`, `hasFile`, identifiers and tag labels.
4. Scan serialized JSON for obvious secret/config fields and paths.
5. Confirm snapshot generation made zero Radarr writes.
6. Confirm `radarr-current.json` exists in the private repo and can be fetched through the user's existing GitHub integration if that integration has access to the repo.
7. Run the snapshot/export twice against unchanged Radarr state and verify deterministic content except `generated_at`.
8. Keep the existing Movie List reconciliation behavior and scheduler unchanged.

## Completion report

Report:

- implementation/deployed revision;
- private state repository name (never credentials);
- live exported movie count;
- exact exported field list;
- proof no Radarr writes were introduced;
- proof no secrets/paths are present;
- whether ChatGPT's GitHub connector can already read the private repo. If not, state the single user authorization step required.

After successful deployment, set `docs/CODEX_TASK.md` back to idle with links to the implementation report.
