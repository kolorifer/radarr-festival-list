# Current Codex task

Status: **Assigned — apply watched-state correction for Rambo III (1988).**

User confirmed that **Rambo III (1988), IMDb `tt0095956`**, was watched and was missed during the previous watched classification.

Private source of truth for this correction:
- `kolorifer/radarr-state/watched-corrections.json`

Required actions:
1. Verify the current Radarr record resolves exactly to IMDb `tt0095956` / Rambo III (1988). Do not use title-only matching.
2. Add the existing `watched` tag to this exact movie.
3. Set `monitored=false` for this exact movie.
4. Preserve the movie file, quality/profile/root-folder settings, all unrelated fields, and any existing tags.
5. Merge `tt0095956` into the canonical private `watched-targets.json` manifest, updating its target count from 358 to 359 and preserving exact-IMDb-only semantics.
6. Run a second dry-run/idempotency check proving zero pending changes for this correction.
7. Refresh the sanitized private Radarr snapshot and verify Rambo III is `watched` + unmonitored afterward.
8. Do not add/delete movies, search/grab/download, delete files, or modify unrelated movies.
9. Add/update the implementation report and return this task file to Idle after completion.

Expected result: canonical watched count = **359**.
