# Issue 53: passive identity eligibility bridge

Specification: https://github.com/kolorifer/radarr-festival-list/issues/53

Finalize PR 52 with research disabled, then implement a separately reviewable
passive bridge from explicit movie-intel resolution outcomes to durable research
eligibility. Missing IDs and provisional groupings are not failures. Preserve
original evidence, four seed histories, actor behavior, collector isolation and
researcher metadata-only confinement. No new research GETs or schedule.

Acceptance: explicit routing; strong source correlation; fail-closed conflicts;
material-version deduplication; retry/restart/pressure diagnostics; full local,
seedbox and Python 3.12/3.13 CI; zero-acquisition shadow verification; precise
coverage denominators and a proposed, unactivated cadence/budget.

Rollout: reuse existing outcome key, unchanged listener and confinement. Passive
activation only after preflight and rollback checks. Stop for review if new
credentials/permissions, material interruption or unresolved delivery risk is
needed. Keep the prior finite pilot closed. Phase 2 remains a separate PR.

Implementation choice: atomic additive eligibility tables in the collector inbox,
with an authenticated, narrow Stage 2 manifest export. No worker store access to
Stage 1 and no import into the closed pilot. A small actor-owned asynchronous
retry spool provides at-least-once delivery after persistence; the preceding
bounded memory window remains explicitly uncertain across process crashes.
