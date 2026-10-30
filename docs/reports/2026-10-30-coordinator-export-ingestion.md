# Engineering report: issue #115 confined coordinator export ingestion

**Specification:** [Scoped brief](2026-10-30-coordinator-export-ingestion-brief.md),
latest canonical issue-owner supervisor Task 1, 30 October 2026.
**Result:** Implemented; awaiting parent publication and independent review/CI.
**Repository revision:** `automation/issue-115-worker`, baseline accepted main
`098338e48771ee4c4b705393fa43ba12994b85c2`. Parent owns containing commit/PR.
**Verification date:** 30 October 2026, synthetic temporary roots, macOS / Python 3.9.6.

## What changed

A later authorized reporting owner can read exactly two existing movie exports
through one auditable offline component instead of task-local reader logic.
Original bytes are staged unchanged with SHA256, true embedded generation time
or null, and actual collection time only after a successful read. Independent
acquisition failures retain the valid other source and incomplete review.

New version-1 diagnostics contain only fixed `source`, `stage`, `reason` and
`version`. Typed failures/errno distinguish acquisition from atomic staging,
hash identity, strict decoding, provenance, freshness, source schema and movie
pair conflicts. No exception-prose classification or private source/path output.
ENOTDIR remains `path_component_ambiguous`; unrecognized OS errors are `io_unknown`.
The public CLI retains coarse fixed summaries/errors, including argument errors.

Manifest v2 adds bounded acquisition/staging diagnostics, with consistency checks
against staged declarations; v1 manifests remain accepted. Observations retain
precise validation diagnostics without changing outbox/receipt ownership or
rewriting old pending bytes. Full source validators are preserved. Compatible
fresh movies remain `incomplete_upstream`; quality/release remains unavailable.

## Files and components changed

| File/component | Purpose |
| --- | --- |
| `automation/coordinator_exports.py` | Fixed offline reader, new private output root, original-byte atomic staging, manifest/observations and bounded staging failure records. |
| `automation/coordinator_diagnostics.py` | Versioned allowlist and typed validation/errno mappings; no arbitrary imported strings. |
| `automation/coordinator_io.py` | Reusable caller-pinned descriptor read, typed regular/size/change/link failures, unchanged no-follow/bounded cleanup guarantees. |
| `automation/coordinator_sources.py` | v1/v2 manifest acceptance, isolated per-stage diagnostics, existing validators/pair semantics and quiet comparison preserved. |
| `automation/coordinator_integration.py` | `stage-exports` command and fixed public-safe argument errors. |
| `test_coordinator_exports.py` | Synthetic ingestion-to-report rehearsal and focused confinement/failure/race/privacy/transition regressions. |
| `automation/COORDINATOR.md`, `automation/COORDINATOR_PILOT.md` | Exact contract, invocation, diagnostic vocabulary/defaults, retry semantics and reproducible synthetic rehearsal. |
| `docs/MOVIE-NOTIFICATIONS-GUIDE.md`, `docs/PROJECT_STATE.md`, scoped brief/report | Plain-language offline status and verified engineering handoff. |

## Acceptance criteria and evidence

| Criterion | Result | Evidence / limits |
| --- | --- | --- |
| Fixed source/root authority; no discovery/transport | Implemented | `incoming/snapshot.json` and `review-report.json` only, under explicit absolute canonical research-state root. |
| No-follow confinement, bounded reads, descriptor cleanup | Synthetic pass | Canonical/symlink roots, ancestor/final links, traversal, FIFO/directory, oversize, changed input and injected stat/read failures. |
| No source overwrite/alias; private new output | Synthetic pass | Lexical and filesystem ancestor exclusion; hardlinks, dangling links, existing roots/files and racing create-only collisions rejected. Source bytes/mtime unchanged. |
| Precise bounded private diagnostics | Synthetic pass | Distinct hash/JSON/schema/stale/future/time/revision/pair tests; errno injections including denied/ENOTDIR/unknown; fixed fields and secret sentinels. |
| Independent findings and truthful partial outcomes | Synthetic pass | Valid engineering/parent findings survive movie errors; missing source has null hash/generation/collection; no earlier-pair substitution. |
| Original bytes and freshness | Synthetic pass | Noncanonical JSON/newlines preserved exactly; original SHA256; original generation clock; no source refresh/retimestamp. |
| Existing immutable outbox/receipts and dedup | Synthetic pass | Existing legacy fixture recovery/receipt tests retained; failure-to-success produces one new report; unchanged fresh observations quiet. |
| Supported-runtime exact-head CI/review | Pending | Available local runtime is unsupported 3.9.6; parent must publish and obtain independent exact-revision review plus 3.12/3.13 CI. |
| Live integration/recurring operation | Not authorized | Synthetic results establish neither actual source access nor activation. Historical Task8 cause remains unknown. |

## Tests run and results

Final implementation checks:

```sh
python3 -m unittest test_coordinator_exports -v
python3 -m unittest test_coordinator_exports test_coordinator_integration test_coordinator test_github_worker test_supervisor_policy test_supervisor_communication test_identity_automation.HandoffTests -v
python3 -m unittest -v
PYTHONPYCACHEPREFIX=/private/tmp/issue115-pycache python3 -m py_compile automation/coordinator_io.py automation/coordinator_diagnostics.py automation/coordinator_exports.py automation/coordinator_sources.py automation/coordinator_integration.py test_coordinator_exports.py
git diff --check
```

- New focused export suite: **17 tests passed** (1.257 seconds).
- Final broader relevant suite: **272 tests passed** (71.084 seconds), including
  all **153 coordinator/integration/export tests** and the existing worker,
  policy, communication and handoff boundary checks. Existing full-case-set,
  parent/source write protection, refresh deduplication and legacy pending-v2
  receipt/recovery regressions passed without changing those fixtures/tests.
- Final full suite: **784 tests run**, **109 errors**, **2 skipped** (183.823
  seconds), exit1. Error categories are 84 missing `requests`, 9 missing `bs4`,
  10 unavailable `TestCase.enterContext`, 1 unavailable SQLite `sqlite_errorcode`,
  2 unavailable SQLite `SQLITE_BUSY`, and 3 HTTP fixture `RemoteDisconnected`
  errors in storage-failure/timeout tests. Those handlers use unavailable SQLite
  constants on this runtime. The two skips require Linux seccomp / Linux x86-64.
  No full supported-suite pass is claimed. An earlier during-development full
  run also completed (782 tests, same 109 errors and 2 skips); the counts above
  are the final implementation, including the two added boundary tests.
- Compilation of every changed/new Python file passed with bytecode in a synthetic
  temporary root. `git diff --check` and untracked-file whitespace checks passed.
- The exact Python block in the new issue #115 section of
  `COORDINATOR_PILOT.md` was extracted and executed successfully: original byte
  preservation/SHA256, manifest/observations, one immutable report, quiet repeat,
  same pending bytes/ID/hash and exact recovered payload. Only its fixed public
  projection was printed; all synthetic temporary inputs/outputs were removed.
- Documentation relative targets and new anchor links were checked. Final tracked
  and new file diffs were inspected; protected/unrelated files match baseline.
  No source, deployment, network-publication or live operational check was run.
No project virtual environment or supported Python 3.12/3.13 is available on PATH;
only `/usr/bin/python3` 3.9.6. Dependencies were neither installed nor changed.
No earlier accepted-head CI is presented as a newly run check.

## Diagnostic/default choices and rationale

- Research-state root is explicit and canonical; no implicit home resolution.
  Fixed layout matches existing producer exports. The producer's own
  `Path.home().resolve()` is a documented distinction, not a historical diagnosis.
- New output root requires an existing stable owner-only parent, matching the
  coordinator's private-state trust model and keeping creation under caller
  control. No caller-owned old root is reused, overwritten, rolled back or deleted.
  Per-file atomic create-only installation uses pinned directory descriptors;
  no bundle-wide atomicity is claimed. A staging failure can leave partial fixed
  files and a best-effort fixed `diagnostics.json`; a new root is required to retry.
- Acquisition failures are independent. Unread bytes have no fabricated provenance.
  Successfully acquired invalid content is still retained exactly for inspection;
  staging/read success never asserts schema/freshness/pair success. Root preflight
  failures produce no output report; fixed typed errors are available to library
  callers, and public CLI failure remains generic.
- Maximum two 2 MiB original exports (4 MiB combined), fixed manifest fields,
  at most 40 allowlisted diagnostic records, at most 512 KiB observations.
  Structured staging failure records are create-only and best-effort when the
  underlying output failure permits writing; absence is not evidence of success.
- Diagnostics are private explanatory observation metadata excluded from semantic
  comparison. Coarse status/reason, expiry, validated findings and evidence/version
  changes retain comparison-v2 meaning. Adding diagnostic collection or refining
  an already-failed stage alone does not create an upgrade/duplicate report;
  an availability/validation success/failure transition remains material. The
  latest private observations expose diagnostic detail independently of publication.
  No pending payload, ID, hash, intent, receipt binding or publication evidence is
  migrated or rewritten to add diagnostics.
- Generic source-validator exceptions map to `schema/invalid_source_schema`,
  rather than guessing their hidden cause. Explicit checks identify provenance,
  freshness and pair mismatches. ENOTDIR never asserts a symlink. Unknown errno
  remains unknown. No arbitrary exception text is inspected or recorded.
- Stable owner-controlled parent directories are required. Filesystem descriptor
  confinement is not protection from a malicious same-UID process that can rename
  the caller's directory hierarchy. This is the same explicit directory-control
  precondition as existing offline coordinator state, not a new execution owner.

## Deployment result

Not authorized and not performed. No SSH/seedbox, real private inputs/state/logs,
source refresh, provider/research request, service, notification, Radarr/media,
network publication or recurring execution was used. The runner owns all Git
publication and issue reporting; this worker made no commits/pushes/PRs/comments.

## Unexpected findings

The available runtime is Python 3.9.6 without project dependencies. The required
full test command was executed and its failures retained, rather than suppressed.
Unsupported unittest/SQLite APIs and missing `requests`/`bs4` prevent a full local
pass; precise final error counts are recorded with the test results. No dependency
or unrelated runtime code was changed to make these tests pass.

Issue #113 Task8 established SSH exit0 and generic `file_rejected` with neither
export imported. No specific host/path cause is established by that evidence or
by these synthetic root tests.

## Unresolved issues and risks

Independent review and current parent-published-head 3.12/3.13 CI remain required
before acceptance/merge. This worker cannot supply that later published revision.
Actual canonical source-root authority, access/transport, fresh compatible original
exports, private destination and reporting ownership need a separately scoped
verification after code acceptance. This task grants no replay or deployment.
Source revision stays unknown when absent; manifest byte pins authenticate staged
identity, not an external producing authority. Old report provenance stays dated
to its own inputs. Recurring identity/publication/recipient receipts/retention/
scheduling and production quality/release evidence remain separate work.

## Commit and PR reference

No worker publication. Baseline is `098338e48771ee4c4b705393fa43ba12994b85c2`;
parent branch is `automation/issue-115-worker`. The containing parent commit/PR
will supply the exact review/CI reference. PR #114's accepted head/merge are supplied
baseline facts, not current-head CI evidence.

## Project context updates

Scoped brief/report saved under `docs/reports/`; coordinator/pilot and movie guide
updated; current facts appended to project state. No product policy decision was
invented, so `docs/DECISIONS.md` is unchanged. The unrelated active
`docs/CODEX_TASK.md` remains byte-identical. The dispatcher/supervisor/receipt
protocol, claims/locks/quota/cap, #86/PR #110, production/scoring/research budgets
and all retained issue #113 execution/outbox artifacts are unchanged.

## Task 2 correction report — 30 October 2026

**Specification:** Latest canonical issue #115 supervisor Task 2 and the appended
[scoped brief](2026-10-30-coordinator-export-ingestion-brief.md#task-2--reviewed-filesystem-corrections-30-october-2026).
**Result:** Both focused filesystem corrections implemented; awaiting parent
publication, independent exact corrected-revision review and supported CI.
**Repository revision:** Clean starting head
`e8e86942cea7e88ef44434cebb6a2e52e4bec622`, retained branch
`automation/issue-115-worker`, existing [PR #116](https://github.com/kolorifer/radarr-festival-list/pull/116).
The containing parent-published commit supplies this correction's exact revision;
this worker does not commit, push or update the PR/issue.
**Verification:** Synthetic temporary roots only, macOS / Python 3.9.6.

### Findings reproduced before correction

Two new regression methods ran against unchanged Task 1 production code. The
ordinary synthetic checkout destination was rejected, but the `//` spelling
was accepted (one failed subtest). A separate synthetic probe confirmed all four
fixed files (`investigations.json`, `research_report.json`, `manifest.json`,
`observations.json`) inside the fixture checkout. Original synthetic source bytes
were unchanged. Module `__file__` was patched to this synthetic checkout; no real
exports or actual checkout staging were used.

Injecting EIO on fstat of the newly opened `..` descriptor failed all five repeated
accounting subtests: two descriptors acquired, one closed, one still open each
time. Caller source/parent descriptors remained valid. The regression's cleanup
closed each deliberately reproduced leak, preventing accumulation during baseline
verification. Together the two methods ran with six failing subtests before
correction. No particular host/path rejection in historical issue #113 Task8 is
inferred from either finding.

### What changed and why

`stage_exports` now rejects absolute roots whose anchor is not the single `/`;
this rejects `//` rather than silently interpreting it as another supplied root.
Existing lexical guards remain early checks, supplemented by the same small
descriptor ancestor identity guard for **both source and checkout** before mkdir
or any output write. A no-follow stat of an existing final entry also rejects
identity aliases of either protected root when its parent is outside that tree.
This covers case-insensitive aliases of the root itself as well as descendants.
Unrelated existing entries retain exclusive-mkdir collision handling. Supplied
paths are not resolved through symlinks; no fallback/discovery is introduced.

Ancestor traversal transfers the newly opened descriptor directly to the variable
owned by the existing finally block, before closing the previous ancestor or
calling fstat. Open failure leaves ownership of the old ancestor intact; stat
failure closes the new ancestor. Original errors propagate to library callers;
the public CLI still emits its fixed generic rejection. Caller-owned descriptors
are only duplicated, never closed by this guard.

Stable owner-controlled directories remain a precondition. These corrections do
not claim protection against a malicious same-UID process renaming the hierarchy.
No changes to parent-export, diagnostics vocabulary, dispatcher/receipt protocols,
transport, manifest/outbox ownership or runtime behavior outside this component.

### Files and components changed

| File/component | Task 2 change |
| --- | --- |
| `automation/coordinator_exports.py` | Single-anchor preflight, checkout/source identity exclusion and safe ancestor descriptor ownership. |
| `test_coordinator_exports.py` | Five new regression methods covering rejected destinations, filesystem aliases, repeated descriptor failures/root traversal and fixed public errors. |
| `automation/COORDINATOR.md` | Corrected path and descriptor contract, platform alias behavior and preserved directory-control assumption. |
| `docs/MOVIE-NOTIFICATIONS-GUIDE.md` | Plain-language corrected offline output safeguards. |
| Scoped brief/report and `docs/PROJECT_STATE.md` | Task 2 scope, reproduction, implementation, actual checks and separate review/CI/live gates. |

### Acceptance criteria and evidence

| Criterion | Result | Evidence / limits |
| --- | --- | --- |
| Both baseline findings reproduced synthetically | Passed | `//` creates four fixed files in fixture checkout; newly opened ancestor fstat leaks one descriptor per attempt, cleaned by regression. |
| Checkout and source separation before writes | Passed locally | Ordinary checkout, double-slash source/checkout destinations, injected checkout identity alias and actual case-insensitive source/checkout root/descendant aliases reject before any mkdir. Valid external output succeeds. |
| No weakened no-follow/collision/source protections | Passed locally | Existing alias, symlink, source inode, hardlink, dangling-entry and racing collision tests preserved and passing; source bytes and unrelated marker unchanged. |
| Descriptor cleanup and caller ownership | Passed locally | Five attempts each for first/later ancestor fstat failure, first/later ancestor open failure and successful traversal: acquired/closed counters equal, no owned descriptor left live, caller descriptors usable, original error object preserved, successful traversal reaches filesystem root. |
| Sanitized public preflight failure | Passed locally | Real noncanonical-anchor rejection and injected stat/open EIO expose only fixed `NEEDS_USER` / `invalid_or_unavailable_input`; no mkdir/output. |
| Existing ingestion/report contracts | Passed locally | All coordinator/export/integration regressions retained: original bytes, size/FIFO/race/privacy, manifests v1/v2, freshness/full-case-set, immutable pending recovery and observation-only dedup. |
| Exact corrected-head 3.12/3.13 CI and independent review | Pending parent | Task 1 CI run 41052004267 and owner-supplied 153-test Python 3.12.14 review are historical baseline evidence, not correction verification. |
| Live source integration or activation | Not authorized / not run | No host/source/private-input access or operational replay; Task8's specific rejection remains unknown. |

### Tests run and results

Commands executed on the corrected implementation:

```sh
python3 -m unittest test_coordinator_exports test_coordinator_integration test_coordinator -v
python3 -m unittest -v
PYTHONPYCACHEPREFIX=/private/tmp/issue115-task2-pycache python3 -m py_compile automation/coordinator_exports.py test_coordinator_exports.py
python3 production_scoring.py --check
git diff --check
```

- Coordinator/export/integration suite: **158 tests passed**, 21.752 seconds,
  including all **22 export tests** and five added regression methods. The real
  case-insensitive alias test passed on this Mac; it explicitly skips on a
  filesystem without those aliases. Portable injected identity checks still run
  there. First/later traversal errors and success repeat five times each.
- Full unittest: **789 tests run**, **109 errors**, **2 skipped**, 183.841 seconds,
  exit1. Error categories: 84 missing `requests`, 9 missing `bs4`, 10 unavailable
  `TestCase.enterContext`, 1 unavailable SQLite `sqlite_errorcode`, 2 unavailable
  `sqlite3.SQLITE_BUSY`, and 3 HTTP fixture `RemoteDisconnected` errors. Skips
  require Linux seccomp and Linux x86-64. These are the same error categories and
  counts recorded for Task 1 on this unsupported environment, with five additional
  regression methods now running. This is not a supported-runtime full-suite
  pass. No dependency or unrelated code change was made to suppress failures.
- Compilation and frozen production scoring passed (1,909 candidates, 224
  grandfathered, 163 new, 387 qualified). Diff whitespace checks passed.
- Updated documentation relative file targets were checked; final diff inspection
  verifies only the scoped files changed. `docs/CODEX_TASK.md`, decisions,
  dispatcher/policy/receipt files, scoring/dependencies and retained issue #113
  artifacts were not edited.
- No project virtual environment or supported Python 3.12/3.13 is available on
  PATH; the local command uses `/usr/bin/python3` 3.9.6. No dependencies were
  installed or changed. No prior CI is presented as a corrected-head run.

### Deployment, unresolved gates and project context

No deployment, runtime activation, real/private source read, SSH/seedbox access,
provider/research refresh, notification, Radarr/media operation or network
publication was performed. No operational capability was needed for reproduction
or correction. The existing runner owns commit/push/PR/issue publication on the
retained branch/PR; no replacement PR or new execution owner was created.

Parent publication, independent review of the exact containing corrected commit,
current-head Python 3.12/3.13 CI, merge and any later separately authorized live
integration remain distinct gates. Synthetic success establishes neither source
access nor daily-agent operation. The scoped brief/report were appended and
guide/state facts updated; the unrelated active `docs/CODEX_TASK.md` remains
unchanged. No product decision or unrelated research/production work was changed.
