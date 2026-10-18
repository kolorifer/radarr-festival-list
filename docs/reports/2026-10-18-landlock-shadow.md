# Engineering report: Landlock confinement for Stage1

**Specification:** [issue49 brief](2026-10-18-landlock-shadow-brief.md), issues47/49.
**Result:** release gates passed, PR48 merged, separately confined collector running
in production. Final intake measurement is recorded below.
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
445 tests,444 pass and the same1 kernel skip. Full seedbox suite:445 passed, none
skipped. [CI39151621680](https://github.com/kolorifer/radarr-festival-list/actions/runs/39151621680)
passes445 on each Python3.12/3.13, including the actual kernel-policy subprocess.
Dependency/offline deployment-config checks pass; frozen scoring unchanged at1909
candidates,387 qualified (224 grandfathered,163 new). Diff/leak review passed.

Tested and deployed collector source: **3a2090703f9b4b85d5a3982b0e99ef452a625420**.
PR48 merged as **4740413a60b5bb17d668a00564f2988371543ae6**; full trees match.
Only the four collector modules and two unit files were installed, checked against
a private hash manifest. The installed production child repeated the file/FD/
symlink/metadata denial probes and configuration preflight successfully, then ran
the exact tested launcher. Authenticated health200, active/running, NRestarts0.
Process environment contains only HOME, PATH and PYTHONDONTWRITEBYTECODE.

movie-intel remains pinned clean at **30adc20b7d46bbe89bb14728d778d9d1142c57c6**.
Its code/process was not restarted or changed; outcome observer remains off.
Both approved identity bindings are preserved. The whole movie-intel checkout
therefore intentionally differs from main, while the separately installed collector
matches the tested/merged source. This is the issue49-authorized collector-only rollout.

Private configuration/action/cache snapshots, consistent autobrr DB backup and
initial triage backup are retained with owner-only permissions. No stale action
snapshot was restored. The temporary proof/validation services are stopped and
their units removed; synthetic databases remain separate from production.

The existing authenticated browser session added exactly one enabled WEBHOOK route,
`Identity shadow intake`, event RELEASE_NEW only, POST to the authenticated local
collector. Readback verified the URL/header and byte-equivalent original notifier
rows plus filter, filter-notification, indexer-association and external-filter tables.
No API key was created (count remains0); existing credentials were not rotated.
Autobrr serializes events as a PostgreSQL-style array and stores default POST as
NULL; the readback helper was corrected to those actual representations before
import. No live test button or action webhook was invoked.

## Actual intake and final verification

Route activation:2026-10-18 17:57:38UTC (19:57:38 Warsaw). At18:03:32UTC,
**live release_new deliveries:0**. No live rejected/quarantined/duplicate attempts
were recorded either. This verifies deployment/configuration and reachable health,
not a successful real publisher-to-receiver delivery. No synthetic POST was sent
to the production collector to disguise this gap.

| Source | Actual production-store result |
| --- | --- |
| Four approved private seeds | 4 accepted,4 duplicates on repeat; all unresolved |
| Bounded retained scan | 461 rows,450 accepted,4 quarantined,7 rejected/excluded; cursor461 |
| Same retained scan repeated | 454 duplicate events,7 excluded again; no added evidence/cases |
| Live release_new | 0 during the measured window |
| Current outcome observer | Off;0 deliveries |

Final store:450 release fingerprints,454 evidence versions,345 provisional cases,
all unresolved,4 seed associations. The generic `observed_movie_deliveries=454`
includes450 retained and4 seeds; it is not the live intake count. The seven
excluded rows are counted again on repeat, so the rejected-attempt counter is14.
Current retained data has four more accepted records than the earlier offline457-row
sample; these are retained observations, not evidence of newly delivered webhooks.
Private DB/WAL/SHM and backup are0600, containing directory0700; quick_check passes.
No synthetic production rows or secret values in collector journal were found.

One `storage_unavailable` aggregate warning occurred during the retained import,
on the minute-monitor interval; subsequent minute summaries and authenticated
health/metrics succeeded. The fixed log intentionally lacks exception details,
so contention is a plausible explanation, not a proven root cause. The process-local
counter remains1 (it was not reset to hide the warning). Bounded storage failures
fail closed and are tested; an overlapping upstream delivery could be lost because
there is no durable sender retry. No such loss can be proved or excluded here.

Final movie-intel local/public health200,1909 movies, active/running,NRestarts0;
both reviewed bindings validate. Environment, bindings, action store and resolver
cache hashes match the predeployment snapshot, and process PID/start time is
unchanged. Collector active/running,NRestarts0,health200,installed hashes match.
No deliberate Telegram event, approval token, Radarr request, search or download.

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
Existing autobrr logging is disabled; its empty journal cannot substantiate a
claim of zero send errors. Logging/settings were preserved. Collector minute logs,
authenticated health/metrics and systemd failure state provide operator checks;
no external alerting or automatic investigation schedule was installed.
Disable only the new route, set enabled=false, stop both socket/service. Preserve
the observation DB privately; never restore old action state. Full procedure in
[runbook](../../deploy/IDENTITY_TRIAGE.md).

## Sources and context

Rights/limits checked against the [Linux Landlock documentation](https://docs.kernel.org/userspace-api/landlock.html)
and [6.12 UAPI header](https://github.com/torvalds/linux/blob/v6.12/include/uapi/linux/landlock.h).
Complement uses [systemd.exec syscall filtering](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html).
The earlier [namespace-blocked report](2026-10-18-identity-triage.md) remains historical.
No product decisions or unrelated CODEX_TASK work changed.
