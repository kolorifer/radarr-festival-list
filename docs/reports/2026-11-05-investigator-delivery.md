# Investigator draft delivery — completed brief and report

## Specification

Connect the accepted qualified new-case draft to the existing notification
mechanism in disabled code. Preserve duplicate suppression and uncertain-delivery
handling. Test exact occurrence/draft binding, acknowledgement, known pre-send
failure and restart without duplicate replay using only a substituted final
sender. No notification, credential access, production installation, activation,
provider call, spend, new worker or claim is authorized for this increment.

## Implementation

`ai_movie_investigator.draft_delivery.deliver` selects a completed immutable
report from the existing private History. It requires exact job, occurrence
binding, report hash and draft hash, rechecks selected currentness, decisions,
research dependencies and evidence validity, and refuses a changed/stale draft.
It replaces only the draft-status footer with the no-approval qualification;
the rest of the selected notification text is preserved exactly.

The adapter calls the actor's existing `Digest.tick`, with a narrow single-message
option that bypasses the ordinary digest's additional header/footer wrapping.
The default production digest path, delivery table, reservation transaction,
uncertain-send state, 429 delay and duplicate logic are unchanged. The adapter
pins the selected outbox path/device/inode in History before an attempt; switching
or replacing that ledger does not refund an uncertain or completed delivery.

The existing ledger records `uncertain` before invoking the final sender.
An independent send-start latch in the existing review journal is flushed before
the external call; replacement/restoration of the SQLite ledger cannot erase it.
The existing parser records the actual 429 due time in History before its
SQLite update; readback must match that independent bound.
Only a retained explicit-rejection receipt with the original due time permits
another sender invocation. A missing ledger after a possible send is refused.
Timeouts, non-200 results, and interruption retain that state across restart.
Only an explicit 429 rejection can retry after the existing delay. Known storage
failure before reservation does not invoke the sender and can resume safely.
A retained `sent` state plus its journaled matching send-start and returned-200
proof can complete a missing local receipt without another send. An unbound
pre-existing ledger row never establishes acknowledgement; retry receipts also
require a journaled explicit 429 rejection.
The receipt binds occurrence, report, original draft, final message and ledger;
it distinguishes transport acknowledgement from recipient ingestion, which
remains unverified. Simulated assessments retain their explicit visible label.
The report and draft are not retroactively mutated to claim delivery or approval.

The function defaults to disabled and has no production startup or CLI wiring.
It receives the existing outbox and sender from an explicitly selected caller;
it constructs no client, reads no credential and changes no schedule. Tests
explicitly enable only their private synthetic path. The installed runtime
manifest includes the adapter and updated existing delivery module.

## Verification

Focused tests use real private History and SQLite Digest instances, replacing
only the final sender. They exercise successful acknowledgement and restart,
wrong job/report/draft/occurrence, actual pre-send database lock failure, timeout,
interruption, non-200 response, explicit 429 delay, outbox substitution,
superseded input, changed freshness and distinct occurrences. Existing digest
and new-case regressions run alongside them. Replacement-and-restoration,
false pre-existing acknowledgements and changed retry states have negative tests.
53 focused tests pass on both Python 3.12 and 3.13.
Independent review and exact-head
Python 3.12/3.13 full CI are required before merge. This is synthetic integration,
not a live notification test or proof of recipient ingestion.

## Remaining scope

The disabled notification-delivery connection is implemented. It is not installed
or activated. The owner now reports claimed Pro API credits, superseding the earlier
unavailable-credit assumption. The selected next route is the existing dormant
Responses adapter, not an unattended Pro-chat bridge. Grant amount, expiry,
project linkage and no-cash billing exposure remain unverified; no live API use
or billing change follows from this delivery integration. Supplied answers do
not establish unattended generation.
A genuine eligible new-occurrence assessment and notification through the intended
flow still require that assessment dependency and the separate final publication
and activation gate. Identity reuse and downloads continue to require confirmation.

## Context and revision

This report is the scoped completed brief and state record. The notification guide
links it; unrelated cleanup work and the closed coordinator trial are unchanged.
The containing PR supplies the accepted source revision and supported CI evidence.
