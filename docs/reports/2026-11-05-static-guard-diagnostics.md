# Static guard diagnostics — 2026-11-05

## Change

The authorization catch previously collapsed every caught refusal and exception
into one generic reason. It now preserves only exact Refusal instances whose
single reason is already in the finite safe-reason allowlist. Unknown codes,
extra arguments and subclasses remain generic. Other caught OSError, TypeError,
KeyError and ValueError instances map to four literal class codes. No exception
message, path, metadata value or arbitrary field name is returned.

The two evidence checks now distinguish per-read device/inode/size/mtime/ctime
from selected bytes/device/inode/size/mtime. A fixed ordering selects the first
differing component; this reports a predicate, not its external cause. Checks use
only the same already-read bytes/stat results. Persistent selection still omits
ctime, while the per-read race check still includes it. Exact selection tuple
equality is retained, including malformed length/type fallback refusal.

Every failed branch still refuses. Token mutation remains after successful
validation only. Existing reason/category/journal machinery carries diagnostics;
no new journal fields, reads, retries, authority or framework were added.

## Validation

Six injected tests cover all compared components, malformed selection equality,
allowlisted/unknown/subclassed refusals, static exception classes, token ordering,
full-debit preservation and non-replay, and a genuine installed fixture command
with a synthetic I/O exception containing leak sentinels. Existing expiry tests
now assert the more specific reasons without changing their refusal assertions.

Local focused run: 58 tests, 56 passed and two failed. Both failures were
identified by the new reason supervised_evidence_changed_read_ctime:

- The existing installed unknown-exception fixture refused before the expected
  terminal prompt.
- The existing reauthorization expiry fixture refused before its expected stale
  evidence check.

These are retained failures, not successful reproduction claims about older
runs. They establish that the compared per-read ctime differed in these two
runs. The external cause and historical causes remain unknown. No rerun to erase
them or guard relaxation occurred. Supported exact-head CI and independent
review remain required; their results are recorded in the completion checkpoint.
No full local suite or dependency repair was performed for this change.

## Scope

Only supervised_authorization.py and supervised_credit.py change at runtime;
the selected runtime manifest is refreshed. Existing operational artifacts and
request budgets are untouched. No actual state/evidence/runtime, provider,
account, credential, source, service, new slot or live handoff operation occurred.
This diagnostic change does not implement separately authorized standing-credit
preparation. The unrelated assigned task/project-state record remains untouched;
this report is the scoped implementation record.
