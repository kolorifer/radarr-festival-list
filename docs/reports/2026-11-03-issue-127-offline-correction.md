# Issue 127: synthetic pilot correction, 2026-11-03

The correction started from the retained Task 8 snapshot
`66925204ee394f632ed6ef1991f034c729127f2aec1fe91bb91c537b536168df`.
Invented-data tests on both supported Python versions reproduced the three
reviewed defects and a nonempty positive control before changes.

Admission now checks the original eligible collector route and verifies the
current occurrence and exact oldest due native ledger material under the
existing control/history/ledger locks before appending the pilot claim. The
atomic selected lease retains its own later revalidation.

Because the source row has no approved typed runtime or edition facts, these
claims are withheld from its model-facing projection, and invented citations
to them are refused. No source text or raw NFO is sent. This is a conservative
withholding rule, not a real runtime or edition identification.

The fixture-only account reserves before count and generation, binds distinct
local operation IDs and the canonical exact body, and settles only observations
from the specific enrolled fake issuer matching the actual operation, response,
IDs, usage and price bounds. Changed, foreign, malformed or unknown observations
retain the appropriate hold; interrupted effects are not retried or refunded.
The fake issuer is not real-provider authentication or permission to send.

Focused invented-data regression tests exercise positive and negative admission,
withheld and forged claims, post-effect fresh IDs, substituted issuers, changed
wire and response bytes, currentness and ledger contention. The separate current
runtime manifest pins the installed-only closure. Historical Task 8 records and
the original retained snapshot remain unchanged.

One earlier Python 3.12 full-suite attempt against an intermediate candidate ran
1,487 tests with 35 failures, 346 errors and two skips under a sandbox denying
network and protected filesystem access; it is not a green full run. The
corresponding intermediate Python 3.13 run was interrupted to address review
findings. Supported exact-head CI and independent review remain the acceptance
gates; no result should be inferred from this report alone.

No real investigator, model, provider, account, spend, acquisition, deployment,
service or schedule was activated. Actual producer and live verifier facts remain
unverified. Identity, edition, scoring and download approval remain separate.
