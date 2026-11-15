# Reviewed assessment on the original Telegram card

## Concrete source and operation boundary

The selected deployed actor revision is `06d17aafefb5a5161364e4bf6f63667a649e1aa3`.
Public Git blobs for retry_telegram.py, identity_retry.py and
identity_outcome_outbox.py exactly match main's independently observed deployed
hashes and the current repository. The whole movie_intel_service.py differs from
HEAD; its edit_retry_message, _telegram_request, _reply_markup and public_action_url
ASTs match. No whole-HEAD actor deployment or restart is needed or authorized here.

The existing retry pump reads a waiting row then edits outside its transaction.
An `edited` row alone does not prove absence of another process holding a stale
selection. Main must verify one serial retry pump and no other edit writer at the
exact deployed revision, and supply that bounded, expiring attestation for each
operation. This helper cannot discover or authenticate process topology.

Only one original receipt is supported in this bounded first version. It must
already have an `edited` callback-return record, a terminal done/review job, no
current lease, no supersession and no matching receipt spool. The normalized
original retry-job observation and saved payload must independently produce the
same external-ID release key/version and exact `outcome-` case ID. Title matching
is never used. Another version referencing the same chat/message refuses.

A separate durable table reserves that message and case before any Telegram call,
then moves the original row out of the old pump's waiting selection. The existing
SQLite write transaction is held across the single existing sender
call under an armed 15-second SIGALRM deadline to serialize newer outcomes, old pump selection and cleanup. Receipt lifetime
must cover the entire main-selected operation window. SIGALRM bounds normal interruptible Python/socket work; delayed signal handling,
uninterruptible kernel calls, cleanup or commit can exceed that interval. Holding
the writer transaction can defer the actor (its SQLite timeout is 0.1 seconds) and
its bounded admission queue. Main uses a supervised one-shot and retains uncertain
state on interruption; this is not an absolute wall-clock guarantee.
The reservation table is not
subject to the old eight-day message cleanup. An exception or interrupted commit
is uncertain and never automatically resent. A later identical call only returns
its retained status. This does not authorize another sender process or recover an
ambiguous old edit.

## Reviewed content and actions

Main's actual full operator review and receipt-correlated retained report bind a
private deterministic plan. A supported result says “Reviewed assessment supports
a candidate”, uses the report/catalogue candidate title/year/IMDb and includes
main's concise reviewed discrepancy, evidence and uncertainty. The exact tracker
starting link is read from the hash-bound local report context, never guessed or
provided separately; query/fragment-bearing links refuse rather than disclose
possible capabilities. Unresolved results
do not invent a candidate. All cards explicitly retain production matching and
no-download boundaries. Text is plain, bounded to 900 UTF-16 units, and hashed.
No poster, identity memory, acquisition, Radarr or model operation occurs.

This helper deliberately clears the old inline keyboard rather than reusing an
unverified or stale acquisition/review action. Review continues in the main chat.
It creates no action token and grants no download approval. A sender return means
its existing acknowledgement handling completed; it is not human ingestion.

## Main-only API

- `prepare(operator, reservation, summary)` requires an existing full reviewed
  stage and exact receipt-backed completion. Summary has discrepancy, evidence,
  uncertainty; these are authored/verified by main, not model-controlled commands.
- `inspect_target(store, version, sources)` returns the exact read-only original
  row/ref/source binding for main to verify and pin.
- `deliver(store, plan, target_pin, sources, boundary, edit)` accepts the existing
  approved sender's `edit_retry_message` function in memory. Main supplies exact
  plan acceptance and a fresh verified actor boundary. The helper does not read
  bot configuration, import/start the actor, or place secrets in files/argv.
- `record_delivery(operator, reservation, receipt)` records main's independently
  read-back acknowledgement separately from the existing chat delivery stage.

The helper runs locally with the reviewed operator for plan preparation and as a
bounded main-approved one-shot beside the existing actor modules for delivery.
Its remote delivery path needs no v13 package or provider runtime. Main retains
all private artifacts and performs real invocation only after exact review/CI.

No scheduler, worker, service restart, source/model/provider call, secret read or
live notification was performed by the coordinator. The existing hourly main
heartbeat can call this same API for later genuinely reviewed results. Waiting,
failed, multi-reference or unverified targets remain precise operator-needed
outcomes, not reasons to send a new message or bypass the guard.

## Issuance template and verification

`automation/reviewed_telegram_UNISSUED.py` is the reviewed isolated `-I -S -B`
one-shot entry. Its `ISSUED` stays None in the repository. Main supplies exact
actor-root/eight-file hashes (six inert modules plus movie_intel_service.py and
deploy/run.py), the helper pin, private plan/target/sources/boundary pins, selected
existing bot-config pin, existing retry-store path, new private receipt-output
path, interpreter hash and main-acceptance path. Main then inspects the issued
wrapper and writes the exact accepted wrapper/pins artifact. The sole invocation
argument is `--main-accepted-reviewed-telegram`; credentials never enter argv.

The wrapper executes only the selected sender functions, not the actor module or
service entrypoint. It reuses the deployed literal environment parser on guarded
in-memory config bytes; the two Telegram values remain function globals and are
never exported to os.environ. An existing Outbox transaction is bound without its
initializer or RetryStore migrations. No retry thread starts. The sender receives
only token=None and cannot create/read/reuse actions. Errors print one fixed safe
status rather than exception/URL/credential text. The private receipt is written
once and the console contains only status plus its hash.

The source-binding reader restores only the omitted `implementation` transport
label from the exact stored retry-job observation after all other normalized
release inputs match. This is a documented old receipt-serializer omission, not
new source evidence. Terminal jobs may retain a finite expired `until` timestamp;
no active lease or current/future expiry is accepted. Main must also establish no
producer can republish a binding for this acknowledged original reference during
the interval: the SQLite lock cannot serialize the independent filesystem spool.
All existing pending refs across versions are scanned before and after reservation.

Initial validation: 13 invented helper tests passed on Python 3.12 (0.693s).
The 66-test relevant suite passed 65 tests; its sole local loopback-server test was
blocked by restricted socket access, then passed separately with that local test
socket allowed (0.533s). The issued-wrapper fake-HTTP test subsequently passed in
the 14-test new suite (1.275s), with native/network tripwires, no actor startup and
no environment mutation or secret output. Final exact-head review/CI remain gates.

The selected parser's live mode was reported group-writable by main. No chmod or
live-file execution is proposed. Main instead selects owner-private frozen public
blobs from the exact deployed revision as actor_root and independently verifies the
live actor boundary. The prepared eight-file bundle is byte-exact to 06d17aaf;
the full issued-template fake-HTTP test also passes with that actual frozen bundle,
not only repository-HEAD fixtures. The main-owned actor process remains untouched.
