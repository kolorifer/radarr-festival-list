# Caller-invoked reporting cycles (issue #117)

This is an offline CLI/library component, with synthetic lifecycle verification.
It runs the accepted original-byte movie reader and existing observation
validators. It does not run engineering tasks, publish to a network, send a
message, refresh sources, install a process or schedule itself. Live integration,
transport, recipient ingestion and recurring operation remain unverified.
The separate v2 issue/task outbox and its 20 retained entries are unchanged.

## Explicit interface and owner sequence

The later accountable owner supplies every root and identity. Paths below are
placeholders, not discovered or authorized operational locations. Root arguments
must be canonical absolute paths with one leading slash, no dot components,
trailing slash or symlink ancestors. The cycle root must be NEW, under an existing
owner-only directory, outside the checkout, source, staged-evidence and worker
state trees. An existing root is usable only with this component's matching
`identity.json`. No existing state is migrated or adopted. A failed initialization
that leaves an unmarked directory is rejected; preserve it and select a new root.
Before any mkdir, marker, lock, temporary cleanup or state write, the component
checks source/evidence spellings and filesystem identities against the intended
writable root and checkout. Symlink components, ambiguous/inaccessible directory
opens and errors in identity/separation guards reject the invocation; they are
not downgraded to movie unavailability. No supplied symlink is resolved and no
alternate root is guessed. A proven missing descendant is allowed only after
no-follow ancestor checks establish safe separation. If both the state root and
a protected entry below its immediate parent are absent, separation is unproven:
filesystem case/normalization rules could alias their prospective names. This
case rejects without writes, even for apparently different names, rather than
guessing those rules. Missing descendants below a distinct existing directory,
or proven absent paths against an existing state identity, remain reportable.
Once separation is proved,
missing or inaccessible export files still produce useful partial reports with
independent findings. An inaccessible source directory whose separation cannot
be established rejects before writes; an OS error alone does not identify a
specific symlink cause. This applies to existing state too, before cleanup.

Concurrent initialization can reject a caller before the identity marker exists;
retry its identical request after initialization. Subsequent callers serialize
on the cycle root's `lock`. This is not an engineering lock or liveness evidence.

The root and all newly owned stable directories are owner-only, with private
regular files and no-follow traversal. The external owner must prevent directory
replacement by another writer. That stable-directory assumption is the same as
the accepted reader's; these checks do not authenticate a compromised local owner.
Inputs are caller-selected offline exports, never an invitation to discover
homes, credentials, worker state, remote files or changing source identifiers.

1. Select a runtime ID, accountable owner ID, named system recipient, private
   destination, stable cycle ID and observation timestamp. IDs use the existing
   bounded identifier syntax. One cycle ID binds the whole request, including
   timestamp, roots, optional manifest, destination and recipient. Retrying it
   must use the same request. A new acquisition always requires a new cycle ID.
2. Optionally stage an existing observation manifest and exact original bytes
   for `engineering` and/or `parent_status`. Other manifest source paths must be
   null. The same source validators check identities, hashes, times, full
   engineering findings and projected parent contracts. Missing/invalid optional
   inputs remain unavailable; neither source can erase the other's valid findings.
   Do not point this interface at live parent journals. A separately authorized
   adapter must export/validate selected journal evidence first.
3. Invoke one cycle:

   ```text
   python -m automation.coordinator_cycles cycle
     --root <new-cycle-root> --runtime <runtime-id> --owner <owner-id>
     --cycle-id <stable-cycle-id> --now <unix-observation-time>
     --source-root <explicit-movie-export-root>
     --evidence-root <explicit-staged-independent-root> --manifest manifest.json
     --destination-repository kolorifer/radarr-state
     --destination-path operations/<explicit-private-artifact>.json
     --recipient <named-system-recipient>
   ```

   Omit both optional evidence arguments when none is supplied. The actual
   `stage_exports` reader reads only `incoming/snapshot.json` and
   `review-report.json`. It never refreshes either producer. Its manifest and
   acquired bytes are preserved; a separate combined manifest is constructed in
   newly owned staging. Copies are exact bytes, never source hardlinks or
   escaping paths. Compatible movies remain `partial/incomplete_upstream`.
   Investigations expire after 3600 seconds and research reports after 172800;
   collection time cannot renew their embedded generation times. Complete case
   sets, source pairing and proposal/evidence versions remain required.
   Quality/release evidence is always `unavailable/passive_export_missing`.
4. When `status=prepared`, obtain a local publication handoff:

   ```text
   python -m automation.coordinator_cycles handoff
     --root <cycle-root> --runtime <runtime-id> --owner <owner-id> --id <report-id>
   ```

   The exact payload is create-only at `handoff/<report-id>.json`. Its full
   immutable binding is in `active/<report-id>.json` under `attempt`; public
   output includes only the report/attempt hashes and fixed statuses. Before
   exposing the handoff the component durably records one attempt and an
   **uncertain** boundary. Only the invocation creating that boundary can return
   `may_attempt=true`. This is an opportunity for the already-authorized external
   owner/adapter, not permission to publish. Every retry returns false, including
   a crash before the handoff file or successful stdout. A missing/conflicting
   handoff never authorizes a resend. Reconcile readback instead.
5. The separately authorized external owner performs its one publication,
   independently reads the exact private destination, authenticates its own
   transport evidence and stages selected receipt/readback bytes in an owner-only
   inbox outside cycle state. Import publication evidence offline:

   ```text
   python -m automation.coordinator_cycles receipt
     --root <cycle-root> --runtime <runtime-id> --owner <owner-id> --id <report-id>
     --kind publication --owner-evidence-root <authenticated-owner-selected-inbox>
     --evidence-id <selected-receipt-id>
   ```

6. After the **named system recipient** actually ingests the exact payload, the
   external owner authenticates that recipient's evidence and stages a distinct
   recipient receipt. Invoke the same command with `--kind recipient` and its
   separately selected evidence ID. Publication readback alone never acknowledges
   a recipient. A recipient receipt alone never verifies publication. Neither
   establishes human reading, product acceptance, independent engineering review,
   deployment, identity approval or acquisition/download permission.
7. After both receipts, explicitly archive the report:

   ```text
   python -m automation.coordinator_cycles archive
     --root <cycle-root> --runtime <runtime-id> --owner <owner-id> --id <report-id>
   ```

   Archive replay is safe even when both archive and active copies remain from
   an interruption. Only after exact-byte verification, file/directory fsync and
   a durable state update are the replaced active and handoff copies reclaimed.
   Original source evidence remains inside the verified archive record. No
   archive history, legacy state or caller input is deleted.

The equivalent library functions are `cycle`, `handoff`, `import_receipt` and
`archive` in `automation.coordinator_cycles`. They return only the same safe
projection used by the CLI. Private durable files carry the report and evidence;
stdout is not a publication payload. Library validation/I/O failures raise
exceptions; the CLI catches the accepted fixed failure classes and returns exit
1 with `NEEDS_USER/invalid_or_unavailable_input`. Parser errors use exit 2 and the
same fixed projection. No exception text or input value is echoed. Success and
truthful backpressure use exit 0; the owner must inspect `backpressure` and
`status`, not just the exit code. CLI help contains only static argument names.

## Receipt contract and authentication boundary

Cycle receipts are version **1**, deliberately separate from engineering terminal
and private-receipt schemas. Each owner-selected `<evidence-id>.json` contains
exactly:

```json
{
  "version": 1,
  "kind": "publication",
  "owner": "synthetic-owner",
  "issuer": "synthetic-owner",
  "binding": {
    "runtime": "synthetic-runtime",
    "cycle": "synthetic-cycle",
    "report": "<64-lowercase-hex-report-id>",
    "destination": {
      "repository": "kolorifer/radarr-state",
      "path": "operations/synthetic-cycle.json"
    },
    "recipient": "original-supervisor",
    "payload_sha256": "<64-lowercase-hex-of-original-payload>",
    "attempt": "<64-lowercase-hex-attempt-id>"
  },
  "observed_at": 1800000100,
  "reference": "synthetic-owner-evidence-reference"
}
```

For `kind=recipient`, `issuer` must equal the bound named recipient. For
publication it must equal the accountable owner. The observation time must not
predate the cycle. The binding must match the recorded attempt exactly, including
the intended private repository/path and original payload hash. Publication also
requires `<evidence-id>.payload`, independently staged destination readback, to
match the original payload byte for byte. Successful-looking flags, source prose,
engineering receipts, arbitrary extra fields, mismatched attempts/destinations,
wrong issuers and missing readback are rejected. Identical original receipt bytes
replay idempotently; conflicting bytes are rejected without replacement.

**Authentication belongs to the external accountable owner/adapter.** Before
selecting this inbox and invoking the importer it must independently establish
the authenticated publication readback or named recipient ingestion. The inbox
is the explicit trust boundary; there is no CLI `trusted=true` or hash-pin shortcut.
A private directory, owner/issuer string, payload hash or receipt schema alone
cannot establish external origin. The importer checks structure, binding and byte
consistency; it cannot distinguish identical forged bytes supplied by a dishonest
or compromised owner. No signing credentials are created. Staging arbitrary bytes
in a directory does not turn them into authenticated evidence. Synthetic tests
use a fake external owner that assumes this role, and prove no real delivery.

## Durable state, immutable evidence and recovery

All new files live under the one explicitly owned root. `identity.json` fixes
component/schema version **2**, runtime and owner; `state.json` records full cycle
requests, durable outcomes, active/archive references, comparison baseline and
current observation identity. A cycle ID is an acquisition identity; a report ID
binds runtime/cycle and original payload bytes; an attempt ID additionally binds
destination and recipient. Numbered engineering task IDs are never used for
these identities. Engineering task references inside validated findings are only
evidence and cannot complete engineering stages through lifecycle receipts.

The state records acquisition intent before source reads. A single reserved
`staging/` slot holds `independent.json` (a checkpoint of selected original
independent bytes and metadata), the new `movie/` reader bundle, a separate
`combined/` validator input, and `collection.json`, installed last. Each cycle
ledger entry has `checkpoints.independent` and
`checkpoints.collection`, initially null. On capture, each checkpoint file is
written durably and its exact encoded-byte SHA256 is then committed to the cycle
ledger, before later collection/preparation proceeds. Reload validates these
anchors before using either checkpoint, including the independent checkpoint
when a complete collection exists. The complete collection also includes an
`evidence_binding` map and binds the request, report and actual original bytes.
Recovery uses a verified completed collection unchanged. If it is absent, the old
cycle is finalized as `interrupted` with unavailable movies and only durably
checkpointed independent findings. It never rereads sources, imports a newer
manifest or substitutes an earlier cycle's successful bundle. A different cycle
is blocked while an interrupted one awaits resolution; retry the recorded
identity first. A retained complete collection can finish preparation after an
active-file/state interruption without another acquisition.

A checkpoint missing its recorded bytes, with changed bytes, a mismatched anchor,
or with no durable anchor is rejected without checkpoint reclamation, rereading or
recomputing a trusted baseline. A crash between checkpoint-file installation and
ledger-anchor commit can leave such an unverified file: all bytes and acquisition
intent are preserved, the CLI returns the fixed failure outcome, and recovery
requires owner investigation. This deliberately fails closed instead of adopting
post-crash contents. A missing checkpoint with a null anchor means capture did
not commit; the existing interrupted-outcome rules still apply.

Reports and envelopes use schema version **2** and **comparison_version=2**.
Their exact payload string/hash never changes. Active envelopes add attempt/receipt evidence;
archives freeze the complete envelope. Envelopes encode original evidence using
base64 without reserialization of source bytes. This includes source JSON,
original optional manifest, original reader manifest/observations, and the new
combined manifest. The payload's `evidence_binding` maps every exact captured
name to
`{"sha256": "<actual-byte-hash>", "size": <actual-decoded-byte-count>}`. It is
computed at collection, bound by the collection checkpoint anchor, and included
in the immutable payload hash/report ID and hence the attempt/receipt bindings.
Record loading compares the complete captured set and actual decoded bytes to
that original payload binding before handoff, receipt promotion, replay cleanup,
archive or reclamation. Missing, changed, substituted or extra members (including
manifests) reject without replacing the binding or deleting recoverable records.
Changing the binding and payload hash cannot preserve the ledger's report ID.
Original optional manifest claims are evidence, not the actual-byte binding:
a correctly diagnosed `hash_mismatch` remains reportable, retains its original
manifest and actual invalid source bytes, and can archive/recover unchanged.
Absent source bytes are never fabricated. File identity/hash checks and source
validation remain those of the accepted reader. Raw bytes with invalid embedded
content can still be retained as truthful acquisition evidence; they do not become valid findings.

**Cycle-format compatibility:** Task 1 format-1 roots lack this immutable evidence
binding and checkpoint provenance. They are rejected with the existing fixed
`NEEDS_USER/invalid_or_unavailable_input` outcome (library validation failure),
before lock creation or cleanup. Preserve every old byte; there is no automatic
migration, retrofit, reconciliation or deletion. Select a new explicitly owned
format-2 root for new cycles. This version is specific to the new cycle component;
legacy `coordinator_outbox` v2 payloads, identities, receipts and recovery are
unchanged. Cycle receipt JSON remains version 1 with the same fields/API; its
payload/attempt hashes now naturally bind the format-2 report. Engineering
terminal receipts and external authentication requirements are unchanged.

`state.baseline` retains the comparison-v2 material fingerprint after archives
release active capacity. Availability/finding transitions produce exactly one
report. Changes only to source serialization, generation/observation clocks and
private diagnostic detail remain quiet under accepted semantics. `current.json`
keeps the latest independently dated observation/diagnostics, separate from the
immutable report; it does not claim those fresh bytes are the old report's
provenance. Quiet observation bytes have finished their staging purpose once
the durable current outcome is recorded. They are reclaimed without changing
previous report evidence. A report too large for the payload bound yields a
durable backpressure outcome and a fixed `observation_too_large` current summary.
The material baseline remains unchanged so a new cycle can try again.

After the durable cycle outcome, only the explicitly reserved slot's declared
files are reclaimed. Unknown files, links to other locations or unsafe ownership
stop cleanup and preserve state for diagnosis. Atomic-write temporaries are
bounded fixed names; accepted reader temporaries have their fixed generated
name syntax. Recovery removes only owned disposable temporaries, including the
recognized transient hardlink of an atomic create-only install. Sources are
copied through descriptors, never linked. Source bytes referenced by reports
are embedded durably in the active record before staging reclamation and in the
verified archive before active reclamation. Pending, uncertain, unacknowledged
or conflicting records are never evicted. Filesystem errors fail closed and may
retain a slot/capacity until the same identity can safely resume.

## Finite bounds and backpressure

| Resource | Bound and accounting |
| --- | --- |
| Cycle ledger | 4096 retained cycle identities; 4 MiB encoded state; no quiet-cycle directories |
| Active reports | 20 envelopes, 128 MiB total; admission reserves 64 KiB per record for attempt/receipt growth |
| Archives | 256 complete envelopes, 256 MiB total, including all retained source bytes and receipts |
| Report payload | 512 KiB exact UTF-8 JSON |
| Original evidence per record | 8 MiB decoded bytes, including duplicate reader/combined references and original manifests |
| Envelope/collection | 12 MiB encoded, with a 64 KiB receipt reserve at preparation |
| Newly owned staging | One slot, at most 32 declared files and 64 MiB; fixed reader limits and explicit original-byte copy limits bound writes before final validation |
| Handoff | At most one 512 KiB payload per active report (10 MiB total), retained through ambiguity |
| Current observation | One 512 KiB file; oversize observation is replaced by a fixed bounded summary |
| Receipt input | 16 KiB per original receipt; publication readback 512 KiB |
| Atomic temporary overhead | One bounded `.write` per active operation under the lock, at most 12 MiB; accepted reader temporaries remain within the staging bound |

Active/archive counts include referenced source evidence inside their envelopes;
there are no external uncounted source bundles. The global cap is finite, including
ledger, current, handoff, staging and temporary overhead. Backpressure does not
silently prune history or raise the old outbox cap. No age-based deletion exists.
Archive exhaustion preserves complete active records; pending active exhaustion
stops acquisition before reading sources. Cycle ledger exhaustion also stops
before acquisition. Byte/payload exhaustion discovered during collection records
a durable backpressure outcome, retains the old comparison baseline and reclaims
only disposable collection data with no report references. Resolving capacity
policy needs a later owner decision; this task chooses no migration or history
removal. The external owner's inbox/transport storage is caller-owned and must
be bounded by that later adapter, not deleted by this component.

## Synthetic rehearsal and later activation gates

Run from the checkout with an available runtime and no private data:

```sh
python3 -m unittest test_coordinator_cycles -v
python3 -m unittest test_coordinator_cycles.CycleTests.test_cli_all_lifecycle_commands_with_fake_owner_adapter test_coordinator_cycles.CycleTests.test_more_than_twenty_archives_baseline_survives_restart -v
```

The fixture uses the actual report writer, actual accepted reader, engineering
snapshot validator and parent-export validator in temporary owner-only roots.
It stages fake authenticated-owner evidence, verifies exact publication bytes,
imports separate recipient ingestion, archives 25 successive material reports,
and verifies quiet refresh/restart with the archived comparison baseline. Other
tests inject interrupted checkpoints, I/O/capacity/conflict failures and validate
legacy bytes/recovery. No external owner, private destination or recipient was
contacted. Fresh exact-head Python 3.12/3.13 CI and independent review remain gates.

After accepted code, the supervisor must scope a bounded integration task for
this NEW component: inspect the existing Mac owner/runtime/launcher and source
producer timing; define exact authorized roots, transport, private destinations,
recipient identity and authenticated evidence selection; verify one real cycle,
actual destination readback and actual named-recipient ingestion; then consider
recurrence and its capacity handling. Invoking the combined investigation scan
service can also run provider research: it is **not a read-only refresh**. No
request budget policy is selected here. Before claiming recurrence, observe an
actual scheduled wakeup through preparation, publication and recipient receipt.
Do not add a speculative dispatcher hook: its loop holds the engineering execution
lock across workers and its private state is issue-specific. Preserve all eight
consumed executions and issue #113's retained/uncertain artifacts. The precise
historical Task 8 source rejection remains unknown.
