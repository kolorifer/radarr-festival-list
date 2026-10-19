# Stage 1 private identity observation

Stage 1 is observational only. It cannot resolve a case, issue an approval, send a
notification, fetch a provider, or acquire a release. All cases remain unresolved;
even a recorded `verified_tmdb` outcome is a report of existing behavior, not an
accepted triage decision. Stage 2 requires separate review.

## Isolation and deployment gate

Issue #49 replaces the failed user-namespace approach with Linux x86-64 Landlock
ABI6 plus the provider's effective systemd syscall filter. No root/provider changes,
helper daemon, hand-written seccomp program or new dependency. The separate socket
unit binds only `127.0.0.1:40715`; the collector inherits that listening FD3. The
service cannot create sockets or connect, including UDP and pathname Unix sockets.

`identity_triage_sandbox.confine` runs before reading configuration, creating the
store or serving requests. It verifies the fixed private layout, clean stdio and
listener, closes every descriptor above3, sets no_new_privs and installs a
deny-by-default policy. Reads are limited to collector code/config, the exact
system Python standard library and architecture library directory; writes only to
collector state (regular files, WAL/SHM, truncate/remove). No execute, cross-tree
rename, device/socket creation, `/proc` or unrelated home access is granted.
ABI6 also scopes signals and abstract Unix IPC; new TCP bind/connect is denied.

Landlock does not cover chmod/chown/xattr/time changes or all socket operations.
The unit explicitly denies those metadata syscalls, socket/socketpair/connect,
ptrace/process_vm/pidfd_getfd and io_uring, with native ABI and no_new_privs.
Startup actively requires protected-directory, `/proc`, new-socket and same-mode
chmod denials. A missing kernel right, path, listener or effective complementary
filter fails startup. A plain Python invocation cannot start an unconfined receiver.
Do not remove probes or broaden roots to make it start. Linux/Python layout changes
require revalidation. Landlock does not hide stat metadata and this is not isolation
from a malicious host administrator or other unconstrained same-user process.

The actual user-service child passed read/write/list, symlink, inherited-FD,
process `/proc`, signal and socket denials on the provider, while SQLite and inbound
HTTP worked. Kernel-refusal and changed-root failures produced no success ACK and
no DB changes. Repeat these gates for the installed revision before routing.
See [issue #49 report](../docs/reports/2026-10-18-landlock-shadow.md).

## Schema and limits

`identity_triage_intake.py` accepts autobrr v1.88 `version: 1.0`, `release.new`
envelopes with UUID, timezone timestamp, movie release and configured identifier /
display-name pair. Protocol is torrent, implementation IRC or RSS. IMDb/TMDb IDs
are optional but, if supplied, must be valid. Missing/invalid movie metadata goes
to quarantine. Non-movie/unsupported/source-spoof requests are rejected. A malformed
JSON body cannot establish movie provenance and is counted as rejected.

Projection retains title/year, release name, source, public film-ID assertions,
opaque release fingerprint, timestamp/event UUID, and fixed outcome/reason codes.
It never selects or persists download/magnet/info URLs, headers, raw rejections,
approval tokens, arbitrary markup or acquisition capabilities. Known URL/credential
syntax, controls, markup and long opaque strings in text are quarantined. Ordinary
punctuation is retained as data, never interpreted as HTML/instructions.

Schema v1 tables: `deliveries`, `releases`, `evidence`, `cases`, `outcomes`, `seeds`,
`conflicts`, `counters`. Migrations use one immediate transaction; unknown versions
fail. WAL + FULL synchronous commit precedes success. SQLite busy timeout is 250ms;
write/capacity/permission failure returns fixed 503, never success. Directory0700,
DB/WAL/SHM/journal/backup0600, owner/regular-file/link checks before and after access.
Do not loosen permissions to recover a failure.

Delivery keys are channel + UUID. Repeating a UUID with equivalent projected data
is a duplicate. A changed payload under the same UUID is a quarantined conflict
(409); the original stays intact. A new UUID with unchanged release metadata records
a delivery without a new evidence version/case. A stable source torrent ID is
hashed with source/protocol; absent IDs use a weaker release-name fallback. Changed
metadata creates another evidence version and association, without overwriting old
evidence. An out-of-order older observation reuses its earlier evidence version.

Grouping hashes normalized title/year plus the exact pair of asserted movie IDs.
All groups are provisional, with random opaque case IDs. Different or missing IDs
remain separate groups; this deliberately allows fragmentation instead of silently
joining conflicting identities. The same release fingerprint still links their
evidence versions. No semantic film deduplication is claimed.

HTTP bounds: loopback only, 64KiB body, 3s socket idle timeout, 5s hard connection lifetime, 8 concurrent requests,
queue8, fixed responses, no request-path/body logs, separate route keys, constant-time
comparison. Capacity is 1,000,000 delivery rows and 1,000,000 conflict rows; there is
no automatic pruning. Disk capacity must be monitored. Retained reconciliation is
at most 500 rows per explicit invocation, with an explicit ID cursor. No background
provider/reconciliation worker or durable publisher outbox exists.

## Configuration and staged installation

Generate two different random URL-safe secrets directly into a private JSON file
(never print them). No existing credentials or sessions need to be rotated.
Collector config `~/.config/movie-identity-triage/config.json`, owner0600:

```json
{
  "version": 1,
  "enabled": false,
  "port": 40715,
  "sources": {"example": "Example"},
  "release_key": "REPLACE_WITH_PRIVATE_RANDOM_RELEASE_ONLY_SECRET",
  "outcome_key": "REPLACE_WITH_DIFFERENT_PRIVATE_OUTCOME_ONLY_SECRET"
}
```

Use actual inspected source identifiers/names; examples are synthetic. The config
is reread for each request, so disabled immediately returns503 without ingesting.
Do not point either new route at movie-intel's Telegram-forwarding webhook.

1. Verify clean production revision, installed autobrr binary/version/source and
   original notification events. Save private configuration/state backups; never
   restore a stale action snapshot. Run full tests, both CI Python versions,
   dependency/scoring/leak checks. Review and pin the exact code revision.
2. Create mode700 collector code/config/state directories. Copy only
   `identity_triage_service.py`, `identity_triage_intake.py`,
   `identity_triage_store.py`, `identity_triage_sandbox.py`, `identity_selection.py` to `~/.local/lib/movie-identity-triage`. Use stdlib
   `/usr/bin/python3`3.12/3.13; no movie-intel env/venv/config inheritance. Record
   source SHA and file hashes privately. Install both `identity-triage.service` and
   `identity-triage.socket` after confirming the boundary works. Verify the child
   cannot open movie-intel credentials, approval/cache/backups, `.apps`, `.ssh` or
   the production checkout. Verify `/proc/<pid>/environ` has only the explicit safe
   environment. The application also refuses readable protected directories or
   inherited acquisition/provider variables. Enable/start the socket unit, not an
   unrestricted alternate launcher. No mount-namespace claim is made.
3. Before routing, enable config and run `--check-config` **inside that exact
   service sandbox** (temporary service ExecStart suffix), restore normal ExecStart,
   then start and verify authenticated `/health` and `/metrics`.
   An unsandboxed shell preflight is expected to fail. Do not substitute a passing
   synthetic HTTP test for this check. The collector imports no sender/acquisition
   modules and opens no outbound connections.
4. Through an existing authorized autobrr administration session, add one new
   WEBHOOK notifier, POST `http://127.0.0.1:40715/v1/release`, event **RELEASE_NEW
   only**, header `X-Identity-Intake-Key=<private release key>`. Preserve every
   existing notifier/filter field. Do not use a notification Test button: autobrr's
   test event is unsupported. Verify the route by configuration readback, passive
   delivery and authenticated health. Do not create/rotate an autobrr API key or
   restart its service without resolving the access prerequisite.
5. Optional current-outcome observer: a separate owner0600 file containing only
   `port`, `key` (outcome key), `sources`. Set
   `MOVIE_INTEL_TRIAGE_OBSERVER_ENABLED=1` and
   `MOVIE_INTEL_TRIAGE_OBSERVER_CONFIG=<private absolute file>` in movie-intel only
   after safe code deployment and preflight. Absent flag is off. Deploy/restart
   movie-intel using the existing runbook, preserving both reviewed bindings.
   The hook runs after context creation, before normal action handling. A daemon
   queue holds at most32 sanitized observations; loopback transport timeout0.5s,
   no redirects/proxies/retries. Disabled/missing config/full queue/service outage
   never changes resolver/Telegram/action behavior; a fixed warning reports lost
   observer delivery. Queue loss on crash is a documented gap, not a durable outbox.
6. Stage passive monitoring. Check old and new services, flags, permissions,
   `/metrics`, private journal summaries, no credential logging, and no collector
   access to action state. Do not replay a live action webhook or test an approval,
   Telegram message, Radarr call or download. Report whether any real release.new
   was received; zero is a valid but incomplete observation result.

## Coverage, seed and reconciliation

Metrics distinguish `release_new`, `outcome`, `retained`, `seed`. Accepted/quarantined
counts describe unique deliveries; duplicates count repeat attempts. Rejected counts
are attempts, so repeating excluded TV records increases rejected counts. Live
last-good time/lag are updated only by successfully stored release_new movie
observations, never by seeds/reconciliation. Minute logs contain bounded aggregate
metrics only. `/health` and `/metrics` require the release route key. Storage failure
counts are explicitly process-local because failed disks cannot persist them.

`coverage=incomplete` is permanent in Stage1. `no_delivery_observed` and
`stale_or_quiet` (15min without a stored live movie) are warnings, not proof of source
failure. A stopped collector has no endpoint; systemd failure, autobrr's failed HTTP
send and observer's fixed `unavailable_delivery_lost` warn the operator. There is no
external alert sender. Configure/check provider service monitoring separately before
activation; a source quiet period and missing upstream events cannot be distinguished.

Autobrr v1.88 publishes release.new before filters, generates a new webhook UUID,
and sends one HTTP request without durable retry. Its DB may contain only releases
that matched a filter with an action. It is not an announcement archive. Receiver
commit durability cannot repair an outage at the publisher.

`identity_triage_admin.py --config <private> --state <private> metrics` prints only
aggregates. Maintenance is an explicit operator command outside the collector
sandbox; do not grant the long-lived collector access to autobrr DB or private
research evidence. `reconcile <readonly-autobrr-db> --after-id N --limit 100` selects
only ID/type/torrent-ID/title/year/name/time/indexer/protocol/implementation. No URLs,
actions or credentials. It uses `mode=ro`. Re-run a retained row to deduplicate;
changed projected metadata generates a new retained-event UUID/evidence version.
Never call this an exhaustive backfill. Record the cursor and scanned count privately.

`seed <private-bundle>` accepts exactly four validated release envelopes, with
`data.seed={"provenance":"<SHA256 of private evidence>","contradictions":[<fixed codes>]}`.
Only approved private evidence may supply these rows: Fragmentos, Steve Howe,
Syd Barrett, Rainbow. Public film IDs are source assertions, never guessed mappings.
No speculative candidate TMDb IDs. The fixed reason set includes missing_crosswalk,
year/title/runtime/director_conflict and insufficient_evidence. Validate all four
before first write; missing/unsafe records fail with no invented replacements.
Report any missing case individually. Importing each row is transactional; if a crash
interrupts the bundle, replay it idempotently to complete. All four remain unresolved.

## Backup, recovery and rollback

`... identity_triage_admin.py --config <private> --state <private> backup <new-private-path>`
uses SQLite's consistent read-only source backup, validates quick_check, fsyncs and
checks0600. Destination parent must be0700. It refuses overwrite, so rotation means a
new filename followed by checks; manage retention explicitly. Do not copy a live DB
without WAL or assume a partial file is a valid backup.

For crash recovery, reopen the store and run metrics/integrity checks. SQLite rolls
back precommit writes; a lost postcommit acknowledgement is safe on redelivery.
Autobrr does not automatically redeliver, so do not claim crash recovery restores
missing source events. Only synthetic test fixtures may be replayed deliberately;
use a separate temporary state directory and `python -m unittest -v test_identity_triage`
for recovery/HTTP tests. Never replay production notifications into movie-intel.

Disable: first disable/remove only the dedicated RELEASE_NEW route through normal
administration, set collector `enabled=false`, disable the observer flag, stop the
socket and service (`systemctl --user disable --now identity-triage.socket` followed
by `systemctl --user stop identity-triage.service`). Stopping the service alone lets
the socket reactivate it. Preserve the original notifier snapshot for comparison. Roll back the
movie-intel code/observer config with its existing stop/checkout/start procedure;
retain current action state and reviewed bindings. Keep the observational DB private.
Schema v1 has no downgrade; restore a triage backup only with collector stopped and
only into triage state, acknowledging observation loss after the snapshot. Never
restore an action/cache backup as part of triage rollback. Recheck old service health.


## Passive eligibility bridge (issue 53)

Install `identity_selection.py` alongside the four collector modules. Its tables
are additive; v1 evidence, deliveries, seeds and constraints stay intact. Disable
or roll back code without restoring an old action store or deleting observations.
The original four seeds retain their separate reviewed history.

The optional movie-intel observer uses the existing collector outcome key in its
private three-field configuration (`port`, `key`, `sources`). The actor owns a
700/600 retry spool at `~/.local/state/movie-identity-outcomes`. No collector or
researcher access to that directory is granted. Committed messages retry with the
same UUID until acknowledged. The 32-item asynchronous pre-persistence queue may
lose events on crash or saturation; process counters and fixed-code journal
messages expose known failures, but cannot reconstruct an unknown crash window.
The publisher still has no durable outbox. Never claim complete intake.

`/metrics` reports observed source releases, releases without outcomes, assessed
release cases, explicit routes, correlation strengths, material versions and
legacy rows without chronology. These are release cases, not canonical distinct
movies. Strong source-ID matching is required for automatic eligibility; name
fallback and unmatched outcomes are withheld. Provider failures go to retry later;
conflicts to review only; invalid data to quarantine. No research is executed.

Authenticated `GET /v1/eligible` uses the existing **outcome** key and returns at
most ten current Stage 2-compatible manifests. This private export is the pending
research queue. Future research still needs an explicitly approved budget/run and
controlled manifest transfer; the worker never reads the collector database or
holds its key. Export pagination/large backlog draining is not implemented.

Before activation, back up private observer/environment configuration and collector
code; snapshot only triage state for migration verification. Keep research disabled,
its token empty and its finite ledger closed. Check exact notifier configuration,
collector socket/system-call policy, effective startup denials, local/public actor
health, original reviewed bindings and researcher installed hashes. Disable the
observer environment flag and restart only movie-intel to stop outcome production;
its committed spool remains private for a later approved resume. Old collector
code can ignore additive selection tables. Do not restore stale acquisition state.

## Selected-action intake (issue60)

`POST /v1/selected` uses the existing limited release key and accepts only autobrr
v1.88 `action.approved/rejected/error` with corresponding `PUSH_APPROVED/REJECTED/ERROR`
status, positive filter ID, known action type and bounded action-name/client fields.
Names/client labels are hashed into an opaque action identity; filter numeric ID,
action type and fixed outcome codes are stored separately from movie metadata.
URLs, raw rejection/error text, credentials and full payloads are never retained.
`unknown_movie` is a fixed classifier of rejected results, not a verified identity.

Set optional collector `source_mode: "selected_only"` only after verification;
`/v1/release` then returns410 without storing announcements. Omission/default
`announcements` keeps the old route for staged comparison/rollback. `/v1/outcome`
and its separate credential/export remain unchanged. Change only the dedicated
Identity shadow intake notifier to the three PUSH events and `/v1/selected`.
Do not repoint the actor rejection webhook or restore duplicate Telegram events.

An additive `selected_observations` table/index leaves schema-v1 history intact.
UUID redeliveries remain duplicates; equivalent action observations with new UUIDs
are separately counted as duplicate observations. Filter/action/outcome changes
add observations on the same source release/evidence, not new movie identities.
Autobrr omits numeric action/status IDs, so repeated identical attempts cannot be
distinguished from new-UUID delivery duplicates; metrics count distinct observations,
not a guaranteed number of executions. Changed movie metadata still creates a new
evidence version. Old collector code can read the database after rollback.

Selected source evidence supports strong outcome correlation just like historical
release.new/retained evidence. Missing stable IDs stay weak/unmatched. Explicit
movie-category episodes become diagnostic quarantine without making real TV movies.
Action acceptance alone never enters research or verifies/downloads a movie.
Metrics expose selected fingerprints, distinct event/filter observations, Unknown
Movie correlations, missing outcomes, weak IDs and dedup/rejection counters. A zero
count is not proof of a gap or no activity: upstream has no durable webhook outbox.

Back up configuration and SQLite through its backup API before migration. Test
both overlapping channels and rollback before changing the notifier. Bounded
parallel comparison may briefly record both channels but shares release/evidence
identity; remove the temporary notifier at cutover or timeout. Preserve all ledgers.
Rollback restores only the original dedicated notifier and saved collector config/
code, restarting only the collector; never restore stale action/research databases.
No historical purge is authorized. Estimate any future cleanup on a private copy
and request a separate retention decision before deleting observations.
