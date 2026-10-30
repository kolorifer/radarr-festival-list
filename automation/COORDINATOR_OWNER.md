# Owner commissioning adapter — issue #119 Task 2

`automation.coordinator_owner` is a finite offline adapter over the accepted
format-2 reader/cycle/handoff/receipt/archive API. This runbook grants no operations
authority. There is no transport, publisher, authentication implementation,
scheduler, executor, credential discovery or import side effect. Synthetic tests
establish code behavior only.

## Exact caller configuration

Every command takes the **same complete caller-selected arguments**. No JSON
configuration loader, environment authority or default observation clock exists.
Staged JSON is evidence, never execution authorization.

```text
python -m automation.coordinator_owner <command>
  --base <new-absolute-owner-base>
  --runtime <stable-runtime-id> --owner <accountable-owner-id>
  --cycle-id <stable-acquisition-id> --now <original-unix-observation-clock>
  --intake-root <base/new-intake-name>
  --cycle-root <base/new-shared-format2-name>
  --evidence-root <base/new-independent-evidence-name>
  --receipt-root <base/new-receipt-inbox-name>
  --parent-output <separate-existing-parent-staging-directory/new-payload.json>
  --selector <exact-externally-approved-source-selector-id>
  --source-path <explicit-canonical-remote-export-root>
  --destination-repository kolorifer/radarr-state
  --destination-path operations/<exact-new-private-destination>.json
  --expected absent --recipient <named-original-supervisor-system>
  [--evidence-manifest-sha256 <caller-approved-original-manifest-sha256>]
```

IDs use the accepted 1–80 ASCII identifier syntax; owner and recipient differ.
Local paths must be absolute, normalized, single-`/` paths. The base and its four
distinct direct-child root names use lowercase ASCII letters/digits/hyphens,
begin with a letter, and have at most 64 characters. This restricts prospective
names so case or Unicode normalization cannot alias two absent roots. Existing
ancestors must have their exact directory-entry spelling, even on permissive
filesystems. Parent output has a lowercase ASCII `.json` basename and an existing,
separately selected private parent outside the entire base and checkout. This can
be the existing parent's exact artifact output directory; it is never created.

Base parent/output parent must belong to the current UID with no group/other
permissions. Ancestors open without following symlinks. Directory identity and
ancestor checks prove existing roots disjoint from checkout and one another
before writes; intent binds their device/inode identities. The source-path
selector is checked syntactically and against lexical base overlap, **never
opened locally or remotely**. A later transport must independently prove the
remote canonical spelling, endpoint/key selection and no-follow identity. A
selector string proves none of those facts. Stable directories and an honest
external owner are required; this is not hostile-same-account process isolation.

## Finite invocation sequence

1. `reserve` creates only the selected new base, marker/lock, per-acquisition
   intake/evidence/receipt directories, intake's `incoming/`, and accepted cycle
   store. Its immutable create-only intent binds request, directory identities
   and content hash; fsync precedes `acquisition_grant=true`. Only that first
   successful return gives the separately authorized external transport one
   acquisition opportunity. Lost stdout burns it. Exact replay returns the same
   hash with `acquisition_grant=false`. Changed requests, replaced roots,
   interrupted/unanchored initialization and exhausted capacity fail closed.
2. The **external authorized transport** stages only original bytes of
   `incoming/snapshot.json` and `review-report.json` in the intake, as private
   regular files. Do not refresh/research, substitute an old bundle, change clocks
   or retry an uncertain transport. Missing/invalid/stale exports remain honest
   outcomes. Optional independent evidence requires the separately caller-approved
   manifest SHA256 reserved above, with original `manifest.json`,
   `engineering.json` and/or `parent_status.json`; all other manifest source paths
   must be null. These are selected exports, never live parent-journal roots.
3. `seal` declares acquisition complete and binds the actual fixed-file set,
   sizes and SHA256. Private no-follow descriptor reads check pre/post inode,
   owner, mode, size, link count and nanosecond timestamps, plus final directory
   entry identity. Extra paths reject; missing files are bound as missing.
   Identical seal replay succeeds; changed bytes reject. A seal authenticates no
   transport origin and never rewrites source JSON or embedded clocks.
4. `prepare` verifies the seal, calls accepted `cycle` with the **original**
   request clock/roots, and verifies the seal again. Actual accepted validators
   preserve full case sets, proposal/evidence versions, source revisions,
   original times and issue-qualified independent findings. Valid movies remain
   `partial/incomplete_upstream`; quality remains
   `unavailable/passive_export_missing`. Unavailable movies cannot erase valid
   engineering/parent evidence. Accepted material comparison preserves quiet polls.
5. For `status=prepared`, `handoff` calls accepted handoff once. Accepted state
   records **uncertain before exposure**. Only `may_attempt=true` stages one
   create-only exact payload at the reserved parent-output path; hash/bytes match
   accepted handoff and size is at most 512 KiB. Any preexisting output (even
   identical) rejects. `may_attempt=false` never restages/resends. Crash after
   uncertain but before output gives no second attempt. The future existing parent
   alone performs its separately authorized ONE exact PRIVATE_ARTIFACT write and
   destination readback **after child exit**. This adapter cannot generate that
   parent's subsequent terminal receipt or invoke its publisher.
6. `inspect` validates and projects existing state read-only. It never imports
   staged receipts, acknowledges a recipient or creates state files.
7. After independently authenticating actual destination readback, the external
   owner selects `publication.json` plus `publication.payload` in the receipt root
   and invokes `receipt --kind publication --evidence-id publication` with all
   common arguments. After **distinct genuine original-supervisor system ingestion**,
   independently authenticate/select `recipient.json` and invoke
   `receipt --kind recipient --evidence-id recipient`. Explicit invocation is the
   unchanged external-owner selection boundary, not origin authentication.
   There is no automatic selection, receipt generator, `trusted=true`, signing
   shortcut or origin proof from JSON, hash, READY, private directory or sender
   readback. The unchanged cycle-v1 importer checks issuer, full binding/attempt,
   destination, content hash, timestamp, reference, exact retained receipt and
   publication readback bytes. Conflicting bytes never replace history.
8. `archive` calls accepted archive only after both receipts, preserving original
   evidence and fsync/verifying before active/internal-handoff reclamation.
   Restart/replay is idempotent. Owner intake, seals, inbox and external parent
   output remain retained. Accepted lifecycle staging cleanup is unchanged.

For a later explicitly authorized finite call, reuse base/runtime/owner/cycle-root
and supply a new acquisition ID, intake/evidence/receipt names, output/destination
and original clock. The shared accepted baseline keeps unchanged observations
quiet. This supports a future owner callback, not an indefinite retention policy,
installed runtime or recurring engineering task.

## Capacity and failure codes

| Resource | Bound |
| --- | --- |
| Intent ledger | 20 retained acquisitions, 16 KiB each, 512 KiB aggregate; no reset/eviction |
| Base entries | At most 163; only marker/lock and intent-declared roots/seals; unknown entries/debris reject without deletion |
| Intake per acquisition | Two fixed private files, each 2 MiB, and private `incoming/` |
| Independent evidence | Three fixed files, each 2 MiB; 6 MiB aggregate, caller-pinned manifest |
| Receipt inbox | Two 16 KiB receipts plus 512 KiB readback; 544 KiB aggregate |
| Parent output | One create-only 512 KiB payload per prepared acquisition, at most 20 |
| Seal | One fixed-file metadata manifest per intent, read capped at 16 KiB |
| Accepted cycle store | Unchanged: 4096-cycle/4 MiB ledger, 20 active/128 MiB, 256 archives/256 MiB, 64 MiB staging and existing remaining limits |

All 20 intake/evidence/inbox sets count after archive or quiet completion. Before
another acquisition grant, check outstanding collection, cycle ledger and active
capacity, conservatively reserving one maximum record. External input beyond
bounds rejects and remains retained. An honest owner must enforce staging grants;
the adapter cannot prevent external writes between invocations. Exhaustion needs
a later retention decision, not automatic rotation, history loss, age eviction,
capacity reset or legacy-outbox migration.

CLI failures use exit 1 with fixed `NEEDS_USER` reasons, parser failures accepted
exit 2. No paths/content/exception text are emitted. Library failures raise.

| Codes | Meaning |
| --- | --- |
| `owner_path`, `owner_path_spelling`, `owner_output_path`, `owner_overlap` | Noncanonical/ambiguous/overlapping roots |
| `owner_distinct_recipient`, `owner_create_only`, `owner_request`, `owner_request_bound` | Invalid explicit caller configuration |
| `owner_missing`, `owner_identity`, `owner_cycle_identity`, `owner_cycle_request` | Missing/unowned store or mismatched cycle |
| `owner_busy`, `owner_backpressure` | Concurrent invocation or finite count/byte/collection capacity |
| `owner_unanchored`, `owner_intent_binding`, `owner_intent_conflict`, `owner_root_changed`, `owner_root_exists` | Unanchored/corrupt state, changed request, replaced/reused roots |
| `owner_intake_entries`, `owner_manifest_selection`, `owner_manifest_paths`, `owner_input_changed`, `owner_intake_changed` | Unexpected/unselected files, unstable reads or changed sealed bytes |
| `owner_not_prepared`, `owner_output_exists`, `owner_publication_uncertain`, `owner_handoff_binding` | No new handoff opportunity or conflicting exact output |
| `owner_receipt_selection` | Missing/mismatched explicit receipt selection |
| `invalid_or_unavailable_input` | Accepted validation/filesystem failure, with no inferred host/root cause |

## Compatibility and remaining live boundaries

Cycle format 2, cycle receipt v1, legacy outbox v2 and dispatcher/policy/terminal
schemas remain unchanged. Preserve all eight consumed issue #113 executions,
uncertain outboxes and retained roots; #86/PR #110 and unrelated `CODEX_TASK.md`
stay separate. No Task 1 private selections appear in public code/fixtures.

Task 1 acceptance proves a bounded diagnosis, not acquired exports, freshness,
publication, recipient ingestion or activation. The real source's symlinked home
must later be replaced by an **explicit owner-authorized canonical no-follow
path**, never auto-resolved or substituted by changed case. The observed producer
scan/handoff discrepancy needs a later exact read-only/reconfiguration decision;
the combined scan can run research and is not a read-only refresh. The historical
source rejection remains undiagnosed. Proposed persistent roots must later be
newly created under a proven private parent and independently verified; none was
created here.

Still external: selected SSH/key/endpoint and canonical source remediation;
real fresh source transport; passive quality exports; independent export
production; cycle-specific authenticated publication/readback contract; genuine
original-supervisor ingestion and authenticated receipt selection; first real
cycle/archive; retention policy, deployment and scheduling. The first pilot uses
the existing parent's exact artifact capability after child exit. Recurring
network publication and origin authentication require an explicit observed owner
contract before implementation. The installed Mac launcher discovers engineering
work; it is not a report schedule. Later daily cycles must not consume numbered
Codex tasks. Verify one genuine cycle through readback, distinct acknowledgement
and archive before recurrence, then observe an actual scheduled invocation.

Synthetic rehearsal (no credentials, remote hosts or private inputs):

```sh
python3 -m unittest test_coordinator_owner -v
python3 -m unittest test_coordinator_owner.OwnerTests.test_actual_cli_rehearsal_all_steps_fake_publisher_distinct_recipient -v
```

The actual CLI test reserves, supplies fixed synthetic bytes, seals, prepares,
inspects, hands off to a fake publisher, imports separately selected fake
publication/recipient receipts, archives and restarts. It proves no operational
publication, authenticated origin or real source freshness. Parent-published
exact-head Python 3.12/3.13 full CI, independent review and scoped merge remain
mandatory after worker completion.
