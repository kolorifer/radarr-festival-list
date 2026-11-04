# Engineering report: historical diagnostic trusted parent

**Specification:** [completed brief](2026-11-04-historical-parent-brief.md).
**Result:** Dormant implementation complete; independently accepted locally.
**Verification date:** 2026-11-04. Repository-only, synthetic fixtures.

## What changed

HistoricalDiagnosticParent now implements authorize, validate and validate_receipt
for the existing complete_disclosed path. OperatorContext binds an exact evidence
bundle and separate evidence pins supplied by trusted integration. It checks
owner/privacy/account/credential-route/coverage/pricing facts, freshness, selected
history identity, request and local-context hashes, and fixed disclosure policy.
The full rational worst-case debit is durably reserved before the attempted send;
uncertainty consumes the attempt and never refunds or retries.

The fixed HTTP implementation stamps the exact request hash and project onto its
local result. Receipt validation rejects absent or mismatched stamps and reparses
usage. These stamps are trusted local transport correlation, not provider-signed
receipts or independent billing evidence.

## Files and verification

- bound_send.py: executable trusted-parent context validation and receipt checks.
- responses_http.py: local request/project correlation stamps.
- test_historical_parent.py: connected fixture success, refusal and consumed-attempt cases.
- test_responses_transport.py: actual fixed HTTP stamp production with fake connection.
- Existing coordinator repair manifest: updated hashes for those two runtime files.

52 focused tests passed on Python 3.12 and 3.13; the independent reviewer repeated
52 successfully and verified every manifest hash and dependency closure entry.
Tests cover missing/stale/mismatched authority, excessive cost, unknown coverage,
credential-object mismatch, changed disclosure, timeout reservation retention,
receipt mismatch and real-gate refusal. All I/O used recording or fake transports.
Full supported exact-head CI is required by the containing PR before merge; local
focused results do not substitute for that check.

## Deployment and limits

Not deployed. No real credential, provider/account query, source read, external
request, spend, download or production activation occurred. The fixed HTTP gate
still unconditionally refuses real authorization. The parent methods are executable;
trusted integration must supply authentic independently verified external facts.
Hashes prove correspondence, not authenticity. Synthetic TEST-USD price and limit
fixtures establish neither a real price nor approval of a USD 0.50 ceiling.

Before any separately authorized live activation, the operator must establish
owner and privacy authority for the exact selected historical request; the actual
project/model and credential injection route; current pricing and complete input,
cache, output and ancillary coverage; and the selected durable history identity.
No movie/model output can supply that authority. The proposed one-call diagnostic
remains separate from current-case admission, identification or acquisition approval.

## References and context

The containing commit/PR supplies the exact revision and CI evidence. The local
PROJECT_STATE addition records dormant implementation separately from live acceptance;
that large historical file is omitted from publication after approval review rejected
its payload. This focused report carries the published status instead. The completed
brief is archived above; unrelated CODEX_TASK.md, claims and uncertain source
attempt remain unchanged. No new product rule or deployment decision was made.
