# Radarr Movie List reconciliation

D017 uses the authoritative D016 catalog. Sync only movie-list and these five
score-band tags: ml-below-225, ml-225-249, ml-250-299, ml-300-399, ml-400-plus.

Use existing private credentials; no credentials appear in arguments/reports:

```sh
.venv/bin/python deploy/radarr-sync.py --dry-run --report ~/.local/state/movie-intel/radarr-sync/plan.json
.venv/bin/python deploy/radarr-sync.py --apply --expect-plan ~/.local/state/movie-intel/radarr-sync/plan.json --report ~/.local/state/movie-intel/radarr-sync/apply.json
.venv/bin/python deploy/radarr-sync.py --dry-run
```

Dry-run makes GET calls only. Apply verifies live state/catalog against the plan,
then uses only tag POST, movie POST and tag-only movie/editor PUT.
IMDb lookup and a separate TMDb lookup must agree on exact identifiers.
Ambiguous mappings are skipped and reported. Changed live state stops an apply.
Private per-run full snapshots and operation journals permit resumed reconciliation.

Missing films are added monitored, with searchForMovie=false, released availability,
the validated root/profile and both managed tags. Existing monitoring/root/profile/
path/files/Overview and unrelated tags are preserved. No search, release push,
download, import-list refresh, movie/file deletion or move is emitted.

Defaults must be unambiguous across the existing library or configured explicitly
in ~/.config/movie-intel/radarr-sync.json (600), with only root_folder and
quality_profile_id. The initial library uses one root and profile consistently.
The deployment records and freezes those validated choices in private config.
No new credentials or environment/unit changes for movie-intel are required.

After first apply and clean second dry-run, install exactly one timer:

```sh
install -m 644 deploy/movie-list-sync.service ~/.config/systemd/user/movie-list-sync.service
install -m 644 deploy/movie-list-sync.timer ~/.config/systemd/user/movie-list-sync.timer
systemctl --user daemon-reload
systemctl --user enable --now movie-list-sync.timer
```

It reconciles daily at03:43UTC plus up to15min random delay. Persistent=true
catches missed runs. A private flock prevents overlapping CLI/timer executions.
The oneshot has no retry-on-failure loop; inspect latest.json and journal status.
The existing catalog has no automatic collector/refresh hook; this timer is the
single reconciliation path and reads the current deployed catalog on every run.

Rollback: disable the timer first; restore the previous code revision while
preserving private action/cache state and movie-intel configuration.
Restore only project-managed tags from the private before.json snapshot using
movie/editor add/remove, preserving current unrelated tags and fields.
Added movie records remain; deleting them is outside this brief's safety boundary.
Never replay whole movie records or overwrite new private state over later activity.
No rollback was executed when deployment succeeds.

## Private read-only snapshot

After successful reconciliation, the same daily run exports/publishes the
allowlisted current state to a verified private GitHub repository. Publication
failure never repeats reconciliation. See [snapshot runbook](RADARR_SNAPSHOT.md).
