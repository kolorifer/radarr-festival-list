# Issue125: seven selected daily reporting opportunities

Task3 implements code only. The parent supervisor already has authorization for
independent exact-revision review, supported CI, selective deployment and this
fixed seven-day trial. No additional engineering task, generic schedule approval,
worker, runner, daemon, automation or notification is needed or supplied here.
Only the existing sole Mac dispatcher's ordinary poll executes the protocol.
Installing these files activates nothing. This document grants no child access.

The baseline supplied by the supervisor is public main93762ee and clean selective
launcher7cb003f7673d2440f7c023f3588ce2e521e2fa7a. These are supplied facts, not
worker observations of any installation. Issue122's completed archive/receipts,
original bytes and closed cycle are immutable. Issue119's eight claims, issue122's
three claims, issue125's three consumed slots, general eight, quota, both locks,
retained probe, code/state/claims/worktrees, plist, services, sources and unrelated
#86/PR110 remain. Code rollback never restores older claims, state or evidence.

## Review and selective installation (parent only)

1. Review the exact parent-published code revision and diff, including the small
   pure reader helper, separate trial protocol and issue125 cap. Require fresh
   exact-head Python3.12/3.13 CI. Local native3.9.6 tests and synthetic isolation
   are separate evidence, not substitutes for those CI jobs.
2. Run `python3 -B -m unittest test_coordinator_trial -v` at that reviewed head.
   Its installed harness copies ONLY the declared manifest into a new temporary
   bundle and runs native Python with `-I -B -S`, no site/PYTHONPATH/test modules
   or checkout fallback. Nonempty provenance/torrent data reaches function-local
   imports; deliberate withholding of ResearchStore's module and torrent evidence
   must fail. The complete bundle exercises actual dispatcher selection/poll,
   acquisition stubs, unchanged suppression, receipt/archive and seven-slot stop.
   Never use live exports, credentials, journals or selections as test fixtures.
3. Under the existing global and issue locks, inspect the clean installed checkout
   and compare against the supplied clean selective baseline. Preserve unrelated
   installed changes; stop on unexpected differences. Selectively apply the exact
   reviewed blobs below atop that launcher, rather than replacing it with main.
   No plist/service/schedule/state/permission change or dependency install occurs.
4. The dependency-complete manifest is `coordinator_trial.MANIFEST`, exactly:

```text
automation/github_worker.py
automation/supervisor_policy.py
automation/terminal_receipt.py
automation/coordinator_storage.py
automation/coordinator_runtime.py
automation/coordinator_transport.py
automation/coordinator.py
automation/coordinator_io.py
automation/coordinator_owner.py
automation/coordinator_cycles.py
automation/coordinator_exports.py
automation/coordinator_sources.py
automation/coordinator_diagnostics.py
automation/coordinator_integration.py
automation/coordinator_outbox.py
automation/coordinator_parent.py
identity_triage_store.py
identity_research_handoff.py
identity_research_provider.py
identity_triage_intake.py
identity_research_store.py
torrent_research_evidence.py
automation/coordinator_recovery.py
automation/coordinator_trial.py
```

5. Verify every installed blob's SHA256 against the reviewed blob, the clean HEAD
   and dependency closure in a disposable installed-only bundle. Parent commits
   the resulting selective deployment, publishes it on the EXISTING launcher
   branch and independently verifies its exact commit exists on GitHub **before
   any new reporting claim or activation**. Retain reviewed/deployed commit/tree
   and per-file hashes privately. Runtime also checks the remote deployed commit,
   local HEAD/manifest cleanliness and hashes before effects. Preserve old code
   for rollback; never roll back state/claims/evidence with it.

The reviewed public commit must be present in the installed repository's object
database. Runtime compares every installed manifest file's Git blob hash to an
exact regular100644 entry in that reviewed commit using fixed `git ls-tree`
arguments. A same-shaped owner hash map, an unreviewed file or a missing reviewed
object fails before the reporting claim. The selective deployment's surrounding
tree can differ; its runtime blobs must be byte-identical to the reviewed ones.

Native deployment preflight is read-only: installed package isolation, exact
code/commit/manifest, existing ordinary poll and locks. The supervisor later
verifies actual scheduled wakeups and outcomes separately. Do not run a second
dispatcher or add a manual/hidden CLI. Do not repeat Task2's SSH/timing queries.

## Selection: exact private authority and output grants

Use the existing private immutable-publication process for the selection. No
selection/body/payload, host, paths, identities or hashes belong in public issue
comments except the already accepted private pin form. A pin P has exactly
`repository,path,commit,tree,blob,sha256`: the accepted private repository,
canonical regular `.json` path, exact40-hex commit/root-tree/blob and64-hex content
SHA256. GitHub private-repository metadata, immutable commit/tree traversal,
regular100644 blob, exact byte count, Git blob hash and SHA256 are all checked.
Use canonical `coordinator_io.encode`; selection and journal each cap at65536 bytes.

Selection has exactly these keys:

| Key | Required value |
| --- | --- |
| version,repository,issue,phase | integer1, `kolorifer/radarr-festival-list`, integer125, `issue-125-seven-day-v1` |
| reviewed_revision,deployed_revision | exact public reviewed commit and remotely verified clean selective installed commit |
| code_sha256 | exact24-entry manifest map above, no omitted/extra entries |
| storage | existing commissioned private parent selection `{version:1,path,expected:{dev,ino}}`; reuse only |
| staging | existing separately commissioned private output directory `{path,dev,ino}` |
| source | unchanged exact accepted `{host,port,account,key,known_hosts,root,uid,gid,ancestors}` |
| recipient_chat | `01a18e6b-d16e-7e80-ab37-381b11891c2f` |
| producer_identity,installed_schedule | both literal `unknown` |
| windows | exactly seven ordered `{slot,start,end}` objects, slots1..7, consecutive UTC dates, `T11:30:00Z` to `T11:40:00Z` |
| requests | seven complete accepted owner-request templates, omitting ONLY `now`, as below |
| local_chains | exactly `{storage,staging,key_parent,known_hosts_parent}`: selected descriptor-chain observations, including every ancestor's exact path, `[dev,ino,uid,gid,mode]` and accepted ACL identity |

The supervisor chose11:30–11:40 UTC from two observed original export generation
times11:08:13 and11:05:13. This is NOT an independently verified installed timer.
For upcoming Warsaw dates that is12:30–12:40 local. After accepted deployment,
select the next upcoming11:30 UTC and its six consecutive successors. First start
must be AFTER activation comment and within24h of it; activation must execute
within1h of that unedited comment and before the first start. If safe accepted
activation cannot occur in time, do not reset a consumed claim or extend dates.

Source key/known_hosts selectors are existing canonical regular files, each
`{path,dev,ino}`; no bytes are copied or printed. Source ancestors are the accepted
ordered `[dev,ino,uid,gid,st_mode]` list including `/` and every canonical component.
No wildcard, home/root discovery, symlink, alias, new secret, permission repair,
new source file or source refresh is allowed. Source reads remain exactly
`incoming/snapshot.json` and `review-report.json`, <=2MiB each, through the existing
bounded read-only transport. Existing remote uid/gid/mode/ACL/ancestor checks,
local held credential descriptors/chain checks and transport keeper remain.
These detect stable-owner change; they do not claim atomicity against hostile
same-account swap-and-restore at an OpenSSH pathname open.

Construct each request with the EXISTING `coordinator_owner.request` function,
then remove `now`. Set:

| Request field | Required binding |
| --- | --- |
| version,runtime,owner,cycle | accepted integer1, phase above, exact issue owner, `day-N` |
| base | one explicitly selected NEW absent lowercase-named child under commissioned storage; different from phase evidence directory and original archived base |
| cycle_root | one selected child under NEW base, shared only for accepted comparison/history |
| intake_root,evidence_root,receipt_root | separate exact lowercase-named children under NEW base for EACH slot; no reuse |
| parent_output | seven distinct absent canonical lowercase `.json` files directly under the commissioned staging directory |
| selector,source_path,paths | `existing-exports-only`, same canonical selected source root, the two fixed export paths |
| destination | private accepted repository, exact absent `operations/issue-125/day-N.json` |
| recipient | same designated chat identifier above, distinct from owner |
| expected,evidence_manifest_sha256 | `absent`, null |

All fields other than the six slot-specific fields (cycle/intake/evidence/receipt/
output/destination) are identical across templates. Paths are explicit, not derived
as grants from broad storage access. The adapter checks lexical and descriptor
separation, exact spelling, ownership,0700 directories/0600 regular single-link
files, ACLs and before/after identities. No old engineering export is staged:
independent engineering/current parent findings stay unavailable here. The
selected code/review identities remain independently verified deployment facts.

The supervisor may capture `local_chains` read-only with the EXISTING
`coordinator_storage.Grant.chain(path,guard=True)` on ONLY the already selected
storage/staging/key-parent/known-hosts-parent, with `grant.home` set to the normal
OS-account home as in Runtime.guards. Retain its returned observation list
privately. This is a local selected-parent observation, not new host exploration
or a permission correction. Use Task2's unchanged selected source/ancestor facts;
no additional timing/metadata/SSH preflight is part of this code task or runbook.

## Activation and normal polling

Owner posts one unedited single-line canonical command generated by `io.encode`:

```text
COORDINATOR_TRIAL: {"action":"activate","phase":"issue-125-seven-day-v1","selection":P}
```

P denotes the complete six-field immutable pin, not literal text `P`. Issue body,
worker result, scheduled wakeup, trusted=true or journal JSON never substitutes.
Only the authenticated issue owner in exact repository/issue125 can select it.
Parent re-fetches issue/comments and original owner command under both locks;
latest DONE/closed, stop or newer engineering assignment prevents effects. Normal
engineering arbitration remains in force. Not-due polls avoid private selection
fetch, credential/source access, publication and writes.

Activation validates all code/roots/outputs, preflights unchanged credentials,
fsyncs an exclusive local claim_uncertain record, then attempts ONE fixed
create-only operation ref at the reviewed commit. Lost/uncertain claim burns the
phase; it cannot adopt an existing ref. It creates only the exact selected phase
evidence directory and records canonical selection/authentication. No source is
acquired at activation and no engineering execution is consumed. Subsequent
effects reauthenticate selection, code, original command, exact retained
authorization and remote permanent reporting claim.

The scheduling journal is the issue state file `issue-125-seven-day-v1.json`,
outside the accepted owner-store inventory. Phase records are under selected
storage's exact `issue-125-seven-day-v1/` child: selection/authorization and fixed
`day-1`..`day-7` directories. No other new storage epoch, cleanup or eviction exists.
Each day retains reservation, bounded original transport, preparation and, if
applicable, publication-observation/publication/acknowledgement/archive records.
Accepted owner intake, seals, receipts, active/archive content and output retain
their own exact grants and limits (MAX_INTENTS20, all existing byte/count ceilings).
Seven opportunities fit these existing caps; cap failures stop honestly.

At a due poll, durable slot consumption precedes owner.reserve and its ONE
transport. The clock is actual reservation/observation time, never scheduled
window start. Window/current owner checks run again immediately before reservation
and transport. Original source timestamps/bytes/SHA are unchanged; acquisition
completion time is retained separately. Snapshot freshness remains<3600s, report
freshness<172800s, future skew<=300s. No provider or source regeneration occurs.
Failed/missing/stale/incompatible data stays explicit; safe known cases survive
compatible standalone snapshot validation. Quality/release remains unavailable.

Past end is `missed`, with no source/credential/PUT operation. At most one selected
operation executes per poll. Several missed windows are recorded one per later
poll, with no catch-up acquisition. Lock contention/offline Mac/network cannot
extend a window; a poll after expiry records a miss. Clock rollback below the
durable high-water mark is inert until that clock is reached again. Restart reads
the durable reservations; no in-memory clock or callback grants another attempt.

Changed material prepares one immutable payload, accepted handoff and at most ONE
create-only GitHub PUT to the slot's exact private absent destination. Byte/blob/
SHA and immutable commit/tree readback precede publication receipt. No movie,
source or host data is emitted publicly. Unchanged material becomes `quiet`,
retaining per-slot evidence with no handoff/PUT or invented recipient receipt.
Original report hashes/version/evidence/material and availability/freshness changes
remain material. Only the declared recurring evidence semantics normalize
observation timestamps; no arbitrary alternate hashes or material-field removal.

## Reconciliation, actual recipient inspection and archive

Lost/uncertain PUT completion permits only an explicit owner command:

```text
COORDINATOR_TRIAL: {"action":"reconcile","phase":"issue-125-seven-day-v1","selection":P,"slot":N}
```

Maximum TWO distinct reconciliation comments per slot, within32 total trial
commands. Each is consumed before readback. No404, failure, restart or new comment
permits another PUT/acquisition. The existing verifier checks actual remote bytes,
Git blob, immutable commit/tree pin and SHA. A retained exact publication
observation may finish interrupted local receipt import using the same command;
there is no second mutable readback attempt for that consumed command. If a
readback fails before an observation, only the second explicit comment can read
again. Exhaustion is an unresolved outcome, never a retry slot or new task.

AFTER verified publication, the designated coordinator chat above must actually
fetch the exact immutable payload, check its pin/hash and inspect ALL content,
original source clocks, partial/stale coverage and independent unknowns. Parent
readback, child READY and automation wakeup are not ingestion. The supervisor
retains a concrete actual ingestion reference/time, then pins canonical ack A
with EXACT fields:

| Field | Binding |
| --- | --- |
| version,phase,slot | integer1, exact trial phase, integerN1..7 |
| selection | original P |
| binding | exact retained `{runtime,cycle,report,destination,recipient,payload_sha256,attempt}` |
| recipient_chat | exact designated distinct chat identifier |
| ingestion_reference | genuine retained identifier/reference, accepted identifier syntax |
| observed_at | actual ingestion epoch, >= retained publication observation and <= ack comment creation time |
| publication | exact retained immutable publication pin `{repository,path,commit,blob,sha256}` |

The ingestion event must precede the GitHub acknowledgement comment; post after
its timestamp, allowing GitHub's whole-second precision. The selected private ack
pin A has the six-field commit/tree/blob/SHA form. Then owner posts:

```text
COORDINATOR_TRIAL: {"acknowledgement":A,"action":"ack","phase":"issue-125-seven-day-v1","selection":P,"slot":N}
```

Wrong chat, owner, slot, report/hash/attempt/destination/publication, future or
pre-publication/pre-ingestion times, extra issuer/trusted fields, edits, conflicts
and cross-slot replay reject. The first exact ack remains the selected origin.
An invalid ack is consumed and cannot poll/retry indefinitely; conflicting
replacement pins are forbidden. A durably validated genuine ack may finish
interrupted receipt import/archive idempotently, preserving the same exact bytes.

Authentication guarantee: **owner-attested selection after actual distinct-chat
inspection**, not cryptographic proof that JSON identifies a chat. This code
provides no new recipient transport and cannot observe the chat itself. The
already commissioned supervisor performs the actual fetch/inspection here and
selects its concrete evidence; no future adapter or extra worker is assumed.
Only then is the accepted distinct recipient receipt imported. Archive checks
and fsyncs exact retained report/evidence/receipt bytes before releasing active
content. Check both the accepted archived record and phase acknowledgement/archive
records; publication alone never archives.

## Failure, stop and completion

| Boundary | Outcome and only permitted continuation |
| --- | --- |
| Unsafe selection/code/root/credential before activation | Refusal, no claim/source; no repair or inferred permission |
| Local claim or remote claim ambiguity | Phase consumed/inert; no adoption, reset or new claim |
| Slot consumed then reserve/acquire/seal/prepare/handoff interruption | That opportunity is burned; retain exact boundary/evidence, no automatic continuation/retry; later slots face unchanged accepted backpressure |
| Returned failed/uncertain transport | Honest unavailable report may be prepared once; no transport retry |
| quiet or backpressure | Retain outcome; no PUT or recipient receipt |
| publication_uncertain | Only the bounded exact readback protocol above |
| published | Only separately selected actual recipient ack, then archive |
| interrupted validated ack/archive | Same selected ack can finish exact local receipt/archive |
| archived/quiet/missed/burned slot | No further source/publication activity for that slot |

Consumed `reserved`, `acquisition_uncertain`, `preparation_uncertain`,
`handoff_uncertain` or `handoff_ready` boundaries also mean a burned opportunity;
they retain their precise original status rather than hiding it behind success.
After seven windows, no eighth source opportunity, worker, claim, automatic
extension or new publication is possible. Pending permitted readback and valid
recipient/archive reconciliation may finish without acquiring/publishing again.
Report each stage separately: implemented, independently reviewed, CI passed,
deployed, selected, acquired, published, actually ingested and archived. Seven
selected dates alone establish none of the later stages. Missed/partial/full
coverage and producer/timer unknowns stay explicit.

An owner can permanently stop this phase with canonical
`COORDINATOR_TRIAL: {"action":"stop","phase":"issue-125-seven-day-v1","selection":P}`.
No restart/replacement activation of a stopped phase exists. Latest trusted DONE,
issue closure and newer normal engineering assignment retain their existing
arbitration; none resets the seven-slot ledger. Keep original archive/evidence
and roll back code only if necessary. Supervisor's existing follow-up handles
actual review/acknowledgements and stops at completion; this worker creates no
follow-up automation or operational channel.
