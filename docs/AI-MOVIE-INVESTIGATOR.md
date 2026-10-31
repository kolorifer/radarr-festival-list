# Inactive AI movie investigator

Issue #127 adds an isolated product module, `ai_movie_investigator`. It is not
connected to movie-intel, the collector, the recurring producer, Telegram or a
schedule. Importing it starts nothing. No real identification has been made.
Only synthetic temporary storage and fake transports were exercised. Task2 also
inspected installed-client metadata without inference or configuration changes.

## Explicit interfaces and trust

`contracts.captured_outcome(envelope, sources=..., binding=..., evidence=...,
decisions=..., trusted_issuers=...)` is a pure import adapter for an already
captured **public observer-shaped** `identity.outcome` envelope. It uses the
existing intake normalizer and selection routes. It does not fetch an event or
parse Telegram prose. Source selection and trusted decision issuers come from
the caller, never the event, evidence text or model.

The binding has exactly `source`, `case_id`, `version` and `occurrence`.
`case_id` must equal the normalizer's `outcome-<release hash>`; `version` is the
exact caller-selected collector version. A known occurrence has `event_id` and
an actual retained `delivery_id` receipt. The adapter checks event identity and
retains its original timestamp and input hash with an explicit hash basis. Raw
captured bytes retain their exact SHA-256; already decoded objects retain their
canonical JSON hash without claiming original byte preservation. It does not
invent a receipt from an observation time. `legacy_snapshot` accepts an existing
selection snapshot case with `occurrence=None` and `event=None`; such a case is
blocked from investigation/closure until a separately authorized adapter can
establish actual binding. Existing snapshot/report schemas are unchanged.

Evidence records contain ID, kind (`catalogue`, `source`, `shadow`), complete
scope, observation/expiry times, origin/digest provenance, optional IMDb/TMDb
candidate, bounded text, enumerated claims and image-reference **count**. The
caller must supply capability-free projections. URLs, private paths, credential
syntax and unknown raw fields are rejected. Torrent evidence in the captured
envelope is validated using the existing interface; only its digest/reference
count crosses into investigator facts. Its descriptions/NFO may be supplied as
separately scoped retained records. No image is fetched or visually analyzed.

Owner decisions carry ID, monotonic revision, caller-trusted issuer, provenance,
decision time, source/case/version/occurrence scope, exact evidence IDs **and
hashes**, kind, chosen target only for an actual confirmed identity, supersedes,
revocation and expiry. Superseded history never revives when a replacement
expires or is revoked. Changed scope/evidence and untrusted provenance are
displayed, not applied. Intentionally skipped and completed occurrences suppress
model admission. A confirmed movie remains distinct from verification of this
source, runtime and edition. Same title/year is never a scope join. An absent
disposition and empty retained search do not prove novelty or catalogue absence.
Historical shadow successes remain dated knowledge after freshness expires.

## Durable controller and storage

The caller explicitly selects an existing canonical owner-owned 0700 directory
and constructs `History(directory)`. Only `ai-investigator-v1.jsonl` is opened:
owner-only 0600, regular single-link file, no symlinks, locked descriptor,
directory/file namespace identity rechecks, a two-second lock-wait ceiling,
bounded size/record count, fsync and
hash-linked sequence checks. Rendering never creates a file. A partial append
fails closed as an incomplete history; there is no automatic truncation or
refund. Same-account hostile tampering and host compromise are outside this
owner-local integrity boundary. Checks are POSIX; unsupported platforms need
review before activation. No existing collector, research, actions, identity
cache, receipts or pilot ledger is written.

`history.intake(packet)` returns a job and explicit admission/change reason.
Exact redelivery is deduplicated under the lock, including concurrent intake.
The immutable event ID cannot acquire different original bytes or timestamps.
Distinct delivery, case-version change, retained material change and decision
history changes are retained separately. A freshness-only observation retains
its exact input without granting a new job. Omitted or rolled-back decision
history is refused. A later case version supersedes pending older work;
reservation and final-result guards also catch changes during inference.

`controller.investigate(history, job, invocation, transport, quota=...)` handles
one selected case and returns a persisted result. One invocation per job is
consumed durably, even on failure. Each attempted model call is reserved and
synced **before** execution. There is no automatic retry of unknown/interrupted
work. A changed invocation ID cannot replay the same job. Limits are two model
calls, five retained lookups, 49,152-byte prompts, 8,192-byte model replies,
25 seconds per call and a 60-second investigation loop. Preflight permits one version and one exec-help command, each at most five
seconds, sharing a ten-second aggregate ceiling. It never retries either command.
The monotonic 60-second investigation deadline includes preflight and durable
operations; model calls still have a 25-second ceiling. History is capped at 16 MiB/10,000 records;
capacity exhaustion fails closed and never evicts history.

The model may request `retained_get` by evidence ID or `retained_search` by
kind and bounded text query. The controller validates and executes these actual
local lookups only against the selected case/version/occurrence. At most eight
rows and 16 KiB per lookup are returned; overflow blocks rather than silently
truncating. Missing evidence produces an empty retained result, not a new
provider request. Model-selected operations are not execution authorization.
All descriptive text is untrusted data. An operation such as shell, browser,
arbitrary URL or provider request is rejected.

The final response has an explicit JSON Schema plus local binding/citation
validation. Candidate IDs, alternatives and enumerated claims must agree with
evidence actually returned to the model. A current supported candidate needs
retained catalogue crosswalk and source-identity support; stale support, changed
bindings, forged citations, unsupported claims, conflicting asserted IDs or an
owner-target conflict block that claim. This is a conservative validation of a
**review proposal**, not a new production matching rule or confidence threshold.
`supported_candidate`, `unresolved`, `blocked` and owner-derived
`intentionally_skipped` stay distinct. Only concise evidence rationale and
actual query/answer traces are retained; internal model reasoning is not stored.
No result is learned into a verified identity cache or grants download consent.

## Codex CLI transport and current blocker

The optional `CodexCLI` implements bounded stdin-to-`codex exec` JSONL transport,
schema delivery, strict completion/event parsing, process-group cancellation,
output/time bounds and explicit configured model selection. It defaults to
disabled, uses `forced_login_method="chatgpt"`, and has no API-key fallback,
auth-file access, credential parsing/copying, account creation or subscription.
The existing configured model must be supplied explicitly; no account/model
access is inferred from its name. Environment key/loader/proxy overrides are
not inherited. Authentication stays with the existing client.

Task2 assessed these official references on 2026-10-31; Task3 rechecked the
configuration reference and corrected the bootstrap/audit claim below:

- [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode):
  fresh exec, bounded stdin/JSONL/schema use and user-config/rules controls.
- [Authentication](https://learn.chatgpt.com/docs/auth): existing ChatGPT sign-in
  stays inside the client; API-key auth is a separate route.
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference):
  tool features, project-document/catalogue limits and managed-policy precedence.
- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents):
  capability reductions and skill settings are described for custom agents;
  those examples alone do not establish root exec behavior.
- [Developer commands](https://learn.chatgpt.com/docs/developer-commands):
  command and metadata surfaces, distinct from actual session execution.

**Task3 correction:** the Task1/Task2 reports remain dated evidence. Their
synthetic checks did not establish complete real-client configuration
compatibility. Independent review [5725098181](https://github.com/kolorifer/radarr-festival-list/pull/128#pullrequestreview-5725098181)
reproduced rejection of `skills.max_context_tokens=0`; the official reference
requires a positive integer and describes an available-skills catalogue budget.
Task3 removes that setting without substituting a positive budget. A catalogue
budget cannot suppress skill instructions or enforce tool availability.

The explicit optional `codex_transport.inspect_configuration_metadata` checks
the exact complete `configuration_args()` vector shared with the transport.
It accepts caller-selected version and root/features/exec help hashes, runs
only version/help/features-list metadata commands, and returns safe hashes and
selected feature states. It never registers a profile or inspects a real client from runtime
preflight or ordinary tests. Each subprocess gets empty stdin, a temporary cwd,
filtered environment, five seconds and at most 32 KiB combined output (4 KiB
for version); all six commands share a ten-second deadline. Process groups are
killed on failure; no retry or inference fallback exists. Unknown non-feature
schema, unsupported values, missing selected features, unknown listing schema,
enabled states, missing client, failed inspection and executable/version/help
drift refuse visibly. Synthetic tests exercise the mechanism and an independent
TOML parser's nonzero-integer rejection; they do not attest a real client.

Task3's actual installed `codex-cli 0.166.0-alpha.5.1` check accepted all 23
selected controls and reported all 17 selected feature families false in 0.602s
using the final frozen helper.
See the [corrective report](reports/2026-10-31-issue-127-task3.md) for exact
commands, vector and pins. `features list` does not support exec's
`--strict-config`, `--ignore-user-config` or `--ignore-rules`; none was guessed
or removed from the actual exec route to obtain a pass. Root config overrides
are accepted by metadata; effective non-feature semantics and exec isolation
remain unproved. No prompt, account inspection, app server or model turn ran.
Metadata acceptance does not establish effective tool inventory, skill/context
isolation, mandatory-policy preservation or a stable dependency lease.

The control audit is deliberately incomplete for real activation:

| Route | Candidate restrictions and remaining evidence needed |
| --- | --- |
| Commands and files | Shell tool and shell snapshots disabled; fresh empty 0700 cwd, bounded schema, read-only sandbox, no approval. Read-only still permits reads if any file tool is exposed. Prove the entire effective tool inventory is empty, including alternate file/patch tools. |
| Web and browser/computer | Web search disabled; browser_use, browser_use_external, browser_use_full_cdp_access, computer_use and in_app_browser false. Prove none can execute through alternate surfaces. |
| Apps, plugins and MCP | Apps, plugins and remote_plugin false. No generic MCP-empty override is asserted: inventory managed, global, remote and dynamically discoverable integrations; refuse any unknown server/tool or loader path. |
| Image and code mode | view_image disabled; image_generation and code_mode_host false. Prove no alternate image/executor or nested code tool remains. |
| Subagents and permissions | multi_agent and agents.enabled false; request_permissions_tool false. Prove all collaboration/escalation tools absent. No subagent is launched by this feature. |
| Hooks and memories | Both feature families false. Bind effective loaders, local/remote sources and retained context; an event filter cannot undo a hook effect. |
| User/project/history | Ignore user config and user/project rules; zero project-document bytes, no resume, ephemeral session. Bind effective config, cwd ancestry and instructions; an empty cwd alone does not establish an empty inherited context. |
| Skills | skill_search false requests constrained discovery only. No catalogue token budget is set: zero is unsupported, and a positive value is not enforcement of instruction or tool isolation. A supported independently proven root-route skill/context boundary is unresolved. Custom-agent examples alone do not establish root exec applicability and are not copied as an attestation. |
| Mandatory policy and system context | Preserve built-in client system instructions and all mandatory managed security instructions/requirements. These are legitimate dependencies, distinct from unintended ambient user/project/history content. Never blank model_instructions_file, developer instructions or managed requirements to create apparent isolation. Refuse if policy requires an incompatible context/tool or cannot be attested. |

All listed controls are compatibility candidates, not operational proof. Model
output-event rejection is secondary validation, never a prevention mechanism.
**The shipped enforcement is the empty reviewed-client registry:** no real
client can reach metadata or inference through this module. Installing it
activates nothing, and no caller-supplied boolean or profile file enables it.

A future code-reviewed registry entry must include a `boundary_adapter` whose
bounded `lease(context)` obtains authoritative effective state and prevents its
drift throughout the subprocess. Nothing implementing that lease for a real
client ships here. It must cover the complete dependency closure: executable
and runtime/loader dependencies; effective configuration; mandatory managed
policy; all effective tools; integrations; built-in, mandatory and ambient
instructions; skills and discovery state; the actual filtered environment;
and exact protocol/implementation. Each category has an expected digest; missing,
unknown or changed state refuses before execution. A file list or claimed true
booleans cannot establish completeness, remotely delivered policy, or a lease.
If the installed route cannot expose and stabilize those dependencies, it
remains unsupported. No credential values may enter that evidence.

Preflight checks that contract for each metadata command. Each model attempt
reacquires it for its exact argv, executable hash, input/schema hashes, cwd and
actual passed environment, and rechecks model and controls. A failed preflight
clears earlier success. Environment values and raw dependency state are not
stored in result history. Synthetic adapters test dependency and invocation
drift, missing/unknown inventories, failed inspection, stale profile rejection,
and no execution after refusal. They establish the refusal mechanism only,
not the installed client's isolation or a real immutable lease. That proof,
reviewed implementation and registration remain explicit activation prerequisites.

## Current time and immutable outcomes

Freshness advances the previous effective time by the monotonic elapsed time
since its last sample, then takes the maximum with current wall time. The first
sample starts at invocation-start wall time. A forward jump rebases that clock;
it keeps advancing from the new high watermark even after a rollback. Forward
jumps expire support immediately; a backward jump or fixed test clock cannot
extend it, stall it or revive a decision. A separately supplied `now` anchors
the invocation, rather than freezing future checks. Total duration still uses
only the monotonic clock. Checks cover initial admission, each reservation,
each retained lookup and final acceptance. Expired evidence stays available as
clearly dated historical knowledge, never current support.

Decision applicability is reconciled at those boundaries. A change during an
attempt blocks further model calls and acceptance, retaining the updated prior
choice states. The history lock rechecks selected-case currentness at reservation
and supported-result append; the final freshness/decision check also runs inside
that lock. Evidence/decision expiry, a new skip/revocation, supersession, timeout
and uncertain completion never refund a consumed invocation. Results retain an
effective `checked_at` separately from original event/input and journal clocks;
result and original-input identities remain immutable. Synthetic tests cover
expiry during either call, forward/backward clocks, preflight delay, stale quota
at the next reservation, and expiry between external validation and append.

## Shared accounting and future provider broker

Model reservations are separate from provider GET accounting. This slice always
reports zero provider GETs. For a real transport the caller must provide an
already authorized shared-quota projection: original observation time, one or
two remaining-percentage/reset windows, and provenance digest. Match the
existing dispatcher's five-hour telemetry age ceiling and **<=15% pause in
either shared allowance**; invalid, unknown, expired or stale telemetry fails
closed. This module never starts a quota probe or reads sessions/conversations.
No quota or request budget is added/reset. A blocked invocation is retained;
there is no automatic retry after allowance changes in this first slice.

Any future live evidence broker needs separate authorization and reviewed code
to call the existing fixed GET-only provider interfaces **through their actual
shared reservation/cache/rate-limit ledgers and existing private credentials**.
Do not wrap raw HTTP around these controls or invent a replacement budget.
RecurringStore currently declares weekly limits whereas a retained historical
daily producer contract differs: neither is normalized or rewritten here.
Installed producer identity, timing, current queue and health remain unknown.
A replayed query result is retained evidence, not a new GET.

## Review and reproducible proof

Run in a suitable Python 3.12/3.13 project environment:

```sh
python -m ai_movie_investigator.replay --synthetic
python -m unittest -v test_ai_movie_investigator
python -m unittest -v
```

The offline command starts with the actual observer envelope shape in
`synthetic.json`. Fourteen synthetic cases cover confirmed identity with pending
source verification, a technical gap, two intentional skips, a reviewed
occurrence, six earlier shadow successes with stale display, unknown disposition,
conflicting IDs and materially changed occurrence/evidence. Nonempty retained
queries feed simulated model findings, durable records and private daily views.
It prints **SIMULATED — no real new identification** and uses a removed temporary
root. There is no private historical movie data in these fixtures.

`review.daily_digest` requires an explicit ISO date and IANA timezone. It reads
actual records as of that calendar day, exposes stable changed-result hashes,
prior choices, evidence, tools, uncertainty and next actions. A pending intake
is pending; an interrupted reserved call is failed/unknown. No schedule means
missed live runs are not measured. An empty history is quiet, not proof of a
healthy live queue. The detailed private case view retains provenance and scope
disagreements. Rendering never marks sent, acknowledged or archived and sends
no Telegram message. `propose_rule` records a generic failure pattern, actual
supporting result hashes and positive/negative test suggestions; it cannot edit
production code automatically.

The isolated installed-only test copies these exact runtime dependencies into a
temporary installation, invokes Python with `-I -B -S` outside the repository,
and runs nonempty replay plus legacy import. No site packages, PYTHONPATH, test
module or checkout fallback is available. Removing each existing dependency
must fail the proof:

```text
ai_movie_investigator/{__init__,contracts,history,controller,codex_transport,review,replay}.py
ai_movie_investigator/synthetic.json
identity_triage_intake.py
identity_triage_store.py
identity_selection.py
torrent_research_evidence.py
identity_research_handoff.py
identity_research_provider.py
```

These existing files are imported without changes; no historical shadow runtime
is promoted into product operation. The existing `movie-intel-test.yml` matrix
runs all root unittest tests on Python 3.12/3.13. The prior PR run checked a
tree-identical merge preview; the parent must arrange direct final exact-head CI.
Local supported tests do not establish published exact-head CI or independent
review; the parent owns both publication and that review path.

## Prerequisites for a later one-case real demonstration

This is a plan, not operational authority. The later sanctioned demonstration
must specify:

1. Independently reviewed exact public code and pinned runtime/dependency files,
   passing exact-head Python 3.12/3.13 CI, and the real client's complete audited
   tool/context boundary profile. A safe profile is a required code follow-up,
   not a reason to bypass a missing boundary or managed requirement.
2. Evidence of existing ChatGPT sign-in/model access and current shared quota
   through an already authorized route, with no credential copying or new API.
   No model/probe is commissioned by this document.
3. Exactly one sanctioned captured outcome, original bytes/hash, source/case/
   version/event/delivery binding, dated retained evidence and full trusted owner
   decision/revocation/supersession history. Redact capabilities before import.
4. A selected private owner-only storage grant, selected date/timezone, and exact
   private output/review destination. Rendering remains separate from message
   sending; any delivery needs its own sanctioned destination and authority.
5. One explicit invocation, at most two calls/five retained lookups, no fresh
   provider/source/screenshot requests, and durable unknown-attempt handling.
   Budget evidence must be shared, current and fail closed; preserve all actual
   producer limits. No private root or provider credential was inspected here.
6. Rollback: stop calling the standalone API and leave the transport disabled;
   preserve consumed history. No service rollback is needed because no existing
   service is changed. Do not delete evidence or retry an unknown invocation.
7. Separately report real model inference, evidence-supported candidate, system
   verification, production identification and delivery acknowledgement. The
   demonstration may establish only the first two. No automatic identity
   override, cache learning, source refresh, media/Radarr mutation or download
   consent follows. Original notification and explicit download confirmation
   remain unchanged.
