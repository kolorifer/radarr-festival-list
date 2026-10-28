# Observer timeout and diagnostics deployment — 28 October 2026

**Specification:** [deployment brief](2026-10-28-observer-deployment-brief.md).
**Result:** deployed at 20:30 UTC; host tests, health and preservation checks passed.
**Implementation:** [PR #108](https://github.com/kolorifer/radarr-festival-list/pull/108),
head `7afa98135652abd36128ffa2c61425380bdfcaf6`, merged as
`67d14c76d105252d2daf765768edd5a0f9fafc76`.

## Change and runtime identity

Only `identity_triage_observer.py` changed in the actor checkout. Minimal runtime
commit `06d17aafefb5a5161364e4bf6f63667a649e1aa3` is based on the previously
deployed clean `d7487700ee8bb6eed86adefeca365945ecccc001`, with the exact observer
bytes from PR #108. It is retained on `runtime/observer-timeout-diagnostics`.
The actor was not advanced to repository main. No collector, dependency, schema,
configuration, identity policy, acquisition or shadow code was deployed.

The observer now allows six seconds per socket operation, exceeding the
collector's five-second connection lifetime, and records only fixed failure
stage/reason, validated HTTP status and bounded elapsed time. Asynchronous
admission, queue size, durable same-event retries and backoff are unchanged.
The [implementation report](2026-10-28-observer-timeout.md) explains the contract
and the uncertainty surrounding the earlier 20:42 Warsaw incident.

| Observer bytes | SHA-256 |
| --- | --- |
| Previous | `9936d73a73a8003695e8a60282f99f2fadef46aaf3df6e20fa0086f9637be38f` |
| Installed | `0cb6b012d67553954c818f549c1cbf0c4d5328ad41c8b0ec74b2e663a6d56d5e` |

## Host tests and preflight

The candidate Git archive was tested in a private staging directory with the
existing Python 3.13.5 virtual environment and a separate test HOME. The live
actor remained on its old code during these checks.

- Exact actor runtime: `python -m unittest -v`, **757 tests passed**.
- `python -m pip check`, frozen `production_scoring.py --check` and offline
  `deploy/run.py --check-config` against the actual private configuration passed.
- Separate paired staging copied the installed collector modules and candidate
  observer, then ran PR #108's `test_identity_observer`: **10 tests passed**.
  These cover the real queued-writer timeout regression, 503 backpressure,
  lost-response/deduplication, local ACK and retry-state failures, redaction and
  asynchronous admission. HTTP fixtures used disposable synthetic stores and
  loopback listeners; no test event reached the production collector.
- Earlier implementation validation remains distinct: 106 focused and 932 local
  full-suite tests (two Linux skips), old-timeout regression failure and successful
  [Python 3.12/3.13 CI](https://github.com/kolorifer/radarr-festival-list/actions/runs/40761297053).

The actor checkout has its older collector source because the live collector is
installed separately. The paired regression run therefore used the actual
installed collector combination without adding collector changes to the actor.

## Activation and preservation

A mode-700 private host directory retains the runtime bundle, test logs, previous
observer, protected configuration copies/manifests and state backups. SQLite
backups used read-only source connections and passed `quick_check`.

Before and after stopping only `movie-intel.service`, checks found an empty
observer outbox, no executing approvals, no queued message bindings and no
digest/retry notification work due within the startup verification period.
The clean actor checkout switched to the tested minimal commit, passed offline
configuration preflight again and started normally. No unit or environment
override was installed. Current state was preserved rather than restored.

Activation and follow-up checks verified:

- Actor active/running, NRestarts 0, local and public health HTTP 200, 1,909 movies.
- Collector health and metrics HTTP 200, unchanged process, zero storage failures.
  The installed PR #105 store and all companion modules remained unchanged.
- All **286 protected files and modes** unchanged, including the monitor's 279
  protected files, actor/collector configuration and shadow runtime/configuration.
  The shadow timer remains active/waiting; no timer or budget was altered.
- All **18 existing approvals** unchanged. Logical database contents for acquisition
  receipts, retries, observer outbox/counters, digest receipts and verified cache
  were unchanged, as were message bindings.
- No new observer failure or digest-delivery/deferred-message marker appeared
  during the verification interval. There were no webhook replays, live POSTs,
  Radarr acquisition calls, deliberate downloads or Telegram messages.

## Monitoring, limitations and rollback

The original read-only monitor remains ACTIVE every 15 minutes through
**29 October 18:56:35 UTC / 19:56:35 Warsaw**, without resetting the window.
Its pre-activation check covered the elapsed journal window, found zero collector
storage failures and no new incident beyond the previously reported observer
delivery failure. Its existing fixed-prefix matcher supports the new diagnostics.

Collector deliveries remained 1,267 across the activation/follow-up checks, so
this interval does not prove a new natural upstream delivery. Health and synthetic
regressions do not guarantee complete upstream intake; unlogged loss and transient
between-check saturation remain outside full observation. Failure diagnostics
were verified synthetically rather than by deliberately failing production.

If rollback becomes necessary, stop only the actor, restore its recorded previous
Git revision and restart it; preserve all current private state. Never restore an
old action or receipt snapshot over later activity. The collector and shadow do
not require rollback for this one-file actor change.

Project state, repository status and the collector runbook now record deployment.
The implementation report remains an accurate historical record of the earlier
undeployed stage. The unrelated `docs/CODEX_TASK.md` and all policy decisions are
unchanged. Runtime provenance is the commit above; the containing documentation
PR supplies the report's own review reference.
