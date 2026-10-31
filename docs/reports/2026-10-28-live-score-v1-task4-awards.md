# Engineering report: #86 Task 4 — eight-film awards coverage

**Specification:** [Completed scoped brief](2026-10-28-live-score-v1-task4-awards-brief.md),
latest owner supervisor Task 4; D002/D007 research separation remains intact.
**Result:** Bounded packet implemented, ready for review; evidence incomplete,
product acceptance pending. No audience enquiry dependency or operational work.
**Repository revision:** Clean starting `automation/issue-86-worker` at
`824ed090e93c69e7ee5af6fe7df398725d8a6056`; worker leaves scoped diff for parent.
**Verification date/environment:** 2026-10-28, local offline research tests,
Python 3.9.6. Public award-source research through web reader, day precision.

## What changed

An awards-only packet inventories all eight films across fourteen institutions,
records bounded source checks, reproduces the exact retained Recognition arithmetic,
and compares Task 2/base/TIFF/screenplay/both results without acquiring ratings or
calculating Audience/overall scores/ranks. The original 34 Task 1/2/3 packet and
archived report files match pinned hashes and local Git objects byte-for-byte.
Historical source revision `9c5a0f06e1c39e48653338fd0865ddabdc525a61` is pinned.

**All eight base subtotals and all same-variant subtotals remain unchanged versus
Task 2.** In cohort order: Hamnet15.8, Anora41, Brutalist26.3, Substance14.7,
Sentimental Value30.8, Accident24.4, Nina2, Buildings0. These are observed
Recognition subtotals /50; complete-score fields are null. No leaderboard.

70 explicit new checks (36 scoped negative, 16 pending, 18 unavailable) close
**49 previously open category/edition/stage evidence gaps**, with no newly scored
component/correction. Gap closures: Spirit20, EFA12, Sundance8, BAFTA7, Gotham2.
Those counts are expanded stage cells, not 49 independent source reads or a
completeness claim. Sixteen additional cells become explicitly pending. Two
candidate corroborations and three exclusion/context facts add no points.

The full three-edition audit envelope has 1,224 cells: 53 positive, 70 scoped
negative, 1,048 unchecked, 17 unavailable, 36 pending. The initial release-season
candidate subset has 408: 53 positive, 66 scoped negative, 248 unchecked,
17 unavailable, 24 pending. The broader envelope prevents hidden assumptions
about different release seasons; neither envelope establishes eligibility.
Every unresolved cell (1,101 in full envelope) has a key and concrete reason.

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| `simulations/live-score-v1/task4-awards/inventory.py`, `inputs/gap-inventory.json` | Derived pre-research inventory, retained facts/checks/categories, edition scope and research priority. |
| `inputs/baseline-manifest.json`, `inputs/evidence.json` in that packet | 34 SHA-256 preservation pins, exact commits, source/access records, normalized facts, complete-list scope and missingness. |
| `compare.py`, `test_compare.py` in that packet | Isolated offline Recognition reuse, comparisons/matrix/deterministic generator, eighteen tests. |
| `results.json`, `comparison.csv`, `breakdowns.md` | Eight-film family/component/evidence/bonus deltas and provenance; no Audience/overall scores/ranks. |
| `coverage.json`, `coverage.csv`, `unresolved.csv` | Every category/edition/stage, status, check/positive references and unresolved reason. |
| `report.md` | Readable findings, source links, limits, scope, review questions and proposed display examples. |
| This report, completed brief, narrow project-state addition | Engineering handoff; implementation vs verification vs publication/acceptance separated. |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Inventory first, exact eight × fourteen | Passed | Derived 112 entries from pinned Task 1/2; retained Task 3 IDs/context tested, including Nina conflict and future TMDb event. |
| Bounded official-source research with provenance | Completed with barriers | 19 source records: ten readable primary-origin pages (cache possible), one mirrored primary PDF, one secondary film-context dossier, one indexed primary syndicated release, six failed origin URLs. Indexed release also failed direct open. No indexed/failed-source absence inference. |
| Scoped as-of matrix | Implemented; incomplete coverage explicit | 2026-10-28; nomination/selection and winner stages separate. Every unresolved cell enumerated; no film eligibility inferred. |
| Recognition comparison and separate deltas | Passed offline | Eight rows, four families/four variants; evidence delta0 for all, experimental bonus effects retained, complete fields null. |
| Actionable owner review | Delivered, not accepted | Findings table and partial/pending/verified-absence text examples; questions are proposals, not policy/UI implementation. |
| Offline reproduction and safety cases | Passed | Eighteen focused tests including nonzero synthetic evidence/bonus separation; input hashes, byte checks, pinned local Git objects. Synthetic tests are not award-source verification. |
| Preservation/handoff/checks | Passed locally | Twenty Task 1, fourteen Task 2, eighteen Task 3 preservation tests; deterministic checks; final diff/paths/whitespace review. Parent publication remains separate. |

## Tests run and results

Available `/usr/bin/python3` is **3.9.6**; no project `.venv`/`venv` or Python
3.12/3.13 executable was found. Research utilities use only the standard library;
no dependency changes/installations. Actual commands from repository root:

| Command | Actual result |
| --- | --- |
| `python3 -m unittest discover -s simulations/live-score-v1/task4-awards -p 'test_*.py' -v` | **18 passed** after final scoring/data changes. Identity, source/component binding, strongest-once/additive components, caps, Sundance convergence, bonus restrictions/off-in-base, positive/absence contradiction, pending/unavailable behavior, real/synthetic deltas, deterministic bytes and Git pins. |
| `python3 -m unittest discover -s simulations/live-score-v1 -p 'test_*.py' -v` | **20 passed**, retained Task 1 tests; this discovery does not recursively include hyphenated research directories. |
| `python3 -m unittest discover -s simulations/live-score-v1/task2 -p 'test_*.py' -v` | **14 passed**, retained Task 2. |
| `python3 -m unittest discover -s simulations/live-score-v1/source-validation -p 'test_*.py' -v` | **18 passed**, retained Task 3 synthetic/mocked access tests, no provider reads. |
| `python3 simulations/live-score-v1/calibrate.py --check` | Passed, Task 1 bytes unchanged. Offline preservation execution only; not a new Audience calibration or observation. |
| `python3 simulations/live-score-v1/task2/compare.py --check` | Passed, Task 2 bytes unchanged; same offline preservation distinction. |
| `python3 simulations/live-score-v1/source-validation/validate_sources.py` | Passed in **synthetic_offline** default, two invented observations, eight-ID manifest, **network_requests0**. No gated network flags used. |
| `python3 simulations/live-score-v1/task4-awards/compare.py` then `--check` | Six generated artifacts reproduce byte-for-byte; no network, audience calculation or baseline writes. |
| `git diff --check` plus new-file whitespace and scope review | Passed; reviewed tracked diff and new packet/docs. |

Total **70 focused/preservation tests passed**. No full repository runtime-suite,
supported-version CI, production scorer/service, network integration or deployment
verification is claimed. No runtime modules/dependencies changed, so the latest
scoped task's research checks apply; no production checks were run.

An early provenance test found the initial manifest covered 28 packet files but
omitted six archived Task 1/2/3 brief/report files. The manifest was expanded to
34 and the test then passed against each pinned Git object. Final results above
are reruns, not that earlier failed attempt.

## Deployment result

**Not authorized and not performed.** No seedbox, Radarr, tracker, media,
downloader, Telegram, notifier, live service/integration, private credential/state
or operational access. No daemons, provider contact, paid budget, authenticated
provider calls, rating acquisition, runtime collector/cache/event work, catalog/feed
mutation, merge or main promotion. Existing unrelated task/decisions and source-
validation implementation remain unchanged.

## Unexpected findings

Buildings' official Fortnight dossier establishes a side-section world premiere,
which earns zero under existing main-Competition policy. It does not certify main-
Competition absence. Nina's screenplay attribution is strengthened by a readable
mirrored official-jury PDF, distinct from failed Berlinale-origin access. Gotham's
International Feature win for Accident remains outside the existing component.
These are real evidence distinctions with zero marginal base points.

LAFCA archive/press reads still fail, even though indexed primary excerpts surface.
No new LAFCA negatives are asserted; Anora's retained positive is not erased.
TIFF-origin/syndicated direct reads and Cannes 2026 selection access also failed.
Attempted, unvalidated URL paths are labeled failures rather than fabricated
supporting citations. Accessible complete Spirit/EFA/BAFTA/Gotham/Sundance scopes
were completed independently, without bypassing any barrier.

## Unresolved issues and risks

- Evidence remains partial for every film; the machine-readable matrix lists
  exact pending, unchecked and unavailable category/edition/stage scopes. The
  1,101 unresolved envelope cells must not be read as verified zeros.
- New evidence did not change a scored component or demonstrate a misattribution.
  Zero score change is the result, not evidence that all award gaps are closed.
- TIFF +4 and main-Competition screenplay +6 remain independent sensitivity
  proposals: Hamnet +4; Substance/Nina +6. No adoption/completeness policy.
- Legacy EFA expanded nominations/shared Globe component mappings are retained,
  flagged for review; no new category weights, section eligibility or convergence.
- Public web-reader results can be cached; source observation day is not guaranteed
  origin freshness. Mirrored/indexed/secondary/retained provenance is separate.
- Audience/provider enquiry is untouched; no source availability, rights or
  confidence calibration conclusion is inferred from this awards-only task.

## Commit and PR reference

Worker did **not** commit, push, comment, reopen/edit/merge #88 or publish a PR.
Parent owns publication on `automation/issue-86-worker`. Supervisor says #88 is
closed/unmerged; new research PR must link #86/#88 and identify the new Task 4
delta against `824ed090e93c69e7ee5af6fe7df398725d8a6056`. Inherited Task 1/2/3
research remains prior unmerged work, not newly claimed delivery. No infrastructure,
claim refs or schedules were touched; no extra worker/runner launched.

## Project context updates

Only a narrow Task 4 research-status addition to `docs/PROJECT_STATE.md`.
Completed brief/report saved here; **`docs/CODEX_TASK.md` and `docs/DECISIONS.md`
intentionally unchanged** under the latest task's explicit prohibition. User and
ChatGPT review the findings, remaining gaps, candidate awards and display wording;
no next task, provider trial, production phase or cohort expansion is commissioned.
