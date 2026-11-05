# Connected supervised new-case review — completed brief and report

## Specification

Connect an explicitly selected normalized occurrence and its retained evidence
and decisions to minimized supervised-chat input, validated assessment and an
unsent notification draft. Reuse existing intake, reconciliation, private journal
and notification formatting. Preserve occurrence-specific decisions and all
existing live-pilot admission protections. No model worker, API account, spend,
source read, production activation, publication or download is part of this change.

## Result and components

`ai_movie_investigator.new_case.prepare` accepts the existing normalized packet
and an exact source/case/version/event/delivery selection. It requires captured-byte
hash basis, an unresolved eligible original route, and eligible reconciliation.
The existing History intake prevents event conflicts and decision rollback.
Research-derived inputs still require existing journal receipts. Local snapshots
remain caller assertions, not independently authenticated production admission.

The handoff contains safe retained evidence, explicit stale/missing/withheld
states, scoped decision applicability and facts, with operational IDs replaced
by a hash and evidence aliases. Long operational references in text are redacted
as exact substrings; short labels and numbers use token boundaries, not a promise
of complete anonymization of every possible substring. Untyped source runtime/edition claim labels are
withheld. The existing historical workflow is unchanged.

`complete` accepts a directly supplied answer and provenance, reserves once,
rechecks selected currentness and decisions, validates evidence/candidate support
using the existing controller, and retains the exact result and notification
text in the private hash-chained journal. Invalid or interrupted completion
cannot be replayed. `History.start` also refuses a second model workflow for an
already prepared supervised job. The existing digest's `readable_case` supplies
the notification body; no sender or delivery ledger is called. The installed
runtime closure now includes this module and the existing digest/redaction dependencies. The draft contains
qualifications and no action buttons, approval or download authority.

## Executable interface

```
python -m ai_movie_investigator.new_case prepare --history-dir PRIVATE_DIRECTORY
python -m ai_movie_investigator.new_case complete --history-dir PRIVATE_DIRECTORY
```

Each command consumes one JSON object on stdin and returns JSON on stdout.
Prepare accepts `{packet, selection}` and returns the actual minimized handoff.
Complete accepts `{request_hash, answer, provenance}`; request_hash is the
canonical digest of that handoff, and answer uses its output schema and binding
hash. Provenance is `{mode, chat_reference}`, with mode `supervised_supplied` or
`simulation`. The existing supervisor can pass these objects directly; no
operator-created input, reply, or provenance files are required. The same Python
functions work in-process. Private journal originals are retained automatically.
A source adapter must still provide a separately authorized normalized packet;
the CLI never selects or reads a source itself.

## Verification

Focused synthetic cases cover two distinct new occurrences, minimized input,
missing IDs/evidence, original-route and prior-decision refusals, old-approval
non-transfer, stale/future/wrong-occurrence evidence, expiry during assessment,
supersession, cross-workflow reservations, replay refusal, wrong bindings,
conflicting IDs, unsupported runtime claims and research receipt requirements.
Network and notification send paths are forbidden during these tests. All 20
focused tests pass. Independent review accepted the corrections and ran an
installed-only isolated prepare-to-complete check successfully. The coordinator
also inspected a synthetic handoff and supplied an unresolved answer for its
expired evidence, producing a qualified unsent draft. This is supervised synthetic
verification, not a real new-case read or unattended assessment. Supported
Python 3.12/3.13 exact-head CI is required before merge.

## Remaining finish criterion

This is a connected supervised review and draft path, not an unattended agent.
`prepare` does not invoke a model; `complete` does not authenticate chat authorship.
A simulated answer tests plumbing only. The existing Codex transport still has
no reviewed real-client profile, and there is no installed supported bridge that
invokes the existing Pro chat and returns its bound answer without supervisory
participation. That is an implementation and verification gap, not just pending
activation. Automatic notification delivery is also not connected here; a future
approved integration must preserve the existing delivery uncertainty/deduplication
and exact occurrence gates. Current live-pilot admission and source authenticity,
disclosure, quota, isolation and authority checks remain unchanged.

The finish criterion still requires a real eligible new occurrence to receive a
genuine assessment without manual handoffs and one qualified result through the
intended notification flow. Actual publication/activation is a separate final
gate. No deployment, credentials inspection, provider request, spending, source
operation or actual notification occurred for this code increment.

## Project context

This scoped report records the current state and completed brief; the unrelated
active cleanup task and historical project-state payload remain untouched. The
notification guide records the disabled draft path. The containing PR supplies
exact revision, review and CI evidence.
