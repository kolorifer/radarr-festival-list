# Current Codex task

Status: **Assigned — finish Rambo III watched correction, then apply the explicitly approved Radarr cleanup.**

The user and ChatGPT have completed a conservative cleanup review. Preserve the existing Rambo III correction first, then process only the five explicitly approved removals below. Do not generalize these removals into a broad cleanup rule.

## Phase 1 — Rambo III watched correction

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

Expected result for Phase 1: canonical watched count = **359**.

## Phase 2 — explicit cleanup removals

The user explicitly approved removal of these five Radarr movie records:

- **The Rescue (2027)** — IMDb `tt35606013`, TMDb `1425472`; snapshot Radarr ID `448`.
- **Zip Wire (2026)** — IMDb `tt36980377`, TMDb `1482547`; snapshot Radarr ID `79`.
- **Rage of Stars (2026)** — IMDb `tt29512655`, TMDb `1323244`; snapshot Radarr ID `96`.
- **Drishyam (2015)** — IMDb `tt4430212`, TMDb `352173`; snapshot Radarr ID `690`.
- **Drishyam (2013)** — IMDb `tt3417422`, TMDb `244049`; snapshot Radarr ID `717`.

### Hard deletion safeguards

Before any delete, re-read the live Radarr record and verify exact identity by IMDb/TMDb ID, not title alone.

**Never delete a movie if `has_file=true`.** Downloaded movies are protected by user preference even when they would otherwise be cleanup candidates.

Also do not delete a movie carrying the canonical `watched` state; watched movies remain in Radarr and should normally be unmonitored instead.

If any of the five targets has changed identity, gained a file, or become watched since the recorded snapshot, **skip that target and report it** rather than deleting it.

For an eligible target, delete the Radarr movie record only. Do not deliberately delete media files, trigger search/grab/download, refresh import lists, or modify unrelated movies.

After the operation, refresh `kolorifer/radarr-state/radarr-current.json` and verify each eligible approved target is absent and all skipped/protected targets remain intact.

## Explicit keep / no-cleanup decisions

Do not remove or alter these based on the cleanup review:

- **La Ciénaga** — user confirmed watched; its watched state is correct.
- **Uncle Boonmee Who Can Recall His Past Lives** — user confirmed watched; its watched state is correct.
- **Sicario 3** — keep even though release metadata is incomplete/no release date yet.
- **The Return (2003)** — keep.
- **The Return (2024)** — keep.
- Horror/cult titles — cleanup category parked; do not prune them.
- Recent action/streaming-style titles — no generic cleanup rule; do not prune by that category.
- Franchise/sequel status — not a cleanup criterion.

The previously classified Indian-production `R` cohort is **not part of this deletion task**. Those entries were classification/rejection state for the existing unmonitored library, not an authorization to physically delete the whole cohort. Leave them unchanged in this task.

## Verification and handoff

1. Preserve all production scoring/qualification behavior and D016/D017 synchronization logic.
2. Record exact Radarr IDs/IMDb/TMDb IDs acted on, safeguards checked, skipped targets, and resulting movie count.
3. Verify no protected downloaded or watched movie was deleted.
4. Run an idempotency/read-only verification after the cleanup.
5. Save/update the engineering report, refresh project state/decisions only where appropriate, and return this task file to Idle after completion.
