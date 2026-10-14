# Engineering report: watched state for the October 14 import

**Specification:** [Assigned brief](2026-10-14-watched-new-import-brief.md).
**Result:** Implemented, deployed and applied; verified complete.
**Branch:** production/watched-import-state; implementation55cfbc5a7afb16e8b194b903ee876ca668f1bc8d.
**PR:** [#10](https://github.com/kolorifer/radarr-festival-list/pull/10), merged45c3311adbaed93c171354c63f1cf9384503077f.
**Verification:** 2026-10-14, seedbox Python3.13.5. Subsequent documentation handoff preserves runtime bytes.

## Change

A separate one-time CLI reads the private87-film cohort, proves every exact IMDb
match against the original235-film import audit, and requires qualified catalog
membership plus Movie List/score-band tags. Recorded dry-run and fresh full-state
guards precede writes. Existing watched tag is added without replacing tags;
a separate guarded editor operation supports only currently monitored exact
targets becoming unmonitored. General Movie List API restrictions are unchanged.

After complete Radarr verification, merge/deduplicate the cohort into the private
canonical watched manifest with blob-SHA protection and readback verification,
retain the cohort file as provenance, and refresh the private current snapshot.
All per-film data and operation payloads remain private. Public reports contain
aggregate counts only. Watched state never changes scores/qualification.

## Files/components

| File/component | Purpose |
| --- | --- |
| radarr_watched_import.py | Provenance checks, guarded monitored-off operation, verification and canonical merge |
| test_radarr_watched_import.py | 15 manifest/state/privacy/preservation/idempotence tests |
| test_radarr_movie_list_sync.py | Explicit existing watched/unmonitored preservation regression |
| deploy/radarr-sync.py | watched-import-only mode with existing private credentials |
| deploy/WATCHED_IMPORT.md | Private execution/recovery runbook |
| .github/workflows/movie-intel-test.yml | Branch CI |
| Project-state/decision/task documents | Aggregate completion and idle handoff |

## Live acceptance results

| Criterion | Verified result |
| --- | --- |
| Cohort size /unique exact matches | 87 /87;0 missing/ambiguous |
| Original import provenance | All87 proven in the original235-film addition audit |
| Initial state | 87 needed watched;87 monitored |
| Applied | 87 watched;87 unmonitored; existing watched tag9 reused |
| Write audit | 1 additive tag-editor PUT +1 monitored=false editor PUT |
| Other writes | 0 movie add/delete/search/grab/download/import-list commands |
| Preserved | Files/settings/path/metadata, Movie List/band/unrelated tags and all non-target movies |
| Second independent cohort dry-run | 0 to-tag;0 to-unmonitor;0 missing/ambiguous |
| Canonical merge | 271 prior +87 cohort −0 overlap =358 unique watched targets |
| Private snapshot | Refreshed immediately;992 records; all87 states/IDs/tags verified via GitHub |
| Normal Movie List dry-run | 387 qualified/already correct;0 additions/tag changes/removals/unresolved |
| Re-monitoring | No normal-sync write or monitoring-on path; all87 remain false |
| Scheduler/service | Installed unit hashes unchanged; timer active; same active movie-intel PID, NRestarts0 |
| Health | Local/public HTTP200 |

These operation-specific audits do not claim to suppress Radarr's independent
scheduled background jobs. No real notification/download test was triggered.

## Tests

167 complete unittest tests pass before and after deployment:151 existing +16
new (15 cohort,1 normal-sync). Tests cover manifest count/state/uniqueness,
missing/duplicate IDs, original import identity/membership, true-to-false-only
target guards, full live-row drift, unchanged general write restrictions,
non-target/metadata/file/tag preservation, idempotence/partial timeout recovery,
private canonical deduplication and public-repository rejection.
Explicit normal reconciliation regression preserves an existing qualified
watched film's monitored=false and watched tag.

Python3.12/3.13 CI run38620446942 passes. pip check, configuration preflight,
production_scoring.py --check, git diff --check and private-ID/token scans pass.
Frozen catalog stays1909 films,224 grandfathered +163 new =387 qualified.
Normal sync runtime/scoring/source inputs remain byte-identical.

## Deployment/recovery

Previous deployment6dad4ec475e22e8ec319224fdf79091a4c378a16 was recorded/backed up
with source/private configuration/units under
~/.local/state/movie-intel/watched-import/deploy-backups/20261014T190409Z.
Switched the clean checkout under the existing sync lock; no service restart,
daemon reload or scheduler change. Fresh dry-run/apply ran detached so an SSH
disconnect could not interrupt it.

Private before/after/write audit:
~/.local/state/movie-intel/watched-import/backups/20261014T190436Z.
Cohort/canonical/post-plan/normal-sync/verification reports remain private in the
watched-import state directory. The canonical merge happens only after a fully
verified apply. GitHub failures do not repeat writes; resume with a new dry-run
skips already-correct targets.

Rollback code to6dad4ec475e22e8ec319224fdf79091a4c378a16 with sync idle/lock held.
Retain verified watched/unmonitored annotations and canonical manifest. Turning
monitoring back on or removing annotations requires explicit instruction; there
is no automatic reverse mutation, file deletion or snapshot replay.

## Findings and handoff

Radarr had992 records before apply and992 after. Two additions occurred between
earlier990-record verification and this iteration; this operation did not add
them. Their origin was outside this task; all non-target records were preserved.
No target identity/access/deployment blocker remains.

D020 and project state record the agreed cohort behavior; CODEX_TASK returns
idle. Existing daily sync preserves unmonitored state on existing movies and
treats watched as an unrelated tag. No new recurring watched enforcement rule
was added. Preserve prior live Telegram/research/audit reports.
