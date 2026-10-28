# Completed research brief: issue #86 / supervisor task 1

**Source:** issue-owner supervisor task 1 supplied to this implementation worker
on 2026-10-25; [control issue #86](https://github.com/kolorifer/radarr-festival-list/issues/86).
**Status:** research artifacts implemented for review; product policy and live
provider feasibility remain undecided. This brief does not replace or authorize
the unrelated assignment in `docs/CODEX_TASK.md`.

## Objective and agreed behavior

Produce a read-only, reproducible Live Movie Score v1 calibration for 20–30
exact-ID films spanning 2024–2026. Include Hamnet, Anora, The Brutalist, The
Substance, Sentimental Value, It Was Just an Accident and sparse 2026 controls.
Preserve Audience 25 IMDb + 25 Letterboxd and Recognition 20 European  + 10
Independent  + 10 US Institutional  + 10 Critics, total 100.

Use the agreed linear rating scales (IMDb 6.0→8.5 and Letterboxd 3.0→4.3) and
compare unsmoothed/modest/stronger vote-count Bayesian smoothing with explicit
neutral priors. Reuse historical normalized award types/caps from
`sources/evidence-families.json` at
`9c5a0f06e1c39e48653338fd0865ddabdc525a61`, verifying additional film-level
evidence with dated URLs. Keep TIFF +4 Independent and uniquely attributed major
festival screenplay approximately +6 European as separate sensitivity experiments.

Supply offline utilities/tests, film-level machine results, a readable report,
provenance, freshness/missingness flags, provider feasibility, Hamnet curated 1
audit, score sensitivity, and a proposed calibration with product-review questions.
Do not treat missing as numerical zero, fill a missing Letterboxd half with IMDb,
or rank films with incomparable evidence coverage as complete overall scores.

## Authorized scope and boundaries

Public repository and bounded lawful public movie/award/provider research only.
All code/data live in a segregated research path. No production dependencies or
runtime collectors. The runner owns commit/push/PR and issue reporting on
`automation/issue-86-worker`; this worker leaves a reviewable diff and reports
actual checks. No worker Git publication or issue comments.

No seedbox access (including reads), private identity/configuration, credentials,
Radarr/media/tracker/download/Telegram/notifier access, live test, import refresh,
daemon, operational change, deployment, main merge, frozen catalog or feed change.
Do not alter `docs/CODEX_TASK.md`, D012/D016/D017 or unrelated work. Future
event-driven refresh, durable 30-day cache and enrichment are context only.

## Acceptance and result

The [engineering report](2026-10-25-live-score-v1.md) records implementation,
tests, limitations and publication handoff. The
[calibration report](../../simulations/live-score-v1/report.md) and linked
film breakdowns/machine outputs cover 24 films and twelve variants each.
Original rating observation times and full live award histories remain unknown;
the deliverable expressly reports those gaps rather than claiming live completion.

Use focused offline tests, repository applicable checks and `git diff --check`.
Record the full-suite result honestly, including interpreter/environment failures.
Promotion, provider rights, confidence constants, new award types and product
acceptance require owner/ChatGPT review; none is implicitly authorized by this brief.
