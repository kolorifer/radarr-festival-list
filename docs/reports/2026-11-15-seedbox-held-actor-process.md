# Selected actor metadata across confinement

## Problem and evidence

The corrected collector connection entered successfully on the deployed PR206
package, but full confinement could no longer resolve the selected actor process
path after the earlier no-create layer. Main's read-only diagnostic verified that
the actor was visible with the selected lifetime and command before that layer,
and its path returned ENOENT afterward. The original actor and paused worker
remained unchanged; the queue still contained only enrollment and its circuit.

Main then proved that preopened read-only stat/cmdline descriptors and a pidfd
for the exact actor remain usable after the early layer, with matching fresh
metadata and a live pidfd. No credential, network, signal or state operation was
performed. Linux documents process-access restrictions across Landlock domains:
https://www.kernel.org/doc/html/latest/userspace-api/landlock.html

## Correction

Before either confinement layer, the bootstrap opens only the selected actor's
process directory, stat and cmdline plus a nonsignalling pidfd. It validates owner,
PID, start ticks and command digest, keeps the handles close-on-exec, and retains
them for the worker lifetime. Full confinement validates this exact held selection
without resolving the now-hidden process path or expanding process access.

Every actor check rereads bounded current metadata from offset zero and checks
pidfd liveness before and after. Empty data, zombie/exit, changed command or
lifetime, changed selection and read errors refuse. Existing binary hash checks,
finite topology authority and the check immediately before the real edit remain.
This is a point-in-time observation, not a lock preventing a subsequent exit.
Handles close on setup failure and normal exit; credentials and child processes
do not inherit them. No cached successful observation authorizes delivery.

## Validation and deployment boundary

Invented Linux tests use a separate unconfined actor process, then apply both
actual confinement layers in the worker. Fresh metadata opens must fail while
retained reads succeed; actual actor exit or exec command change must then refuse.
Additional tests cover parser refusals, handle cleanup and close-on-exec flags.
Local focused tests ran14 with9passing and5Linux-only skips; exact supported CI
and independent review are required before merge. Final evidence is recorded on
the PR and private checkpoint.

Main alone performs the final installed read-only proof and recovers the same
retained queue if verified. No actor restart, history reset, re-enrollment,
credential provisioning, provider retry or notification replay is included.
