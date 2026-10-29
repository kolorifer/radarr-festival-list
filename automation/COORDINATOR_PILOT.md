# Coordinator offline rehearsal and later private pilot

Issue #113 Task 1 is code only. This runbook authorizes no operational read,
publication, deployment or activation. All runtime/source/destination paths below
are configuration examples, not discovered installed facts. Do not use this code
task's network capability to acquire private inputs or inspect hosts.

## Reproducible synthetic rehearsal

From the checkout, using the supported project Python when available:

```sh
python3 -m unittest test_coordinator_integration test_coordinator -v
python3 - <<'PY'
from pathlib import Path
import tempfile
from automation import coordinator_outbox as outbox
from automation.coordinator_sources import observations
from automation.coordinator_parent import export_parent
from automation.coordinator_integration import public_projection, recover
from test_coordinator_integration import synthetic_stage, parent_fixture, NOW
root = Path(tempfile.mkdtemp(prefix='coordinator-synthetic-', dir='/private/tmp')).resolve()
staged = root / 'staged'
staged.mkdir(mode=0o700)
synthetic_stage(staged)
parent_fixture(root / 'synthetic-worker')
parent = export_parent(root / 'synthetic-worker', 113, [1], NOW)
assert parent['writer_liveness'] == 'unknown'
state = root / 'outbox.json'
first = outbox.poll(state, lambda: observations(staged, 'manifest.json', NOW))
again = outbox.poll(state, lambda: observations(staged, 'manifest.json', NOW + 1))
assert first['changed'] and not again['changed']
assert first['pending_outbox'] == again['pending_outbox']
item = first['pending_outbox'][0]
assert recover(state, item['id'], root / 'synthetic-report.json') == item['sha256']
print(public_projection(first))
print(public_projection(again))
PY
```

The fixture clock is deliberately fixed (`NOW`), and the report uses the actual
research-report writer against an in-memory synthetic store. No provider calls,
worker launch, permanent claims or operational databases are involved. The
rehearsal leaves only new synthetic files under an OS temporary directory.
The CLI's default clock is real time; do not retimestamp these fixtures and call
them real observations. The unit suite also exercises process restart, concurrent
independent interpreters and parent receipt reconciliation with synthetic bytes.

## Before authorizing a real-input pilot

The original-account supervisor independently reviews the exact parent-published
revision and supported 3.12/3.13 CI, resolves concrete findings, and merges the
accepted integration. Then prepare a NEW **operations_only** task with actual
verified exact grants. Private-input/private-artifact capabilities suppress public
code publication; the pilot must leave its exact public checkout unchanged.
No source, path, repository or permission is inferred from this runbook.

The task must establish all of these facts before dependent operations:

1. Inspect the currently installed existing macOS dispatcher/launcher revision,
   actual installed command and discovery mode. Repository reference invocation
   is `python3 automation/github_worker.py --once` with no `--issue`, plus its
   installed `--repo`/`--github-repo` options. This is a reference to compare, **not
   an instruction to launch it during the pilot**. Record observed installed
   revision/arguments, not just this checkout's revision or a historical heartbeat.
   Verify the existing single engineering writer, retained checkout, lock ownership,
   permanent claims and quota/eight-consumed-execution protections remain intact.
2. Select one accountable coordinator state/publication owner. Supply exact new
   owner-only state/output directories outside any tracked checkout; no discovery
   of home/private state. Establish which repository owns the explicitly allowed
   parent-state root and select only this control issue and exact task numbers.
   Authorize journal reads separately from coordinator writes. Do not acquire
   dispatcher locks, traverse other issues, launch/replay tasks or infer liveness
   from heartbeat/PID/RUNNING. Independent process-to-inherited-lock evidence would
   require separately verified trusted observations; this exporter leaves it unknown.
3. Specify every staged source's exact path, immutable content SHA256 (and private
   input commit/blob where the parent requires it), known producing revision,
   source generation/observation time, collection time and freshness limit. Use
   actual values, not wildcard/directory grants. A later fresh source changes its
   immutable private-input identity and requires the corresponding exact grant.
4. Supply a complete investigations snapshot less than one hour old and compatible
   research report less than 48 hours old. Both allow at most five minutes future
   skew. Compare the complete known case-ID set, every base field, occurrence and
   research versions, coverage, eligible subset and proposal dates/currentness.
   Preserve upstream incomplete coverage. Do not substitute `changed_cases` or the
   eligible subset for the complete set.
5. Use an already fresh coherent pair, or, **only under an explicit separate exact
   host grant**, the existing confined handoff alone to obtain `/v1/investigations`
   and pair it with a still-compatible report. Never run the normal research scan,
   research worker, report regeneration against its DB, or collector DB reads to
   refresh this read-only input. Never retimestamp old evidence. Require zero new
   provider requests and preserve research ledgers/budgets/digest ownership.
   If no coherent fresh pair exists, report that source unavailable/partial and
   stop short of claiming a full movie review; obtain the missing evidence through
   the existing authorized owner, not an invented acquisition path.
6. Supply the exact permitted private artifact repository/path and CAS
   `expected_blob`, plus independent exact terminal diagnostic grant when desired.
   Bind `--intent` to the pilot's repository/issue/task and destination. Existing
   parent publication is the only engineering-task writer. Preexisting public
   checkout and sources stay unchanged; new private coordinator state/output and
   one exact publication are the only new writes allowed by the later task.
7. Establish who can retrieve the exact artifact and parent receipt privately and
   authenticate their provenance. Separate private publication readback, receipt
   availability, parent public-result posting, recipient delivery, supervisor
   review and product acceptance. No recipient interface is configured by this
   implementation; the supervisor must actually inspect the report and record
   its own receipt outside this importer before claiming recipient receipt.

No seedbox/SSH, Radarr, Telegram, trackers, media mutation, new provider request,
paid API, new daemon/schedule or second execution/sending owner is implied.
A later task must expressly grant any exact source-system operation it needs.

## Pilot execution and offline reconciliation contract

These CLI shapes show configuration, not verified operational paths. Replace
placeholders only with exact values authorized by that later task:

```text
python -m automation.coordinator_integration parent-export
  --root <authorized-worker-state-root> --issue 113 --task <selected-task>
  --output <new-staged-parent-status-file>
python -m automation.coordinator_integration report
  --root <authorized-staged-root> --manifest manifest.json
  --state <new-owner-only-state-file> --intent <explicit-intent-file>
python -m automation.coordinator_integration pending --state <state-file>
python -m automation.coordinator_integration recover
  --state <state-file> --id <reported-id> --output <authorized-staged-artifact>
python -m automation.coordinator_integration publication-uncertain
  --state <state-file> --id <reported-id>
```

`report` prepares and persists; `recover` writes exactly the bytes identified by
the pending report hash. They do not publish. The publication owner should
persist the uncertain boundary before its one authorized publication attempt.
For a numbered operations-only pilot, preparation happens within the existing
parent's one task: the child stages the artifact and the parent performs its
existing exact CAS/write/readback/receipt path. The coordinator does not publish,
create a follow-up task, retry the parent, or reuse a consumed task number.

After parent completion, a separately authorized readback can reconcile offline:

```text
python -m automation.coordinator_integration receipt
  --state <state-file> --id <reported-id>
  --worker-root <authenticated-parent-state-root> --issue 113 --task <pilot-task>
  --trusted-receipt-sha256 <independently-verified-parent-terminal-hash>
  --artifact-root <authorized-readback-staging-root> --artifact-file <exact-alias>
```

The caller must authenticate the source of `terminal-N.json`; a copied hash and
structurally valid JSON from a child are not proof. Match actual parent identity,
`verification.artifact_readback: true`, the one `artifacts` reference, exact
repository/path, blob and report SHA256, and byte-for-byte independently staged
artifact content. The receipt pin binds the exact supplied receipt bytes.
Parent `delivery-N.json` describes receipt/public-result availability separately;
a successful public comment POST is not recipient readback. No hash pin gives
network or execution authority. Invalid/missing evidence leaves pending/uncertain
publication unchanged; do not resend after ambiguous writes. A new reconciliation
task, if needed, requires exact read-only evidence grants and never replays work.

Retrieve and inspect the report itself, not only the hash/READY result. Record
source times, coverage and limitations; confirm useful engineering facts remain
when sources fail. Repeat an unchanged poll and restart with the same state:
`changed: false`, identical pending payload/ID/hash, one durable entry and no new
task/publication attempt. Keep report/state/source bytes for recovery. Verified
private publication still leaves recipient delivery `not_configured` here.

## Production quality/release evidence and recurring operation gaps

There is no complete passive production quality/delivery export yet. Do not use
#86's Audience50/Recognition50 experiment, synthetic quality fixtures,
`pending_actions.py`, or `retry_telegram.py` as a complete production ledger.
A follow-on producer needs a bounded read-only allowlist of already-computed
exact movie/release identifiers; rating and count with source/update/measurement
provenance and unknowns; production design/version and recognition/completeness
provenance; notification type/intended route, stable material ID, known outcome
and observation/attempt times; explicit pending/uncertain/confirmed distinctions;
and identity/acquisition decisions only where authoritative evidence exists.
Do not force unknown approvals to booleans, compute new scores, look up providers,
expose tracker URLs/tokens or add another sender. Preserve the actor's existing
identity digest and all research budgets. Such a producer needs its own scope.

Daily cycles must be owned by an inspected existing runtime/publication owner,
not consume one of eight numbered Codex executions per cycle or create another
engineering executor. This code task supplies no recurring owner/activation.
Before recurrence, inspect that owner's source/export access, single-writer state,
publication/recipient-receipt interface, retention/backpressure handling and
existing digest schedule. The outbox stops after 20 retained reports or its byte
bound; without a recipient acknowledgement/archival workflow, indefinite daily
operation is not ready. Do not silently drop published-but-undelivered entries.
Observe an actual scheduled wakeup, report preparation, private artifact readback
and recipient receipt before claiming recurring operation. Written configuration,
a heartbeat or historical RUNNING is insufficient. The next concrete action after
code review/CI/merge is the separately scoped one-report read-only pilot, not
scheduler installation or broad activation.
