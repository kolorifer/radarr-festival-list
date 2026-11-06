# Credential-correction authorization: implementation and verification

The new `verify_owner_reported_credential_correction` purpose requires
`material_credential_correction_attested: true` plus the existing owner reference,
canonical private authority, predecessor-run pin and exact grant/attempt/terminal/
request/root-prefix hashes. It accepts only `responses_http_401` recorded at
`http_response_received`. The attestation is a trusted owner/parent statement,
not independent verification that a credential changed or caused the earlier
401. The report retains `prior_cause: unknown` and does not reinterpret the
previous outcome.

The existing lineage, one-child, account-freshness, expiry, no-UI Keychain,
three-cent debit, request framing, parser, receipt and report paths are reused.
Only diagnostic correlation aliases change in the actual request. Previous
purposes retain their original rules. No secret-derived fields are accepted.
This adds no automatic retry, authentication ping, endpoint, model, output
setting, case, deployment or production activation.

Invented tests cover rejected attestations and pins, wrong terminal outcomes,
full request equality apart from aliases, one child across distinct identifiers,
and installed `-m` success/401/refused-Keychain paths with complete fake HTTP
framing and an independent network tripwire. Exact results, independent review
and supported Python 3.12/3.13 CI are acceptance gates recorded in the PR.

## Manual credential setup correction

Do not use the interactive trailing `-w` prompt of macOS
`security add-generic-password` for long API keys. Apple's implementation calls
`getpass`; macOS `getpass(3)` documents a 128-character limit and silent truncation.
Replace the entire intended item's password directly in Keychain Access instead.
Never place the secret in command arguments, environment variables, logs or
setup files. Saving the value does not establish authentication or unattended
access; existing no-UI checks still apply, and a denied lookup remains a refusal.
No Keychain operation was performed for this engineering change.

Source: [Apple SecurityTool keychain_add.c, pinned implementation](https://github.com/apple-oss-distributions/Security/blob/db15acbe6a7f257a859ad9a3bb86097bfe0679d9/SecurityTool/macOS/keychain_add.c#L510-L529)
and local macOS `getpass(3)`. No existing repository recommendation for the
truncating prompt was found; this scoped note records the correction without
adding a setup framework. Unrelated project/task documents remain untouched.

Initial focused local run: installed success and 401/restart passed. Three
fixture setups refused with the retained macOS ctime check. The denied-key test
correctly observed no debit/send but wrongly expected no directory: history
locking creates an empty attempt directory. Its assertion now checks zero
attempt events and the exact denied-key refusal; no runtime guard was changed.
