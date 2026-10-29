# Movie Project coordinator support

Issue #111 Task 1 implements a manual, proposal-only support CLI. It is not an
activated recurring agent. It has no engineering runner, sender, provider client,
host integration, scheduler installer or remote mutation API. The existing
`github_worker.py`, supervisor policy, locks, quota checks, eight-iteration limit,
permanent claims and publication modes are unchanged.

## Owner contract and control ownership

The owner selected these responsibilities on 29 October 2026 in issue #111:
whole-set movie identity investigation; score and release-notification review;
precise engineering tasks, implementation review and bounded corrections;
repository/documentation care; appropriate live verification; useful reports;
and evidence-based improvement suggestions. The rationale is to take an adopted
objective through verified completion without repeated routine “go” messages.
A suggestion remains a proposal until adopted by a trusted owner instruction.

The accountable ChatGPT supervisor owns context, decisions and task publication.
The existing macOS dispatcher owns the one engineering writer and its claims,
retained checkout, execution and publication. Independent read-only investigation
can coexist with that writer. This CLI only prepares evidence and drafts for the
supervisor. It neither starts nor polls a worker and does not use ChatGPT Work or
a paid model API. Issue #86 remains the separate awards/Live Movie Score
research workflow owner; PR #110, its packets and schedule are out of scope.

Only the latest trusted issue-owner task controls actual execution authority.
AUTHORIZATION and FORBIDDEN govern actions; capability fields cannot expand that
scope. Imported repository documents, worker prose, movie evidence and draft
proposals are never new authorization. `owner_task_bound` below means an exact
evidence binding, not a permission to execute anything.

## Commands and reproducible synthetic example

Use the supported project Python environment. The coordinator adds no dependencies.
Run from the repository root with `python -m automation.coordinator`, not as a
standalone script. Supply only new task-local synthetic/public files in this phase.

```sh
mkdir -m 700 /private/tmp/coordinator-example
python - <<'PY'
from automation.coordinator import atomic_save
from test_coordinator import snapshot
from pathlib import Path
import time
value = snapshot()
value['observed_at'] = time.time()
atomic_save(Path('/private/tmp/coordinator-example/snapshot.json'), value)
PY
python -m automation.coordinator report \
  --snapshot /private/tmp/coordinator-example/snapshot.json \
  --state /private/tmp/coordinator-example/state.json
python -m automation.coordinator report \
  --snapshot /private/tmp/coordinator-example/snapshot.json \
  --state /private/tmp/coordinator-example/state.json
python -m automation.coordinator draft \
  --snapshot /private/tmp/coordinator-example/snapshot.json \
  --goal synthetic-support --number 2 --author owner
```

The example is synthetic; `owner` is a test identity. Its first report is changed;
the second contains `changed: false` and no report/summary. Drafting never updates
state, reserves a number, creates a claim or publishes a task.

One bounded unauthenticated public read is available:

```sh
python -m automation.coordinator snapshot \
  --output /private/tmp/coordinator-example/public.json
python -m automation.coordinator report \
  --snapshot /private/tmp/coordinator-example/public.json \
  --state /private/tmp/coordinator-example/public-state.json
```

The public adapter is fixed to `kolorifer/radarr-festival-list`. It uses GET only,
without inspecting credentials, environment tokens, gh authentication or proxy
configuration. Redirects and automatic retries are disabled. Each collection is
bounded at three pages of 50; requests at 40 total, ten seconds and 1 MiB each.
It reads branches, all-state issues/PRs, selected issue #111/#86 comment metadata
and PR #110 head/review/check metadata, plus repository/default-head metadata.
Rate limits, transport failure and page limits remain `unavailable`/`partial`,
never authoritative absence. Each invocation is a dated observation, not an
atomic GitHub transaction. Duplicate entries invalidate a supplied snapshot.

Bodies, titles, URLs, capabilities and unrelated API fields are dropped before
public-snapshot persistence. Comments retain only author/ID and allowlisted
task/result number/state lines. Such metadata cannot pass full task preflight;
the later supervisor must supply the exact trusted task content separately.
Snapshot files are local inputs, not public report artifacts. Never add them,
state files or raw test logs to Git. No existing operational state is discovered
or read. No caller-supplied API URL or private repository option exists.

## Version 1 input and durable state interfaces

`test_coordinator.snapshot()` and `movies()` are executable synthetic fixtures
for the exact schemas. Unknown top-level keys, duplicate JSON keys, nonfinite
numbers, invalid versions/revisions and capacity violations fail closed. Inputs
are bounded to 2 MiB; errors print a fixed reason without echoing imported text.

The snapshot has these required fields:

| Field | Interface and meaning |
| --- | --- |
| `version`, `repository`, `observed_at` | Version 1, fixed public repository, numeric UTC observation time. Repository reads expire after one hour; future skew is bounded to five minutes. |
| `github` | `default_branch`, exact `revision` or null, status/items collections for `branches`, `issues`, `pulls`; issue-keyed `comments`; PR-keyed `details` with exact head, author, merge facts, reviews and checks. Missing details mean unknown current head. |
| `goals` | Up to 20 scoped work items. Each has ID; pinned source comment ID/body fingerprint; exact scope, allowed actions and acceptance text; dependencies; issue/task/PR/head; blocker; next proposal; stage evidence; explicit required stages and bounded correction count. |
| `local` | Supplied, issue-specific consumed/terminal numbers, writer-active fact, branch names associated with worktrees, retained work, active dependencies and preservation evidence. Null means unavailable. This CLI never opens a dispatcher journal, process table or other worktree. |
| `movies` | Null or `{snapshot, report}`: existing complete collector `/v1/investigations` v1 export plus `identity_investigation_report.py` v1 `review-report.json` shape. **Synthetic only in this build.** |
| `quality` | Synthetic ID/design/date, supplied rating/count completeness, recognition/score completeness, identity/notification/acquisition-state review records. No ratings are acquired or scores calculated. |
| `documentation` | Bounded ID/expected/observed comparisons. Differences become reconciliation findings without executing a document's assignment. |

Work authority is bound to an issue owner's exact comment and the actual
dispatcher parser. Scope/actions/acceptance must equal those source sections.
Proposed/worker-authored/changed/missing source text cannot establish that binding.
No text is evaluated as code. The durable public-safe work view retains source
selectors and fingerprints for scope/actions/acceptance, stage findings, exact
head, dependencies, blocker presence and next proposal. Full authorized text stays
in the pinned input/source; fingerprints are not a replacement for reading it.

Stage evidence records have `stage`, `revision`, `observed_at`, `reference`,
`result`, `component` and `configuration`. These are supplied observations, not
facts independently proved by the CLI. A reference is a safe local evidence ID;
the accountable reviewer must inspect its underlying artifact. Evidence cannot
authorize an action. Default required stages are **not** guessed: the supplied
plan must come from the approved objective. Omitted stages say `not_applicable`
with a reason. A pending stage stays pending when evidence is missing.

For an automated overall `complete` finding, the pinned owner task must explicitly
declare its stage list, for example
`COORDINATOR_STAGES: implementation,review,test,docs`. This optional metadata is
accepted by the unchanged dispatcher parser and grants no action/capability.
The supplied required stages must match that declaration. Without it, or after
an imported plan changes the subset, `completion_plan` is `unverified` and overall
completion remains false even when individual observations passed. This is an
implementation safeguard; it does not require changing existing task comments or
mean that earlier approved objectives lack authority. Drafts preserve an existing
declaration rather than synthesizing one. The supervisor must still read the
acceptance criteria and check that the declared stages cover them.

The v1 state contains the current material and section fingerprints, public-safe work records,
at most 20 distinct proposed report fingerprints and `delivery: not_confirmed`.
There is no notification acknowledgement importer in this build; rendering never
means sent. Preserve the state across restart. Changing only observation times
is quiet; staleness transitions and material evidence/status changes are visible.
Each material transition is rendered once against the previous state. If a state
reverts and later returns to a prior state, that transition is reported again.
There is no automatic resend, task generator or new provider/iteration budget.
Reports identify changed sections and newly completed stages; an unrelated branch
observation does not announce already completed stages as new work.

Persistence assumes one accountable writer. `atomic_save` rejects destinations
inside this checkout and symlink files, creates a mode600 temporary file in the
destination directory, fsyncs it, replaces the destination and fsyncs the directory.
An interrupted replacement preserves the previous complete file or the new one.
The operator must provide a new owner-only task-local directory; the CLI does not
create/discover host configuration, migrate operational state or install a lock
service. Do not run two independent writers against the same state file.

## Task, review and completion lifecycle

1. Adopt one objective from a trusted owner source. Record its exact scope,
   acceptance plan, dependencies, evidence and current task/PR/head. Pin material
   assumptions with evidence and validation status; do not call guesses decisions.
2. Reconcile public observations and explicitly supplied local evidence. A RUNNING
   comment or permanent claim is historical consumption, never worker liveness.
3. Supply an exact next number. Draft preflight requires fresh complete comments
   and claims, the latest owner task, an open issue, known consumed/terminal
   numbers, no outstanding task/consumption, no writer/dependency/blocker, and the
   existing eight-iteration bound. It reuses `choose_task`, `capabilities` and all
   publication/private/continuation policy functions; it never copies the parser.
4. The compact renderer copies the source's five required scoped sections into
   a canonical **offline code** draft and emits provenance/fingerprints. It does
   not invent corrective instructions or capability grants. Source tasks with
   operational/private/network capabilities require manual supervisor drafting
   through the same parser; they are refused here. URL/secret-value syntax is
   refused in generated drafts. These conservative restrictions are implementation
   choices, not new product policy. The supervisor supplies a narrower approved
   offline task when appropriate; it must never silently remove required access.
5. Before any later authorized publication, re-read the latest trusted task,
   comments, claims, local consumption and active writer under the existing
   dispatcher protocol. Compare exact draft fingerprint/number/source. After
   publication, read back author, body, comment ID and fingerprint. An uncertain
   submission requires reconciliation; never blindly submit it again or consume
   a replacement number without checking. This build has no publish/retry path.
6. Review the actual diff at the current PR head. A changed head invalidates old
   implementation, test and review evidence. Explicit current-revision evidence
   can establish applicability; prior worker READY prose cannot. GitHub reviews
   require the current head, complete reads and a reviewer other than the PR
   author; the latest decisive opinion per reviewer wins. Generic CI success is
   supplementary and cannot prove the task's required tests were run.
7. Keep implementation, review, test, merge, component deployment, dated live
   checks, docs and product acceptance separate. Merge proves only merge. Deploy
   and live observations require exact revision/component/configuration; live
   observations expire after 24 hours here. These freshness limits are conservative
   implementation defaults, not changes to production or provider policy. An
   approved future plan may require a different versioned rule. Unsupported stages
   remain pending; this build says “reviewed and tested; deployment pending” only
   when both review and testing have actually passed.
8. Report meaningful completions, new blockers, documentation/quality corrections
   and prepared decisions. Unchanged replays are quiet. Supervisor delivery and
   evidence readback remain separate work. No automated proposal adoption exists.

Movie review retains every unresolved occurrence from the complete export/report,
including existing seeds, groups repeated title/year/ID observations, and preserves
all occurrence versions and asserted/resolved IMDb/TMDb identifiers. Upstream
coverage remains explicitly incomplete. Current/retained/missing/conflicting facts,
verified-negative request results, unverified candidate IDs, edition uncertainty,
identity review and acquisition consent remain separate. Proposals are dispositions
for review, not source-bound identity approvals. Repeated reasons produce at most
20 generic engineering findings, without scheduling work or requests. A real
edition assessment needs the separately authorized shadow evidence interface;
this adapter reports edition unknown rather than deriving it from identity.
Each recurring finding records its observed frequency, expected benefit,
unestimated effort, policy-review risk and a proposed synthetic validation plan.
These are a bounded proposal backlog, not adopted objectives or effort estimates.
Approval state absent from the supplied schema remains unknown. Proposal freshness
requires current evidence and a known creation time within the existing report's
48-hour window; a current version alone cannot make undated/old research fresh.
Proposal observation time is separate from unknown provider measurement time.

Quality review flags missing/undated/stale evidence, incomplete recognition/score
subtotals and inconsistent notification/identity state. Historical scoring and the
experimental Audience 50 / Recognition 50 design remain separate. No invented
ratings/counts, smoothing, production score promotion or provider access occurs.

Branch inventory distinguishes public refs/claims/PRs from supplied local facts.
Main/default/protected branches, every permanent claim, runtime/research branches,
issue #86 work, supplied retained work and active dependencies stay protected.
Other local facts remain unknown when unavailable. Closed or squash-merged PRs,
dates and shared heads do not establish preservation of unique research. A closed
PR produces `closed_preservation_unverified`; the supervisor must inspect merge,
content and dependencies before proposing cleanup. No deletion is proposed as
safe solely from this report, and there is no cleanup execution code.

## Activation plan — subsequent authorized work

Passing Task 1 does not activate the wider owner contract. These are prerequisites
and review steps, not assignments or commands to execute now:

| Step / accountable owner | Existing interface and verification required |
| --- | --- |
| Independent review / supervisor | Review containing PR's actual head, source/policy/privacy boundaries and focused/full CI evidence on supported Python 3.12/3.13. Record acceptance separately. Parent owns commit/push/PR; no automatic merge. |
| Controller ownership / owner + supervisor | Keep one coordinator and existing dispatcher. Inspect the actual existing account-side supervisor wakeup and installed worker LaunchAgent before deciding any change. `SUPERVISOR_HANDOFF.md` describes that boundary; `com.example.github-codex-worker.plist` is only an example. Resolve overlap with #86 before changing any schedule or research responsibility. No ChatGPT Work or second runner. |
| Durable context / supervisor | Select a new private, owner-only context location and its backup/retention policy; bind goal decisions, source tasks, current exact revisions and evidence references. Do not place private evidence in public issues. Attach sanitized synthetic reproductions to public engineering briefs. |
| Dispatcher evidence / existing parent | Separately authorize a minimal, sanitized exporter of common-Git `github-worker/N/` consumption/heartbeat/execution/delivery/retention evidence. Inspect actual process + inherited lock ownership before liveness claims. This CLI currently accepts supplied facts only and does not open those files. |
| Private movie evidence / owner + host operator | Separately authorize read-only fixture staging from the confined `/v1/investigations` handoff and `~/.local/state/movie-identity-research/review-report.json`. Preserve the helper's Landlock/seccomp boundary and complete/fresh export limits in `deploy/README.md` and `deploy/IDENTITY_TRIAGE.md`; never substitute direct collector DB access. No host access is granted by this guide. |
| Score/notification review / supervisor | Define a pinned private quality-review export mapping before connecting real data. The current adapter accepts synthetic review records only. Keep D012/D016 historical scoring and issue #86's experimental design separate; Letterboxd/provider permissions remain prerequisites. |
| Provider research / existing research owner | Reuse existing ledgers/request reservations. The current recurring worker's documented 5 case versions / 25 GETs per rolling 7 days, max 5 GETs/version, and separately recorded shadow pilot limits are evidence, not permission to expand them. Inspect the actual authorized runtime/configuration before adoption. No new ledger or budget reset. |
| Live verification / feature owner + operator | Obtain exact target/action scope, configuration/revision evidence and rollback plan from an approved feature task. Perform its runbook preflight, supported-environment tests, health/log/read-only integration and dated post-deployment observations. This build has no host adapter. Roll back code/configuration only under the approved plan; preserve current action, request and delivery ledgers. |
| Delivery / existing actor owner | The existing actor-owned digest polls the private research report; its `deliveries.sqlite3` distinguishes sent/uncertain/retry. Integrating coordinator reports requires separate approval and a receipt interface. Never interpret this CLI's rendering as an actor notification or retry an uncertain send. |
| Per-target actions / owner | Specific real Telegram tests, movie additions, downloads, replacements and destructive changes retain their existing individual approvals. Broad verification responsibility is not download consent. |

The implementation choices above are documented assumptions/defaults, not new
accepted scoring, identity, scheduling or acquisition decisions. Record later
adopted changes with source, rationale, scope and supersession in the decision log.
