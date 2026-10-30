# Scoped brief: confined coordinator movie-export ingestion

**Authority:** Issue #115, latest owner supervisor Task 1, 30 October 2026.
**Baseline:** Accepted main `098338e48771ee4c4b705393fa43ba12994b85c2`;
accepted PR #114 head `9aaa89a4422e78b4c73f9c1853cebc911f60bf6d`.
**Scope:** Reusable offline code, documentation and synthetic verification only.
**Status:** Implemented for parent publication and independent review; see
[engineering report](2026-10-30-coordinator-export-ingestion.md).

## Objective and behavior

Provide a bounded, no-follow reader/stager for the existing investigations snapshot
and research report. Caller authority supplies an absolute canonical research-state
root and a distinct new owner-only output root. Fixed logical sources and paths
are `investigations` / `incoming/snapshot.json` and `research_report` /
`review-report.json`. No discovery, alternate path, transport or source refresh.
The producer's resolved-home layout is a contract distinction; it does not explain
the historical pilot failure.

Preserve original bytes/SHA256 and true generation provenance. Enforce ancestor
and final-entry confinement, regular-file and 2 MiB/source limits, nonblocking
bounded reads, modification detection and descriptor cleanup. Reject links,
source/destination aliases, existing destinations and overwrites. Stage each source
independently under mode0700 with mode0600 files, atomic create-only installation,
bounded manifest/diagnostics and observations. Never reuse an old staged pair.

Introduce a versioned private diagnostic vocabulary limited to fixed source,
stage and allowlisted reason. Distinguish acquisition, staging, hash identity,
strict JSON, provenance, freshness, schema and pair failures without parsing
exception prose. ENOTDIR remains ambiguous; unread sources have no invented hash,
generation or collection clock. Keep coarse availability/review semantics and
independent engineering/parent/other-source findings. Preserve strict duplicate-key,
nonfinite, full-case-set, base-field, version, eligible-subset, coverage and proposal
validation. Fresh compatible movies remain `incomplete_upstream`; quality/release
remains unavailable.

Integrate observations and immutable report preparation without changing outbox
ownership/receipts or rewriting old payloads, IDs, hashes, intents or publication
evidence. Preserve observation-refresh deduplication and material availability/
validation transitions. Public CLI output/errors contain only fixed safe fields;
private diagnostics belong to the explicitly selected private output/report.

## Acceptance and verification

Synthetic tests must cover canonical versus symlink roots, ancestor/final links,
escapes/aliases/collisions, missing/denied/nonregular/FIFO/oversize/changed reads,
bounds and descriptor cleanup, separate validation diagnostics, independent findings,
secret sentinels, original bytes, partial failures and no old-pair substitution,
failure-to-success and quiet refresh, and legacy payload recovery/receipt binding.
Retain existing source-journal write protection, whole-set and dedup regressions.
Run relevant and full unittest suites, compilation and diff checks; no dependency
installation/change. If only unsupported Python 3.9 is available, report actual
results and exact limitations. Exact parent-published-head 3.12/3.13 CI and
independent review remain acceptance gates.

Update the coordinator guides, scoped report and verified project state. Keep
`docs/CODEX_TASK.md` and old decision rationale unchanged. The runner owns Git
publication and issue reporting; no worker commit/push/PR/comment.

## Boundaries

Use synthetic temporary roots only. No seedbox, SSH, private inputs/state/logs,
credentials/config/key discovery, services, provider/research/refresh requests,
notifications, Radarr/media/download operations, scoring/budget/ledger changes,
identity/acquisition approvals, deployment or recurring activation. No dispatcher,
supervisor policy, receipt protocol, claims/locks/quota/cap modifications; no new
worker, runner, daemon or scheduler. Preserve #86/PR #110 and all issue #113
retained execution artifacts and eight consumed executions.

Task8 established SSH exit0 followed by generic `file_rejected`, with neither
export imported. The specific host/path cause remains unknown. Later authorized
source integration must be decided from this contract and actual evidence after
code acceptance; this brief does not authorize operational replay.
