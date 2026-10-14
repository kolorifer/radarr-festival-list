# Radarr watched-tag reconciliation brief

## Goal

Apply one additive Radarr tag, `watched`, to the exact movies the user classified as already watched during the October 14 library cleanup.

The authoritative target manifest is private:

- repository: `kolorifer/radarr-state`
- file: `watched-targets.json`
- schema: exact IMDb-ID list only

Do not copy the private target list into this public repository or into public logs/reports.

## Matching and safety

- Match targets by exact IMDb ID only.
- Before any write, take a fresh live Radarr snapshot and require every manifest IMDb ID to resolve to exactly one existing movie.
- If any target is missing, duplicated, or otherwise ambiguous, stop before writes and report only counts plus the specific problematic IDs through a private/local report.
- Create the `watched` tag only if it does not already exist.
- Add `watched` to target movies without replacing or removing any existing tags.
- Do not remove `watched` from any non-target movie in this task.
- Preserve monitored state exactly as-is.
- Preserve files, movieFileId, root folder, quality profile, path, minimum availability, metadata/Overview and all unrelated tags.
- No movie add/delete, file delete/move, search, release grab, download push, import-list refresh or acquisition command.
- The operation must be idempotent and resumable.

Use the existing deployed Radarr credentials/client and the supported tag/movie-editor API path already used by the Movie List reconciliation. Prefer a tag-only bulk/editor operation if it preserves unrelated tags; verify returned/live state afterwards.

## Required execution

1. Read the private manifest and validate its declared count and uniqueness.
2. Fetch live Radarr movies/tags.
3. Produce a private/local dry-run summary: target count, already tagged, to-tag, missing/ambiguous, tag create/reuse plan.
4. If the dry-run is clean, apply without another routine approval.
5. Re-read live Radarr and require every target to carry `watched`, with zero changes to monitored/file/settings fields.
6. Run the dry-run again and require zero remaining changes.
7. Refresh/publish the existing private `radarr-current.json` snapshot immediately after the apply so ChatGPT can verify the result.
8. Keep the existing daily scheduler unchanged; this is a one-time user-state tagging operation, not a new recurring sync rule.

## Reporting

Create a concise completion report in this public repo containing implementation/deployment status and aggregate counts only. Do not list the watched titles/IMDb IDs publicly. Confirm explicitly:

- exact-target matching succeeded;
- `watched` tag created or reused;
- target movies tagged;
- monitored/file/settings state preserved;
- acquisition/search/delete operations remained zero;
- private Radarr snapshot refreshed;
- second dry-run is clean.

After completion, return `docs/CODEX_TASK.md` to idle and link the completion report.
