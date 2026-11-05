# Manual fresh-evidence renewal for an unused synthetic slot

## Agreed scope

Implement a one-time manual recovery after the accepted module-entry repair.
Retain the same enrolled root, project, credit ledger, two existing attempt
folders, consumed first slot and all original evidence/history. This code work
does not apply renewal to retained live state, deploy a runtime or retry an API
request. PR151's accepted content is the dependency; its merge is separately
blocked by approval review. This distinct candidate does not change PR151.

## Behavior

`supervised_credit reauthorize --previous-evidence OLD --evidence NEW` takes the
existing `--state`. Both paths must pass the original private-file, ownership,
ACL, ancestor, symlink and read-race checks. NEW must be a distinct file/inode
and hash, currently valid, for the same project and fixed model/pricing/context
contract. Its observation must follow OLD's expiry. OLD is checked against its
original observation time solely to validate retained facts, never as fresh
send authority. Enrollment binds its exact bytes; the original start binds its
canonical evidence digest and time.

Under the existing root transaction and a pinned credit-file read lock, renewal
requires exactly enrollment-start, enrollment, and slot1-start records. The
credit ledger must be empty; both pinned attempt directories must be completely
empty. Any journal (even empty), unknown file, extra root record, prior charge,
storage replacement or incomplete history refuses. The command appends exactly
one record binding the original three-event prefix, old/new hashes, project,
fresh expiry and permitted existing slot2. It prompts for no credential and
performs no network call. It neither erases nor refunds slot1, edits evidence,
creates a root/ledger/attempt, nor extends the two-slot allocation.

The normal run and HTTP authority checks resolve this record while continuing
to use the original enrollment object and storage pins. All prompt provenance,
held durable transaction, freshness, request/endpoint, credential, ledger,
clock, single-use permit and HTTP guards remain. The only possible generation
is the original unused slot2, still reserving 3 cents against the unchanged
5-cent ledger. A failed/uncertain slot2 is consumed; another renewal is refused.
This deliberately does not recover charged, reserved, ambiguous or arbitrary
failures. Evidence references remain operator assertions, not authentication.

## Validation and limitations

Regression fixtures exercise the manual command with no prompt/network,
preserved original bytes/history prefix/storage identities, slot1 rejection,
slot2 authorization through the actual HTTP guard with an offline sink,
timeout/debit persistence, consumed-slot replay, second renewal, charged ledger,
unknown/empty attempt files, extra root events, changed project/pricing/expiry,
old-file changes, hardlinks, storage replacement and unsafe permissions. The
installed-runtime test invokes genuine `python -m ... reauthorize`, then runs
slot2 through a PTY and real hidden input using a dummy credential. Socket/DNS
tripwires prohibit real network access.

Initial 32-test execution had one intermittent private evidence read-race
refusal (`supervised_evidence_changed`) rather than the expected later refusal;
the existing fail-closed guard was retained. Subsequent exact candidate test,
independent-review and CI results are recorded in the PR/checkpoint.

No live evidence, retained state, credentials, provider, seedbox, schedule,
production service, quota, worker or claim was changed. This change grants no
movie disclosure, acquisition, notification or unattended operation.
