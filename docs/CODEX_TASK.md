# Current Codex task

Status: **Assigned — finish Rambo III watched correction, apply the five approved cleanup removals, then audit Indian-language legacy titles.**

The user and ChatGPT have completed a conservative cleanup review. Preserve the existing Rambo III correction first, then process only the five explicitly approved removals below. After that, build an audit-only candidate set for Indian-language legacy titles. Do not delete that Indian-language cohort in this task.

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

Also protect exact identities present in the canonical private watched manifest. If any target has changed identity, gained a file, or is canonical-watched, skip that target and report it rather than deleting it.

For an eligible target, delete the Radarr movie record only. Do not deliberately delete media files, trigger search/grab/download, refresh import lists, or modify unrelated movies.

After the operation, refresh `kolorifer/radarr-state/radarr-current.json` and verify each eligible approved target is absent and all skipped/protected targets remain intact.

## Phase 3 — audit-only Indian-language cleanup candidates

The user clarified that the intended cleanup target is not every India co-production. The target is primarily **mainstream/legacy Indian-language cinema**, distinguished first by original language.

Do **not** delete any title from this Phase 3 cohort in this task. Produce a complete review table for ChatGPT/user approval first.

### Candidate definition

Start from current Radarr records that are outside the managed Movie List and evaluate the movie's authoritative original-language metadata.

Primary candidate signal: original language is one of the major Indian film languages, including at minimum:
- Hindi (`hi`)
- Tamil (`ta`)
- Telugu (`te`)
- Malayalam (`ml`)
- Kannada (`kn`)
- Bengali (`bn`)
- Marathi (`mr`)
- Punjabi (`pa`)
- Gujarati (`gu`)

Include other clearly Indian original-language codes if encountered and document them. Use production-country metadata only as supporting context, not as the primary deletion criterion.

### Protection rules for the audit

Mark a title **protected / not a cleanup candidate** if any of these apply:
- current Radarr record has `movie-list` tag;
- exact IMDb/TMDb identity is in the current D016-qualified production catalog synchronized by D017;
- `has_file=true`;
- exact IMDb identity is in the canonical private watched manifest.

Do not treat a live `watched` tag alone as canonical evidence if it disagrees with the private manifest. A prior contextual excerpt was misread for **3 Idiots (2009), IMDb `tt1187043`**; its full current record has `tags: []`, and it is absent from the canonical watched manifest.

International co-productions whose original language is English, French, German, etc. should **not** be included merely because India appears among production countries.

### Required audit output

Produce a table containing, for every current Indian-language record found:
- Radarr ID
- title and year
- IMDb ID
- TMDb ID
- original language
- production countries
- `has_file`
- current tags
- Movie List / D016 protection status
- canonical watched status
- final classification: `protected` or `candidate`
- concise reason

Also report counts by original language and total candidate/protected counts.

No Radarr delete/mutation is authorized for this Phase 3 cohort yet. Return the audit artifact for product review.

## Explicit keep / no-cleanup decisions

Do not remove or alter these based on the general cleanup review:

- **La Ciénaga** — user confirmed watched; its watched state is correct.
- **Uncle Boonmee Who Can Recall His Past Lives** — user confirmed watched; its watched state is correct.
- **Sicario 3** — keep even though release metadata is incomplete/no release date yet.
- **The Return (2003)** — keep.
- **The Return (2024)** — keep.
- Horror/cult titles — cleanup category parked; do not prune them.
- Recent action/streaming-style titles — no generic cleanup rule; do not prune by that category.
- Franchise/sequel status — not a cleanup criterion.

## Verification and handoff

1. Preserve all production scoring/qualification behavior and D016/D017 synchronization logic.
2. Record exact Radarr IDs/IMDb/TMDb IDs acted on in Phase 2, safeguards checked, skipped targets, and resulting movie count.
3. Verify no protected downloaded or canonical-watched movie was deleted.
4. Build and save the complete Phase 3 Indian-language audit artifact without mutating that cohort.
5. Run idempotency/read-only verification after Phase 2 cleanup.
6. Save/update the engineering report, refresh project state/decisions only where appropriate, and return this task file to Idle after completion.
