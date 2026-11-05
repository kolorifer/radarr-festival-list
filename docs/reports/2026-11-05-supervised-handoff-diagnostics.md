# Safe refusal diagnostics and bounded interactive handoff

The owner received a generic refusal before any renewal, second-slot start or
reservation. Its historical cause is unknown; this repair does not label it as
expiry, file mutation, a key problem or an API failure.

## Agreed scope and timing

The existing 300-second supervised account-evidence limit was a local
implementation constant, not a stated owner budget or general transport rule.
The architect selected a 900-second maximum for this existing interactive,
fixed synthetic test so a human can complete the handoff. This changes only
`supervised_credit.validate_evidence`; the generic simulated transport's
300-second grant remains unchanged. The private-file, exact project/model/
pricing/context, observation/expiry/credit-expiry and no-retry checks remain.

Send authority has a separate 60-second maximum measured from successful
hidden input, using captured real wall and monotonic clocks. Delayed session
creation cannot restart that clock. The existing session clips its deadline to
account evidence, credit and model expiry, checks real wall rollback and elapsed
monotonic time, and latches expiry so it cannot revive. The operator permit is
clipped to the same deadline. Existing HTTP authorization checks still recheck
before socket/connect/POST, and the session checks time again after evidence/
ledger verification. No new permit layer or service is introduced.

## Diagnostics

The CLI prints a static allowlisted category plus `enroll`, `reauthorize` or
`run`. Enrollment and renewal state `no API request`; run conservatively states
`request status unconfirmed`. No post-error history reads or phase-tracking
machinery were added. Known expiry and evidence-change refusals are distinct;
unknown errors use an unclassified category. Exception bodies, paths, provider
responses and key material are never echoed, including unexpected exceptions
and invalid parser arguments. Every refusal still says retain state and do not
automatically retry.

## Verification

Focused tests cover exact 900-second freshness, expired/future/credit-bound
facts, 60-second wall and monotonic limits, rollback, delayed session creation,
non-revival, clipped operator permits and retained debit after refusal. Actual
installed `python -m` tests cover expiry, a real fixture metadata change,
unknown secret-like exceptions, invalid arguments and an offline send refusal.
Dummy credential PTY tests and socket/DNS tripwires remain.

The first 41-test local run passed the new handoff tests but the existing
installed renewal test failed on the known intermittent read guard. The new
output correctly identified `category=evidence_changed; action=reauthorize;
no API request`. This is retained evidence, not a silent pass or a reason to
weaken the guard. Exact-head independent review and supported CI are recorded
in the PR. No fresh real account evidence, retained runtime/state/journal,
credential, reservation or API request was created or changed by this repair.
The 3-cent request and 5-cent cumulative limits, consumed first slot, original
history, fixed request and production restrictions remain unchanged.
