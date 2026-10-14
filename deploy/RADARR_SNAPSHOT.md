# Private Radarr snapshot bridge

The existing daily Movie List reconciliation exports/publishes only after its
post-apply validation succeeds. It reuses the same Radarr environment and timer.
A failed export/publication is reported as snapshot_publication.status=failed;
reconciliation still returns success and is never automatically repeated.

## Private destination and credentials

Create **kolorifer/radarr-state** as a private repository. The destination name is
fixed; the publisher checks GitHub's private flag before sending any snapshot.
Grant the existing ChatGPT GitHub connection access to this private repository.

No seedbox GitHub credential existed during initial inspection. If an existing
GH_TOKEN/GITHUB_TOKEN is available through the private environment, it is reused.
Otherwise create a fine-grained GitHub token limited to **radarr-state**, with
Contents read/write and metadata read permissions:
[GitHub token instructions](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
Enter it only through the hidden prompt over an interactive SSH terminal:

```sh
cd ~/radarr-festival-list
.venv/bin/python deploy/setup-github-state.py
```

The setup writes ~/.config/movie-intel/github-state-token and
~/.config/movie-intel/radarr-snapshot.json with mode600. No additional Radarr
credential store is created. Keep a token expiry/reminder appropriate to the user;
an expired credential results in a failed publication without changing Radarr.

## Export and validation

Use the existing credential-reading launcher. Both commands perform only
GET/movie and GET/tag; neither reconciles or changes any Radarr record:

```sh
.venv/bin/python deploy/radarr-sync.py --snapshot-only
.venv/bin/python deploy/radarr-sync.py --snapshot-only --publish
```

Local snapshots are atomic replacements under
~/.local/state/movie-intel/radarr-snapshot/radarr-current.json, mode600.
Only sanitized fields enter the private repository's radarr-current.json.
The exporter rejects extra schema fields, duplicate Radarr IDs, unresolved tags,
invalid timestamps/flags and obvious private values in allowed text fields.
Missing IMDb IDs remain null. Tags are resolved labels, sorted/deduplicated.
Movies sort by numeric Radarr ID. Publication uses GitHub's atomic Contents API
with the existing file's blob SHA and verifies the resulting bytes.
Redirects are refused and exception payloads/credentials are never logged.

There is one current-state file, no dated exports or new scheduler. GitHub commits
naturally retain prior versions of that file; this does not provide a separate
snapshot-history feature. Keep the repository private and avoid making it public.

Schema v1 top-level: schema_version, generated_at, movie_count, movies.
Per movie: radarr_id, title, year, imdb_id, tmdb_id, monitored, has_file,
movie_file_id, date_added, tags. UTC timestamps; optional absent date/IMDb are null.
Overview, paths, roots, quality profiles, queue/releases/download clients and
server connection details are deliberately excluded.

## Rollback

Restore the previously recorded code revision (458755a for this iteration).
Do not replay Radarr backups: snapshot export makes no Radarr writes.
The unchanged movie-list-sync.timer/service then use the prior sync path.
The new private configuration/state may be retained; it is ignored by old code.
No movie-intel restart is needed for this sync-only code update.
