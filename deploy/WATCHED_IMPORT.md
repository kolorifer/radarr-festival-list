# One-time watched state for the October 14 import

Authoritative private input:
kolorifer/radarr-state/watched-targets-2026-10-14-import.json, exactly87 targets.
This operation adds watched and turns monitoring off, without changing scores or
qualification. It has no scheduler.

```sh
.venv/bin/python deploy/radarr-sync.py --watched-import-only
.venv/bin/python deploy/radarr-sync.py --watched-import-only --apply \
  --expect-plan ~/.local/state/movie-intel/watched-import/dry-run.json
```

Exact matches must be unique. Every target must be proven newly added by the
private before/after D017 import audit, with original Radarr/IMDb/TMDb IDs and
addition timestamp intact, plus qualified catalog membership and existing Movie
List/score-band tags. Missing/ambiguous/out-of-cohort targets stop before writes.
A recorded clean plan and fresh full-state guard precede apply.

The existing watched-only client supports additive tags. Monitoring-off uses a
separate guarded operation with a fresh full-row check and exact target IDs:
PUT/movie/editor with only movieIds and monitored=false. Already unmonitored
rows are skipped. There is no true/enable-monitoring parameter or code path.
The normal sync client's write restrictions remain untouched.
Radarr's [editor resource](https://github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Movies/MovieEditorResource.cs)
and [controller](https://github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Movies/MovieEditorController.cs)
support nullable monitoring changes while omitted settings/tags remain unchanged.

Verify all other movie fields/tags and non-target movies, require zero pending
changes, then deduplicate/merge the cohort into the private canonical manifest
using its current blob SHA and verify readback. Preserve the cohort file as
provenance. Immediately refresh the private current-state snapshot.
CLI/public reporting is aggregate-only; private plans/manifests/before-after/write
audits live under ~/.local/state/movie-intel/watched-import, mode600.

On partial application or GitHub publication failure, obtain a new clean dry-run;
already-correct targets are skipped. Do not blindly repeat a stale write plan.
The shared sync lock prevents overlap with the existing daily job. Normal
reconciliation preserves monitored=false on existing films and watched tags as
unrelated user tags.

Code rollback uses the previous recorded revision with sync idle/lock held.
Keep verified watched/unmonitored user state. Changing those annotations back
requires an explicit user instruction; no automatic movie/file deletion,
monitoring-on or tag removal is part of rollback.
