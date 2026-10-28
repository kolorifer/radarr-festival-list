# Engineering report: issue #86 — Live Movie Score v1, Task 2

**Specification:** [completed supervisor task 2 brief](2026-10-26-live-score-v1-task2-brief.md),
latest trusted task 2 and [control issue](https://github.com/kolorifer/radarr-festival-list/issues/86).
**Result:** offline comparison implemented, ready for research/code review;
fresh paired rating acquisition remains unavailable under demonstrated rights
and access. The task explicitly permits this fallback. No production policy accepted.
**Repository revision:** `automation/issue-86-worker`, clean starting HEAD
`b62f00de56b2f1aa488e9f41742b86617efcec72`, Task 1 / PR #88.
**Verification date:** 2026-10-26, local isolated standard-library Python 3.9.6
venv `/private/tmp/live-score-task2-venv`. No seedbox or operational access.

## What changed

Created a separate `simulations/live-score-v1/task2/` packet against the immutable
Task 1 result. The baseline's fourteen packet/report files are hash-pinned and
checked against local Git objects. Original Task 1 files remain byte-for-byte.
All 24 exact-ID film identities, release context and rating/count observations
are retained. A deterministic offline utility reuses Task 1's research arithmetic
and award policy; it imports no production module and contains no acquisition.

The new packet records **26 award corroborations** (25 direct primary-page reviews,
one indexed primary), **11 components upgraded to direct primary support across
ten films**, and **81 scoped checks** (19 positive, 52 category/edition absences,
eight pending, two unavailable). No newly scored award or fresh rating pair was
established. These provenance improvements change **zero numeric points** versus
Task 1 in all 288 corresponding film/variant comparisons.

Current provider terms/access were reviewed before acquisition. No lawful fresh
paired route was established for this public packet. Coverage remains **IMDb:
zero fresh, 22 archived + two stale indexed; Letterboxd: zero fresh, 22 archived +
two unavailable**. Original measurement timestamps and upstream precision are
unknown. No raw new rating dataset or source article was acquired or published.
Task 1's no-auth ReelDB 403 was not relabeled as a fresh Task 2 endpoint test.

The 0/1,000/10,000 comparison uses the same fixed observations and exact priors
7.25/3.65. Audience-only ranks are limited to the 22 paired archival rows;
indexed/partial controls are excluded. Two raw ties separate under smoothing,
while all same-scenario ranks match Task 1. Every overall score and rank remains
null. TIFF and screenplay variants stay separate and off in base. Detailed
findings, source citations and product decisions are in the
[research report](../../simulations/live-score-v1/task2/report.md).

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| `simulations/live-score-v1/task2/compare.py` | Deterministic comparison, baseline hash gate, attribution/coverage validation, comparable audience ranks, separate evidence/smoothing deltas |
| `simulations/live-score-v1/task2/test_compare.py` | Fourteen provenance, arithmetic, missingness, rank, deduplication, extension/cap and reproducibility tests |
| `simulations/live-score-v1/task2/inputs/` | Pinned baseline manifest, dated award/coverage annotations and pre-acquisition access/rights audit |
| `simulations/live-score-v1/task2/results.json` | 24 film-level identities, provenance, twelve variants, coverage, evidence changes and null overall fields |
| `simulations/live-score-v1/task2/comparison.csv` | 288 side-by-side rows with raw/adjusted ratings, counts, component points and deltas |
| `simulations/live-score-v1/task2/breakdowns.md` | Generated readable comparison and per-film evidence/coverage changes |
| `simulations/live-score-v1/task2/report.md` | Findings, provider limitations, conditional ranking interpretation and product decisions |
| `docs/PROJECT_STATE.md` | Narrow Task 2 research/review status |
| This report and completed brief | Recoverable scoped handoff |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Immutable Task 1 baseline and same 24 exact-ID cohort | Passed | Fourteen baseline file hashes compared to pinned Git objects; exact identity/rating/release-context regression |
| Seek permitted fresh paired ratings before acquisition | Documented limitation, accepted fallback | Current IMDb reuse restrictions, Letterboxd API/terms, ReelDB auth/provenance/rights gaps; zero fresh claims |
| Preserve rating/count pairs, freshness, provenance and precision | Passed for retained evidence | No pair/date blending, null original exact timestamps, indexed/archived/unavailable status retained; no invented precision |
| Improve award evidence across four families | Passed | 26 corroborations; direct Gotham/competition/Academy/critics records; 11 component provenance upgrades; scoped absences and failures labeled |
| Exact three scenarios, scales, priors and 50/50 caps | Passed | Shared pinned policy, both-source hand arithmetic, real low-count signed-effect tests and cap checks |
| Separate evidence change from smoothing | Passed | Zero same-variant Task 1 deltas across 288 rows; nonzero within-snapshot smoothing deltas and tie changes |
| Unknown data and ranking comparability | Passed | Two partial rows excluded; 22 archival audience-only ranks; all overall fields null; no whole-family absence inferred |
| Optional TIFF/screenplay rules separate | Passed | Four combinations, both off in base; original evidence dates retained; no new award types/weights |
| Offline reproducibility and focused tests | Passed | Byte-identical regenerated artifacts; 14 Task 2 + 20 Task 1 research tests |
| Full applicable repository suite | Environmental failures | 515 run, 68 errors, two skips; details below; not a full-suite pass |
| Scope, privacy and publication review | Passed locally | Only authorized research/report/state edits; baseline/protected production files unchanged; no new raw rating dataset/source text or credentials |
| Commit/push/PR, deployment and operational verification | Not performed by worker | Parent owns publication; no operational authority |

## Tests run and results

All commands below were actually run in this task. `PY` is
`/private/tmp/live-score-task2-venv/bin/python`. No repository venv was present;
the isolated venv uses the available Python 3.9.6 and standard library. No
packages or production dependencies were added. The research utility needs none.

| Command | Actual result |
| --- | --- |
| `PY simulations/live-score-v1/task2/compare.py` | Generated 24 films / 288 variants offline |
| `PY simulations/live-score-v1/task2/compare.py --check` | Passed, byte-identical artifacts and baseline hashes |
| `PY -m unittest discover -s simulations/live-score-v1/task2 -p 'test_*.py' -v` | 14 passed |
| `PY -m unittest discover -s simulations/live-score-v1 -p 'test_*.py' -v` | 20 passed; Task 1 regression tests, not new source acquisition |
| `PY production_scoring.py --check` | Passed unchanged: 1,909 candidates / 224 grandfathered / 163 new / 387 qualified |
| `PY -m unittest -v` | 515 run in 195.430s; 68 errors, two skips; **not a full-suite pass** |
| `git diff --check` plus new-file whitespace/diff inspection | Passed |

The full suite's isolated-environment errors were classified from its temporary
local log: **60** missing `requests`, **four** missing `bs4`, **one** missing
`OperationalError.sqlite_errorcode`, **one** missing `sqlite3.SQLITE_BUSY`, and
**two** `RemoteDisconnected` errors in the unchanged HTTP storage-error paths.
The latter four match the Python 3.9 limitations documented in Task 1; the missing
packages are this run's dependency availability limitation. No supported
Python 3.12/3.13 run or full dependency-complete suite pass is claimed. No unrelated
runtime fix or package acquisition was performed. `pip check` was not run;
dependencies did not change. Full production verification was not performed.

Focused tests verify both-source hand calculations, the actual low-count East
of Wall effects, unchanged cohort/inputs against the immutable Git commit,
rejection of hash drift and inconsistent attribution, contradiction between
positive facts and same-edition scoped absence, missing halves staying unknown,
heterogeneous observations excluded from audience ranking, actual ties/rank
changes, signed evidence/smoothing separation, winner/nomination deduplication,
family caps, distinct extension variants and generated bytes.

## Deployment result

Not authorized or performed. No seedbox, Radarr, tracker, downloader, media,
Telegram/notifier, private-state or production-service access, even read-only.
No notification/download test, import refresh, live integration, collector,
background task/daemon, cache/event behavior, merge or deployment.

## Unexpected findings

- Direct Gotham nomination releases were discoverable, improving several
  previously archived/indexed facts without changing scores.
- LAFCA's real archive path uses `Years/<year>.php`; guessed lower-case HTML
  paths were not valid absence checks. Correct direct paths also failed through
  the web reader; indexed Anora corroboration stays explicitly indexed.
- Current terms/access review still fails to establish a rights-cleared fresh
  paired audience route. An accessible third-party marketing page is insufficient.
- No real overtakes occur in the paired archival subset: smoothing only separates
  two ties. East of Wall's large upward adjustment leaves its rank at 20.

## Unresolved issues and risks

Fresh paired evidence, upstream archive rights, original measurement times,
source precision and complete current award histories remain unresolved. A
successful deterministic calculation cannot remove those evidence limitations.
The report makes no claim that all possible licensed providers were exhausted.
Primary web-reader reviews can be cached, and edition-scoped absence does not
establish whole-family completeness or award eligibility.

The owner/ChatGPT must decide the next smoothing candidate (including its upward
effect below the prior), provider/publication rights, TIFF/screenplay scope and
display semantics for incomplete evidence. No product decision or operational
follow-up is inferred. Supported-version dependency-complete CI remains separate
review evidence for the parent.

## Commit and PR reference

Immutable comparison baseline:
[b62f00d](https://github.com/kolorifer/radarr-festival-list/commit/b62f00de56b2f1aa488e9f41742b86617efcec72),
[PR #88](https://github.com/kolorifer/radarr-festival-list/pull/88).
Task 2 worker made no commit/push/PR/comment. The containing parent-created
commit/PR supplies the Task 2 reference; branch remains `automation/issue-86-worker`.

## Project context updates

Project state records Task 2 implementation, technical checks, absent deployment
and pending product acceptance separately. This report and completed brief are
saved under `docs/reports/`. Decisions and `docs/CODEX_TASK.md` are unchanged;
its unrelated cleanup remains assigned and outside this scope. The original
Task 1 packet/reports are preserved. This worker did not read another session's
history, resume another worker, or launch an operational worker/runner.
