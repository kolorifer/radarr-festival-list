# Movie Project coordinator support

The accepted #111/#112 foundation and issue #113 Task 1 provide manual,
proposal-only coordinator support. This is not an activated recurring agent. It has no engineering runner, sender, provider client,
live source collector, scheduler installer or remote mutation API. The existing
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
the second contains `changed: false` and no new report/summary, plus the same
recoverable `pending_outbox` ID/hash (use explicit `recover` for bytes). The legacy CLI output is local evidence,
not a publication or delivery acknowledgement. Drafting never updates
state, reserves a number, creates a claim or publishes a task.

One bounded unauthenticated public read is available:

```sh
python -m automation.coordinator snapshot \
  --output /private/tmp/coordinator-example/public.json --issue 111 --pr 112
python -m automation.coordinator report \
  --snapshot /private/tmp/coordinator-example/public.json \
  --state /private/tmp/coordinator-example/public-state.json
```

The public adapter is fixed to `kolorifer/radarr-festival-list`. It uses GET only,
without inspecting credentials, environment tokens, gh authentication or proxy
configuration. Redirects and automatic retries are disabled. Each collection is
bounded at three pages of 50; requests at 40 total, ten seconds and 1 MiB each.
It reads branches, all-state issues/PRs and repository/default-head metadata.
`--issue NUMBER` and `--pr NUMBER` select comment and exact PR head/review/check
metadata; each option can be repeated for at most two distinct targets. Explicit
selections replace that option's defaults (issues #111/#86 and PR #110). Numbers
must be canonical positive decimal integers no larger than 2147483647; duplicates,
URLs and excess targets fail before network access. Selected issues/PRs are
included even outside the bounded listing window. These selectors do not change
the repository, transport, page or request limits.
Rate limits, transport failure and page limits remain `unavailable`/`partial`,
never authoritative absence. Each invocation is a dated observation, not an
atomic GitHub transaction. Duplicate entries invalidate a supplied snapshot.

Bodies, titles, URLs, capabilities and unrelated API fields are dropped before
public-snapshot persistence. Comments retain only author/ID and allowlisted
task/result number/state lines. Such metadata cannot pass full task preflight;
the later supervisor must supply the exact trusted task content separately.
Ambiguous/duplicate/noncanonical protocol fields retain a fixed `STATE: UNKNOWN`
marker instead of silently becoming valid through projection. No discarded raw
text is copied into that marker, and it cannot establish authority or completion.
Snapshot files are local inputs, not public report artifacts. Never add them,
state files or raw test logs to Git. No existing operational state is discovered
or read. No caller-supplied API URL or private repository option exists.

## Foundation version 1 snapshot and reconciliation interfaces

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
| `movies` | Null or `{snapshot, report}`: existing complete collector `/v1/investigations` v1 export plus `identity_investigation_report.py` v1 `review-report.json` shape. The staged integration below validates actual producer contracts; this code task uses synthetic inputs only. |
| `quality` | Synthetic ID/design/date, supplied rating/count completeness, recognition/score completeness, identity/notification/acquisition-state review records. No ratings are acquired or scores calculated. |
| `documentation` | Bounded ID/expected/observed comparisons. Differences become reconciliation findings without executing a document's assignment. |

Work authority is bound to an issue owner's exact comment and the actual
dispatcher parser. Scope/actions/acceptance must equal those source sections.
Proposed/worker-authored/changed/missing source text cannot establish that binding.
The binding must also match the current governing owner brief selected by the
actual dispatcher with consumption temporarily excluded for scope inspection.
This inspection does not reserve or replay anything. Any later governing brief
requires rebinding, even when its text looks similar: free text cannot prove that
an older acceptance plan continues. Explicit revocation, a corrective assignment,
an ambiguous duplicate brief or a non-ready scope-bearing instruction prevents
old-plan completion. `authority_reason` explains the uncertainty; prior evidence
references and deployment history remain available. Status, claim, terminal
result and receipt comments never grant scope. Untrusted later text is ignored.
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

The test stage also reports `ci`: the selected head's check counts, collection
read status, result, exact checks fingerprint and any conflict resolution. Every
current-head failure, pending/unknown conclusion or incomplete read is surfaced
even with passing supplied tests. Such a conflict leaves testing pending and
prevents overall completion; it does not declare every failed check relevant to
the task. Prior-head checks are counted separately and do not contradict current
tests. CI success alone still cannot establish task-specific test coverage.

An optional `ci_resolution` on the latest same-head test observation documents
independent applicability evidence. It has `checks_fingerprint`,
`observed_at`, `reference`, `reviewer`, `disposition` and `supervisor_receipt`.
The fingerprint must match the reported CI fingerprint; the receipt must bind the
independent supervisor's inspection as described below (a reviewer name alone
does not establish independence, including a different account name);
the reference must identify a separate artifact from the test report. Its date
must be at or after both the snapshot and test observation and no later than now.
`disposition: unrelated` means the artifact documents why those checks do not
apply to this task. `superseded` means an independent artifact verifies a later
task-specific rerun; the passing test observation must also postdate the snapshot.
Partial/unavailable check reads cannot be resolved this way: obtain a complete
read first. Changed checks/head or a later snapshot require renewed evidence.
Failed supplied tests remain failed. The failed/pending GitHub facts remain in
the report even after adjudication. These are inspectable supplied assertions;
the CLI cannot authenticate the reviewer or prove the artifact's contents. The
supervisor must inspect the dated underlying evidence before accepting it.

### Independent supervisor receipts in the shared-owner workflow

Review and implementation can publish through the same GitHub owner account.
A same-account GitHub approval is still insufficient. A review observation can
instead carry `supervisor_receipt: {comment_id, body_sha256}` pointing to one
exact issue-owner comment whose entire single-line body is
`COORDINATOR_RECEIPT: <JSON>`. The JSON has exactly these fields:

| Fields | Required binding |
| --- | --- |
| `version`, `role`, `repository` | Integer 1, `independent_supervisor`, this fixed public repository. |
| `issue`, `task`, `pr`, `source` | Exact work selectors and pinned authorization source `{comment_id, body_sha256}`. |
| `revision`, `purpose` | Exact current implementation head; `review`, `ci_applicability` or `merge_lineage`. |
| `reference`, `observed_at` | Exact safe artifact ID and dated observation, no later than reconciliation time. |
| `payload_sha256` | `fingerprint(payload)` using the module's canonical JSON hash. |

For review, the payload is `{result: passed}` or `{result: failed}`, matching the
observation. For CI applicability, `ci_payload(test_observation)` binds every
resolution field except the receipt itself, plus the test artifact's revision,
reference, observation time and result. For merge lineage, the payload binds
`deployed_revision`, `component`, `configuration`, and `merge_commit`; the
receipt revision is the reviewed implementation head. The executable synthetic
constructors `test_coordinator.receipt`, `bind_review`, `bind_ci` and
`CorrectionTests.lineage` demonstrate exact bindings without publishing anything.

The support layer checks complete issue/comment reads, owner identity, exact
comment body hash, explicit supervisor role, goal/source/head/purpose/artifact/date
and payload bindings. It cannot authenticate which person or process used a
shared account, inspect an artifact's truth, or create independent review itself.
The accountable supervisor must independently inspect the exact diff, tests,
CI relevance or merged-content equivalence and publish/supply its own receipt.
Workers must never issue receipts for their own work. A worker claim, a supplied
boolean, an altered/unknown/untrusted source or an account name alone is
insufficient. No receipts were published by this build; only synthetic tests use
them. This format is evidence, never dispatcher authority or an execution grant.

A valid review receipt survives an empty complete GitHub review list. The latest
decisive GitHub opinion per reviewer still applies: changes requested block a
pass, including from the shared owner account. A failed supervisor receipt also
blocks a pass; conflicting receipts at the same latest observation time fail
conservatively. Partial relevant reads remain pending, and a new head invalidates
the receipt. Independent different-account current-head GitHub approvals remain
supported. The public adapter deliberately drops receipt bodies with other raw
comment text; the supervisor must supply exact authorized sources separately.

This is a compatible v1 input extension: review observations may add
`supervisor_receipt`, deploy observations may add `merged_from`, and CI resolutions
may add `supervisor_receipt`. Old v1 observations still parse; an unreceipted
review or CI resolution remains unverified and is never upgraded into approval.
Persisted v1 work accepts optional `authority_reason` and deploy/live `history`.
Reconciliation recomputes all current facts from the snapshot, never trusting
earlier state as authority. A schema/projection change may emit one changed report
on replay; subsequent unchanged replays remain quiet. Unknown fields/versions
remain refused. Existing v1 snapshot/state top-level keys are unchanged.

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

The pure `reconcile`/`reconcile_report` functions retain the v1 reconciliation
interface: material/section fingerprints, public-safe work records, at most 20
proposal fingerprints and `delivery: not_confirmed`. Pure reconciliation does not
persist or acknowledge anything. Both report CLIs now use the durable v2 envelope
below rather than saving this fingerprint-only object as the whole state.

## Offline integration, version 1 staged manifest

`python -m automation.coordinator_integration` is the offline entry point. It
imports no credentials and has no network writer, URL fetcher, provider client,
executor or scheduler. Only expressly selected staged files are read. See the
[separate pilot runbook](COORDINATOR_PILOT.md) for exact future grants and
reproducible synthetic commands. No real sources were inspected by this task.

The manifest has exactly `version: 1`, `repository: kolorifer/radarr-festival-list`
and `sources`. All five fixed IDs must occur exactly once, including unavailable
sources. Each entry has exactly these fields:

| Field | Meaning |
| --- | --- |
| `id` | `engineering`, `investigations`, `research_report`, `parent_status`, or `quality_release`. |
| `path`, `sha256` | Exact relative staged filename and SHA256 of its bytes; both null explicitly means unavailable. No duplicate paths, URLs, absolute paths, dot segments or traversal. |
| `revision` | Known producing Git revision (40 lowercase hex), otherwise null. For engineering, must equal the snapshot revision. This supplied provenance is not independently authenticated by ingestion. |
| `generated_at`, `observed_at` | True numeric UTC source times or null. Movie generation time must equal the producer's embedded time; engineering observation time must equal the snapshot. Unknown event time remains null. |
| `collected_at` | Actual collection/read time, or null if unknown; never substitutes for a movie/engineering event time. |
| `max_age_seconds` | Positive integer, at most 3600 for engineering/investigations/parent, 172800 for report, 3600 for the reserved quality source. Stricter supplied limits are supported. |

Manifest and individual files are bounded to 2 MiB; paths to 240 ASCII characters.
Every path component, including root ancestors, is opened without following
symlinks. Only regular files are accepted; reads are bounded and checked for
concurrent modification. Duplicate JSON keys, exponent overflow/nonfinite
numbers, conflicting identities and invalid schemas fail without imported text
or paths in errors. No root enumeration or implicit home lookup occurs. Root
and manifest selection are caller configuration, never source-supplied authority.

Each source reports `available`, `unavailable`, `stale`, `inconsistent`, or
`partial`, with fixed reasons and separate read/collection/source times. Declared
absence and rejected data cannot mean an empty completed review. A bad manifest
fails closed; a bad source retains independent valid engineering/movie findings.
Availability/freshness transitions and validated substantive findings participate
in material reconciliation. An observation-only refresh stays quiet even when
regeneration changes source bytes and the manifest's matching SHA256/time pins.
Exact raw-byte verification still runs on every read, and prepared private reports
retain their original source hashes and times. Only `sources.*.sha256` and
`sources.*.generated_at` are additionally excluded from semantic comparison;
the foundation already excludes observation/read/collection clocks. All other
hashes, movie evidence/occurrence/report versions, task/head/result facts, explicit
source revisions, source states/reasons and freshness limits remain material.
Changing evidence is not suppressed merely because a concise summary is unchanged.
This supersedes Task 1's raw-byte-material choice (issue #113 Task 2); the earlier
choice preserved byte provenance but incorrectly exhausted the outbox on refresh.
A quiet poll returns no new report; an old payload's provenance is never relabeled
as a newer observation.

`engineering` is the existing v1 coordinator snapshot with `movies: null` and
`quality: []`; those sources must be supplied independently. Existing whole-task
owner/authority, completion, current-head CI and research separation validators
still apply. Parent observations never fill review/deploy/live stages.

`investigations` is the complete v1 `/v1/investigations` export validated by
`identity_research_handoff.validate_snapshot`: all cases, exact occurrence
versions, eligible `items` subset and the full incomplete-coverage aggregates.
It must be less than one hour old, with at most five minutes future skew.
`research_report` is the actual v1 `identity_investigation_report.write_report`
output, including `cases`, `changed_cases`, `versions`, coverage/budget and fixed
control fields. It must be less than 48 hours old, with the same future skew.
The complete case-ID set, every base field and coverage must match. Producer
`versions` hashes are recomputed over each row excluding `observed_at`;
`changed_cases` must be an exact subset. A proposal marked current must bind the
eligible research material digest (the item excluding `observed_at`), not merely
the collector occurrence version. Proposal times are validated; old proposals
remain retained, never refreshed by a file read. Missing/incompatible report
leaves the complete validated snapshot set visible with review incomplete.

Private report payloads retain every validated base case field (including titles),
all routes, exact eligible IDs/material versions, upstream coverage, proposal
versions/currentness/times and the foundation's retained-evidence findings.
Full proposal evidence remains in the exact hash-bound staged source, which must
be retained for private supervisor inspection; arbitrary raw evidence fields are
not recopied into reports. The integration CLI emits a separate fixed public
projection: source states/reasons, report IDs/hashes, publication states and
backpressure only. It never prints private payloads, paths or intent destinations.
`recover` writes exact payload bytes locally, outside the checkout, mode600,
create-only; an existing divergent file is refused.

`parent_status` is the bounded v1 allowlisted export described next. Its manifest
`generated_at` and `observed_at` must be null; `collected_at` equals export
`read_at`. Its age limit dates the journal read, not an execution event.
`quality_release` is reserved and always unavailable with
`passive_export_missing`, even if a synthetic/empty file is staged. Identity and
acquisition approval remain unknown, and review is not completed. See passive
production export requirements in the pilot runbook; #86 research is not that feed.

### Parent status projection and issue binding

`parent-export --root ROOT --issue N --task T [--task T...] --output FILE` reads
only `N/state.json`, `N/heartbeat.json` and selected `N/execution-T.json`,
`N/terminal-T.json`, `N/delivery-T.json`, up to eight distinct task numbers.
Each file is at most 256 KiB. No task discovery, adjacent logs, retained patches,
raw stdout, prompts, source text, private artifact references or credentials are
exported. This is read-only observation without dispatcher locks/claims or replay.
The CLI rejects any output at/beneath `ROOT`, including filesystem aliases, before
writing. Supply a separate existing staging directory outside the checkout.
Symlink ancestors/final destinations, traversal, hardlinked and nonregular
outputs are rejected with the fixed sanitized input error. Destination directory
identity/ancestors are checked and writes/renames use its pinned directory FD;
source directories/journals are never created or modified by the exporter.

Every present repository/issue/task association is checked; terminal receipts use
the unchanged parent v1 validator. The caller must independently establish which
repository owns the selected root; files lacking repository/issue fields do not
prove that association themselves. Missing records stay unknown. Read time is
separate from unknown event time. Contradictory terminal/execution/delivery or
consumption records yield `inconsistent`, retaining the individual observations.
A parent write can race these separate reads; the export is not an atomic parent
snapshot. Reobserve under later authorized scope rather than certifying health.

The output carries an explicit issue plus selected task numbers. #86 Task 1
cannot fill #113 Task 1 evidence. Optional `local.issue` binds legacy snapshot
consumed/terminal lists; an explicit mismatch blocks drafts. Old v1 lists without
it are usable only when goals and comment collections identify exactly one issue;
multiple-issue snapshots fail closed for drafting. Integration does not copy
parent evidence into those old lists or infer inactive-writer status.

Heartbeat active/PID values, RUNNING comments, permanent claims and a journal's
`running` string never establish process liveness. `writer_liveness` remains
unknown. `exited` proves only the recorded child exit; `completed` only the
recorded code publication; `posted` only a returned public POST. None proves
independent review, merge, deployment, recipient receipt or live correctness.

### Durable version 2 outbox and receipt reconciliation

Both report CLIs serialize read, reconciliation, preparation and save under
`STATE.coordinator.lock`, a coordinator-owned flock distinct from dispatcher
locks. Supply a stable owner-only directory outside the checkout. Preserve the
lock file; do not unlink it while any invocation can hold it. File creation is
exclusive, followed by open-existing on `EEXIST`, avoiding a reproduced concurrent
macOS create/no-follow race. There is no daemon or execution claim.

State has exactly `version: 2`, `reconciliation` (v1), `sequence`, `outbox`, and
`migration`. Each immutable outbox entry has `id`, `sequence`, `material`,
`payload` (complete canonical JSON bytes represented as a string), `sha256`,
`publication` and `recipient_delivery`. ID hashes version/sequence/material;
material binds semantic findings, including source revisions/availability.
Payload hash and its report material are revalidated on reads. The suppressing
material transition and full payload are in the same fsynced, mode600 atomic replacement and directory fsync.
A crash before emission, restart or unchanged poll therefore exposes the same
pending payload/ID through the outbox API and explicit local recovery; CLI stdout
exposes only pending metadata. `changed: false` still means no newly prepared material report.
There is no second task or publication attempt on recovery.

New payloads contain `comparison_version: 2` for the scoped semantic comparison.
The state envelope and ID formula stay v2. Existing pending-v2 payloads without
that marker use comparison v1 for validation: their original bytes, IDs, hashes,
publication intents/status and receipt bindings are unchanged and recoverable.
Unknown comparison versions fail closed. Before comparing a new observation,
compute a transient comparison-v2 baseline from the last immutable payload.
An unchanged poll/restart does not save or migrate state; a substantive transition
appends one new payload and preserves all earlier entries. Fingerprints from the
two comparison versions must not be equated as byte identities. Recovery always
uses the retained original payload and hash, never a reconstructed current report.
Old validators reject new staged comparison-v2 payloads; upgrade readers with
writers. This is forward recovery of old state, not a downgrade migration.

At most 20 reports, 512 KiB per payload and 8 MiB total state are retained.
Exhaustion returns explicit backpressure and `material_change_pending: true`
(`changed: false` means no committed new report), without committing the suppressing
transition or losing any pending payload. Nothing is silently evicted, even after
private publication, since recipient delivery is still unacknowledged. This code
has no automatic archival/acknowledgement policy; resolve retention through a
separately reviewed owner workflow before recurring activation exhausts the bound.

V1 fingerprint-only state is validated, retained as reconciliation history and
reprepared once from current inputs (`v1_reprepared_unacknowledged`); it cannot
recover a lost historical payload or upgrade anything into delivered/reviewed/
approved evidence. Pure v1 reconciliation is still available to existing callers;
persistent report callers should use the locked outbox API.

Optional explicit local `--intent FILE` contains exactly `identity` with public
repository/issue/task, and `destination` with allowlisted private repository,
exact `operations/` path and `expected_blob` (`absent` or 40-hex CAS baseline).
The outbox binds this immutable intent to exact payload bytes/hash on preparation.
It is configuration for the existing publication owner, not authority imported
from source data. No destination is invented when absent. `pending` means prepared,
not attempted. The external publication owner records `publication-uncertain`
before its single authorized attempt; an interruption remains uncertain until
readback reconciliation. This command never sends. Repeated invocation cannot
schedule another attempt. There is no automatic resend or network writer here.

`receipt` reads one selected `ISSUE/terminal-TASK.json` under an explicitly trusted
parent root, an independently supplied exact SHA256 pin, and one staged artifact
readback. The unchanged parent receipt validator must pass; repository/issue/task,
artifact-readback flag, artifact repository/path/reference, payload hash and exact
readback bytes and recomputed Git blob identity must all match the immutable intent/report. Missing, malformed,
wrong, unpinned or conflicting evidence cannot acknowledge publication. Repeated
identical reconciliation is idempotent; conflicting later evidence is refused.
A verified artifact can coexist with a failed terminal/public-comment result.
Local `terminal-N.json` is the parent's intended receipt, not proof that the receipt
itself was published or delivered to a recipient.

**Trust boundary:** the operator/supervisor must authenticate the parent-root
provenance and the pin from actual parent-owned evidence under exact grants.
A supplied hash proves integrity, not provenance. Structurally valid arbitrary
JSON or child-written success flags cannot be treated as trusted parent proof.
No importer can distinguish a forged identical receipt from genuine evidence
without that external trust. This interface has no credential, sender or GitHub
mutation authority. Imported evidence grants no execution authorization.

`publication: verified` only records exact private artifact readback. Recipient
delivery stays `not_configured`; no ChatGPT/Telegram/human acknowledgement is
manufactured. Reports remain recoverable in `pending_outbox`/`pending` regardless
of publication. Publication, terminal receipt availability, public result posting,
recipient receipt, independent review and product acceptance are distinct facts.

## Task, review and completion lifecycle

1. Adopt one objective from a trusted owner source. Record its exact scope,
   acceptance plan, dependencies, evidence and current task/PR/head. Pin material
   assumptions with evidence and validation status; do not call guesses decisions.
2. Reconcile public observations and explicitly supplied local evidence. A RUNNING
   comment or permanent claim is historical consumption, never worker liveness.
   Reconcile the latest valid trusted WORKER_RESULT for the relevant task as
   READY_FOR_REVIEW, FAILED or NEEDS_USER. An older task's late result cannot
   replace newer work. Duplicate protocol fields, incomplete records/reads and
   duplicate briefs stay unknown and prevent drafts; later valid terminal records
   for the same task replace earlier terminal states. Failed/blocked/ambiguous
   records prevent current completion without erasing individual stage facts.
3. Supply an exact next number. Draft preflight requires fresh complete comments
   and claims, the latest actionable owner brief, an open issue, known consumed/terminal
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
   author to approve without a supervisor receipt; the latest decisive opinion
   per reviewer wins. Generic CI success is
   supplementary and cannot prove the task's required tests were run.
7. Keep implementation, review, test, merge, component deployment, dated live
   checks, docs and product acceptance separate. Merge proves only merge. Deploy
   and live observations require exact revision/component/configuration; live
   observations expire after 24 hours here. These freshness limits are conservative
   implementation defaults, not changes to production or provider policy. An
   approved future plan may require a different versioned rule. Unsupported stages
   remain pending; this build says “reviewed and tested; deployment pending” only
   when both review and testing have actually passed.
   Deployment selection first reconciles the latest observation for each
   component across all revisions/configurations, then checks applicability to
   the implementation. Known-component observations with unknown configuration
   participate in that selection. Both the selected deployment and current
   observation need configuration before passing; an incomplete newer deploy
   leaves deploy/live pending, while an incomplete newer live check leaves live
   pending without invalidating a complete deployment. Neither falls back to an
   older pass, and the incomplete observation remains visible in history.
   Later rollback/replacement evidence invalidates an old
   pass. Live evidence must match the latest successful deployment's exact
   component, revision, configuration and time; configuration-only replacements
   need a fresh live check. Equal-time conflicting observations remain unverified.
   Every observed component must pass for the aggregate stage to pass. `history`
   retains earlier observations without presenting them as current completion.
   To support a merge/squash revision, a deploy observation may supply
   `merged_from: {revision, receipt}`: revision is the reviewed head, receipt is
   the independently verified lineage binding above. GitHub must report merged
   and its actual merge commit must equal the deployed revision. An unmerged PR's
   prospective merge SHA, a missing receipt or unrelated revision proves nothing.
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
Each occurrence also carries `material_evidence_v1`, a canonical SHA256 change
signal bound to its exact occurrence/version and retained evidence version.
It hashes a validated allowlist from the real provider/report schema: candidate
records (including runtime, date/year and IMDb crosswalk), confidence/context
flags and each method/query/result/candidate association. Private title/query text
is used only inside that aggregate hash and is never emitted. Unknown payload
keys, URLs, raw source/proposal prose and observation refresh timestamps are
excluded; unsafe known metadata fields are refused with fixed reasons. Missing
legacy query associations stay null/unknown, never verified. A digest change
requests review of the original authorized evidence; it does not reveal the
changed value, establish identity, or approve an action. Observation-time-only
refresh and restart replay stay quiet. Real private export access remains an
activation prerequisite.

Quality review flags missing/undated/stale evidence and incomplete recognition/
score subtotals. `notification_state` describes delivery (`confirmed` means
delivered), separately from `identity_verified` and `acquisition_approved`.
Optional `notification_type` is `informational`, `identity_review`, `acquisition`
or `unknown`; optional `action_eligible` is a boolean or null and refers specifically
to acquisition eligibility, not a review-evidence button. Legacy records default
to unknown type/eligibility and receive `notification_action_evidence_unknown`,
without an inferred identity violation. The audit reports all these facts separately.

A delivered informational Unknown Movie notification with unresolved identity and
no acquisition action is valid, as is an identity-review link without acquisition
eligibility. Offering an acquisition action or asserting its eligibility with an
unverified identity raises `actionable_identity_unverified`; an explicitly
ineligible acquisition action or a type/eligibility contradiction is also flagged.
Acquisition approval with unresolved identity independently raises
`approval_identity_inconsistent`. Verified action eligibility does not imply
per-release acquisition approval. These findings are fixture audits, not live
notification routing or acquisition-policy changes; see the existing
[notification guide](../docs/MOVIE-NOTIFICATIONS-GUIDE.md).
Historical scoring and the
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

## Confined movie-export reader/stager (issue #115, offline code)

The reusable library is `automation.coordinator_exports.stage_exports(source_root,
output_root, now)`; the existing integration CLI exposes `stage-exports`. This is
code for a later expressly authorized source/reporting owner, with no transport,
SSH handling, source refresh, credential discovery or recurring execution owner.
It reads only these exact relative paths under the caller's canonical absolute
**research-state** root:

| Fixed source ID | Relative source path | Maximum bytes / generation age |
| --- | --- | --- |
| `investigations` | `incoming/snapshot.json` | 2 MiB / less than 3600 seconds |
| `research_report` | `review-report.json` | 2 MiB / less than 172800 seconds |

Do not pass a guessed home. The producer constructs its layout with
`Path.home().resolve()`; this reader instead requires explicit canonical authority
and rejects symlink spellings, including ancestor links. Canonical success and
rejected symlink spelling are compatible facts. Neither establishes why issue
#113 Task8 failed. That pilot established SSH exit0 followed by `file_rejected`,
with neither movie export imported; the precise host/path cause is unknown.

The caller supplies a **new** output root, outside the source and checkout, under
an existing stable owner-only parent. Relative roots and traversal are rejected.
Both roots require the single `/` absolute anchor; `//` spellings are rejected
before any output creation. Supplied paths are never silently resolved through
symlinks. Before mkdir or output writes, source **and checkout** exclusion use
descriptor ancestor identities, including case-insensitive directory aliases;
an existing final entry aliasing either protected root is also rejected by identity.
No-follow directory descriptors and ancestor filesystem identities protect writes
against spelling/alias redirects; source hardlinks are also rejected by this
reader. Parent ownership/mode are checked. The parent must remain under the
caller's control; this is not isolation from a malicious process with the same
UID that can rename its directories. The reader does not enumerate either root.

The new root is mode0700; fixed `investigations.json`, `research_report.json`,
`manifest.json` and `observations.json` files are mode0600, fsynced and installed
atomically without replacing an existing entry. Only successfully acquired movie
files are present. Original JSON bytes (including whitespace) are preserved; no
serialization is written over an export. Each source is at most 2 MiB (4 MiB
combined); the manifest uses fixed fields, diagnostics at most 40 fixed records,
and observations at most 512 KiB. Reads use O_NONBLOCK, at most limit+1 bytes,
regular-file checks and before/after size/inode/time/link-count checks. Every
opened descriptor is closed on success and failure. Ancestor traversal transfers
cleanup ownership immediately on open, before stat or other fallible operations;
caller-owned source and parent descriptors remain open.

Manifest v2 adds `diagnostics` to the v1 fields; all five source IDs still occur.
Nonmovie sources are explicitly unstaged, not inferred. Each movie source has an
acquisition result; only acquired/staged bytes have a path/hash/collection time.
The observation `read_at` is an attempt clock, not a successful-read claim.
A valid embedded generation clock is copied exactly, otherwise null; validation
still rejects malformed content. No read or staging time refreshes freshness.
The observed snapshot/report are validated independently before pairing. Existing
full-case/base-field/eligible/version/coverage/proposal safeguards remain in force.
An authorized caller may combine separately authorized engineering/parent inputs
using the existing manifest contract; the reader does not fetch them.

Each private diagnostic is exactly `{version: 1, source, stage, reason}`. Values
come from `coordinator_diagnostics.REASONS`, never arbitrary exception text:

| Stage | Reasons |
| --- | --- |
| `acquisition` | `read_complete`, `missing_entry`, `access_denied`, `path_rejected`, `path_component_ambiguous`, `nonregular_file`, `byte_limit`, `changed_during_read`, `hardlink_rejected`, `io_unknown` |
| `staging` | `staged`, `destination_collision`, `destination_rejected`, `access_denied`, `io_unknown` |
| `identity` | `hash_mismatch` |
| `decoding` | `invalid_json` (including duplicate/nonfinite/overflow/invalid encoding) |
| `provenance` | `time_mismatch`, `revision_mismatch` |
| `freshness` | `stale_evidence`, `future_evidence` |
| `schema` | `invalid_source_schema` |
| `pair` | `incompatible_movie_pair` |

ENOENT means a missing entry, not necessarily the final file; ENOTDIR means an
ambiguous/rejected component, **not proof of a symlink**. ELOOP rejects the path;
unknown OS failures stay `io_unknown`. Generic validator failures describe the
schema stage, not an invented precise underlying cause. A valid snapshot with a
missing/invalid report retains all known cases and incomplete review. Report-only
findings cannot claim a completed movie review; quality/release stays unavailable.
Successful acquisition/staging does not mean successful source/pair validation.

The CLI emits the existing coarse safe source projection, never diagnostics,
paths, imported text or private report bodies. Even argument parsing errors use
fixed safe JSON. Inspect precise diagnostics only in the selected private
manifest/observations/report. Acquisition errors permit truthful partial staging;
failed sources are never replaced by an earlier root. Root/path preflight failures
produce no report; a rejected source-root spelling raises a typed fixed
`ReadFailure`. Output creation collisions raise `StagingFailure` with fixed
private diagnostics. Installation failures leave an incomplete root and, if
writing remains possible, a create-only `diagnostics.json`; its absence is not
success. `StagingFailure.diagnostics` is the bounded library fallback. No error
string/path is copied into these records. There is no rollback/delete/resume of
an existing root. Retry with a separately selected new root; never reuse old files.

The existing `report --root OUTPUT --state STATE` reads manifest v1 or v2 and
keeps the same outbox/receipt owner. `stage-exports` itself prepares no outbox and
publishes nothing. Private diagnostics are explanatory observation metadata and
excluded from comparison-v2, so collecting them cannot manufacture an upgrade
report. Existing status/reason, expiry and validated findings remain material:
failed-to-valid sources produce one new report; unchanged observations stay quiet.
A refinement within the same coarse failed state is available in observations but
does not itself publish another report. Old pending payloads/IDs/hashes/intents/
receipt bindings remain unchanged and recoverable; no migration is performed.

Later-authorized invocation (all paths are placeholders, **not access grants**):

```sh
python3 -m automation.coordinator_integration stage-exports \
  --source-root /AUTHORIZED_CANONICAL_RESEARCH_STATE \
  --output-root /AUTHORIZED_PRIVATE_PARENT/NEW_BUNDLE
python3 -m automation.coordinator_integration report \
  --root /AUTHORIZED_PRIVATE_PARENT/NEW_BUNDLE \
  --state /AUTHORIZED_PRIVATE_PARENT/COORDINATOR_STATE.json
```

After independent exact-revision review and supported CI, the supervisor must
separately establish actual source-root authority/canonical spelling, transport,
fresh original export availability, new private destinations and reporting owner.
Use the fixed stage/reason evidence to select that verification; do not infer a
host cause or repeat the exhausted access pilot from this code authorization.
No live access, recurring operation, notification change or product acceptance is
established by the synthetic rehearsal below.

## Separate caller-invoked cycles — issue #117, offline code

The new [cycle interface and owner runbook](COORDINATOR_CYCLES.md) implement a
complete local reporting cycle with the accepted fixed-path reader, explicit
engineering/parent observations, immutable cycle/report identities, comparison-v2
quiet refresh, a one-attempt private handoff, separate owner-authenticated
publication/recipient receipt imports and verified archival of original evidence.
Synthetic rehearsal exceeds 20 acknowledged material reports through archival.
This does not change the legacy issue/task v2 outbox or configure its recipient.
Active, archive, cycle-ledger and source-staging limits remain finite and expose
backpressure without deleting history. Reports and current observations keep
separate dates and provenance.

No runtime/launcher/schedule/transport was activated or inspected for this task.
Fresh supported CI, independent review, a separately scoped real integration cycle
and actual publication/recipient evidence remain gates. The existing Mac owner is
the later integration target. Its dispatcher is not hooked by this feature, and
engineering execution caps/claims/locks/terminal receipts remain unchanged.
