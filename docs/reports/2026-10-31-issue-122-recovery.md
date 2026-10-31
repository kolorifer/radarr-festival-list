# Engineering report: issue122 Task3 isolated package and same-cycle recovery

**Specification:** [saved final Task3 brief](2026-10-31-issue-122-recovery-brief.md),
owner [Task3](https://github.com/kolorifer/radarr-festival-list/issues/122#issuecomment-6543198432),
[additional authorization](https://github.com/kolorifer/radarr-festival-list/issues/122#issuecomment-6543142163)
and [live failure review](https://github.com/kolorifer/radarr-festival-list/issues/122#issuecomment-6543043459).
**Result:** Scoped implementation/tests/docs completed for independent review; actual deployment/recovery and
recipient/archive acceptance remain supervisor gates.
**Repository revision:** Clean starting `automation/issue-122-worker` at
`bd789435118e29806766e2e4c72f3996edaa1e07`; parent alone supplies the containing
commit/new PR. Supplied PR123 merge and launcher/deployment identities were not
re-inspected operationally.
**Verification date:** 2026-10-31, native macOS Python3.9.6, synthetic fixtures only.

## What changed

The selective package now includes both unchanged function-local offline
validator dependencies, identity_research_store.py and torrent_research_evidence.py.
The manifest has23 files including the new fixed recovery module. The20-file
closure claim in Task1/Task2 was false; historical results are preserved with
explicit errata. The reachable offline chain and unreachable producer/extractor
imports are documented. No dependency installation or producer/provider/database
invocation is needed for this route.

A single new unedited authenticated issue-owner recovery command selects the SAME
retained phase/partial-1 cycle. It binds the exact original pin/comment/request,
original claim/reservation/intent/seal and original collecting checkpoint to a
NEW explicitly selected reviewed/deployed code identity and all23 exact hashes.
The original20 code pins stay intact. Only the documented pre-report boundary
is admitted. A bounded fixed-role read-only inventory checks private files and
directories, no-follow/spelling/ownership/modes/ACL/identity/stability/size, original
transport-vs-intake bytes and the saved independent checkpoint. No selected
arbitrary filesystem paths or operational command/script executor is added.

Authentic recover/continue commands are consumed in a separate bounded private
scheduling ledger before immutable-input fetch, so failed pins/code/boundaries
and repeated commands are quiet without changing original adapter/evidence.
This ledger is not authorization. Separate canonical recovery selection,
authorization and exact original/checkpoint/partial-staging copies are fsynced
before a recovery binding is committed and before accepted owner/cycle effects.
Conflicts retain originals; unanchored interrupted authorization is not adopted.

Recovery uses the accepted owner.prepare with the original request/clock and
collect(resume=True). It NEVER invokes acquisition, credentials, reserve, reseal,
source-path reread, refresh or fuller movie recovery. The honest resumed report
uses saved independent findings and interrupted/unavailable movie input. Original
intake, seal, transport and generation clocks survive disposable-stage cleanup.

Accepted handoff, sole PUT, immutable publication readback, durable observation,
receipt import and archive are reused. A fresh explicit matching continuation can
finish safe interrupted preparation or already-exposed exact handoff output;
uncertain publication permits readback only. All continuation/ack commands and
ack selections additionally bind the exact recovery pin/new code authorization.
Final parent archive evidence links original selection, attempt and recovery.
Genuine recipient authentication remains **owner-selected acknowledgement after
actual designated-chat ingestion**, not a JSON issuer, sender/hash proof or
engineering terminal receipt. No automatic recipient is introduced.

Issue122 alone now has exact engineering cap3; Task3 is admitted once and Task4
is refused. General cap8, issue119 history, existing locks/keeper/quota/isolation,
code/operations publication, DONE/closed stop rules and ordinary engineering
selection remain. Installing code activates nothing.

## Files and components changed

| Component | Purpose |
| --- | --- |
| automation/coordinator_runtime.py | Complete manifest; fixed recovery/continuation selection; explicit code transition; bound ack/archive integration |
| automation/coordinator_recovery.py | Fixed retained-boundary validation, separate durable authorization/evidence, accepted local continuation only |
| automation/github_worker.py | Only issue122's two thresholds and limit message change2 to3 |
| test_coordinator_runtime.py | Admit3, consumed3 inert, refuse4; preserve issue119/general8 |
| test_coordinator_recovery.py | Pure synthetic fixtures, ordinary dispatch, isolation/negative imports, recovery/receipt/archive, interruption/tamper/clock/quiet tests |
| automation/COORDINATOR_RUNTIME.md |23-file install, exact R/P/A schemas, fixed evidence identities, allowed continuation and honest ingestion/freshness contract |
| Task1/Task2 saved briefs/reports | Append historical closure/budget errata; retain original results/history |
| Task3 saved brief/report; docs/PROJECT_STATE.md | Current scope, implementation/validation/live gate handoff |

## Acceptance criteria and evidence

| Criterion | Evidence / practical limit |
| --- | --- |
| Complete installed closure | Fresh `-I -B -S` subprocesses copy only23 runtime files; no checkout/PYTHONPATH/site/test-module fallback. Each omitted module independently produces ModuleNotFoundError on nonempty torrent_evidence; complete bundle validates and stages exact original bytes |
| Same retained cycle | Real ordinary parent poll from synthetic preparation_uncertain/collecting checkpoint, separate new immutable owner selection; original selection/start/request/clock/claim/intake/seal retained |
| Authentication and guarded boundary | Authentic comment re-fetch, immutable commit/tree/blob/SHA256, exact clean code hashes; altered pins/checkpoint/state/claim/seal/independent/modes/symlink/output/receipt/clock/author/edited commands refuse |
| No extra opportunity | Recovery stubs acquisition/credentials/reserve/reseal/reader/provider/network/SQLite to fail; claim/acquisition/PUT counters stay1/1/1 |
| Accepted honest resume | Saved independent engineering findings remain available; movie collection interrupted/unavailable; separate offline reader reports incompatible original movie pair |
| Publication/recipient/archive | Synthetic exact readback, separate selected recipient after actual fake payload read, accepted receipt/archive; real designated-chat ingestion is NOT verified by these tests |
| Failure/idle progress | Safe preparation/exposed-handoff interruptions continue explicitly; publication/import/archive resume through existing rules; unexposed consumed handoff refuses; subsequent polling quiet and another issue's real discovery proceeds |
| Guard/history preservation | Issue122 cap3/refusal4/consumed3; issue119/general8; accepted owner/cycle/source/transport/storage modules and unrelated task/configuration/histories unchanged |
| Final supported CI/deployment | Still required from parent/supervisor on exact published correction; no child live action |

## Tests run and results

Final frozen-source focused command:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest test_github_worker test_supervisor_policy test_supervisor_communication test_operations_publication test_coordinator_storage test_coordinator_owner test_coordinator_runtime test_coordinator_recovery test_coordinator_cycles test_coordinator_exports test_coordinator_integration test_coordinator -v
```

**479 tests passed** in631.478s, including all44 runtime/transport tests and all9
new recovery tests. The latter include fresh installed-only `-I -B -S`
subprocesses, both missing-module negatives, nonempty torrent_evidence, exact-byte
reader staging, same-checkpoint recovery/publication/separate recipient/archive,
type-sensitive pins, tamper refusals, forbidden edges, later wall clock,
interruptions, consumed-command quietness and real other-issue discovery.

The ONE required final repository command:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v
```

**966 tests run in680.329s:109 errors,2 skips,zero assertion failures. This is
NOT a passing full-suite result.** All44 runtime/transport and9 recovery tests
passed again. Exact error categories match the supplied Task2 baseline:
84 missing requests;9 missing bs4;10 unavailable TestCase.enterContext uses;
3 unavailable SQLite APIs (one sqlite_errorcode, two SQLITE_BUSY); and3 existing
HTTP-fixture RemoteDisconnected errors. Two existing Linux/seccomp cases skip on
this native Mac. Unrelated dependencies/APIs were not repaired. Only ONE full
suite was executed; focused and full suites did not overlap. All25 frozen source
hashes were rechecked unchanged after this full run too.

All23 runtime files and both changed test files compile and parse with native
Python3.9 grammar. Their25 SHA256s were frozen before final validation and
rechecked unchanged after the focused run. Frozen inventory SHA256:
`08f08014dcb867674555fe6e53e5bb78119ad69a58f88ecd1176a9322b774962`.
`python3 -B production_scoring.py --check` passed:1909 candidates/387 qualified
(224 grandfathered,163 new). Local documentation links and diff/preservation
checks pass. No runtime/test source was edited during final validation.

No project .venv/venv exists in this checkout; these commands use available
Python3.9.6. No dependencies changed or were installed, so no new pip check is
required. Parent-published exact-head supported Python3.12/3.13 CI and independent
review remain required before bounded deployment; they were not run by this child.

Development results are distinct from final validation: the initial eight-test
recovery run had7 passes/one test-fixture serialization error (233.792s). Isolated
harness corrections addressed byte serialization, ancestor descriptor audit
allowance and a missing deepcopy import. A subsequent complete isolated test
passed in17.646s, then a nine-test development run passed in250.257s
before final type-sensitive binding additions. No runtime missing-module fallback was introduced. These are
not substitutes for the final frozen-source focused/full results above.

## Deployment result

**Not deployed or operated by this child.** No real home/key/private root/export/
source/journal/server access, live SSH, refresh/provider/service/media/Radarr/
notification/download action, permission/admin change, schedules/plist/watch,
Work, daemon/subagent/worker/runner launch or Git/issue publication occurred.
No dependency was installed or changed. The supplied one-source-read opportunity
remains consumed; no live recovery was attempted.

The [runbook](../../automation/COORDINATOR_RUNTIME.md) is the bounded supervisor
handoff. Exact supported CI/review, selective installation, owner-selected SAME
retained-cycle recovery, actual immutable publication, genuine distinct chat
ingestion/owner-selected acknowledgement and verified archive are already
authorized supervisor work. They require no generic new approval and grant no
engineering executor or Task4. Each live gate must be verified independently.

## Unexpected findings

Function-local imports made empty/import-only repository smoke tests inadequate.
The isolated positive test therefore exercises both nonempty torrent evidence and
the whole finite recovery path, with deliberate missing-file negatives. New
fixtures are static and build no research database or producer output. The
accepted resume contract deliberately yields less movie information than a fresh
reader; completing the closure does not authorize rereading interrupted inputs.

## Unresolved issues and risks

A crash after recovery evidence installation but before its parent binding leaves
unanchored evidence and stops. An unbound accepted collection checkpoint or a
consumed core handoff without exact durable parent output can also remain
unfinishable; no reset, second handoff or broader core recovery is provided.
These refusals preserve accepted safety boundaries; the supplied original failure
has neither a handoff nor a collection checkpoint and is the implemented gate.

Local dependency/API failures cannot establish passing supported CI. Genuine
publication/readback, actual distinct chat ingestion and archival remain unrun
live acceptance gates. Source freshness is unchanged: original timestamps and
incompatible/stale evidence remain honest; successful partial reporting proves
no full movie coverage. No recurrence or automatic additional execution follows.

## Commit and PR reference

Parent alone commits/pushes/creates the new PR and posts terminal reporting.
This report's containing parent revision provides the exact correction reference.
No child publication or merge was performed.

## Project context updates

Task3 brief/report and project state record this correction separately from
historical Task1/Task2. The runbook withdraws the false20-file closure claim.
Unrelated active CODEX_TASK.md, decisions, notification guide, #86/PR110,
production/research configuration, schedules/services/watch, accepted core modules
and all claims/history remain untouched. Product/live acceptance is not inferred
from implementation or synthetic mechanics.
