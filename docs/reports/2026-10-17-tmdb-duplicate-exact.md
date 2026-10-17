# Engineering report: Issue #33 — TMDb duplicate exact matches

**Specification:** [Completed brief](2026-10-17-tmdb-duplicate-exact-brief.md),
control issue #33 / supervisor task 1 supplied to this fresh worker.
**Result:** Implemented locally; ready for review, product acceptance pending.
**Repository revision:** `automation/issue-33-worker`, starting from clean
`a7017dd` (local `origin/main` tracking reference); no remote inspection.
**Verification date:** 2026-10-17, offline local checkout, Python 3.9.6 in the
existing isolated `/private/tmp/issue30-venv` environment. No packages installed.

## What changed

Multiple exact normalized title/original-title + year results can now resolve
only if the top popularity is **at least 10 times** the runner-up and leads by
**at least 10 popularity points**. Both bounds are inclusive. The order-of-
magnitude requirement rejects modest relative leads; the absolute gap rejects
large ratios between tiny values. Comparing against the strongest runner-up
also covers every lower-ranked candidate, independent of response order.

Every exact candidate must have finite, nonnegative numeric popularity;
missing/None, booleans, strings, negative and nonfinite values leave the result
unresolved. A known numeric zero is permitted, subject to the absolute gap.
The duplicate exception requires an explicit matching year. Unique results
retain the prior behavior, including acceptance without popularity. Zero exact
results remain unresolved. Details lookup, IMDb resolution and cache behavior
are unchanged. These resolver constants implement the task's requested
conservative guard; they do not change recommendation/scoring policy.

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| `tmdb_resolver.py` | Duplicate-only guard, named bounds, validity checks and resolver documentation. |
| `test_tmdb_resolver.py` | Eleven focused tests, with subcases covering limits, invalid data, all candidates and offline identity regressions. |
| `docs/reports/2026-10-17-tmdb-duplicate-exact{,-brief}.md` | Completed scope and engineering evidence. |
| `docs/PROJECT_STATE.md` | Local implementation/verification status and remaining live-validation boundary. |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Unique and zero exact matches preserve behavior | Passed | Existing exact-title/year test plus unique/missing-popularity and zero-match cases. |
| Explicit conservative dominance rule | Passed | Both bounds tested at/around their limits; result order and three-candidate cases covered. |
| Near ties and missing/None stay unresolved | Passed | Near/equal ties; missing/invalid values in every candidate position; no details lookup on refusal. |
| Snowman (2017) resolves to `372343` | Passed offline | Supplied popularity values `22.9187` / `0.9759` replayed in either order and through `resolve_movie()`. Ratio about 23.48; gap 21.9428. |
| Hamnet (2025) still resolves to `858024` | Passed offline | Synthetic unique response through `resolve_movie()`, details compaction and temporary cache. |
| No malformed-title/year recovery or matching expansion | Passed | Malformed Hamnet remains unresolved; popular wrong-title/wrong-year results excluded; original-title normalization preserved. |
| Notification/action behavior | Passed offline | Existing movie-intel service, action and pending-action unit tests. No plumbing changes. |
| Live TMDb/service behavior | Not verified | Network, seedbox access and deployment forbidden. |

## Tests run and results

- `/private/tmp/issue30-venv/bin/python -m unittest -v test_tmdb_resolver test_movie_intel test_movie_intel_service test_movie_intel_actions test_pending_actions`
  — **42 passed**, including all 16 resolver tests.
- `/private/tmp/issue30-venv/bin/python /private/tmp/issue33-offline-tests.py`
  — **283 discovered: 273 passed, 10 skipped**, 63.512 seconds, no failures.
  The temporary offline wrapper uses `unittest.defaultTestLoader.discover('.')` and
  `unittest.TextTestRunner(verbosity=2)`, skips all `test_movie_intel_http` methods
  and `test_real_http_serialization_and_no_acquisition`, and installs a Python
  audit hook rejecting all `socket.*` events before discovery. The canonical
  unfiltered `python -m unittest -v` is not run because those tests open sockets.
- `git diff --check` — passed. Final diff and added documentation reviewed;
  relative documentation links verified locally.

## Deployment result

Not authorized; no deployment, service restart or live integration check. No
network or seedbox access, real notification, Radarr/media mutation or Git
publication performed. Repository suite automation tests use synthetic
boundaries and temporary Git repositories; no real Codex worker/runner started.

## Unexpected findings

No project-local virtual environment was present; the existing isolated test
environment has the required dependencies. Python 3.12/3.13 CI was not run by
this offline worker.

## Unresolved issues and risks

TMDb popularity changes over time, so this explicit conservative gate may leave
future duplicates unresolved. Offline fixtures verify the supplied identities
and algorithm, without asserting current live search responses. Ten existing
socket-based tests are excluded by the task's network prohibition. Product
acceptance and later authorized live verification remain with the supervisor.

## Commit and PR reference

Runner owns commit/push/PR and issue reporting. This worker leaves the local
diff for publication and makes no remote Git calls.

## Project context updates

Completed task and evidence are archived in the linked brief/report. Project
state distinguishes local implementation, offline verification, absent
deployment and pending product acceptance. `docs/DECISIONS.md` and the unrelated
legacy `docs/CODEX_TASK.md` remain unchanged; no next task is inferred.
