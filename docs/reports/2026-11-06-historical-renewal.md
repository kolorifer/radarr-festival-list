# Engineering report: exact forward-diagnostic renewal

**Specification:** [agreed brief](2026-11-06-historical-renewal-brief.md).
**Result:** Code-only renewal implemented; independent review and exact-head CI gates apply.
**Verification date:** 2026-11-06.

## Behavior

`authorize-historical-renewal` consumes one explicitly selected canonical private authorization and its SHA-256. It creates a new attempt grant in the existing root journal, without a key lookup or API request. Subsequent `run-historical-keychain` uses the normal locked, one-shot path and shared credit ledger. The original attempt is never reset, refunded, replayed or reinterpreted.

The single supported purpose is `observe_current_response_with_finite_diagnostics`. Its prior attempt must be an original historical grant with one retained `response_parsing` diagnostic carrying the old composite `responses_not_completed` reason and exactly reserved/attempted records, with no receipt/completion. The new response observes only the forward path. It cannot classify the discarded earlier response.

The private authorization binds an explicit diagnostic ID, owner reference, exact current root prefix, prior slot/grant/attempt/terminal/request hashes, project, input hash, resulting request hash, existing policy, three-cent maximum debit, one request and a bounded validity window. The same asserted case ID, case version, input bytes, source facts and original assessment/source clocks are preserved. Only protocol correlation aliases change, derived from the explicit diagnostic ID, not a refreshed timestamp. At most one renewal of that exact prior attempt is allowed, even with another ID or rewritten authorization.

The authorization and prior pins are checked under the existing root lock before allocation, before credential retrieval, and again by the send authority. Altered input or authorization refuses. Interruptions remain consumed; prior ledger bytes and unknown outcomes remain retained. Ordinary synthetic authority and the original initial-disclosure path cannot substitute for this explicit renewal.

## Authorization provenance

The file is a trusted local operator selection representing the already delegated owner instruction, not cryptographic authentication of a human statement. Its owner reference and exact pins must be established by the parent. Renewal grants use a distinct `authorization_binding` field, never the original `owner_confirmation` field produced by a typed terminal challenge. Reports explicitly identify `selected_private_owner_authorization`, its SHA, and `direct_interactive_confirmation=false`.

No actual authorization file was constructed by this implementation. Successful new reports retain `prior_cause=unknown` and `prior_outcome_reinterpreted=false`, alongside all existing historical currentness/capture/approval limitations. Reports remain private and unsent.

## Components and verification

- `historical_nano.py`: exact renewal body, authorization, prior-history checks, allocation and report provenance.
- `supervised_credit.py` / `supervised_authorization.py`: CLI and the same preflight/locked send boundary.
- Existing 42-file runtime manifest: updated hashes, no new runtime framework or dependency.
- `test_historical_renewal.py`: invented legacy failure, exact disclosure/clocks, altered pins/purpose/policy/expiry, replay with a new ID, changed authorization before and during credential retrieval, and installed noninteractive authorization → framed response → receipt/report → restart refusal. Real network is independently blocked.

Initial local renewal run: four of five tests passed; the remaining test stopped in fixture setup at the existing evidence ctime guard before its intended old-refusal assertion. That failure is preserved. Independent initial five-test run passed all five. The provenance finding was corrected before final acceptance; the focused run after the provenance correction passed all 29 tests in 19.672 seconds. A subsequent small validation correction rejects an explicitly unknown owner reference after normalization; its negative case is checked separately. Final CI results are recorded with the containing PR and private checkpoint. A default system Python compile command was refused by its cache permissions; validation uses the known supported Python runtime instead. No cache repair or guard relaxation occurred.

## Deployment and limits

Not deployed or operationally adopted. No actual Keychain item, credential, provider, source, input, evidence, ledger or grant was read/changed. The previously prepared accepted Keychain runtime remains separate and unchanged. This narrow renewal does not grant arbitrary future diagnostics: another purpose/prior outcome is outside its finite acceptance contract. Existing promotional credit accounting remains unchanged, and no new financial approval is requested. The containing commit/PR supplies the code reference; scoped brief/report preserve the task while unrelated task documents remain unchanged.

## Connected bounded Keychain correction

Before publication of this change, main reported that the prior accepted availability probe returned a generic unavailable result under restricted execution and remained blocked in a host-access diagnostic until termination. No key or HTTP request was observed; the actual cause remains unknown. This report does not attribute it to a bad key, dialog, ACL, restriction, or output-token exhaustion.

The runner now obtains the current `SecKeychainGetUserInteractionAllowed` flag, calls `SecKeychainSetUserInteractionAllowed(False)` before the fixed no-UI query, and restores the prior flag on ordinary success, failure and cancellation. CF objects are released even when another release fails. Restore failure refuses credential handoff. When cleanup fails after another local failure, the primary refusal is retained with a finite cleanup reason. A caller's unrelated active exception cannot mask failed cleanup. Stage tracking does no I/O and cannot block or prevent restoration.

Because native ctypes calls can defer Python signal exceptions, lookup has a five-second absolute monotonic deadline and a process-local watchdog. Only the genuine one-shot `python -m ai_movie_investigator.supervised_credit` entry opens this termination boundary. Normal imported Keychain calls refuse before creating a watchdog or invoking native APIs, so an ordinary imported dispatcher path cannot be terminated by lookup. A late result is refused even if the watchdog was delayed. The watchdog is cancelled under the same gate and joined before credential return or any slot/debit/send. It cannot survive into a later request.

On a blocked native call, the dedicated process exits with a fixed code identifying the last entered local stage. No error printing, file write, exception handler or atexit completion is required:

| Exit code | Last entered local stage |
| --- | --- |
| 80 | Lookup entry |
| 81 | Framework loading/binding |
| 82 | Get interaction flag |
| 83 | Disable interaction |
| 84 | Build exact query |
| 85 | Execute exact query |
| 86 | Validate/copy returned data |
| 87 | Release CF objects |
| 88 | Restore interaction flag |
| 124 | Unknown stage fallback |

These codes report a timeout and local stage, not the underlying native cause. Hard termination does not claim normal finally-based restoration; the isolated process and its in-memory interaction state end. No persistent Keychain ACL or preference is edited. The native APIs and no-UI flag are deprecated but available in the inspected SDK; actual running-OS behavior remains for main to verify.

A new `check-keychain` command performs the existing project/account/standing-credit preflight under the root's shared lock, then availability and format validation only. It appends no grant, attempt or debit and creates no HTTP send authority. Its success means only that a formatted credential was available locally, not provider authentication. Main can use that dedicated command for the next explicitly authorized availability check before a diagnostic send.

`test_keychain_bounds.py` uses dummy native APIs and separately spawned invented installed processes. A real blocking C `pause()` substitutes for the native query and must exit at code 85 within the bound, with byte-identical state, no new attempt, no HTTP and released lock. Another test delays the fake POST beyond the lookup deadline after successful retrieval; it completes with no live watchdog. Other cases cover direct-import refusal, restored prior flags, missing/denied access, broken stderr, cleanup failure, cancellation, delayed watchdog scheduling and the inherited-exception edge. Real network is independently blocked and no actual Security query is made.

The first combined 19-test run passed 16, including all six then-current bounded-lookup tests; three historical fixture/behavior tests stopped at the unchanged evidence ctime guard. Those failures are retained. The targeted bounded suite is repeated only after the new cleanup regression and fixed timeout stage codes, not to erase ctime failures. Final independent and exact-head CI results belong to the containing PR/checkpoint. The earlier selected runtime copy remains unchanged; this combined correction requires its own accepted runtime before use.


The corrected seven-test bounded suite passed in 12.821 seconds. A subsequent installed fake-native regression for a primary lookup refusal plus restoration failure passed in 0.841 seconds; CLI output contains only the finite primary/cleanup codes. These targeted checks were justified by concrete review corrections and do not erase the earlier ctime refusals.

Primary-source context: [Apple's Security globals](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/Globals.h) and [initialization](https://github.com/apple-oss-distributions/Security/blob/main/OSX/libsecurity_keychain/lib/Globals.cpp) support the application-local flag interpretation. [Chromium's scoped interaction helper](https://chromium.googlesource.com/chromium/src/crypto/+/refs/heads/main/apple/scoped_keychain_user_interaction_allowed.cc) documents the legacy file-keychain interaction boundary and restores the prior setting. These implementation sources do not establish the exact installed Apple binary's behavior or explain the earlier interrupted probe.
