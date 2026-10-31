# Engineering report: issue #127 task 1, inactive AI movie investigator

**Specification:** [commissioned brief](2026-10-31-issue-127-investigator-brief.md),
the supplied latest issue-owner supervisor task, and the
[implementation contracts and live prerequisites](../AI-MOVIE-INVESTIGATOR.md).
**Result:** reviewable partial implementation with an inactive, tested offline
slice; completing the real-client tool/context boundary remains blocked. No
real identification or product acceptance is claimed.
**Repository revision:** `automation/issue-127-worker`, clean starting HEAD
`be2fb324e59a20e8bf2feb3128c2855553731d41`, tree
`d02faa76e673d5eff68c463d508013c4da7b62ed`. Implementation is uncommitted for
the parent runner; this worker performed no Git/PR/issue publication.
**Verification date:** 2026-10-31, isolated local Python 3.12.16 and 3.13.18
virtual environments; synthetic temporary roots only. No deployed state read.

## What changed

Captured failed-identification outcomes can now enter an explicitly called
standalone investigator. Before AI admission, it joins versioned owner choices
and dated shadow knowledge by exact source/case/evidence/occurrence scope. Exact
redelivery is idempotent, new deliveries/material evidence are explicit, and
legacy snapshots remain unbound rather than acquiring invented receipts.
Confirmed film identity is distinct from source/runtime/edition verification;
skipped/completed occurrences suppress repeated investigation; absent history
does not establish novelty. Revoked/superseded choices cannot silently revive.

The controller durably consumes one selected job and reserves each model attempt
before execution. At most two model calls/five retained lookup operations are
allowed. The model can select real case-scoped retained get/search operations;
it cannot authorize provider requests or arbitrary commands. Strict protocol,
binding, evidence/candidate/citation validation and failure/unknown-attempt
handling produce durable review results, private daily/case views and generic
rule proposals. No existing service imports or starts this module.

The optional Codex CLI implementation includes bounded subprocess transport,
JSON Schema/JSONL protocol, ChatGPT-only authentication selection, fixed safety
configuration, compatibility preflight and process cancellation. **It ships no
approved live-client profile.** Current public documentation does not establish
that the installed client excludes every ambient skill/plugin/MCP/managed
instruction and browser/computer/tool path. No real CLI command or model/probe
was executed to fill that gap. Therefore the real path remains disabled and an
unverified executable returns `model_tool_boundary_unverified` before invocation.
The fake executable proves the protocol only, not real-client isolation.

This is useful reviewable code with an explicit activation blocker, not a claim
that the live transport boundary or a new film identification has been proved.
The remaining boundary needs independently reviewed client evidence and a safe
profile/code follow-up; configuration flags or a caller's boolean are insufficient.

## Files and components changed

| File/component | Change and purpose |
| --- | --- |
| `ai_movie_investigator/contracts.py` | Pure observer/legacy adapters, strict bounded evidence/decision schemas, exact hash basis and occurrence-aware reconciliation. |
| `ai_movie_investigator/history.py` | Separate owner-only descriptor-checked, locked, hash-linked, fsynced bounded append history; idempotency and durable invocation/model accounting. |
| `ai_movie_investigator/controller.py` | Two-call/five-lookup loop, actual retained queries, shared quota gate, validated findings and no production side effects. |
| `ai_movie_investigator/codex_transport.py` | Disabled optional Codex CLI transport, fail-closed exact-profile preflight, finite protocol/process bounds and injectable simulated transport. |
| `ai_movie_investigator/review.py` | Date/timezone-selected private digest and detailed case view, stable result IDs and evidence-backed generic-rule proposal records. |
| `ai_movie_investigator/replay.py`, `synthetic.json` | One offline command covering fourteen synthetic cases from actual observer envelope shape to persisted simulated findings. |
| `test_ai_movie_investigator.py`, fake executable fixture | 46 focused positive/failure/isolation tests and an installed-only nonempty dependency-closure proof with six missing-dependency negatives. |
| `docs/AI-MOVIE-INVESTIGATOR.md` | Exact interfaces, reviewed official documentation, boundaries, limits, installation closure and later demonstration prerequisites. |
| Project state and notification guide | Implemented-versus-inactive facts; no live behavior change asserted. |
| Saved brief/report and [source manifest](2026-10-31-issue-127-runtime-manifest.json) | Recoverable engineering handoff and exact 16 runtime/dependency/test content hashes. |

Existing interface trace: observer/outbox shape and intake normalization;
collector release/event semantics; selection routes and exact occurrence review;
research handoff/provider schema concepts; worker retained query/answer traces;
RecurringStore's unknown-request/no-repeat pattern; investigation-report and
Telegram-digest changed-result concepts; memory's separation of remembered film,
current occurrence and download consent. Historical shadow code informed dated
evidence representation only. No archived shadow runtime was promoted, existing
snapshot/report schema changed, or collector/research/action/cache API invoked.

## Acceptance criteria and evidence

| Criterion | Result | Evidence or remaining gap |
| --- | --- | --- |
| Explicit observer import, exact immutable identity, concurrent deduplication | Passed offline | Canonical decoded-object or exact captured-byte hashes are labeled; conflicting original event bytes/timestamps rejected; concurrent admission creates one job. |
| Scope-aware decisions and dated shadow evidence | Passed synthetic | Owner-confirmed versus technical-gap; two skips; completed occurrence; six stale shadow successes; missing dispositions; revocation/expiry/supersession; wrong version/occurrence and evidence hash changes. |
| Optional real ChatGPT-route model transport | Protocol implemented; boundary blocked | Fake executable exercises actual subprocess flags/schema/stdin/JSONL path. No actual client is approved or invoked. Complete real-client tool/context proof remains required. |
| Real retained lookup controller | Passed offline | Get/search queries filter actual selected retained records; wrong scopes/operations, prompt injection and excessive result sets fail closed; zero fresh GETs. |
| Durable bounds/accounting and isolation | Passed synthetic | Exact two calls/five lookups; reservations precede execution; interruption/timeout/malformed output/reused invocation cannot silently replay. Superseded jobs cannot reserve or publish supported results. |
| Explicit output schema and evidence-backed results | Passed synthetic | Forged citations, unsupported claims, unreturned candidate IDs/alternatives, stale support, changed bindings and conflicting IDs cannot produce a supported claim. |
| Safe owner-only history | Passed temporary fixtures | Regular/single-link/owner/mode, no-follow/namespace/directory identity, finite lock wait, partial-tail refusal, no history omission/revocation rollback. No existing database writes. |
| Useful read-only daily/private review and proposal | Passed synthetic | Explicit calendar/timezone/as-of view, stable changed IDs, pending/failed/quiet states, no false inference on a preflight-only block, tools/evidence/uncertainty/next action; no sent/ack/archive effects. |
| Installed-only nonempty runtime closure | Passed both supported local Pythons | `-I -B -S` outside checkout; no repository/PYTHONPATH/site/test fallback; nonempty replay and legacy import; removal of each of six required existing dependency modules fails. |
| Unchanged notification/download confirmation and production policies | Passed local regression checks; code preserved | No existing runtime file changed. Existing notification/identity/action tests passed in both full supported-runtime suites. |
| Supported exact published-head CI and independent review | Not verified here | Existing GitHub Python 3.12/3.13 matrix covers new root tests. Parent owns commit/publication, exact-head CI and independent review. Local supported runs are not published CI. |
| Later one-case real demonstration | Plan complete; not authorized/executed here | Exact seven-part prerequisite list in implementation documentation; no blanket live authorization. |

## Tests run and results

Dependencies were acquired in temporary test environments using the existing
unchanged `requirements.txt`. Product code adds no third-party dependency.
Actual runtimes: Python **3.12.16** and **3.13.18**. Installed test packages were
requests 2.34.2, beautifulsoup4 4.15.0, certifi 2026.10.23,
charset-normalizer 3.5.2, idna 3.20, urllib3 2.8.0, soupsieve 3.0.4 and
typing-extensions 4.16.0. This does not pin or change production dependencies.

| Actual command/check | Result |
| --- | --- |
| Each temporary environment: `python -m unittest -v test_ai_movie_investigator` | **46 passed** on Python 3.12 and **46 passed** on Python 3.13. |
| Repeated actual concurrent-intake test | **20 passed** after exclusive-create fix, no duplicate jobs. |
| Final frozen Python 3.12: `python -m unittest -v` | **1,334 run, two skipped, zero failures/errors**, exit 0; 1,897.995 seconds. |
| Final frozen Python 3.13: `python -m unittest -v` | **1,334 run, two skipped, zero failures/errors**, exit 0; 1,889.503 seconds. |
| `python -m ai_movie_investigator.replay --synthetic` | Fourteen persisted results/private views; nonempty retained tool queries; explicitly simulated; zero real identifications. |
| Both temporary environments: `python -m pip check` | No broken requirements. |
| `python production_scoring.py --check` | 1,909 candidates, 387 qualified (224 grandfathered, 163 new); existing policy unchanged. |
| Frozen content hashes, Python 3.12 syntax, task/decisions preservation, diff inspection, documentation links/whitespace | Passed, including unchanged 16-file source/test manifest after both final full suites. |

During development the fake executable exposed canonical-versus-aliased
temporary working directory paths; the CLI path is now canonical. Concurrent
first intake also exposed an intermittent create/open error; exclusive creation
followed by a no-follow open fixed it, with repeated stress checks. Earlier
candidate-suite runs were stopped through their execution sessions after source
fixes; they are superseded by the final frozen runs above and are not cited as
final passes. Only synthetic fixtures were used. No hidden reasoning,
credentials, source links or approval capabilities were printed or stored.

## Deployment result

**Not authorized; not deployed or activated.** No existing notification,
Telegram digest, producer, service, timer/schedule, runtime configuration,
provider, source, seedbox/SSH, Radarr or media state was inspected or changed.
No model inference, app-server/probe, new account/API/subscription/payment,
credential read/copy, live notification, addition or download was performed.
There was no ChatGPT Work use, second worker/runner/subagent or daemon.

The synthetic tests use subprocess Python fixtures, fake executables and local
temporary state. The existing full suite's mock/loopback fixtures are test
activity, not operational service deployment. The parent exclusively owns
Git publication, PR/issue reporting and independent review.

## Unexpected findings

Legacy collector snapshots expose a case/version and observation time, not an
actual source delivery/event receipt. The new adapter preserves this unknown;
it does not retrofit the existing schema or infer operational closure.

Supported CLI flags do not establish the absence of all managed/ambient context
and tool exposure. A profile cannot safely be registered from a configured model
name, help text or fake fixture. Consequently the complete real-client boundary
is an explicit blocker, not a claimed tested property.

The retained daily recurring producer contract differs from repository weekly
RecurringStore fields. No budget names/values, ledgers or quotas were normalized,
reset or rewritten. Installed producer identity/timing and current health/queue
remain unknown. Shared model quota uses the existing <=15% pause and five-hour
telemetry ceiling with no probe; provider GETs remain a separate zero counter.

## Unresolved issues and risks

1. Real-client compatibility, zero tool exposure and exclusion of ambient
   conversations/instructions/skills/hooks/plugins/apps/MCP remain unproved.
   The shipped empty profile set guarantees refusal, not a working live setup.
   A separately reviewed safe profile/code follow-up is needed before activation;
   do not weaken managed requirements or use API-key fallback.
2. Parent publication must obtain exact-head supported CI and independent review.
   This worker has neither operational access nor authority to complete those.
3. Owner decisions/provenance/quota projections are trusted explicit caller inputs,
   not cryptographic proof from JSON issuer names or model text. Actual sanctioned
   input selection and current shared ledgers must be established for a real case.
4. One invocation is consumed even on preflight/quota block in this conservative
   slice. There is no automatic retry, refund, history pruning or partial-journal
   repair. Capacity exhaustion/unknown state needs reviewed operator handling.
5. Owner-local filesystem checks do not defend against a hostile same-account
   process or compromised host. No real private storage grant was tested.
6. No fresh provider broker exists in this slice. Later GET-only integration must
   reuse actual authorized provider clients, reservations, caches and limits;
   retained replay is never represented as a new GET.
7. Rationale is model-supplied bounded text; cited structured support is checked,
   but this is a review proposal, not independent system verification. Image
   reference counts are not image analysis, and no result grants production
   identity, cache learning, override, download consent or acknowledgement.

The later demonstration plan specifies reviewed code/dependency/client pins,
actual boundary and shared quota evidence, exact one-case outcome/evidence/full
decision inputs, private storage and destination, finite invocation, preserved
unknown attempts and rollback by stopping the standalone API while retaining
history. It permits no production mutation. Distinguish **model inference**,
**supported candidate**, **system verification**, **production identification**
and **delivery acknowledgement** at every handoff; only the first two could be
demonstrated by that later authorized experiment.

## Commit and PR reference

No worker commit, push, PR or issue comment. The parent runner owns publication
from `automation/issue-127-worker`; its containing commit/PR will identify these
uncommitted changes. Review and exact-head CI are pending. The
[16-file manifest](2026-10-31-issue-127-runtime-manifest.json) pins the reviewed
local runtime/dependency/test bytes independently of publication metadata.

## Project context updates

Saved the commissioned brief, this engineering report and source manifest under
`docs/reports/`. Added explicit inactive/blocked facts to project state and the
movie notifications guide. `docs/CODEX_TASK.md`, decisions, old histories, trial/
coordinator/dispatcher modules, claims/locks/quotas/caps and production code stay
unchanged. No cleanup work or new next task was inferred. The user/supervisor
and parent reviewer must assess the code and unresolved client boundary before
agreeing any later real-case work.
