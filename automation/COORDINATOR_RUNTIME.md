# Issue125 continuation

The distinct authorized seven-window trial is specified in
[COORDINATOR_TRIAL.md](COORDINATOR_TRIAL.md). It does not restart or reinterpret
the completed issue122 cycle below. The issue125 worker implements/tests only;
parent review, CI, selective deployment, activation and actual ingestion remain
separate stages.

# Issue 122 finite reporting route

Task3 correction: the Task1/Task2 **20-file closure claim was disproved** by
live review6543043459. The two function-local validator dependencies were absent.
The current manifest below has **23 files**: the two unchanged reviewed validators
and the fixed recovery module are added. Repository-wide import/tests alone are
insufficient. The isolated installed-package test is required independently.

The owner explicitly authorized exactly one additional engineering execution in
[6543142163](https://github.com/kolorifer/radarr-festival-list/issues/122#issuecomment-6543142163).
Task3 is final; issue122 cap3, general cap8 and all consumed claims remain.
The historical Task1/Task2 deployment/start instructions below are retained as
protocol context. **Do not start another cycle or acquisition.** Use the Task3
same-cycle recovery section for the retained original operation. No child live
access, installation, publication or operation is authorized.

Implementation and synthetic tests only. No deployment or real cycle has been
performed by this worker. The owner already authorized independent review,
bounded deployment, one supervised partial cycle and its later acknowledgement.
The supervisor carries out those fixed operations after the gates below; no
further engineering task, new executor, Work schedule or permission-reset is needed.
Issue 119's eight consumed claims and exhausted cap remain intact. Task8's
accepted source-directory correction and Task6's retained Mac probe are supplied
facts, not reasons to inspect or repair either host again in this code task.

## Review and selective installation

1. Independently review the exact parent-published revision and Python 3.12/3.13
   full CI. Review the synthetic Python 3.9.6 results separately: this is the
   deployed parent's interpreter, so newly reachable code must support it.
2. On the already authorized Mac deployment boundary, verify clean launcher
   `229148e7296c00ea635f8809b4e4f09320b920f7`, the sole installed invocation, and
   unchanged plist hash/cadence. Use the existing clone-wide `dispatcher.lock`
   and issue lock protocol; inherited locks must be released before updating.
   Do not launch a parallel parent/worker or touch the paused old supervisor watch.
3. Select ONLY the reviewed runtime blobs listed below. Apply the small
   `github_worker.py` integration patch atop launcher229148; compare its complete
   resulting blob with the reviewed file. The supplied baseline says the parent,
   policy and storage files match main. If that fact has drifted, stop for review;
   do not replace the launcher with main or overwrite unrelated launcher changes.
   Pin a clean resulting deployment commit and every manifest SHA256 privately.
   Retain the previous code for code-only rollback. Do not restore old state.
4. Preserve plist/schedule, all claim refs (including issue119's eight), quotas,
   worktrees, issue journals, retained probe/roots, uncertain outboxes, #86/PR110,
   source producers, production/research services and credentials. No permission
   repair, root creation, source refresh or service operation belongs to install.
5. Before releasing locks, compile/import the installed closure and run the
   synthetic focused suite with temporary homes and fake edges. Importing modules
   does not invoke `Runtime`, SSH, publication, storage selection or reserve.
   Verify the installed closure hashes, clean deployment HEAD and original plist
   hash. Release the existing locks for the next ordinary poll. No operation
   comment means no new effects. Do not exercise `operate` through a separate CLI.

Current selective runtime manifest (also `coordinator_runtime.MANIFEST`):

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
```

The six top-level modules supply offline validators only. The reachable import
chain is sources -> handoff.validate_snapshot -> provider.validate_case ->
research_store.ELIGIBLE and optional torrent_research_evidence.validate. Store
imports triage_store; all remaining reachable validator imports are stdlib.
The intake validator's optional torrent evidence uses the same included module.
SQLite imports are inert; no Store/ResearchStore constructor or transaction is
called. Torrent HTML extraction's local bs4 import and producer confinement,
observer and identity-selection imports are unreachable in this offline route. Their
transport/provider/producer entrypoints are never called. Sandbox modules imported
only by unused producer confinement functions are outside this reachable closure.
No dependency installation is introduced. Test modules are review/validation
artifacts, not a new operational entrypoint.

## Canonical owner comments

Only unedited comments by the authenticated current **issue owner** on open
`kolorifer/radarr-festival-list#122` select this phase. The parent account must be
that owner. The description, tasks, other authors, source prose and worker JSON
are never operational authority. The existing poll, under its clone-wide lock,
honors closed/latest-trusted DONE before selection and selects at most one
engineering task OR pending fixed operation, ordered by comment ID;
the operation also takes the existing per-issue lock. It never calls
`run_selected`, quota probes, Codex, engineering claim refs or the old publisher.
Issue122's engineering path has a separate three-execution ceiling; the existing
eight-execution guard remains unchanged elsewhere.
An explicit newer owner engineering directive supersedes an older operation
command, preserving the existing latest-task rules and three-execution ceiling.
It does not reset the operation; resumption requires a newer matching explicit
continuation and the same exact deployed identity. Complete code correction and
exact-revision review before the pilot; installing new code cannot silently
rebind an already consumed operation to a different revision.

Each command is exactly one line: `COORDINATOR_OPERATION: ` plus JSON produced by
`coordinator_io.encode(command).decode('ascii')` (sorted keys, compact separators,
no trailing whitespace/newline). Duplicate keys, alternate casing/spacing, extra
keys, unsupported actions, edited comments or conflicting pins reject. There
must be exactly ONE start comment and at most 32 total phase commands. Start must
be at most one hour old when first consumed; its pinned request clock must be
at most five minutes before the first poll and cannot be in the future. Once
consumed, age never reauthorizes it. Bound local phase state filters consumed
starts, consumed inert reconciles and completed archive acknowledgements before
private-input fetch/validation, so they cannot starve another issue. Malformed or
unbound journals grant no work. A fresh explicit matching reconcile/ack remains
eligible. A consumed reconcile can finish receipt import only when the exact
anchored durable publication observation exists; completed publication is quiet.
Comments are fetched again individually and compared byte-exactly with their
authenticated owner/ID/creation/update/body origin before use.

The following are schemas, with `P` and `A` replaced by full pin objects:

```text
COORDINATOR_OPERATION: {"action":"start","phase":"issue-122-partial-v1","selection":P}
COORDINATOR_OPERATION: {"action":"reconcile","phase":"issue-122-partial-v1","selection":P}
COORDINATOR_OPERATION: {"acknowledgement":A,"action":"ack","phase":"issue-122-partial-v1","selection":P}
```

Every pin has exactly `repository`, `path`, `commit`, `blob`, `sha256`:
repository is `kolorifer/radarr-state`, path is exact ASCII repository-relative
JSON (no aliases/traversal/query), commit/blob are full lowercase 40-hex Git IDs,
SHA256 is 64 lowercase hex. The repository must be authenticated private with
default branch main. Nonrecursive exact tree traversal requires modes 040000 /
100644; symlinks, submodules, truncated/ambiguous trees and changed bytes fail.
Git blob hash, size, SHA256 and exact contents path are independently checked.
Start/ack selections are each at most 64 KiB. No mutable branch is a pin.

## Private initial selection schema

Strict finite JSON, no duplicate/unexpected keys, nonfinite numbers or defaults.
All identity numbers below are actual private observations supplied by the
supervisor, not illustrative values to reuse. No real endpoint/account/home/key,
source bytes or receipt/chat references belong in public artifacts.

| Field | Exact contract |
| --- | --- |
| version | integer 1 |
| repository; issue; phase | public repository above; integer 122; `issue-122-partial-v1` |
| operation | one accepted 1..80 ASCII identifier; equals request.cycle |
| deployed_revision | clean, exact installed parent HEAD, full 40 hex |
| reviewed_revision | existing parent-published reviewed commit in the public repository, full 40 hex; authenticated commit lookup; operation claim target |
| code_sha256 | object with exactly all manifest paths above, each exact installed 64-hex SHA256 |
| storage | accepted storage selection: version 1, exact current OS-account home + fixed suffix `/.local/state/movie-project-coordinator-private`, expected object `{dev,ino}`; **absent is forbidden** |
| staging | exact preexisting separate private parent `{path,dev,ino}` |
| source | exact object described below |
| request | complete accepted `coordinator_owner.request` value described below |
| recipient_chat | exact designated successor chat identifier; accepted identifier syntax; differs from owner |
| independent | null or exact object `{manifest:P,engineering:P-or-null,parent_status:P-or-null}` |

Source fields are exactly `host`, `port`, `account`, `key`, `known_hosts`, `root`,
`uid`, `gid`, `ancestors`. Host is literal lowercase DNS/IPv4 spelling (no aliases,
options, IPv6, trailing dot or shell syntax); port is integer 1..65535; account is
bounded lowercase Unix account spelling. Key/known_hosts each select an existing
private regular mode0600 file with `{path,dev,ino}`. They must be outside writable
coordinator/staging/public/Git trees. Exact ancestor spelling, UID/mode/ACL and
stable file identity are checked before consumption without reading, printing or
copying key bytes. SSH uses the selected canonical original file paths; the fixed
keeper and parent retain descriptors for before/after validation. No agent or
ambient config is used. The stable-owner limitation is stated below.

Root is the canonical absolute **physical** source root, not a symlinked home.
UID/GID are explicit numeric source ownership. Ancestors is the exact ordered
list from `/` through root, one `[dev,ino,uid,gid,st_mode]` per directory, including
file-type bits. All are root/current-source-UID owned and not group/other writable;
root is source-UID/GID-owned mode0700. The reviewed Linux helper accepts only
positively absent descriptor POSIX ACLs. Unsupported/uncertain ACL evidence fails
closed. Fixed incoming is source-UID/GID-owned 0700 and files are 0600 with one link.
Do not repair permissions to make this protocol pass.

Request is the exact returned value of accepted `owner.request`, including all
fields: `version,base,runtime,owner,cycle,now,intake_root,cycle_root,evidence_root,
receipt_root,parent_output,selector,source_path,paths,destination,recipient,
expected,evidence_manifest_sha256`. Version is 1, runtime is the fixed phase ID,
owner is the authenticated issue owner's login, now is the ORIGINAL observation
clock, cycle is operation, and paths are the two accepted fixed export names.
Base is NEW under the commissioned enclosing root (never the root itself).
Intake/cycle/evidence/receipt roots are distinct new direct children with accepted
lowercase names. No old adapter/evidence tree is adopted. Parent output is one
new lowercase JSON filename in the exact selected staging directory, outside
base/enclosing root/checkout/Git journal. Existing roots/aliases/unstable identities
or overlaps reject. `selector` binds the explicit source selection identifier;
source_path equals source.root. Expected is `absent`. Destination is exactly
`{repository:"kolorifer/radarr-state",path:"operations/issue-122/<operation>.json"}`.
Recipient is the exact designated coordinator system identifier, distinct from owner.

Optional independent inputs select original existing exports, never live journal
roots. Manifest uses the accepted schema, permits only fixed engineering.json /
parent_status.json paths and pins their exact bytes; all movie/quality paths are
null. Its SHA256 equals request.evidence_manifest_sha256. Each export retains the
existing parent decoder's 900000-byte ceiling, despite the accepted offline
reader's larger upper bound. `parent_status` can explicitly represent issue119
tasks1..8 with all eight consumed histories; engineering can include issue122's
selected current-phase findings. No enumeration of unrelated journals occurs.
Missing/invalid/stale movie exports cannot erase valid independent findings.

## One supervised cycle and retained evidence

1. Supervisor prepares and checks the private selection after exact code review,
   CI and bounded deployment. It posts the canonical start under the existing
   one-cycle authorization, then observes **ordinary** dispatcher pickup. Do not
   launch another parent, engineer a task, invoke owner CLI manually or refresh a
   producer. There is no new generic approval question.
2. Before any phase journal, cross-host claim, evidence/adapter creation or
   acquisition reservation, the parent performs deterministic LOCAL credential
   preflight. Both selected files and ancestors must have exact canonical spelling,
   no links, trusted OS-account ownership, accepted mode/ACL, pinned device/inode,
   separate identities, private-state separation and size bounds (1..65536 bytes).
   File parents remain 0700; files remain 0600 with one hardlink. Unsafe/missing/
   replaced inputs cause zero phase consumption, claims, adapter/source access or
   publication. No chmod, alternative path or permission repair is attempted.
   The OS account profile comes from pwd, including for short SSH-parent paths.
   Held descriptors and namespace/ACL evidence are revalidated before and after
   transport in both keeper and parent. Network source checks still occur only
   after the one durable acquisition grant. Optional independently pinned
   engineering/parent export reads also wait for successful local preflight.
3. The private issue journal `finite-reporting-phase-1.json` is created/fsynced
   with full request/origin/pin before the separate create-only GitHub ref
   `refs/heads/automation/reporting-operation-issue-122-phase-1`. Only a confirmed
   exact create response targeting reviewed_revision permits effects. The local
   selective deployment commit need not be published. Existing refs or lost responses never
   grant ownership. That namespace never touches numbered engineering claims.
4. After confirmed claim, retain new `finite-phase-1/` alongside the retained probe
   and a NEW anchored adapter base. Reuse storage is guarded read-only; no chmod,
   chown, adoption, enclosing mkdir, ACL repair or probe modification. Accepted
   owner.reserve durably records the whole immutable request/original clock before
   its first acquisition_grant permits one external acquisition. Lost grant burns it.
5. One `/usr/bin/ssh` uses `/dev/null` config and the already selected exact
   canonical key/known-host FILE PATHS, strict host-key/publickey checks and no
   forwarding/proxy/multiplex/password/agent/TOFU. OpenSSH9.0p1 closes FDs above2
   before parsing options; `/dev/fd/N` is not a supported credential handoff here
   ([upstream source](https://github.com/openssh/openssh-portable/blob/V_9_0_P1/ssh.c#L599-L606)).
   No private-key bytes are read/copied/hashed/staged by the dispatcher/keeper.
   OpenSSH opens the guarded original files itself. Before/after descriptors,
   namespace, owner/mode/ACL/device/inode checks detect changes under the accepted
   stable-owner threat model; they do **not** provide atomic protection against
   a hostile same-account swap-and-restore while OpenSSH opens a pathname.
   A fixed forked transport keeper holds both dispatcher lock descriptions and
   supervises exactly one SSH child, even after initiating-parent death and SSH
   descriptor closure. It has no command/request execution protocol, CLI, worker,
   scheduler, daemon, retry or persistent loop. Only fixed reviewed transport code
   runs. SSH gets no inherited credential/lock FDs. The keeper kills/reaps only its
   own SSH subprocess on deadline/output/error failure; all diagnostics stay in
   bounded private pipes, never inherited public stdout/stderr. Local SSH bound45s,
   stdout6MiB, stderr16KiB; result transfer adds at most5s (parent wait55s).
   SSH executes only `/usr/bin/python3 -I -B -` and the reviewed helper on stdin,
   with JSON data escaped into Python literals, never shell interpolation.
   Before source path access, actual effective UID must be nonzero and match the
   selected numeric UID; effective GID must match too. An independent remote30s
   alarm bounds helper lifetime after code loading even if SSH is lost. `-B`
   explicitly disables bytecode writes. The helper descriptor-traverses the same
   exact components and only reads `incoming/snapshot.json` and
   `review-report.json` (2MiB each), checking metadata/ACLs before/after. No remote
   writes, source handoff/scan/research, DB reads or provider calls occur.
6. Retain exact bounded transport stdout/stderr/exit/completeness/acquisition time
   privately in `finite-phase-1/transport.json` (base64 bytes, at most about8.1MiB
   including encoding). Successful original file bytes, hashes and original file
   metadata remain bound there and in accepted intake/seal/report evidence. No
   Task8 bundle is reused as new acquisition. Failed/unsafe/uncertain transport
   yields unavailable movie inputs, without transport retry; remote failures do
   not prove missing source files. Stale original generation times stay stale.
7. Accepted seal/prepare/handoff use the reserved clock. Format2 and existing
   byte/capacity/fsync guards remain intact. The one <=512KiB handoff records
   uncertain before exposing exact parent output. Publication verifies private
   destination/absence, durably consumes the write, then makes at most ONE PUT
   without a replacement blob. Authenticated byte-exact readback is verified
   again against an immutable commit/tree/blob/SHA256 pin. Lost PUT/readback can
   only be reconciled by reads. No old issue-global private-receipt.json is written.
8. Separately retained `publication-observation.json` and `publication.json` bind
   runtime/cycle/report/destination/recipient/hash/attempt, observed immutable
   remote pin, actual readback and accepted publication receipt. The candidate is
   durable before import, so interruptions reuse its exact observation time/bytes.
   An observed commit after a lost PUT reply is readback evidence, not proof that
   the parent received a successful PUT response. Publication alone cannot archive.

Private `authorization.json`, `selection.json`, transport, publication observation,
publication, acknowledgement and archive records live in fixed finite-phase-1.
Its anchored identity is in the issue journal. The adapter retains accepted
intent/seal/intake/evidence/inbox plus format2 active/archive evidence. There is
one opportunity and no state cleanup/eviction/reset. Existing accepted adapter /
cycle ceilings remain unchanged; exhaustion preserves history. Public output is
fixed status/rejection text, with no private exception/payload/path/endpoint/hash.

## Actual designated coordinator ingestion and acknowledgement

The current designated coordinator must actually fetch the immutable published
payload, verify its pin/hash and inspect its full content, source clocks, partial
coverage and independent findings in the selected chat. Supervisor retains a
concrete ingestion reference privately. No automatic chat invocation or message
to another person exists. A worker READY, parent engineering receipt, readback,
JSON issuer, trusted=true or matching hash cannot substitute.

Only AFTER verified publication and that real ingestion, supervisor pins a private
ack selection with exactly these fields:

| Field | Exact binding |
| --- | --- |
| version; phase; operation; selection | integer1; same fixed phase, original operation, original start pin P |
| binding | exact original accepted attempt object: runtime, cycle, report, destination, recipient, payload_sha256, attempt |
| recipient_chat | exact initially selected successor chat, never an old chat or parent |
| ingestion_reference | concrete retained ingestion reference in accepted identifier syntax |
| observed_at | actual ingestion epoch, at/after retained publication observation, no later than ack comment clock +300s |
| publication | exact retained immutable publication pin (repository,path,commit,blob,sha256) |

Post the canonical ack command with this immutable pin A and original P. Parent
reauthenticates and retains the original unedited owner's comment identity/body,
validates every field/time/conflict before receipt mutation, constructs/imports
the accepted distinct recipient receipt and calls accepted archive. The archive
verifies/fsyncs exact complete original evidence/receipts before freeing active
copies. `acknowledgement.json`, accepted recipient receipt, archive record and
issue journal status archived are the distinct acceptance evidence. Later polls
with the same completed request make no acquisition, PUT or archive writes.

Guarantee: **owner-attested selection after real designated coordinator ingestion**.
GitHub authenticates the expected account/comment; it does not cryptographically
identify a Codex chat. The supervisor must supply actual ingestion evidence during
the pilot. Synthetic fake identities prove mechanics only. No full movie-coverage
claim follows, even if publication, ingestion and archive all succeed.

## Failure and recovery

| Boundary | Allowed next observation/action |
| --- | --- |
| No command | Existing behavior; no new private lookup, SSH, storage or publication |
| Validation/unsafe root/credential/pin/revision/author/conflict | Fixed refusal, no operational consumption; correct the selection before an accepted start, never repair private permissions through this code task |
| Lost/contended claim | Local consumption retained, no acquisition/effects; inspect exact private claim/history; never adopt a preexisting ref or replay |
| Reserve/acquisition/seal/prepare/handoff interruption | Opportunity consumed; retain all bytes; repeated start inert; no transport/preparation/publication retry or new cycle |
| Successful failed/uncertain transport return | Honest unavailable movie evidence can still prepare/publish independent findings, once |
| Existing private destination | No PUT; retained handoff stays consumed; no overwrite |
| PUT/readback ambiguity | Supervisor posts matching reconcile; one read-only remote attempt for each distinct reconcile comment, local verification/receipt import only; never another PUT |
| Failed reconcile | Same comment is inert unless its bound publication observation permits interrupted receipt import; a new explicit matching reconcile may select another readback (32-command total cap) |
| Invalid/wrong/conflicting acknowledgement | No recipient receipt/archive; stop for supervisor review; no recipient substitution or new operation |
| Receipt/archive interruption | Same genuine selected acknowledgement can finish idempotently with exact retained bytes; never reacquire/republish |
| Complete | Quiet/inert; no recurrence, retention reset, further engineering execution or automatic successor |

An interruption before usable payload/write intent may leave this single cycle
unable to finish automatically. This is a deliberate safety limit, not permission
to invent a receipt, repeat SSH/PUT, change roots or spend a third engineering
task. Reconciliation requires publication_uncertain or a later verified state;
an ack cannot implicitly reconcile a missing publication. Linux source ACL support
and regular private key files are explicit limits. No provider-managed service,
source refresh, direct supervisor SSH, source permission change, production action
or new filesystem grant is an escape hatch.

The supervisor records **deployed**, **publication verified**, **actual distinct
ingestion selected**, and **archive verified** separately, with exact immutable
private evidence. None is established by installing this code or passing tests.


## Task3: explicit recovery of the retained SAME sealed pilot

This is supervisor-only protocol after independent exact-code review, passing
exact-head Python3.12/3.13 CI, native3.9 focused validation and installed isolation.
The worker does not run these steps. The original live failure and original
selection/start/reviewed/deployment identities remain immutable. The supplied
admission-only launcher package is `3f7562cb426cf45c59763fcab36b9610f2cf4a85`;
compare it against the original selective deployment and require only issue122's
two thresholds and limit message to differ. Selectively install the 23 reviewed
blobs under the **existing two locks**, preserving clean parent changes; pin the
resulting new deployment commit and exact SHA256 map privately. Never replace the
launcher with main wholesale. No service/plist/watch, permission, root or claim
operation is needed. Preserve old code for code-only rollback; never roll back
state. Installing code selects no recovery.

Run isolation on a temporary installed bundle copied from those exact blobs,
using only that bundle and stdlib (Python `-I -B -S`, no PYTHONPATH/site/test-module
fallback). The reviewed `test_coordinator_recovery` installed harness includes
both deliberate missing-module refusals, nonempty torrent evidence, original-byte
reader staging and the finite recovery/publication/recipient/archive sequence.
Run `python3 -B -m unittest test_coordinator_recovery -v` from the exact reviewed
source as the test driver; its child imports only the temporary manifest bundle.
Do not mistake driver/repository smoke imports for isolation evidence. No
credentials, home, private selections or exports from the live pilot are test
fixtures. No dependency installation is part of installation or testing.

### Strict recovery selection and owner command

Let P be the **unchanged original** private selection pin, R a new immutable
private recovery selection pin, and A a later immutable genuine ingestion pin.
Pin shape, private-repository/commit/tree/blob/SHA256 checks and unedited
owner-comment authentication are exactly as specified above. All recovery
selection JSON is canonical `io.encode`, <=65536 bytes. R has exactly:

| Field | Required value |
| --- | --- |
| version | integer1 |
| phase; operation | `issue-122-partial-v1`; `partial-1` |
| original_selection | P, byte-exact original pin |
| original_start | authenticated immutable original `{id,body,created_at,updated_at,author}` |
| request_sha256 | `c.fingerprint(original_selection_value['request'])` |
| code | exactly `{reviewed_revision,deployed_revision,code_sha256}`; NEW reviewed public commit, NEW clean installed HEAD and all23 installed blob SHA256s |
| checkpoint | exactly `{directories,files}`, read-only fixed-role inventory described below |

No source/root/path/clock/recipient override is accepted. Original selection
retains its original20 code pins; R attests the code transition separately. The
parent authenticates BOTH public reviewed commits and the current clean installed
code identity. Every later continuation reauthenticates P, R, original start and
recovery origin; a local journal is never authority.

The supervisor obtains the checkpoint only from the explicitly retained local
paths already bound in P/request/journal, using the read-only function
`coordinator_recovery.capture(runtime_view)`. `runtime_view` has exactly the
selected `req`, `runner.state_dir` and the selected enclosing root's fixed
`finite-phase-1` evidence path; it is NOT an operational Runtime invocation.
No credential/source path is opened. The function returns `(checkpoint, contents)`;
only checkpoint goes in R. Do not post either value publicly.

Directories are fixed roles `phase,adapter,intake,incoming,independent,receipts,
cycles,active,archive,handoff,stage` and present optional `movie,combined`, each
`{identity:[dev,ino],acl:<accepted ACL identity>}`. Files are fixed role/name keys,
with exactly `{metadata,acl,sha256}`. Metadata is the exact ordered list
`[dev,ino,uid,gid,st_mode,size,mtime_ns,ctime_ns,nlink]`. No arbitrary relative or
absolute path is accepted. `parent/journal` is the original parent journal.
Adapter files are identity, lock, exact intent and exact seal; phase files are
original selection/authorization/transport; intake files are only the two fixed
exports; independent files are manifest/engineering/parent_status; cycle files
are identity/state/lock; stage has independent.json and optional bounded reader
movie/combined files. Active/archive/handoff/receipts must be empty. Parent output
must be absent. All required directories exist; optional missing paths must be
proven absent. Private mode0700/0600, owner, no-follow/spelling, stable file
metadata/ACL, one link, per-file12MiB, tree total32MiB/48 files plus the
<=64KiB parent journal, and24 entries per directory limits apply.
Existing lock files are selected; no permission repair is permitted.

For a read-only selection preparation script, after authenticating P using the
same immutable fetch and original owner origin, the value is constructed as:

```python
import types
from pathlib import Path
from automation import coordinator, coordinator_io, coordinator_recovery

view = types.SimpleNamespace(req=original['request'],
    runner=types.SimpleNamespace(state_dir=selected_original_issue_state_dir),
    evidence_root=Path(original['storage']['path']) / 'finite-phase-1')
checkpoint, _ = coordinator_recovery.capture(view)
recovery_value = dict(version=1, phase='issue-122-partial-v1', operation='partial-1',
    original_selection=P, original_start=authenticated_original_origin,
    request_sha256=coordinator.fingerprint(original['request']),
    code=dict(reviewed_revision=reviewed_commit, deployed_revision=installed_commit,
              code_sha256=exact_installed_manifest_hashes), checkpoint=checkpoint)
raw = coordinator_io.encode(recovery_value)
```

The snippet does not fetch, reserve, seal,
prepare, start the dispatcher or perform any live recovery. Retain the canonical
selection through the existing private immutable-pin publication process and
independently read it back before posting R. All variables denote the exact
already selected private identities, never newly discovered homes/roots.

The canonical owner commands are generated by `coordinator_io.encode`, not manual
JSON editing. Exactly one recovery command is allowed, newer than original start:

```text
COORDINATOR_OPERATION: {"action":"recover","phase":"issue-122-partial-v1","recovery":R,"selection":P}
COORDINATOR_OPERATION: {"action":"continue","phase":"issue-122-partial-v1","recovery":R,"selection":P}
COORDINATOR_OPERATION: {"action":"reconcile","phase":"issue-122-partial-v1","recovery":R,"selection":P}
COORDINATOR_OPERATION: {"acknowledgement":A,"action":"ack","phase":"issue-122-partial-v1","recovery":R,"selection":P}
```

Post only `recover` initially; the ordinary sole dispatcher poll selects it
under its normal global/per-issue locks. No CLI/manual launch is provided.
Closed/latest trusted DONE still wins. A NEW operation claim, reserve, credential
preflight, SSH, reseal, source reread/refresh or changed clock is forbidden.
The initial gate requires original confirmed claim GET and original authorization,
reservation/intent/seal, exact preparation_uncertain journal, exact collecting
cycle/request, selected independent checkpoint and no collection/report/baseline,
output, handoff, receipt, write intent or archive. Compare all exact checkpoint
bytes/metadata and existing grant baselines before touching adapter state.
Unsupported or conflicting boundaries stop; do not reset or silently re-pin them.

Before recovery effects the parent separately fsyncs canonical
`recovery-selection.json`, `recovery-retained.json` (base64 exact original files,
including parent/cycle/checkpoint/partial-staging bytes) and
`recovery-authorization.json`, then anchors their selection/authorization hashes
in the existing parent journal. Original authorization/transport/intake/seal remain
untouched. The retained copy preserves partial reader bytes when the accepted
cycle reclaims disposable staging. All evidence stays private in the original
fixed phase directory; the core's accepted archive retains its immutable report,
independent evidence and exact publication/recipient receipts. Parent archive.json
and recovery evidence retain the cross-reference to the original operation and
new authorization. Verify both the archived record and these retained originals.
No engineering claims or original journal file are reset. A separate bounded
private command-consumption ledger in the existing issue state records authentic
recover/continue handling; a refused command is quiet without modifying the
original adapter/evidence. It is scheduling evidence only, never authorization.

### Allowed interrupted continuations and completion

Recovery calls only accepted `owner.prepare` on the ORIGINAL request. The existing
collecting entry forces `collect(resume=True)`: it reuses the authenticated saved
independent checkpoint and labels movie collection interrupted/unavailable. It
NEVER rereads the movie source or tries to complete partial reader output. Original
generation/observation/acquisition clocks remain retained. A successful partial
report proves no current full movie coverage and does not repair the original
research-report incompatibility or stale sources.

Each recover/continue command is consumed once. Repeated ordinary polling is
quiet before private fetch; completed/archive commands do not starve other issues.
Only a newer explicit matching `continue` may finish interrupted preparation or
handoff before publication. Safe boundaries:

| Retained boundary | Only allowed continuation |
| --- | --- |
| Auth files written without parent recovery binding | Stop: unanchored evidence; no automatic adoption/reset |
| Bound recovery, interrupted prepare | New `continue`, accepted same-request prepare/resume; unbound core checkpoints still refuse |
| Prepared core, no handoff attempt/output | New `continue`, accepted first handoff |
| Core handoff attempt AND exact durable handoff + parent output; parent return lost | New `continue` verifies exact record/binding/output, never repeats handoff |
| Core handoff attempt but no exact parent output | Stop: accepted owner handoff consumed; no second handoff/exposure is granted |
| handoff_ready, no write intent | New `continue` may perform the sole PUT |
| publication_uncertain / lost PUT response | Explicit matching `reconcile`, READBACK ONLY; no second PUT even after404 |
| Durable publication observation, interrupted import | Same consumed reconcile may finish exact observation import under existing rules |
| Published, distinct selected ack/import/archive interrupted | Same authenticated ack finishes idempotent accepted receipt/archive; no new write |
| Archived or consumed failed recovery/continue | Quiet; no source/private-input polling or new opportunity |

A fresh reconcile that fails readback is consumed and quiet until another
explicit matching reconcile. Core ambiguous checkpoint or unexposed handoff can
remain impossible to finish under accepted safety boundaries; retain it and report
the precise reason. No Task4/successor/reset follows automatically.

After actual immutable publication readback, the already-authorized designated
successor coordinator must fetch that exact pinned payload in the actual chat,
read its honest partial findings and retain a truthful ingestion reference. Only
THEN does the owner publish A with the existing ack fields PLUS exactly
`recovery:R`, preserving original P/binding/publication/recipient_chat. The parent
constructs a recipient receipt only after fresh authentic owner selection of A.
A JSON issuer, sender readback, engineering terminal receipt or hash alone proves
no ingestion. Observe accepted archive=true and exact archived report/receipts,
verify retained original intake/seal/transport and recovery authorization hashes,
then confirm later ordinary polling stays quiet and other issues progress. These
actual publication, distinct ingestion and archive gates remain separate from
synthetic tests and from installation. No recurrence is enabled.
