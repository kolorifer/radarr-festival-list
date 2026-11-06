# Capture startup evidence

The accepted architecture replaces inaccessible external process snapshots with
finite collector self-observation plus independently correlated manager/cgroup
and lifetime evidence. It does not relabel the earlier preflight as passed.
Selected-case/source validation and manager/cgroup readability must succeed
before deployment or the single authorized restart. This change is repository
implementation only: no source read, deployment, restart, grant or capture.

The existing sandbox mints an internal capability only after its effective
denial checks. Capture-specific runtime queries run only after the confined
configuration explicitly enables preparation; default-off startup performs none.
A default-off lifetime cannot later gain capture capability by config toggle. Completion repeats the real
isolation check and runtime identity immediately before Server construction.
Capture binds the capability once and rejects absent, incomplete, reused or
inherited-PID evidence before nonce readiness, file access and reservation; it
rechecks before burning and before finishing retained outputs. Existing nonce,
latch, native transaction, private create-only artifacts and default-off health
behavior remain. Failed new evidence disables capture, not ordinary intake.
The original confinement failures still refuse service startup.

Only three existing runtime modules change: sandbox, service and capture. The
six-module collector closure stays the same; service/socket units, source queries,
investigator manifest, budgets, producer and production action paths are unchanged.
The service's isolation_check remains a wrapper around its original check body,
now shared with capability completion. No arbitrary callback can claim isolation.

Validation uses actual modified confine/main/Server/Handler/Capture entrypoints
with invented kernel and I/O observations, not the design prototype. It covers
exact invalid-ID query arguments, stale errno and denial handling, missing or
incomplete capabilities, Store-time drift, isolated capability ownership,
inherited locked mutex/PID, pre-burn revocation, ordinary default-off and missing-
proof intake, plus the retained capture/isolation suite and isolated six-module
and 42-file investigator closure checks. Supported Python 3.12/3.13 exact-head CI
and independent review are required before merge. No local dependency repair.

This is a trusted-code statement under the existing threat model, not loaded-code
or kernel attestation. Host query compatibility and actual new-instance evidence
remain operational gates. Observed task count and cgroup snapshots are not a
proof of the absence of all historical or hostile escaped children. No live
verification is claimed. The operational sequence remains held for main inspection.

Operational limitation: new-query compatibility with the host's complete inherited
seccomp stack is not established. A fatal filter action cannot be caught as an
errno failure. The unchanged unit's Restart=on-failure can then cause additional
automatic starts. One explicit restart command does not guarantee one actual start.
Default-off startup makes none of these new queries. Enabled deployment remains
held until this specific operational constraint is resolved within owner authority;
no live probe, extra restart or unit-policy change is authorized by this patch.

Focused local verification: 125 tests ran: 124 passed and one Linux-only kernel test skipped
on macOS. Private preflight/health verifier: 16 invented tests passed. Exact-head
CI supplies supported Linux/Python checks; it is not provider-host proof.
