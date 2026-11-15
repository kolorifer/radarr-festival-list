# Seedbox collector WAL lifetime correction

## Problem and scope

PR205's first actual worker step failed before intake with SQLite
SQLITE_IOERR_SHMOPEN (4618). The queue retained enrollment and a global circuit;
no provider reservation, assessment or notification occurred. Main's bounded
read-only diagnostic established that opening and retaining the validated
read-only collector connection before confinement allowed both held and fresh
confined reads: 99 events through cursor99, high-water882. The exact native cause
is not proven. The earlier invented probe kept its writer open and missed this
lifecycle difference.

## Correction

The installed bootstrap now installs a narrow kernel no-regular-file-creation
layer before opening SQLite. Only the already-authorized worker state and actor
state paths may create regular files. Collector directory creation remains denied.
A validated mode=ro collector connection then establishes existing WAL/SHM handles
and stays open for the serial runner's lifetime. The existing full confinement
still follows; there is no blanket source write grant, immutable SQLite mode,
sidecar manufacture, journal-mode change or snapshot copy.

Each collector operation starts and rolls back a fresh read transaction so later
commits remain visible. Identity, private path, ownership, permissions, ACLs and
sidecar identities remain checked. The raw database identity descriptor stays
open until after SQLite closes: closing another descriptor for the same inode
can release process-owned POSIX locks. Separate actor DELETE-mode reads use their
own guarded connection; changed or aliased collector selections refuse.

## Verification and review

Invented real-SQLite tests cover later commits/checkpoints and distinct actor
reads without reopening the collector guard descriptor. Linux subprocess tests
exercise the actual helper under both confinement layers, producer closure and
fresh commits, and a producer cleanup race between validation and open that must
not create missing sidecars. Exact-head CI and independent review are required
before merge; final results are attached to the PR and private checkpoint.

## Deployment boundary

Main alone verifies the final immutable package, performs read-only corrected
access proof, and records explicit recovery of the existing circuit before
continuing the same queue. No re-enrollment, history rewrite, consumed-case reset,
credential re-provisioning, provider retry, actor restart or notification replay
is part of this repository correction. Existing attempts and reservations remain.
A missing/replaced sidecar still stops rather than being repaired. Runtime startup
requires native existing WAL sidecars; normal producer checkpoints remain allowed.
