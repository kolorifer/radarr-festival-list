# Engineering report: qualified historical manual Nano diagnostic

**Specification:** [agreed brief](2026-11-06-historical-nano-brief.md).
**Result:** Implemented for independent review and exact-head CI; no live invocation or deployment.
**Verification date:** 2026-11-06.

## What changed

The supervised Nano command previously accepted only its fixed synthetic body. A separate `authorize-historical` action now reads an explicitly selected private historical input and shows its minimized request plus a canonical grant in the owner's terminal. Confirmation requires the full grant SHA-256. The grant binds the exact body, project, endpoint, selected case and input hash, retention policy and three-cent maximum debit. The synthetic standing grant alone cannot authorize this disclosure.

`run-historical` consumes that selected grant once through the existing interactive key prompt, locks, fixed HTTP transport, response parser, ephemeral authority and shared credit ledger. The full three-cent reservation remains after success or uncertainty. Exact source bytes, policy, project, fresh evidence and the grant are revalidated before sending. Ordinary synthetic commands refuse a pending historical selection. Existing synthetic behavior and legacy records remain compatible.

The local completion record contains a transport-receipt-bound historical report. It accepts only unresolved/blocked results with no alternative identities. Historical observations, source clocks and qualifications remain visible; currentness and decisions remain unknown, captured bytes are false, and identity/acquisition approval is false. No notification is sent. A transport correlation receipt is not provider-signed billing or source-authenticity proof.

## Files and components

- `historical_nano.py`: private proposal, exact consent, verification and qualified report.
- `supervised_credit.py` / `supervised_authorization.py`: selected historical attempt in the existing journal, CLI and authority.
- `bound_send.py`: distinct historical Nano parent mode; fixed synthetic mode retains its exact-body guard.
- `manual_offline.py`: reuse pure typed projection/request functions without eager coordinator imports.
- `installation.py` and runtime manifest: 41-file installed closure.
- `test_historical_nano.py`: invented fixtures, real framing/parser and installed command tests.

## Acceptance and validation

The focused tests exercise preservation of an invented existing eighteen-cent ledger, exact consent and project/policy/ceiling/source binding, declined consent, insufficient credit, expiry, wrong route, changed private input, uncertain response, replay and restart refusal. An installed-only `python -m ai_movie_investigator.supervised_credit` PTY test authorizes the exact grant and processes one framed response into the qualified report; an independent audit hook rejects real socket/DNS activity. No request, authority, parser or receipt validator is replaced in that installed test. Only socket/TLS fixture I/O is substituted.

The focused local run executed 50 tests: 49 passed and one stopped at `supervised_evidence_changed_read_ctime` before consent validation. The independent seven-test run passed six, including the installed command, and one stopped at the same guard before its intended uncertain-response check. Earlier targeted runs passed the six behavioral tests and the installed test separately; these do not erase the later refusals. No failed run was repeated merely to obtain green.

Full supported Python 3.12/3.13 CI and independent exact-change review are required before merge. Results and exact public head are recorded in the containing PR/checkpoint, not asserted in advance here.

## Findings and limitations

Independent review identified and corrected two initial gaps: source-export hashes were an unsuitable replay key, and confirmation of only the request body omitted the project and cost ceiling. Replay protection now conservatively blocks another grant for the same asserted case ID across versions, export hashes and construction times. It does not establish that differently labeled case IDs are distinct occurrences; historical source authenticity remains unverified.

Early local test runs included preserved fail-closed evidence ctime refusals and corrected fixture/binding failures. No race guard was weakened and no state was repaired or replayed. A local full-suite environment issue remains outside this change; supported CI supplies the full suite.

The installed closure supports the supervised historical route. The standalone `manual_offline` CLI still depends on coordinator modules and is not an installed entry point. Only its pure projection/request functions are reused here. The real selected disclosure has not been inspected or approved by this implementation work.

## Deployment and project context

Not deployed. No actual ledger, account evidence, key, retained input, provider, seedbox or production state was accessed or changed. No source capture adapter or new-case admission change was added. Prior reservations, pending decisions and the private transition preview remain outside the change. This scoped brief/report records the task; unrelated task and project-state documents are preserved. The containing commit/PR is the implementation reference; the architect reviews the merged result before any owner disclosure decision.
