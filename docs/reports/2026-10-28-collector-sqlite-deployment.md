# Collector SQLite deployment — 28 October 2026

**Specification:** [deployment brief](2026-10-28-collector-sqlite-deployment-brief.md).
**Result:** collector-only deployment completed and technically verified at
18:47 UTC; follow-up verification at 18:48:58 UTC passed. The existing actor
and shadow configuration were preserved.

## Installed change

Only `~/.local/lib/movie-identity-triage/identity_triage_store.py` changed.
Its previous bytes exactly matched the pre-fix repository version. The installed
file is the tested implementation from [PR #105](https://github.com/kolorifer/radarr-festival-list/pull/105),
implementation `1cd546d65b1d7302527d7abe3abf6414e63b6e2c`, merged at
`55f22402be9a4001f913677587aade203f49ac3f`.

| File checksum | SHA-256 |
| --- | --- |
| Previous store | `435eb5f4ab7d113440e989386a0ba051a02b40dd500d4bd1d8643053cd8263fa` |
| Installed store | `c3cdfe8c54a7103387b1a0b3ed20d287041fb2faf5b065f3488a331716ea17e3` |

The five companion modules are byte-for-byte unchanged. The bounded local writer
queue, separate 250 ms external SQLite timeout, concurrent readers, rollback,
deduplication and commit-before-ack behavior are described in the
[implementation report](2026-10-28-collector-locks.md). No dependency or schema
change was made, and the actor checkout was not advanced to main.

## Deployment and preservation

A private mode-700 deployment directory retains the original module, protected
configuration manifests/copies, test logs and a consistent SQLite backup made
through a read-only source connection. The backup passed `quick_check` and
was fsynced. The module was atomically replaced at mode 600.

The actual `identity-triage.service` ran `--check-config` with its existing
socket, Landlock and systemd restrictions using a temporary runtime override.
It reported `triage preflight_ok`. The override was removed and the normal
collector service restarted. Startup reported Landlock ABI 6; the clean
environment, no-new-privileges, seccomp and private file permissions were checked.
No persistent service or socket definition changed.

The before/after checks verified:

- All 279 protected files and their modes unchanged, including actor/collector
  configuration, relevant units, shadow runtime files and pilot configuration.
- Actor checkout clean at `46cccea3a119ca080e35f6cf071bd0351eba037a`; same process,
  zero restarts; local and public health HTTP 200 with 1,909 movies.
- Shadow runtime remains `4db4e38`; its existing timer remains active/waiting.
  No timer was paused, enabled, rescheduled or manually triggered.
- All 15 actor action records unchanged byte-for-byte and acquisition receipts
  unchanged across activation. No actor restart, webhook replay, notification,
  Radarr mutation, search, grab or download request was made.
- Collector source mode remains `selected_only`; schema version remains 1.
  Live inbox deliveries remained 1,261 and its counters were unchanged across
  the verification window. Synthetic events never entered that inbox.

## Verification

The original slow-writer regression reproduced `database is locked` on the host
with the old store for both distinct and duplicate events. With the candidate
store and installed companion modules, all 77 collector, selected-intake and
confinement tests passed under Python 3.13.5, including real Linux kernel tests.
Initial test staging lacked the unit fixtures; those were copied from the
installed units before the passing run. Production was still unchanged then.

A disposable collector used the same Landlock and systemd restrictions, a
separate home/configuration/database and a separate loopback listener. Only its
test wrapper held the first real write transaction for 600 ms, beyond SQLite's
250 ms timeout. Five concurrent writers reached the connection boundary and
remained queued, while an HTTP metrics read returned the prior committed snapshot.
Additional duplicate and distinct-event bursts then completed.

This HTTP proof passed before activation and again using copies of the installed
modules afterward: **54/54 HTTP 200 responses, 28 distinct committed deliveries,
26 duplicates, zero storage failures** per run. Exact counters and database
integrity passed. The confined process could not open real actor credentials,
action state, SSH paths, production checkout, collector database or shadow pilot;
startup also required socket and metadata-operation denials. Temporary proof
units were stopped and removed.

At the 94-second follow-up, collector and actor health were HTTP 200; both processes
were stable, with zero unexpected restarts. Collector metrics reported zero
storage failures, and its journal had no storage/request/startup failure markers.

Earlier implementation validation remains applicable: 911 local tests (two Linux
skips), 210 repeated concurrency tests, unchanged frozen scoring, and successful
[Python 3.12/3.13 CI](https://github.com/kolorifer/radarr-festival-list/actions/runs/40745374229).
The full suite was not rerun during this one-file deployment; the host checks
above exercised the actual installed collector combination.

## Limits, rollback and handoff

Live collector checks were authenticated GETs only; concurrent POSTs used synthetic
fixtures in isolated stores. No natural delivery arrived during the observed
window, so no new upstream delivery is claimed. Sustained overload, external
writers and queues held beyond their bound can still produce deliberate 503
backpressure. No lossless upstream retry guarantee is introduced.

Rollback, if needed, is an atomic restoration of the retained previous module
followed by restarting only the collector and repeating health checks. Preserve
the current inbox/WAL and action state; do not restore a stale database backup.

Project state and the repository status map now distinguish this collector
deployment from the unchanged actor and shadow revisions. The runbook records
the bounded local queue. The unrelated `docs/CODEX_TASK.md` remains unchanged.
