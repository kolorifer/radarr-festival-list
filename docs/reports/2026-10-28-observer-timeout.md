# Observer timeout and failure diagnostics — 28 October 2026

**Specification:** [brief](2026-10-28-observer-timeout-brief.md).
**Result:** implementation verified locally; deployment explicitly excluded.
**Base:** `edab00725ba3f3a3ce65ecd6b86146f490c54f03` (main after PR #107).

## Problem and evidence

The observer used a 0.5-second HTTP socket timeout, while the collector permits
two seconds of local writer waiting and has a five-second hard connection lifetime.
A delivery could therefore time out at the observer while still validly queued
or committing at the collector. Durable retry prevents a lost acknowledgement
from creating a second event, but the generic `delivery_failed` marker did not
distinguish transport failures, HTTP rejection or local outbox acknowledgement errors.

The 20:42 Warsaw incident had one accepted outcome, one duplicate and an empty
outbox by 20:42:31, with no collector SQLite failure. Read-only investigation
confirmed the mismatch but could not identify that historical exception: its type
and request latency were not retained. Earlier observer failures predated PR #105.
This change fixes the demonstrated timeout contract and diagnostic gap; it does
not retrospectively prove the cause of that incident.

## Changes and preserved behavior

Only `identity_triage_observer.py` changes runtime behavior. Its socket timeout
is now six seconds, allowing the collector's five-second lifetime plus a margin.
It remains a finite timeout per socket operation, not a six-second total deadline.
Slow transport runs only in the existing daemon worker; `observe()` still returns
after bounded queue admission. No caller waits for the network, and the memory
queue remains limited to 32 observations.

Existing failure prefixes/counters are preserved. Diagnostics add allowlisted
`stage`, `reason`, numeric `http_status` or `none`, and elapsed milliseconds capped
at 60,000. Stages distinguish configuration, sending, acknowledging the local
outbox and recording retry state, with corresponding persistence/worker stages.
Reasons distinguish timeout, refused/lost connection, HTTP protocol/status,
SQLite busy/locked/full/I/O/read-only errors, permissions, missing paths and fixed
fallback categories. Elapsed time covers the attempt or worker operation through
the failure; it is not collector queue or transaction latency.

The original delivery failure is logged before recording its retry state, so a
second spool error cannot hide it. The existing outer recovery loop still handles
retry-state failure. No exception is stringified; no response body/reason/header,
private path, release, key, event UUID or arbitrary class name is emitted.

Outbox schema/backoff, same-UUID retries, collector write/ACK semantics, selection,
credentials/configuration schema and identity/acquisition behavior are unchanged.
HTTP rejection still retains the pending event. A lost response or failed local
ACK still retries the same event and deduplicates at the collector.

## Regression and validation

Ten tests in `test_identity_observer.py` exercise:

- A real writer held for 800 ms: the original 0.5-second timeout returns a failed
  delivery before release; the fixed sender waits and succeeds once without retry.
  Restoring only the old timeout makes this regression fail as expected.
- Exhausting the collector's full default writer wait yields an observed HTTP 503,
  rather than a premature client timeout; retry commits the unchanged event once.
- Real lost-response and shortened-timeout paths retain the event and later
  deduplicate; a local SQLite ACK failure is reported separately after HTTP 200.
- Configuration failure does not send or acknowledge; a retry-state failure
  preserves both the original transport diagnosis and the spool diagnosis.
- Fixed-category redaction, hostile exception text, HTTP reason/header/body
  canaries, invalid diagnostic metadata, bounded timing and asynchronous admission.

- Python 3.12.14 focused observer/collector/selection suite: 106 tests passed.
- Python 3.12.14 full suite: 932 tests passed, with two Linux-only skips.
- Restoring the original 0.5-second timeout makes the controlled writer regression
  fail; the new timeout passes. The extra diagnostic-isolation check also passed.
- Dependency check and frozen scorer check passed: 1,909 candidates / 387 qualified.
- Python 3.12 and 3.13 CI on the final PR head are required before merge; see the
  containing PR for check results. Whitespace and documentation-link checks passed.

No dependency requirement changed.

## Deployment, monitoring and limits

**Not deployed.** No actor/collector service restart, configuration change,
shadow activation, live POST, download or Telegram message was triggered.
Actor `d7487700`, installed collector store from PR #105 and shadow `4db4e38`
remain separate runtime identities; merging this branch is not deployment.

The existing read-only 24-hour monitor remains active on its original schedule
through 29 October at 19:56 Warsaw time. During implementation it continued to
report health 200, zero collector storage failures and all 279 protected files
unchanged; the previously reported, recovered observer incident remained the
only observed delivery failure. No production synthetic probe was run.

Longer observer waits can reduce drain throughput during sustained collector
outage; the bounded memory queue can still overflow before persistence. Durable
retries and their existing backoff remain essential. Socket timeout is not a
guarantee that an ACK will arrive, and fixed diagnostics do not expose request
contents or uniquely correlate individual events. Deployment/production acceptance
of this observer change remains pending a separate instruction.

The containing PR supplies the implementation commit and CI references. Project
state, repository status and the collector runbook identify this as undeployed.
The unrelated `docs/CODEX_TASK.md` assignment remains unchanged.
