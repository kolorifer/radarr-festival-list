# Engineering report: Landlock confinement for Stage1

**Specification:** [issue49 brief](2026-10-18-landlock-shadow-brief.md), issues47/49.
**Result:** feasibility and actual user-service integration pass; release gates and
production rollout are in progress at this report revision.
**Repository:** [PR48](https://github.com/kolorifer/radarr-festival-list/pull/48).
**Verification:** 2026-10-18, provider Linux6.12.113, x86-64, Landlock ABI6, Python3.13.5.

## Change and boundary

The namespace-based unit failed on this host. A small stdlib ctypes boundary now
installs Landlock in the receiver's single startup thread, before serving requests.
The separate systemd socket supplies one loopback listener. Standard systemd syscall
filters block new sockets/connects and operations Landlock cannot cover. No root
change, custom seccomp program, helper daemon or dependency was needed.

| Component | Purpose |
| --- | --- |
| identity_triage_sandbox.py | ABI6, fixed private layout, FD closure, no_new_privs, deny-by-default rules and effective denial gates |
| identity_triage_service.py | Mandatory confinement before config/store/HTTP; accept supplied listener without making a socket |
| deploy/identity-triage.service and .socket | Clean isolated Python environment, syscall complement, loopback socket activation |
| test_identity_triage_sandbox.py | Platform/ABI/refusal/layout/activation/no-bypass and real-kernel subprocess checks |
| test_identity_triage.py | Hard-deadline fixture accepts either EOF or TCP reset as connection closure |

Allowed reads: collector code/config, exact system Python standard library and
architecture libraries. Writes: collector regular state files only, including
SQLite WAL/SHM. No execution, cross-tree rename, special files or unrelated home
access. New TCP bind/connect denied; ABI6 scopes signals and abstract Unix sockets.
Unit additionally denies socket/socketpair/connect (covers UDP/pathname Unix),
chmod/chown/xattr/utime families, ptrace/process_vm/pidfd_getfd and io_uring. It pins
native syscall ABI and no_new_privs. FDs>=4 are closed; stdio and FD3 are validated.
The startup gate actively checks representative denials, not just systemd settings.

## Effective integration evidence

Disposable actual user-systemd child, then the real receiver in a separate fake-HOME
layout and synthetic store; neither path is the production collector state.

| Gate | Observed result |
| --- | --- |
| Private action store, credentials, reviewed bindings | Read and write-open denied; no contents read |
| Home, tracker apps, credential/action backup directories | Open/list denied |
| Symlink from own state to protected canary | Read/write denied |
| Synthetic inherited descriptor93 | Closed before service work |
| `/proc/self/environ`, `/proc/self/fd`, outside process environ/fd | Inaccessible after confinement |
| Same-user outside process signal0 | Denied |
| Protected canary chmod/utime/xattr | Denied by effective syscall filter |
| New TCP/UDP/Unix sockets | Denied; sole inherited loopback listener works |
| Own code/config, SQLite WAL commit | Allowed; DB/WAL/SHM0600 |
| Repeated event and new UUID, changed evidence, conflict/quarantine/auth | Expected statuses; one release, two evidence versions/two provisional cases |
| Restart | Original committed event remains a duplicate |
| Immediate disabled config | 503; no additional writes |
| Forced landlock_restrict_self refusal / changed state root | Exit1, no success ACK, database hashes unchanged |

Synthetic integration totals: 3 accepted deliveries, 2 repeated-event attempts,
1 repeated-evidence delivery, 1 event conflict, 1 malformed quarantine, 1 auth
rejection. Conflict also increments the quarantine counter (total2). These are
test observations only, never live coverage.

Unexpected routine fixes: provider home aliases require canonicalizing CLI paths
before fixed-layout comparison. The kernel hides some denied other-process proc
paths as ENOENT; probes first established that peer was visible, and treat ENOENT
only on that proc check as inaccessible. Protected file probes still require
EACCES/EPERM. The hard-deadline socket fixture can receive reset rather than EOF.
Neither correction broadens the policy or suppresses a failed isolation assertion.

## Tests and deployment

Focused suite:54 tests,53 pass and1 Linux-kernel skip on macOS. Full local suite:
445 tests,444 pass and the same1 kernel skip. Dependency check passes; frozen scoring
unchanged at1909 candidates,387 qualified (224 grandfathered,163 new). CI/seedbox
results and exact release/deployment SHAs will be added after their gates complete.
Production has not changed at this revision: clean healthy30adc20, both approved
bindings retained. Plan: install only the separately pinned collector; keep
movie-intel checkout/process at30adc20 and outcome observer off. This minimizes
interference with existing actions and is explicitly allowed by issue49.

## Limits and rollback

Linux x86-64 ABI6 and the fixed system runtime layout are intentional constraints.
Other architectures/older kernels refuse startup. Landlock does not hide stat
metadata; no claim of isolation from a malicious host or unconstrained same-user
process. Protecting code/config from such a process requires a separate account,
outside this scope. Startup is trusted; untrusted HTTP arrives only after confinement.
Every executable-policy change needs the actual-child checks again.

Stage1 coverage remains incomplete: autobrr has no durable publisher retry/outbox,
retained releases are filter-biased, provisional identity groups can fragment,
and quiet sources cannot be distinguished from missed events. No new research,
mapping, digest, notification or acquisition capability is added. Stage2 needs review.
Disable only the new route, set enabled=false, stop both socket/service. Preserve
the observation DB privately; never restore old action state. Full procedure in
[runbook](../../deploy/IDENTITY_TRIAGE.md).

## Sources and context

Rights/limits checked against the [Linux Landlock documentation](https://docs.kernel.org/userspace-api/landlock.html)
and [6.12 UAPI header](https://github.com/torvalds/linux/blob/v6.12/include/uapi/linux/landlock.h).
Complement uses [systemd.exec syscall filtering](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html).
The earlier [namespace-blocked report](2026-10-18-identity-triage.md) remains historical.
No product decisions or unrelated CODEX_TASK work changed.
