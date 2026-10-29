# Engineering report: issue #111 Task 1 — coordinator support

The Task 1 record below is preserved as originally handed off. The appended
**Task 2 correction report** records the subsequent review fixes and fresh checks;
earlier test counts and pending-publication statements describe Task 1 only.

**Specification:** [Scoped brief](2026-10-29-coordinator-support-brief.md), control
issue #111 and latest issue-owner supervisor Task 1 supplied to this fresh worker.
Existing D001/D005/D007/D010 research/production/approval boundaries are preserved.
**Result:** Implemented support, awaiting independent review; broader agent not activated.
**Repository revision:** `automation/issue-111-worker`; clean starting/current
base HEAD `ae11228c45ee72044f30be65e10b3fecd76b1eb1`. The diff is uncommitted by
design. Parent runner owns the implementation commit and one public PR.
**Verification date:** 29 October 2026, local macOS worker; public repository
metadata observation at `2026-10-29T15:26:35.425782+00:00`.

## What changed

`python -m automation.coordinator` now prepares useful, proposal-only work and
repository reports from a versioned snapshot, maintains a restart-safe material
fingerprint, and preflights canonical offline task drafts through the real
dispatcher/policy functions. Work source selectors and scope/action/acceptance
fingerprints survive alongside separate implementation/review/test/merge/deploy/
live/docs/product-acceptance findings. New PR heads invalidate old evidence;
missing head/API/local evidence stays unknown. An explicit owner stage declaration
is required before an overall completion finding, so a supplied subset cannot
silently remove required review/tests from an approved objective.

The public adapter makes bounded unauthenticated GETs to this repository only.
It strips issue/PR bodies, titles, URLs, capabilities and unrelated payloads before
snapshot persistence. Whole-set movie adaptation uses the existing complete v1
export validator and report shape, with synthetic inputs only. Repeated cases
retain distinct occurrence versions and movie IDs. Evidence currency, dated
proposal freshness, missing/negative facts, edition uncertainty and unknown
identity/acquisition approval stay distinct. Quality fixtures yield findings about
missing evidence, partial scores and inconsistent states without calculation or
acquisition. Branch/documentation findings are retention/reconciliation proposals.

No dispatcher/policy/lock/quota/publication implementation changed. No host/private
operational state, service, provider, notification or media target was accessed.

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| `automation/coordinator.py` | Standard-library snapshot/state/CLI, real parser preflight, evidence stages, public metadata adapter, review and inventory projections. |
| `test_coordinator.py` | Executable synthetic snapshot/movie fixtures and 33 boundary/regression tests. |
| `automation/COORDINATOR.md` | Operating contract, schemas, persistence, lifecycle, conservative assumptions and concrete later activation plan. |
| `automation/README.md` | Narrow entry point linking support without changing dispatcher instructions. |
| `docs/PROJECT_STATE.md` | Implementation/review/activation distinction and verified limits. |
| `docs/reports/2026-10-29-coordinator-support-brief.md` | Archived scoped authorization and acceptance. |
| `docs/reports/2026-10-29-coordinator-support.md` | This engineering report. |

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| 1: baseline and preservation | Passed locally | Clean issue worker branch/base inspected. Other refs/worktree metadata observed only; unrelated work preserved. Dispatcher/policy, #86/#110 packets and `CODEX_TASK.md` have no diff. Parent publication pending. |
| 2–3: bounded inputs, state and authority | Passed synthetic/public support checks | Strict v1 schemas, duplicate detection, source task fingerprints, atomic mode600 persistence outside checkout, unknown/partial read distinctions, public-safe state. No credential/config/authentication access. |
| 4: drafts/numbering/parser | Passed for conservative offline code drafts | Actual `choose_task`, `capabilities` and existing publication/private/continuation policy functions invoked. Missing/duplicate/noncanonical/untrusted inputs fail. Claims/local consumption/terminal/writer evidence required. Operational/private/network drafts are explicitly refused for supervisor handling. |
| 5: revision-aware completion | Passed synthetic | New-head, missing-details, self/changes-requested/partial review, CI-only, merge/deploy separation and component/config/live-date checks. Owner-declared completion stages must match; stage evidence remains supplied evidence requiring review. |
| 6: movie/score/notification adapters | Passed synthetic only | Complete export/report set and base fields compared; two same-movie occurrences remain distinct. Fresh/retained/missing/conflicting and verified-negative facts tested. Unknown approvals/editions, incomplete scores and separate score designs preserved. No private/live adapter activated. |
| 7: inventory/reconciliation | Passed conservative support checks | Permanent claims, protected/default branches, runtime/research/#86, retained work/dependencies protected; local evidence unknown unless supplied. Closed PR preservation remains unverified. No cleanup operation. |
| 8: changed-state/report controls | Passed synthetic and public replay | Restart, timestamp-only quiet replay, expiry transitions, bounded proposal history and correction/iteration limits. Rendered output always has delivery unconfirmed. No notification acknowledgement importer. |
| 9: guide/activation | Written, awaiting review | Exact current public/fixture interfaces and existing parent/private host/digest interfaces identified with ownership, prerequisites and verification. No schedule/activation change. |
| 10: validation | Focused passed; full suite environment-limited | Exact commands/results below. Supported Python/dependencies/CI remain required before acceptance. |
| 11: public smoke | Passed adapter/report path only | Complete branch/issue/PR collections, 138 observed branches, same snapshot rendered twice with one changed report. No worker liveness or deployment inferred. |
| 12: handoff/publication | Child handoff complete; parent publication pending | Brief/report/state links prepared; diff inspected. Child did not commit/push/create a PR. Containing parent commit/PR will bind the implementation revision. |

## Tests run and results

No project virtual environment existed in this checkout or at the launcher's
documented `.venv` path. Created the new task-local environment
`/private/tmp/movie-coordinator-111-venv` using system Python **3.9.6**, without
installing dependencies or fetching packages. Commands below use its Python;
there are no dependency changes, so `pip check` was not required.

```sh
python3 -m venv /private/tmp/movie-coordinator-111-venv
/private/tmp/movie-coordinator-111-venv/bin/python -m unittest test_coordinator -v
/private/tmp/movie-coordinator-111-venv/bin/python -m unittest \
  test_coordinator test_github_worker test_supervisor_policy \
  test_supervisor_communication -v
/private/tmp/movie-coordinator-111-venv/bin/python -m unittest -v
git diff --check
PYTHONPYCACHEPREFIX=/private/tmp/movie-coordinator-111-pycache \
  /private/tmp/movie-coordinator-111-venv/bin/python -m py_compile \
  automation/coordinator.py test_coordinator.py
```

- Final coordinator checks: **33 passed**. Cases include actual parser calls,
  invalid/untrusted/duplicate fields, source scope changes, ambiguous numbering and
  outstanding consumption, incomplete/stale reads, restart/atomic failure/replay,
  new-head invalidation, independent current-head review, false deployment/CI
  inference, component/config/date evidence, whole-set/occurrence checks,
  fresh/retained/missing/negative facts, privacy, incomplete scores, permanent
  claim/unique research retention and proposed-versus-confirmed delivery/authority.
- Existing dispatcher/policy checks initially passed **71 tests**. The final
  combined coordinator/dispatcher/policy/communication checks passed **144 tests**
  in **113.038 seconds**. The final malformed-body guard was rechecked by the
  final 33-case coordinator run after that combined run.
- Full-suite attempts are **not passing** in this environment. The earlier run
  was 654 tests / 109 errors / two skips; the next was 660 / 109 / two skips.
  Errors were missing `requests` (84) and `bs4` (nine), plus Python 3.9 API gaps:
  `unittest.TestCase.enterContext` (ten), SQLite error attributes/constants
  (three), plus three synthetic HTTP `RemoteDisconnected` errors, which remain
  unverified on the supported environment. These numbers include import failures;
  they do not imply all tests were
  collected successfully. Supported CI uses Python 3.12/3.13 and installs existing
  `requirements.txt`. The final run/result is recorded below.
- `git diff --check` passed for tracked edits. New-file whitespace checks and
  final documentation link verification are recorded below.
- Compilation passed with the task-local cache prefix. An earlier invocation
  without it was refused by the sandbox because Apple's Python selected a cache
  outside writable roots; no permission override or environment change was made.

Final full-suite result: **664 tests in 246.374 seconds; FAILED, 109 errors,
two skips**. The error categories above remain unresolved here; this is an
environment-limited attempt, not full-suite acceptance.
Tracked `git diff --check` and new-file whitespace scans passed; the latter used
`git diff --no-index --check /dev/null <new-file>` (exit 1 represents added content,
with no whitespace diagnostics). Local Markdown file targets resolved. Synthetic
report/draft CLI commands also passed without consuming a number.

### Bounded public GitHub smoke evidence

```sh
/private/tmp/movie-coordinator-111-venv/bin/python -m automation.coordinator snapshot \
  --output /private/tmp/movie-coordinator-111-smoke/snapshot.json
/private/tmp/movie-coordinator-111-venv/bin/python -m automation.coordinator report \
  --snapshot /private/tmp/movie-coordinator-111-smoke/snapshot.json \
  --state /private/tmp/movie-coordinator-111-smoke/review-state-v1.json
# Repeat the report command with the same snapshot/state.
```

Public snapshot revision: `ae11228c45ee72044f30be65e10b3fecd76b1eb1`.
Observation: `2026-10-29T15:26:35.425782+00:00`.
Branch/issue/PR read status: **complete**; **138 branches** observed.
Sanitized persisted snapshot: **35,060 bytes**, outside tracked files.
Material fingerprint:
`02deede2803941e769f94bf65877a93c581585deb00d75d16f787be0556827b1`.
First final-code render: `changed: true`; second: `changed: false`, same fingerprint,
no repeated report, delivery still `not_confirmed`. The implementation was refined
after an initial development snapshot to project metadata before persistence;
the final bounded network snapshot and offline report replay above use that
sanitized projection. No raw response, comment body or private input is attached.

The issue #111 Task 1 and #86 Task 4 claim metadata both said RUNNING; the report
correctly labels their actual worker liveness **unknown**. This smoke establishes
the GET/projection/report path only. It does not verify local parent activity,
seedbox health, production identity/scoring, deployment or autonomous execution.

## Deployment result

Not authorized; none performed. No merge, service/daemon/schedule installation or
change, activation, notification, movie action or private-state read occurred.
Independent review and supported-environment full-suite success remain pending;
do not describe this build as production-complete or the wider agent as live.

## Unexpected findings

The available system Python and absent dependencies cannot execute the existing
full suite successfully; no attempt was made to acquire a different runtime or
packages outside this task's public-repository network scope. Public GitHub's
full PR/issue objects also contain far more text than this support layer needs;
the adapter now retains only allowlisted metadata. Remote claims and differing
local worktree heads were treated as retention/history evidence, not instructions
to resume their work or assertions about live activity.

## Unresolved issues and risks

- Independent code/privacy review and supported Python 3.12/3.13 full-suite CI
  are prerequisites to acceptance. Local full-suite errors are not waived.
- The CLI validates structure/bindings, not the truth of supplied observation
  artifacts. The supervisor must inspect underlying evidence at exact revisions.
  Owner-declared stage metadata cannot replace reading full acceptance criteria.
- Generated drafts intentionally cover offline code tasks with unchanged source
  sections. New corrective instructions, operational/private/network capabilities
  and publication reconciliation require the accountable supervisor; this is not
  a self-publishing engineering agent.
- State persistence assumes one writer in an owner-only task-local directory.
  GitHub pagination is bounded and not transactionally consistent. Failures/unknowns
  are visible. No real delivery acknowledgement interface is implemented.
- Actual private movie/score/notification and local parent evidence must be
  separately authorized and mapped before activation. Edition assessment remains
  unknown when the supplied schema has no supporting edition evidence.
- Conservative freshness/retention/proposal defaults are implementation choices,
  documented in the guide; no scoring, identity or provider policy was adopted.

The [activation plan](../../automation/COORDINATOR.md#activation-plan--subsequent-authorized-work)
identifies the existing supervisor/dispatcher ownership, selected public inputs,
future authorized private exports, parent execution/delivery interfaces, actor
digest, evidence/receipt prerequisites and live runbook verification/rollback
requirements. It explicitly requires resolving #86 overlap before schedule changes
and preserves all per-target notification/acquisition approvals.

## Commit and PR reference

Parent publication pending on `automation/issue-111-worker`; no child Git
publication or issue comment. Use this report's containing parent-created commit
and PR to identify the exact implementation revision. No merge/deploy/cleanup.

## Project context updates

Archived this scoped brief/report, linked the operating guide from automation
documentation and added a narrow project-state entry separating implementation,
technical verification, independent review, deployment and acceptance. The owner
responsibilities are attributed to issue #111; implementation defaults remain
labelled. No decision log rewrite or new scoring policy. The unrelated active
`docs/CODEX_TASK.md` is preserved per the task's explicit exception. The movie
notification guide is unchanged because no live notification behavior changed.

## Task 2 correction report — 29 October 2026

**Specification:** Task 2 in the [scoped brief](2026-10-29-coordinator-support-brief.md),
[owner task](https://github.com/kolorifer/radarr-festival-list/issues/111#issuecomment-6501726303)
and [dated review](https://github.com/kolorifer/radarr-festival-list/issues/111#issuecomment-6501717512).
**Result:** Three support corrections implemented, awaiting independent review
and supported-environment CI at the parent-published revised head. Wider agent
activation, merge, deployment and product acceptance remain pending.
**Revision:** Existing branch `automation/issue-111-worker`, PR #112. Starting and
worker-final Git HEAD is `9763271299a490a168b0e9bb4163d5e3130becda`; the correction
diff is intentionally uncommitted. The parent dispatcher owns commit/push/PR/issue
reporting and supplies the exact new head after publication. No new hash is
claimed for these uncommitted changes.

### What changed and why

| File/component | Correction and evidence |
| --- | --- |
| `automation/coordinator.py`: quality audit | Removed the blanket delivery/identity violation. Optional notification type and acquisition eligibility default to unknown for old fixtures. Safe informational Unknown Movie and identity-review notifications can remain unresolved. Acquisition eligibility/offered action with unresolved identity, ineligible acquisition actions, type contradictions and identity-inconsistent acquisition approval have separate findings. Output preserves delivery, identity, eligibility and approval separately. |
| `automation/coordinator.py`: test stage | Always surfaces selected-head CI read/result/counts/fingerprint, including when supplied test evidence passes. Failed/pending/partial checks leave testing pending until independent applicability evidence resolves the conflict. Failed supplied tests remain failed. Prior-head checks do not contradict current-head tests; green CI alone never establishes task-specific coverage. |
| `automation/coordinator.py`: public snapshot | Added repeatable `--issue`/`--pr` canonical numeric selectors, at most two distinct targets each, replacing that option's defaults. Selected PR metadata is included outside the bounded listing window. Invalid, duplicate and excess selectors fail before network. Transport/repository/projection/page/request limits are preserved; selected target failures remain partial/unknown. |
| `test_coordinator.py` | Regression fixtures for all three review findings, independent applicability and freshness/schema boundaries, selected PR projection, CLI defaults/refusals and incomplete reads. |
| `automation/COORDINATOR.md` | Selector syntax/limits, notification semantics, CI evidence schema and conservative adjudication requirements; existing activation gates preserved. |
| Scoped brief/report and `docs/PROJECT_STATE.md` | Task 2 authority, exact baseline, fresh verification and remaining review/CI/activation gates. Task 1 history retained. |

The notification semantics follow the existing production guide's topic routing
and confirmation-action sections; no production notification behavior changed.
`action_eligible` specifically means acquisition eligibility, so a review-evidence
button does not assert a download action. A verified acquisition button does not
imply its per-release approval has been given. Unknown type/eligibility produces
an evidence-gap finding instead of an inferred violation.

The CI resolution schema is a routine conservative implementation choice, not a
new owner policy. Optional `ci_resolution` on the latest current-head test evidence
binds an exact checks fingerprint, separate evidence reference, independent
reviewer, observation time and `unrelated`/`superseded` disposition. The date must
postdate both the snapshot and tests; a superseding rerun must also have current
tests dated at/after the snapshot. The reviewer differs from the PR author. New
head/check content or snapshot time invalidates old adjudication. Incomplete
collection reads cannot be overridden; reread them completely first. Even resolved
failures remain visible as GitHub facts. The CLI validates supplied bindings, not
the truth/authenticity of an artifact: independent inspection remains mandatory.
Skipped/neutral or unknown check outcomes conservatively require applicability
review rather than being assumed to cover task requirements.

### Acceptance and verification

The three regressions have synthetic tests. The delivered Unknown Movie case has
no violation; unresolved acquisition actions and approval raise separate findings.
Supplied passing tests plus current failing/pending/partial CI stay pending and
cannot complete the owner-bound plan. Current success plus current task evidence
can pass; stale task evidence and CI-only success cannot. Applicability evidence
requires independent reviewer/reference, exact fingerprint and valid dates; partial
reads, changed observations and failed tests cannot be hidden. Review, merge,
deploy and acceptance stages remain separate. Selected PR head/reviews/checks and
projection are tested with invalid/duplicate/over-limit argument refusal before
network access.

Fresh local command results are recorded below. A new task-local Python **3.9.6**
virtual environment was created at `/private/tmp/coordinator-111-task2.ZKAKys/venv`.
No supported 3.12/3.13 interpreter or project virtual environment was available;
no packages/runtime were fetched outside the authorized public-GitHub read scope.
Dependencies are unchanged; dependency installation and `pip check` were not run.

```sh
python3 -m venv /private/tmp/coordinator-111-task2.ZKAKys/venv
# Commands use the new environment's Python:
python -m unittest test_coordinator test_github_worker test_supervisor_policy test_supervisor_communication -v
python -m unittest -v
python -m unittest test_coordinator -v
python production_scoring.py --check
PYTHONPYCACHEPREFIX=/private/tmp/coordinator-111-task2.ZKAKys/pycache \
  python -m py_compile automation/coordinator.py test_coordinator.py
git diff --check
```

- Combined coordinator/dispatcher/policy/communication run: **155 passed in
  88.731 seconds**, including 44 coordinator tests. After adding an additional
  resolution-schema test and tightening regression assertions, the final
  coordinator-only run: **45 passed in 0.522 seconds**. The implementation did
  not change between these runs.
- Full local suite: **675 tests in 465.148 seconds; FAILED, 109 errors, two
  skips**. This run collected the 44-test coordinator version before the final
  test-only additions above. Errors were missing `requests` (84), missing `bs4`
  (nine), Python 3.9's missing `TestCase.enterContext` (ten) and SQLite error
  attributes/constants (three), plus three synthetic HTTP `RemoteDisconnected`
  errors. Those HTTP failures remain unverified on the supported environment;
  they are not silently attributed to missing dependencies. Import errors mean
  this is not proof that every repository test was collected. No full-suite
  success is claimed for the correction diff.
- Frozen scoring check **passed**: 1,909 candidates, 224 grandfathered, 163 new,
  387 qualified. No scoring/catalog files changed.
- Compilation, CLI snapshot/report/quiet replay, scoped changed-file allowlist,
  local Markdown target checks, added-diff credential-pattern scan and
  `git diff --check` **passed**. The complete scoped diff was inspected. The
  privacy check covers these synthetic/public changes; it makes no claim about
  uninspected downstream/provider logs. No state files or raw logs were added.

### Bounded public PR #112 smoke and historical CI

```sh
python -m automation.coordinator snapshot --issue 111 --pr 112 \
  --output /private/tmp/coordinator-111-task2.ZKAKys/public.json
python -m automation.coordinator report \
  --snapshot /private/tmp/coordinator-111-task2.ZKAKys/public.json \
  --state /private/tmp/coordinator-111-task2.ZKAKys/cli-state.json
# Repeat the report command with the same snapshot/state.
```

Observed at **`2026-10-29T16:05:04.340941+00:00`**:
PR #112 head **`9763271299a490a168b0e9bb4163d5e3130becda`**, not merged,
complete reviews (zero records) and complete checks (two completed successes).
Default branch remained `ae11228c45ee72044f30be65e10b3fecd76b1eb1`.
Branch/issue/PR listing reads were complete; 140 branches observed. Persisted
allowlisted snapshot was 33,993 bytes outside the checkout. Reconciliation from
empty state and replay of the saved state produced `changed: true` followed by
`changed: false`; fingerprint
`8475ec44c6bdefe6fd472496412a786c0b76494d6c3527603de706154373c2e8`.
Delivery remained `not_confirmed`. Issue #111 Task 2's public RUNNING metadata
was explicitly reported with worker liveness `unknown`.

Read-only inspection of [Actions run 40905610701](https://github.com/kolorifer/radarr-festival-list/actions/runs/40905610701)
verified successful Python 3.12 and 3.13 jobs at the **original** head above,
including dependency installation/check, full unittest and frozen scorer steps.
The run completed at `2026-10-29T15:51:46Z`. These are historical Task 1 checks,
not CI evidence for this correction diff. Parent publication must produce the
revised head before supported CI and independent review can verify it. No CI run
was dispatched by the child.

This smoke verifies GET/selection/projection/report behavior only. It does not
verify parent process liveness, private runtime tests, services, notifications,
deployment or broad coordinator activation. No raw API payload or state/log
artifact is tracked.

### Deployment, limitations and disposition

No merge, deployment, host/private-state access, service/daemon/schedule change,
notification or movie operation was authorized or performed. No dispatcher,
authority/policy/claims/locks/quota code, issue #86/PR #110 work, scoring/catalog
or unrelated `docs/CODEX_TASK.md` changes were made. The original Task 1 commit
and report remain preserved; no history rewrite or branch cleanup occurred.

Remaining gates are independent review of the exact new head, supported 3.12/3.13
full-suite CI, and separate product acceptance. All original activation prerequisites
in `automation/COORDINATOR.md` remain: accountable controller ownership, separately
authorized private evidence mapping, durable context, dispatch liveness and delivery
receipt interfaces, and explicitly scoped live verification. This correction is
proposal-only support. Parent dispatcher retains commit/push/existing PR update
and issue result ownership; worker readiness does not establish review or deployment.

## Task 3 correction report — 29 October 2026

**Specification:** Task 3 in the [scoped brief](2026-10-29-coordinator-support-brief.md#task-3--final-authorized-correction-29-october-2026)
and the [consolidated review](https://github.com/kolorifer/radarr-festival-list/issues/111#issuecomment-6501900446).
**Result:** Five demonstrated support findings corrected with synthetic
regressions, ready for independent review after parent publication. This is the
final authorized correction round; it creates no new assignment or retry loop.
**Repository revision:** Clean starting checkout on `automation/issue-111-worker`,
`b37f5791cba20444272f95fab0565ec9404cb745`, retaining Task 1/2 and PR #112.
Worker changes are uncommitted. The exact correction revision is this report's
containing parent-created commit on [PR #112](https://github.com/kolorifer/radarr-festival-list/pull/112);
the parent owns commit/push/PR/terminal reporting. No future hash is invented.
**Verification:** 29 October 2026, local Python 3.9.6 synthetic tests and bounded
public GitHub metadata only. No host/private/provider/service observations.

### What changed, files and finding dispositions

All five findings were reproduced offline against unchanged starting code before
editing: claim/result blocked draft 2 with `draft_authority_not_latest` and left
RUNNING; newer B deployment/live left A passed; a supplied review disappeared
under empty GitHub reviews; a later owner brief left old authority bound; changing
runtime 90 to 120 left `changed: false`. Reproductions used the shipped synthetic
fixtures and real dispatcher/export validators, not production events.

| Finding / files | Implemented disposition and verification |
| --- | --- |
| Lifecycle — `automation/coordinator.py`, `test_coordinator.py` | Actual dispatcher selection recovers the current governing brief without applying consumption to scope inspection. Claims/status/results are reconciled separately; latest valid trusted terminal state applies only to the relevant task. Normal READY_FOR_REVIEW/FAILED/NEEDS_USER histories allow a proposal for the exact next number when the original local terminal/writer/consumption gates pass. Duplicate/partial/noncanonical records stay unknown. Older late results cannot replace newer work. No consumed number is replayed and liveness stays unknown. |
| Deployment/live — same files | Current component observations are selected across revisions/configurations before applicability. Later rollback/configuration replacement invalidates old completion; live evidence must match the latest successful deployment and postdate it, within the existing 24-hour window. All observed components must pass. Equal-time conflicts remain pending. History is retained separately. An independently receipted exact implementation-to-actual-merge/squash link can establish applicability; unmerged prospective merge SHAs, unrelated revisions, missing/bad lineage cannot. No deployment performed. |
| Independent review — same files | A pinned owner-published standalone supervisor receipt binds role, goal/source, exact head, purpose, artifact/time and payload digest. Valid independent-supervisor review survives empty complete GitHub reviews, including a shared owner/PR-author account. Worker claims, arbitrary booleans/account names and unreceipted same-account approvals cannot establish independence. Decisive conflicts, partial reads, new heads and conflicting equal-time supervisor receipts stay conservative. CI applicability now uses the same receipt model, binding the exact test artifact as well as checks/disposition. |
| Superseded scope — same files | Current authority must match the latest governing dispatcher-selected source. Any later corrective/revoking/revising/unclear brief requires explicit rebinding rather than inferred continuity. Non-ready scope-bearing instructions also block historical authority. `authority_reason` exposes the uncertainty. Status/results/receipts/untrusted prose grant no scope. Failed/ambiguous task records prevent overall completion without erasing independently observed stage facts. |
| Movie materiality — same files | `material_evidence_v1` hashes validated source-schema fields and occurrence/version/evidence associations, including candidate/details runtime, date/year, crosswalk, confidence/context and method/query-to-result/candidate relationships. Raw private text is used only within an aggregate digest; unknown payload keys/source prose/observation timestamps are excluded. Separate regressions cover each material change, timestamp-only replay, restart and privacy. Source schemas, whole unresolved-set coverage and per-occurrence approval boundaries remain unchanged. |
| `automation/COORDINATOR.md` | Exact optional v1 receipt/lineage schema, payload constructors, compatibility/unknown-state behavior, supervisor trust limitations, lifecycle/current deployment selection, privacy and unchanged activation prerequisites. |
| Scoped brief/report, `docs/PROJECT_STATE.md` | Task 3 scope, baseline, findings, actual verification, publication binding and remaining acceptance gates. Task 1/2 history preserved. |

Task 2 notification semantics, conflicting-CI handling and selected-PR interface
remain covered. The dispatcher, policy/capability/locking/claims/quota/publication
implementation, permanent refs, #86/#110 research, production/scoring/catalog
files and unrelated `docs/CODEX_TASK.md` were not changed.

### Assumptions, compatibility and independent responsibility

These are conservative support implementation choices, not new product, scoring,
identity, acquisition or operational authority decisions. Any later governing
brief requires rebinding because free-text continuity cannot be mechanically
proved. The support layer does not interpret “stop” as a general executable rule.
Unknown/partial evidence remains unverified. Original observations remain in the
input, with deploy/live history also visible in reports.

Optional v1 evidence extensions are `supervisor_receipt` on review or CI
resolution, and `merged_from: {revision, receipt}` on deployment. Old observations
still parse but cannot gain review/CI approval without validated provenance.
V1 persisted work accepts optional `authority_reason` and deploy/live `history`;
reconciliation always recomputes facts instead of trusting old state approvals.
The movie digest explicitly identifies its projection as v1. Existing snapshots
can produce one material report on first reconciliation under the corrected
projection; subsequent unchanged replay stays quiet. No private state migration.

Receipts validate exact owner-source/binding structure, not independent review's
truth. The shared GitHub account cannot identify the person/process behind a
comment. The accountable supervisor must independently inspect the exact diff,
tests/CI relevance or merged-content equivalence, then publish/supply its own
receipt. A worker cannot self-approve by supplying passed evidence or naming a
different reviewer. No real receipt was created/published here. Underlying
artifacts and source-body readback remain supervisor responsibilities; sanitized
public snapshots intentionally omit full task/receipt bodies.

### Tests run and results

No project virtual environment or supported Python 3.12/3.13 interpreter was
available. Created a new task-local Python **3.9.6** environment at
`/private/tmp/coordinator-111-task3.6HyKOn/venv`, without installing dependencies
or acquiring a runtime. Dependencies did not change; `pip check` was not run.
Commands used that environment's Python:

```sh
python -m unittest test_coordinator -q
python -m unittest test_coordinator test_github_worker test_supervisor_policy test_supervisor_communication -v
python -m unittest -v
python production_scoring.py --check
PYTHONPYCACHEPREFIX=/private/tmp/coordinator-111-task3.6HyKOn/pycache \
  python -m py_compile automation/coordinator.py test_coordinator.py
git diff --check
```

Coordinator-only: **74 passed** after the final lifecycle/projection/receipt validation
tightening. Initial combined run: **184 passed in 68.837 seconds**. Initial full
suite: **704 tests in 200.596 seconds; FAILED, 109 errors, two skips**. Full-suite
errors comprise 84 missing `requests`, nine missing `bs4`, ten Python 3.9
`TestCase.enterContext` gaps, three SQLite attribute/constant gaps, and three
synthetic HTTP `RemoteDisconnected` errors. The HTTP failures remain unverified
on supported Python and are not silently attributed to dependencies. Import
errors mean not every repository test was necessarily collected. A full-suite
pass is not claimed. Final-code rerun results are recorded below.

Final source reruns after the last receipt/projection validation changes:

- **185 focused coordinator/dispatcher/policy/communication tests passed in
  78.795 seconds**, including all 74 coordinator tests.
- **705 full-suite tests in 228.713 seconds; FAILED, 109 errors, two skips**.
  Error categories match the counts above. This is an environment-limited attempt,
  not full-suite acceptance; the three synthetic HTTP errors remain unresolved
  on the available interpreter.
- Frozen scoring, final compilation, `git diff --check`, six-file scope allowlist,
  119 local Markdown targets, added-diff credential-pattern scan, synthetic movie
  privacy and final sanitized public report/state privacy checks passed. Legacy
  v1 state replay remained readable/quiet with unreceipted review pending.
- Runtime/test byte fingerprints were recorded before the final combined/full
  runs and compared afterward; they are unchanged. The complete scoped diff was
  inspected. No raw logs, snapshots or state were added to the checkout. Privacy
  results concern these public/synthetic artifacts, not uninspected downstream
  logging. No dependency or protected production-file change.

Frozen scorer **passed**: 1,909 candidates, 224 grandfathered, 163 new, 387
qualified. Compilation passed. Supported Python 3.12/3.13 current-correction CI
and independent review are external acceptance gates after parent publication.
Read-only public metadata inspection of
[Actions run 40909632850](https://github.com/kolorifer/radarr-festival-list/actions/runs/40909632850)
confirmed successful 3.12/3.13 jobs at **starting head `b37f579`**, completed
16:15:57 UTC. That proves Task 2 CI only. The supervisor supplied its independent
977-test 3.12 observation; this worker did not rerun or independently inspect
that job log. No CI run was dispatched.

### Bounded public snapshot/report/replay

```sh
python -m automation.coordinator snapshot --issue 111 --pr 112 \
  --output /private/tmp/coordinator-111-task3.6HyKOn/public-handoff.json
python -m automation.coordinator report \
  --snapshot /private/tmp/coordinator-111-task3.6HyKOn/public-handoff.json \
  --state /private/tmp/coordinator-111-task3.6HyKOn/handoff-state.json
# Repeat report with the identical snapshot/state; no second network snapshot.
```

The initial 17:39:07 UTC smoke was repeated once after final protocol-projection
hardening, using a new task-local snapshot/state. At final-source observation
**2026-10-29T17:49:34.464507+00:00**, selected PR #112 head was
**b37f5791cba20444272f95fab0565ec9404cb745**, not merged. Reviews were complete
with zero records; checks complete with two completed successes at that head.
Default branch was `ae11228c45ee72044f30be65e10b3fecd76b1eb1`; branch/issue/PR
reads were complete and 141 branches observed. The sanitized snapshot was 34,492
bytes, outside tracked files. First report changed; identical replay returned
`changed: false`, `report: null`, delivery still `not_confirmed`. Fingerprint:
`ec3b46ff73641dfcc8c432b8fc730ec42f853973abb031dae011498ceeca7a61`.
Task 3 RUNNING was historical claim metadata, with worker liveness **unknown**.
This verifies public GET/selection/projection/reconciliation only, not pending
correction CI, actual process liveness, delivery, services or deployment.

### Deployment result, remaining gates and disposition

No merge, deployment, activation, schedule/daemon/worker launch, host/private-state
access, provider acquisition, notification or movie operation was authorized or
performed. No Git publication or issue comments were made by the child. The
notification guide is unchanged because live notification behavior did not change.
The unrelated active task is preserved; this completed scoped brief is archived
here rather than replacing it. No decision-log policy was invented.

The parent must publish this diff on the retained branch/PR and bind subsequent
review/CI to the exact new containing commit. Independent review, supported
full-suite CI and product acceptance remain pending. All existing
[activation prerequisites](../../automation/COORDINATOR.md#activation-plan--subsequent-authorized-work)
remain: one accountable supervisor/controller, authorized private exports and
state location, parent execution/liveness and durable delivery evidence, scoped
live verification/rollback, existing provider limits and per-target approvals.
No follow-on task or unlimited correction loop is created by this report.

## Task 4 correction report — 29 October 2026

**Specification:** [Archived Task 4 brief](2026-10-29-coordinator-support-brief.md#task-4--newer-incomplete-observations-29-october-2026),
latest trusted owner `SUPERVISOR_TASK: 4`, and the
[final Task 3 review/candidate](https://github.com/kolorifer/radarr-festival-list/issues/111#issuecomment-6504539307).
The owner's explicit one-fix extension supersedes Task 3's stopping limit only
for this correction. The review itself was evidence, not new authority.
**Result:** Minimal correction implemented and locally tested; awaiting parent
publication, current-revision supported CI and independent review. Wider agent
activation and product acceptance are separate and remain pending.
**Repository revision:** Clean starting branch `automation/issue-111-worker`,
HEAD `1c5286ac8926d3493a47600453c527919f7e7ba3`; retained
[PR #112](https://github.com/kolorifer/radarr-festival-list/pull/112), verified open,
unmerged and at that exact head through read-only public metadata. Task 1–3
commits/history are preserved. This child leaves an uncommitted scoped diff;
the containing parent-created commit will identify Task 4, with the same PR.
**Verification date:** 29 October 2026, local macOS worker, synthetic fixtures;
public GitHub metadata reads only. No host/private/service observation.

### What changed and original failure

`deployment_status` formerly removed known-component records with
`configuration=None` before selecting the latest observation. Thus a newer
valid-time deployment/live record could be ignored while an older pass still
established overall completion. The schema already accepts unknown configuration.

Before changing runtime code, both new regression methods were run against
baseline logic: **two methods, four subcase failures**. A separate synthetic
fixture probe confirmed validation accepted every input and all four incorrectly
returned `complete: true`, deploy passed and live passed. Each started with the
shipped `deployed_plan()` (revision A/config-a deploy NOW-30, live NOW-20), then
added an actor deploy or live record at NOW-10 with unknown configuration, at
revision A or B. These are synthetic observations, not production events.

The fix is exactly the two reviewed logic changes: include known-component
valid-time observations in selection regardless of configuration, then require
configuration on both selected deployment and current observation to pass.
The selected incomplete record stays current and visible; no older evidence is
silently substituted. Unknown configuration remains unknown. Equal-time conflict
handling, component separation, lineage receipts, revision/configuration matches,
live chronology/freshness and history/projection are unchanged.

### Files and components changed

| File/component | Change and purpose |
| --- | --- |
| `automation/coordinator.py` | Two-line deployment reconciliation correction. |
| `test_coordinator.py` | Two regression methods, each covering revisions A/B, validation, selected observation, completion/stages and retained history. |
| `automation/COORDINATOR.md` | Explain incomplete current deployment/live observations and absence of older-pass fallback. |
| `docs/reports/2026-10-29-coordinator-support-brief.md` | Append the scoped Task 4 authority, acceptance criteria and boundaries. |
| This report | Append reproduction, results, revision binding and remaining gates. |
| `docs/PROJECT_STATE.md` | Record Task 4 support behavior and publication/CI/review status. |

### Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Exact baseline / retained branch and PR | Passed | Clean local HEAD and public PR metadata agree at `1c5286ac8926d3493a47600453c527919f7e7ba3`; no branch/claim/publication mutation by child. |
| Latest observation precedes configuration check | Passed locally | Minimal runtime diff; all original 74 coordinator tests retained and passing. |
| New incomplete deploy at A/B | Passed locally | Validation accepts it; completion false; deploy/live pending; selected incomplete deployment and three-record history retained. |
| New incomplete live at A/B | Passed locally | Validation accepts it; completion false; deploy passed/live pending; selected incomplete live observation and three-record history retained. |
| Scoped checks / frozen scoring / diff/privacy | Recorded below | Local checks concern this diff; supported full CI remains a separate gate. |
| Documentation and handoff | Implemented | Appended brief/report and narrow guide/state changes; Task 1–3 text and unrelated assignment preserved. |
| New revision supported CI / independent review | Pending | Must bind to the containing parent-published Task 4 commit, not baseline or the independent in-memory candidate. |

### Tests run and results

Only Python **3.9.6** was available on PATH and at conventional project/runtime
locations; no project venv or Python 3.12/3.13 interpreter was found. Created a
new isolated venv at `/private/tmp/coordinator-111-task4.HzkixP/venv` with the
available interpreter. No runtime/dependency installation or dependency change.
Logs stayed in that new task-local directory outside tracked files. Commands
below use that venv's Python:

```sh
python -m unittest \
  test_coordinator.CorrectionTests.test_newer_deploy_with_unknown_configuration_invalidates_deploy_and_live \
  test_coordinator.CorrectionTests.test_newer_live_with_unknown_configuration_invalidates_only_live -v
python -m unittest test_coordinator -v
python -m unittest test_github_worker test_supervisor_policy test_supervisor_communication -v
python production_scoring.py --check
PYTHONPYCACHEPREFIX=/private/tmp/coordinator-111-task4.HzkixP/pycache \
  python -m py_compile automation/coordinator.py test_coordinator.py
git diff --check
```

The first command ran before the runtime fix and failed in all four revision/stage
subcases as expected. After the fix, **all 76 coordinator tests passed in 1.076
seconds**, including the original 74 and the two regressions. **All 111 existing
dispatcher/policy/communication tests passed in 73.333 seconds** (187 passing
tests across the two runs). Frozen scoring passed:
1,909 candidates, 224 grandfathered, 163 new, 387 qualified. Compilation passed.

Final `git diff --check` and a task-local validation script passed: exact six-file
scope; no nonignored untracked artifacts; unchanged branch/HEAD; historical
brief/report bytes preserved as prefixes; tested runtime/test SHA256 values
unchanged; exactly two added test methods and no removed methods; all 122 local
Markdown targets/anchors resolve; no added-diff credential-pattern matches.
The complete scoped diff was inspected. Synthetic history/observation assertions
pass for each incomplete record; no raw snapshots or test logs were added.

Per Task 4, the known unsupported Python 3.9 full-suite failure was **not rerun**.
No local full-suite pass or new-head CI pass is claimed; no CI dispatch/rerun was
performed by the child. No `pip check` was needed because dependencies did not
change. The existing unchanged workflow retains dependency install/check, full
`python -m unittest -v` and frozen scoring on **both Python 3.12 and 3.13**.
These must pass on the exact parent-published correction revision.

Read-only public metadata confirmed both jobs and their dependency/full-test/
frozen-scoring steps succeeded in
[baseline Actions run 40925676885](https://github.com/kolorifer/radarr-festival-list/actions/runs/40925676885),
at `1c5286ac8926d3493a47600453c527919f7e7ba3`, completed 17:55:08 UTC.
The independent review records 1,006 full-suite tests on Python 3.12 and 74
coordinator tests; this child did not independently inspect that job log or rerun
those supported-environment tests. All of this is **baseline Task 3 evidence**,
not proof of Task 4 or the independent in-memory candidate.

### Deployment result, unexpected findings and unresolved gates

No merge, deployment, live verification or activation was authorized/performed.
There were no unexpected scope findings; the four baseline cases matched the
review exactly. Local test coverage is synthetic and interpreter-limited.
Independent review and supported current-revision CI remain pending; the child
does not assert product acceptance or truth of supplied operational evidence.

All [activation prerequisites](../../automation/COORDINATOR.md#activation-plan--subsequent-authorized-work)
remain unchanged: one accountable supervisor/controller, separately authorized
private exports/state, parent execution/liveness and durable delivery evidence,
scoped live verification/rollback, provider access/limits and per-target approvals.
No access to seedbox/private operational data, providers or credentials; no live
notification, movie/media mutation, worker/daemon launch or schedule change.
Privacy verification concerns the scoped public/synthetic diff and outputs only;
no downstream/provider logging was inspected or privacy guarantee inferred.

### Commit/PR disposition and project context

The parent owns commit/push, updates to existing PR #112 and issue/result reporting.
Review/CI must refer to the exact containing parent commit, whose runtime/test
files must match this locally tested diff. Baseline CI and historical claim
records cannot establish new-head acceptance or liveness. No additional task,
branch/PR, correction loop, merge or operational authority is created here.

The brief/report are appended to their existing files. The operating guide and
project state explain the corrected support behavior. Historical Task 1–3
reports, unrelated `docs/CODEX_TASK.md`, decisions, movie-notification guide,
#86/#110/research and protected production files are unchanged. Live notification
routing/actions did not change. The supervisor reviews this specific correction
and fresh supported CI through the parent publication path.
