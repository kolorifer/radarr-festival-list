# Collector SQLite writer contention — 28 October 2026

**Specification:** [brief](2026-10-28-collector-locks-brief.md).
**Result:** implementation verified locally; repository-only change, not deployed.
**Base:** `87bc8cae9b775c08629f1c400c832d570aaac72b`.

**Later authorized deployment:** the store module from merged PR #105 was
deployed separately on 28 October at 18:47 UTC. See the
[collector-only deployment report](2026-10-28-collector-sqlite-deployment.md).
The implementation-stage evidence below retains its original scope.

## Cause and change

The [original failing CI run](https://github.com/kolorifer/radarr-festival-list/actions/runs/40723928750)
failed in `Store.ingest` at `BEGIN IMMEDIATE`, not in a data assertion. The
threaded collector shares one Store across up to eight requests. Its independent
SQLite connections competed for the single write transaction, with a 250 ms
busy timer for every contender. A slow/scheduled-out writer or a burst of local
writers could exhaust another request's timer before it acquired the transaction.

`identity_triage_store.py` now serializes writable connections on that Store
with a reentrant thread lock, acquired before opening SQLite and released after
connection close/rollback, including failure paths. The two-second local queue
limit remains below the HTTP handler's five-second lifetime. It produces the
existing fixed `sqlite_busy`/HTTP 503 response when exhausted. SQLite's separate
250 ms timeout is unchanged for external writers or other Store instances.
Read-only metrics/backup connections do not wait on the local writer slot.
No transaction body is retried; commit-before-ack and event deduplication remain.

## Regression evidence

The new controlled-contention test holds a real ingestion transaction for more
than 250 ms while a second thread tries to ingest. On the original implementation
it fails with `sqlite3.OperationalError: database is locked` at the same
`BEGIN IMMEDIATE` line for both distinct and duplicate events. On the fix the
contender waits locally, readers still see the committed snapshot, and release
of the first writer lets both calls finish with exact delivery/counter assertions.
No SQLite failure is mocked and the original concurrency assertions are unchanged.

Additional tests verify bounded queue exhaustion without partial writes, release
and rollback after a mid-transaction error, and a real loopback HTTP 503 followed
by successful retry and duplicate delivery with exactly one committed event.
The existing external-lock, disk-full, crash and permissions tests still pass.

## Validation

- Python 3.12 focused collector/selection suite: 79 tests passed.
- Frozen scoring check passed: 1,909 candidates / 387 qualified.
- Python 3.12 full suite: 911 tests passed, with two Linux-only skips.
- Repeated concurrency validation: 200 original burst tests plus ten forced-contention
  regressions passed (210 test executions).
- Git whitespace and documentation-link checks passed.
- Final-head Python 3.12/3.13 CI must pass before merge; see the containing PR.

## Limits and deployment

No service, production state, Telegram, Radarr or downloader access or deployment.
The local queue is per Store, matching the collector's shared-instance design;
it does not replace SQLite's cross-process locking. Sustained overload or a
writer held beyond the queue limit still returns backpressure rather than a
false acknowledgment. This fixes local contention without promising that every
possible SQLite BUSY condition is eliminated. No schema/dependency change.

The current project-state/status map links this report; earlier consolidation
reports retain their then-unresolved findings as historical evidence. The unrelated
`docs/CODEX_TASK.md` assignment and all historical research snapshots are unchanged.
