# Engineering report: project-bound Keychain diagnostics

**Specification:** [agreed brief](2026-11-06-keychain-diagnostic-brief.md).
**Result:** Implemented for independent review and exact-head CI; no actual credential use or deployment.
**Verification date:** 2026-11-06.

## Behavior and boundaries

`run-next-keychain` performs one fixed synthetic diagnostic using the existing standing credit authority. `run-historical-keychain` performs one already selected historical attempt only after its separate exact disclosure grant. Neither action loops or retries. The manual hidden-entry actions remain available. The account is always the validated evidence project; there is no credential selector or arbitrary service option.

All existing evidence, history, replay, disclosure and budget preflight runs before credential retrieval. The enrolled root transaction stays held. Successful retrieval creates only the existing short-lived in-process credential context; project/request/secret identity, original ledger, full reservation and exact selected disclosure remain enforced at the HTTP boundary. Missing or refused credentials do not append a slot or debit. A consumed attempt is refused before another Keychain lookup. Generic Keychain access does not establish historical disclosure or production authority.

The native Security query asks for one generic-password data item matching service `codex.movie-project.openai` and that project account. It sets `kSecUseAuthenticationUI` to `kSecUseAuthenticationUIFail`; there is no unlock, UI fallback, enumeration, subprocess or shell command. Returned data must be CFData of bounded size and a valid ASCII secret format. Missing, interaction-required, denied, malformed and unsupported results map to finite local codes. Native errors and secret bytes are never printed. CF objects are released; the implementation does not claim reliable zeroization of immutable Python strings.

The existing generic `responses_not_completed` refusal is now separated into object mismatch, model mismatch, non-null error, finite non-completed statuses and incomplete-detail classes. `max_output_tokens` and `content_filter` are accepted only as reported reason labels for refusal, not verified causal or billing conclusions. Unknown values map to fixed generic categories. Acceptance remains completed/exact model/no error/no incomplete details, followed by all original strict checks. No raw response, reasoning, error message or arbitrary remote value is retained. Old historical causes remain unknown and the old finite journal reason remains readable.

## Components

- `keychain_credential.py`: fixed native query and safe in-process credential result.
- `supervised_credit.py`: explicit one-shot CLI actions, credential context and finite diagnostic allowlist.
- `responses_protocol.py`: separate safe failure predicates with unchanged acceptance.
- Installation tuple/manifest: 42-file closure.
- `test_keychain_diagnostic.py` and existing diagnostic expectations: fake native API, installed noninteractive transport path, binding, no-leak, preservation and refusal checks.

## Validation

Tests use invented inputs, ledgers, keys, native results and socket responses. The native fixture checks the exact query, project and no-UI selector plus result type/size and release behavior. The installed `python -m` test substitutes only native credential retrieval and socket/TLS I/O, leaving actual CLI, preflight, HTTP serialization/framing, parser, receipt binding, report and restart checks in place. A separate Python audit hook rejects real socket creation/connect/DNS. No actual Keychain access is part of these tests.

The initial six new tests passed in 7.935 seconds. The final focused run passed all 65 tests in 56.228 seconds; independent review passed all seven new tests, including the installed command. These are synthetic/local results, not evidence of actual Keychain access. Supported Python 3.12/3.13 CI and independent exact-change review are required before merge. This report does not assert those future gates in advance.

## Compatibility and risks

The local macOS SDK documents that the query's authentication-UI fail option returns interaction-not-allowed when interaction is required. That constant remains available but is deprecated in favor of an LAContext API. This minimal adapter fails closed on unsupported behavior; it does not create a second authentication framework or fall back to prompting. Runtime behavior with the owner's actual Keychain, trusted executable ACL, locked state or entitlement has not been exercised here. No claim of current provider/account authentication is made.

Known local ctime guard refusals remain evidence of guarded failures, not permission to retry consumed attempts or relax checks. The earlier historical response was discarded, so its composite refusal cannot be retrospectively diagnosed as output-token exhaustion. No reasoning/output/model parameter was changed on that hypothesis.

## Deployment and project context

Not deployed or adopted. No real Keychain item was read/written, no actual credential was prompted, and no real input, evidence, ledger, provider, account or source was accessed. Existing prepared runtimes and historical attempts remain unchanged. This scoped report/brief records the task without modifying unrelated task documents. The containing commit/PR supplies the implementation reference; actual use remains behind the architect's independent verification and applicable exact disclosure authority.
