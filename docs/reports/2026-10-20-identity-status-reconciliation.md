# Reconcile stale investigation statuses

## Approved brief

After identity-rule changes, refresh affected investigation cases without sending
notifications or starting downloads. Reconcile Bruce and Madame Bovary, preserve
history and existing acquisition/research safeguards. Leave unrelated cleanup work
and identities unchanged.

## Implementation

Added a generic operator maintenance helper and deployment gate. Prepared outcomes
must match the existing case fingerprint and complete normalized source metadata.
Transient failures cannot replace meaningful prior results. Report refresh is
bounded to explicitly named cases and refuses unrelated projection drift.

Silent maintenance receipts suppress only the precise affected digest versions,
using an honest `suppressed` state. Previously sent/uncertain records are retained;
future changed evidence and unrelated notifications are not suppressed. No new
scheduler, matching exception, research call or acquisition path is introduced.

The live actor runtime stays pinned; this maintenance helper is executed separately
with the installed collector and actor modules. An isolated database-copy proof
precedes actual observer ingestion and report publication. Pause the actor/digest
and scan timer during publication, then restore their prior operation and health.

## Verification and result

Local full suite651 tests passed,2 Linux-only skips. Four helper tests also passed
on the seedbox. Live reconciliation pending. Exact source preparations use only
retained metadata and public movie lookups, with all notification/acquisition
methods blocked. No live downloads are authorized.

## Limitations

This is a mandatory deployment procedure, not a new recurring scanner. It requires
retained exact source evidence and an explicit affected-case scope. Missing source
evidence, concurrent case changes or temporary lookup failures are reported rather
than guessed. Research proposal history is retained and stale evidence is labelled;
the ordinary bounded worker may produce future updates on its normal schedule.
