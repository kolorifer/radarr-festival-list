# Engineering report: seedbox event assessment

**Specification:** [accepted brief](2026-11-15-seedbox-event-assessment-brief.md).
**Result:** implemented candidate; final independent review and exact-head CI pending.
**Repository:** PR #205, `codex/seedbox-event-assessment-20261115`.
**Verification date:** 2026-11-15.

## What changed

A single seedbox worker drains the selected retained collector events and follows
new eligible identification failures without a Mac scheduler or hourly case cap.
It retains authenticated original evidence, generates the existing v13 assessment,
then requests a separate bound automated review. Only an approved, reconstructed
review can edit the exact existing Telegram card through the unchanged actor
sender. Neither model approves identity reuse, acquisition or downloads.

The append-only queue imports consumed cases and credit reservations. Unknown
provider and send attempts remain consumed. Shared access failures pause future
work; rate limits preserve cooldowns. Each source-denial record itself carries
its pause authority, avoiding a crash gap between two journal appends.

## Components

`automation/seedbox_*` implements queue, evidence, serial worker, separate review,
original-card delivery, encrypted credential bridge, installed closure and Linux
confinement. The 48-file investigator runtime adds an ephemeral host authorization
boundary; legacy authorization remains separate. See the
[deployment runbook](2026-11-15-seedbox-event-assessment-deployment.md) for exact
configuration, commands, grants and operator sequence.

## Validation and limitations

Invented connected tests exercise retained source bytes, actual v13 parsing,
separate generated review and the existing sender with fake HTTP, plus restart
no-replay, source circuits and first-transaction contention. No real credential,
source/provider request, Telegram edit or service action was performed by the
repository writer.

Initial candidate CI ran 2,318 tests on Python 3.12 with six stale 47-file closure
expectation failures; those expectations were corrected to 48. Initial local
runs also recorded intermittent `packet_changed` refusals under the existing
private-file guard. The guard was not weakened; later targeted passes do not
erase those failures. Main independently tested immutable ae3f9fb: 42 tests
passed, one Linux-only skip, zero external-I/O tripwire events.

Main's invented ae3f9fb host probe verified the 88-file package, same-user
credential decryption, evidence retention, unrelated-file denial, actual DELETE
journal creation/commit/removal and read-only WAL collector access. This is
candidate capability evidence, not final deployment or product acceptance.
Final exact-head supported CI and reviewer findings are recorded with the PR.

## Deployment and material tradeoffs

Not activated by this repository change. Main alone selects and deploys the
final accepted immutable bytes and real configuration under the runbook.
Existing collector WAL and actor DELETE journal modes are preserved. Normal
SQLite locking/recovery is retained. Only a first transaction proven BUSY before
any application statement or send permits a bounded local recheck; uncertainty
remains consumed.

Landlock grants regular-file mutation within the actor state subtree, including
its existing binding spool, because absent native journal names cannot be granted
individually. It does not restrict SQL tables or file names. The fixed reviewed
sender and exact original-card contract constrain use; directory creation/removal
there is not granted. Existing spool bytes are covered by a connected regression.
Same-user systemd credential IPC uses its fixed endpoint; filesystem Unix sockets
are not path-mediated by this Landlock ABI. These are explicit accepted limits.

Separate review uses the same model family and retained evidence, not an
independent source or human judgement. Source gaps remain unknown. Sender return
is not human receipt. Finite promotional credit, topology validity and exact
current-case checks remain mandatory; no cash fallback, original republishing,
unknown-attempt replay or production matching/download change is introduced.

## Context

Project state and notification guide distinguish this candidate from live behavior.
The unrelated active CODEX_TASK assignment is preserved. Final merge/deployment
receipts belong to their actual immutable revision and main's operational record.
