# One-time private watched tagging

The authoritative manifest is private
kolorifer/radarr-state/watched-targets.json. No user target list belongs in this
public repository. This operation changes Radarr tags only, not project scoring
or watch annotations, and is not a recurring sync rule.

The existing private Radarr environment and GitHub state-repository credential
are reused. The credential launcher supports --watched-only:

```sh
.venv/bin/python deploy/radarr-sync.py --watched-only
.venv/bin/python deploy/radarr-sync.py --watched-only --apply \
  --expect-plan ~/.local/state/movie-intel/watched-tagging/dry-run.json
```

The first command is read-only and writes a private dry-run report. Apply requires
that recorded plan, validates the live state again before any write, and stops
on missing/ambiguous targets or drift. Only POST/tag with label=watched and
PUT/movie/editor with applyTags=add, the verified watched tag and exact target
movie IDs are allowed. The shared sync lock prevents overlap with the existing
daily job. No acquisition/movie-add/delete/replace-tag endpoint is supported.

After apply, re-read all movies and verify every non-tag API field and unrelated
tags are unchanged, all targets have watched, and the post-dry-run is zero-change.
Then immediately publish the existing sanitized private snapshot.
The CLI prints aggregate counts only. Private manifests, before/after states,
plans and attempted write audits live under
~/.local/state/movie-intel/watched-tagging with mode600 files.

An interrupted/failed apply can be resumed after a new clean dry-run; targets
already tagged are skipped. A failed GitHub publication does not undo or repeat
tagging. Publish manually through --snapshot-only --publish if necessary.
Never automatically remove watched from non-targets. No scheduler/unit changes.

Rollback code to the recorded previous revision with sync idle/lock held.
The additive watched user state should remain. If the user explicitly authorizes
reverting tags, use the private before snapshot to remove only tags this apply
introduced; never replace whole tag sets or delete movies.
