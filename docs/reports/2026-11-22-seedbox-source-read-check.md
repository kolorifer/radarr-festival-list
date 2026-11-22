# One selected source read check

The worker stays paused. The operator verifies one eligible collector event
observed after the pause, with retained listing evidence and an existing actor
job for the same exact release. Verify the selected collector version, event
and delivery time against the retained collector record. Verify the actor's
stored original observation and job version independently. Confirm the selected
case and release differ from the interrupted case. Establish the expected IMDb
assertion from existing evidence without treating it as a film match. A listing
evidence record by itself does not establish the actor binding or an IMDb assertion.

Pass the exact bytes of an owner-reviewed `seedbox_source_read_selection_v1`
JSON on stdin. The selection contains the configuration hash, excluded case ID,
pause and collector observation times, selection and expiry times, full selected
collector material and version, retained actor observer envelope and actor job
version, and the expected listing IMDb assertion. Use the existing normalized
observer envelope, excluding credentials and any private request URLs. The
selection expires within five minutes of selection. The operator vouches for the
origin of the records and their current eligibility. The program verifies their
matching metadata and case/version digests and does not connect to SQLite.

```text
PYTHON -I -B CODE/automation/seedbox_bootstrap.py CODE/seedbox-runtime.json MANIFEST_SHA source-read-check CONFIG_PATH CONFIG_SHA SELECTION_SHA
```

Execute the reviewed selection once under the existing worker's interpreter and
confinement. Use an external wall-clock limit. Capture only the finite JSON
result. The command makes one exact listing GET, one exact TMDb IMDb lookup if
the heading and single pinned IMDb assertion match, and one exact TMDb details
GET only if the lookup yields a unique movie. It verifies the details response
against both IDs. An authenticated empty lookup records no movie mapping at
inspection time. Any refusal stops the check. A timeout consumes the selected
opportunity. The operator enforces one invocation because the diagnostic has
no durable ledger. Its result does not authorize retries or any case action.

The diagnostic uses read-only Landlock file rights with TCP connect limited to
port 443. The reused HTTP adapter enforces exact hosts and routes, no redirects,
credential separation, deadlines and response bounds. No source body or
identifier is emitted. No model, sender, queue entry, report, or evidence bundle
is created. Existing pauses, attempts and permissions remain in force.

A successful check establishes current authenticated reads for the selected
release. It leaves the original retention path untested. A historical diagnosis
requires retained evidence that distinguishes the original marker, network and
retention stages. Testing present-day production retention would separately
require an authorized isolated write target, the actual production retention
confinement and quota, and independent checks of directory creation, exclusive
file writes, fsync, manifest and readback. Use invented bytes and a separate
journal fixture to test journal append semantics. Neither test is part of this
read check or a replay of the interrupted case.
