# HTTP rejection diagnostics: implementation and verification

Non-200 responses now produce literal codes for 400, 401, 403, 404, 408, 409,
422, 429, 5xx or other. Every category remains a refusal before error headers or
body reads. These labels describe the HTTP observation, not its cause or charge;
earlier generic outcomes remain unknown. Redirects and rate limits never retry.

The new HTTP-specific forward authorization adds an exact predecessor-run pin.
It requires a canonical selected owner authorization, exact old grant/attempt/
terminal/request and root-prefix hashes, unchanged approved disclosure and clocks,
the existing policy and ledger, and one distinct diagnostic identifier. Only
correlation aliases change. The original forward purpose still refuses a renewal
predecessor. The HTTP purpose accepts only the old generic HTTP refusal, never a
new classified refusal, success, parser error or arbitrary purpose.

Retained renewal ancestry is checked with strictly descending slots, original
private authorization hashes and grant/start/attempt timestamps. Past authority
is assessed at recorded historical times; the new authority must be current.
This does not revive a consumed grant. One-child and duplicate-ID protections
apply across purposes and restarts.

Focused tests cover the finite status vocabulary without header/body access,
unchanged content/clocks, lineage pins, expired historical authority versus
current authority, expiry between start and attempt, original-grant refusal,
and installed `-m` authorization/run/restart using invented Keychain and complete
HTTP framing with an independent socket audit tripwire. No real operation ran.

Initial local verification exposed an outdated runtime hash manifest, updated
for the three changed runtime files. A negative test was made independent of
which earlier refusal rejects an incompatible original-purpose grant. Subsequent
local runs retained intermittent `supervised_evidence_changed_read_ctime` fixture
failures; no guard was weakened and no dependencies were changed. Supported CI
and independent exact-head review remain acceptance gates, recorded in the PR.
The first supported CI run found nine subcases in one older transport test still
expecting the generic rejection label. Its assertions now require the exact
finite labels while retaining one-request/no-body checks and adding an explicit
no-header-read assertion. Runtime code was unchanged by this test correction;
the initial CI failure remains recorded and corrected-head CI is required.

No repository-wide state/task documents were changed: their unrelated work is
preserved. No deployment, live access, spending, output, notification or production
activation is included in this repository change.
