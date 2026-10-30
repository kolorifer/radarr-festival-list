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

## Task 2 — reviewed filesystem corrections, 30 October 2026

**Authority:** Latest canonical supervisor Task 2 for issue #115.
**Baseline:** Clean `automation/issue-115-worker` at
`e8e86942cea7e88ef44434cebb6a2e52e4bec622`, existing PR #116.
**Status:** Focused corrections implemented; final local results and remaining
review/CI gates are recorded in the [Task 2 report](2026-10-30-coordinator-export-ingestion.md#task-2-correction-report--30-october-2026).
Task 1 is consumed, not replayed. Its code boundaries and unrelated preservation
requirements above continue to apply; no source integration is authorized.

Reproduce the double-leading-slash checkout exclusion bypass and newly opened
ancestor-fstat descriptor leak before fixing them. Use only synthetic temporary
sources and staging, and patch module `__file__` to a synthetic checkout.
Enforce output separation from both protected trees before mkdir/output writes:
reject noncanonical absolute anchors, retain strict no-follow traversal and
compare filesystem ancestor/final-root identities rather than just lexical
prefixes. Reject equivalent case-insensitive paths where applicable. Give each
new ancestor descriptor a cleanup owner before its next fallible operation.
Preserve original errors or fixed safe diagnostics and caller descriptor ownership.
Do not refactor unrelated parent-export or dispatcher/receipt code.

Focused tests must reject ordinary checkout and `//` destinations before writes,
allow valid external output, retain existing source/alias/no-follow/collision and
original-byte/privacy/manifest/freshness/full-set/outbox regressions, account for
every acquired descriptor under repeated injected stat/open failures, preserve
root-stop traversal and sanitized public failure output. Case-insensitive real
filesystem tests must explicitly skip where aliases do not exist; an injected
identity test must remain portable. Run relevant coordinator/export/integration
and full repository unittest suites, compilation and diff checks on available
Python. Do not install dependencies or hide unsupported-runtime limitations.

Append scoped results here and in the existing report, and update guide/state
facts. Preserve `docs/CODEX_TASK.md`. Parent runner alone commits/pushes/updates
PR #116; independent exact corrected-head review and Python 3.12/3.13 CI remain
acceptance gates. Historical Task 1 CI is not corrected-head evidence. No SSH,
private source acquisition, deployment, runtime activation, merge or task replay.

**Local result:** Both findings reproduced before correction; 158 corrected
coordinator/export/integration tests passed (22 export tests), including real
case-insensitive aliases on this Mac and repeated stat/open descriptor accounting.
Compilation, frozen production scoring and diff checks passed. Full unittest on
unsupported Python 3.9.6 ran 789 tests with 109 errors and two Linux-only skips;
missing dependencies/unavailable runtime APIs and HTTP fixture failures are
itemized in the report. Dependencies and unrelated code remain unchanged.
Corrected parent-head supported CI/review remain pending; no live access or
deployment occurred.
