# Current Codex task

Status: **Active — implement Radarr Movie List membership + score-band sync.**

[Implementation brief](reports/2026-10-14-radarr-movie-list-sync-brief.md).

Authoritative qualification remains D016:
`grandfathered_deployed_224 OR Evidence Score >=225`, inclusive.
Current frozen result: 1,909 candidates; 387 qualified.

## Required production behavior

Reconcile the 387 qualified movies into Radarr using project-managed tags:

- membership: `movie-list`;
- one score band per qualified movie:
  - `ml-below-225` for qualified grandfathered scores <225;
  - `ml-225-249` for 225 <= score <250;
  - `ml-250-299` for 250 <= score <300;
  - `ml-300-399` for 300 <= score <400;
  - `ml-400-plus` for score >=400.

Retroactively tag matching movies already in Radarr. Add qualified movies missing from
Radarr as monitored with the membership and score-band tags, but with movie search
disabled. Preserve unrelated tags and all existing movie settings/files.

The exact Evidence Score stays in the production catalog. Do not create exact-score
tags and do not modify Radarr Overview/description metadata.

Implement an idempotent dry-run/apply sync. Perform and record a live dry-run first;
then apply without another routine approval only if identity, tag, root/profile and
write-plan invariants are unambiguous. If root/profile selection for new movies is
ambiguous, stop before additions and report the precise choice required.

Do not trigger searches, grabs/downloads, import-list acquisition refreshes, deletes,
file moves, or unrelated tag/settings changes. After apply, a second dry-run must be
clean apart from explicitly documented unresolved identity lookups.

Make future reconciliation automatic through one safe existing refresh/scheduler path
(no duplicate schedulers). Full safety, tests, deployment procedure and completion
report requirements are in the linked brief.

On successful completion, update PROJECT_STATE/DECISIONS, write engineering and
machine-readable verification reports, and return this file to idle.
