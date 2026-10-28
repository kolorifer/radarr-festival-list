# Engineering report: issue #86 — Live Movie Score v1 calibration

**Specification:** [completed supervisor task 1 brief](2026-10-25-live-score-v1-brief.md)
and [control issue](https://github.com/kolorifer/radarr-festival-list/issues/86).
**Result:** offline research implemented; ready for product/code review with
explicit evidence gaps. No production policy accepted or implemented.
**Repository revision:** `automation/issue-86-worker`, base `cc11595`.
**Verification date:** 2026-10-25; isolated local Python 3.9 virtual environment
at `/private/tmp/live-score-v1-venv`. No operational/seedbox verification.

## What changed

Added a deterministic calibration packet for **24 films** (2024: 10, 2025: 10,
2026: 4) and **288 film/variant comparisons**. It preserves the agreed 50/50
weights and existing award-type normalization, reconstructing every selected
frozen award-family score before evaluating 93 independently reviewed award facts
and the two optional extensions. The historical catalog/model remains unchanged.

Inputs include 22 archived IMDb/Letterboxd pairs, two sparse indexed IMDb
observations and two unavailable Letterboxd halves. No fresh live paired ratings
or complete current overall scores are claimed. Per-film totals are conditional
observed subtotals; overall scores remain null. Scoped absences and future
award seasons remain distinct from unchecked sources. Overall ranks are withheld;
audience-only ranking diagnostics use the 22 paired archival rows.

The [readable calibration report](../../simulations/live-score-v1/report.md)
contains the detailed findings, provider feasibility, source links, coverage,
Hamnet audit and explicit product-review decisions. The modest pseudo-count
scenario is a conditional review recommendation; neither priors nor award
extensions have become production policy.

## Files and components changed

| File/component | Purpose |
| --- | --- |
| `simulations/live-score-v1/calibrate.py` | Standard-library offline scoring, twelve variants, coverage, byte-check regeneration |
| `simulations/live-score-v1/test_calibrate.py` | Twenty arithmetic, provenance, attribution, missingness and determinism tests |
| `simulations/live-score-v1/inputs/` | Original selected archive rows, hashes/revisions, fixed cohort, public identity metadata and dated new facts |
| `simulations/live-score-v1/results.json` | Film-level scores/components, original facts, source URLs, flags and sensitivity |
| `simulations/live-score-v1/comparison.csv` | 288 flat comparisons with incomplete status |
| `simulations/live-score-v1/breakdowns.md` | Generated readable film-level provenance and twelve-variant breakdowns |
| `simulations/live-score-v1/report.md` | Findings, feasibility, proposed calibration and product decisions |
| `docs/PROJECT_STATE.md` | Research/review status, separate from deployment and acceptance |
| This report and completed brief | Recoverable scoped handoff |

## Acceptance criteria and evidence

| Criterion | Result | Evidence / remaining gap |
| --- | --- | --- |
| Agreed Audience/Recognition caps and maximum 100 | Passed | Boundary, family-cap, deduplication and maximum tests |
| Historical calibration source preserved | Passed | Exact Git revision/full-file hashes; selected raw rows compared to local Git objects; every selected family reconstructed |
| 20–30 films, required titles, 2026 controls | Passed | 24 unique IMDb/TMDb mappings; 10/10/4 stratification; sparse observations 229 and 85 votes |
| Rating/count and award provenance | Partial evidence, explicitly reported | 22 archived paired ratings; two indexed IMDb pairs; 93 new award facts; original measurement times absent; some historical awards remain secondary |
| Missingness and pending awards distinct | Passed | 68 scoped checks: 37 positive, 23 scoped verified absences, eight pending; two LB halves unavailable; all overall scores null |
| Confidence and TIFF/screenplay sensitivity | Passed | Three experimental strengths × four extension combinations; signed source adjustments; extensions need unique verified attribution |
| Hamnet curated 1 explanation | Passed | Membership counter vs separate score; modest observed 56.8 base / 60.8 TIFF; screenplay does not apply |
| Provider feasibility | Documented, unresolved for live promotion | ReelDB no-auth 403; authenticated limits/rights unverified; current Letterboxd access restrictions; IMDb licensing/publication restrictions |
| No production/runtime or unrelated-task changes | Passed | Scoped diff; frozen production regeneration unchanged; active task and protected artifacts unchanged |
| Worker publication / deployment | Not performed | Runner owns publication; operational authority absent |

## Tests run and results

All commands below were run locally, not on a seedbox or production service.
`PY` denotes `/private/tmp/live-score-v1-venv/bin/python` (Python 3.9).
The venv installed only the repository's existing requirements; no dependency
manifest or production dependency changed.

| Command | Actual result |
| --- | --- |
| `PY -m unittest discover -s simulations/live-score-v1 -p 'test_*.py' -v` | 20 passed, final run after research code changes |
| `PY simulations/live-score-v1/calibrate.py` | Generated 24 films / twelve variants each offline |
| `PY simulations/live-score-v1/calibrate.py --check` | Passed, byte-identical generated artifacts |
| `PY -m pip --isolated check` | Passed: no broken requirements |
| `PY -m unittest -v` | 687 run in 140.880s; four errors, two skips; **not a full-suite pass** |
| `PY production_scoring.py --check` | Passed: 1,909 candidates / 224 grandfathered / 163 new / 387 qualified |
| `git diff --check` | Passed; scoped new-file whitespace and artifact audit also completed |

Full-suite errors are in unchanged repository tests under the available Python 3.9:

1. `test_identity_research.AdditionalGates.test_real_sqlite_full_reservation_rollback`:
   missing `OperationalError.sqlite_errorcode`.
2. `test_identity_research.StageA.test_fixed_storage_reason_codes_never_emit_error_text`:
   missing `sqlite3.SQLITE_BUSY`.
3. `test_identity_selected.SelectedHTTPTests.test_selected_auth_and_commit_failure`:
   `RemoteDisconnected` while exercising the unchanged SQLite error handler.
4. `test_identity_triage.HTTPTests.test_busy_or_storage_failure_not_acknowledged`:
   the same simulated storage-error response path disconnects.

The unchanged `identity_triage_service.storage_reason` references SQLite error
constants absent from this interpreter; this explains the error-response-path
limitation. The repository workflow targets Python 3.12/3.13; those interpreter
runs were **not** performed here. Two platform-specific skips also remain.
The environment additionally emitted urllib3's LibreSSL support warning.
No unrelated runtime fix was attempted. Full-suite output stayed in a temporary
local test log; no operational logs or private state were read.

Focused tests cover the 6.0/8.5 and 3.0/4.3 boundaries, a hand-computed Bayesian
example, raising below-prior scores, missing rating/count pairs, invalid input,
winner/nominee replacement, repeated-source deduplication, competition vs wins,
historical Sundance convergence, bonus units/caps, exact historical projections,
ID/year reconciliation, Hamnet, missing LB, verified gap additions and byte
reproducibility. The initial focused run caught the documented Familiar Touch
premiere/release-year distinction and JSON key normalization; both were corrected
before the final passing run.

## Deployment result

Not authorized and not performed. No seedbox, Radarr, media, tracker, download,
Telegram, notifier, private configuration or production-service access. No live
test, cache, collector, background daemon, feed refresh, merge or deployment.
Tests use local fixtures/temporary loopback servers already defined by the
repository, not operational integrations.

## Unexpected findings

- The frozen snapshot misses significant Cannes/Academy/Globe/BAFTA evidence for
  some recent titles. Recognition gains such as Sentimental Value's +22 are
  evidence repairs, not proposed new weights.
- Midpoint-prior smoothing raises East of Wall's Audience by +6.3/+15.4 under
  modest/stronger strengths. It is not a universal sample penalty.
- Hamnet's existing curated 1 is a list-membership counter. Standard known film
  recognition is already 15.8/50; TIFF is a separate +4 experiment.
- Public Nina Roza results contain a conflicting IMDb ID and inconsistent locale
  observations. The wrong-ID result was excluded and one exact-ID pair retained.
- Fresh no-auth ReelDB access returned 403. A public homepage does not establish
  valid-account access, legal Letterboxd coverage or a rate-limit contract.

## Unresolved issues and risks

Original archived rating observation times, fresh paired coverage, complete award
history, provider-specific prior calibration, and future lawful provider/usage
rights remain unresolved. No score precision or full live coverage is inferred
from successful arithmetic. Indexed observations can be stale; pending 2027
award seasons must not be mistaken for negative evidence. Historical unreverified
award facts remain visibly archival.

The owner/ChatGPT must review whether confidence may raise scores; select any
provider-specific means/strengths; decide TIFF categories and screenplay scope,
stacking and caps; and specify future coverage/display semantics. Full repository
CI on its supported Python versions remains useful review evidence and is owned
by the runner. No further operational task is inferred.

## Commit and PR reference

Worker base `cc11595`, branch `automation/issue-86-worker`. No worker commit,
push, PR or issue comment was made, per the latest runner instruction. The
containing runner-created commit/PR supplies this report's final reference.

## Project context updates

Project state records implementation, local verification, absent deployment and
pending product acceptance separately. Completed brief and this report are saved
under `docs/reports/`. Decisions were not changed: no new policy was accepted.
`docs/CODEX_TASK.md` was preserved exactly because its active Radarr cleanup is
outside issue #86 and explicitly forbidden to change.
