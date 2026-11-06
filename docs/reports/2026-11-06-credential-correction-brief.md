# Owner-reported credential correction after a recorded 401

Implement one new purpose-bound historical forward authorization, following an
explicit owner report of a material credential correction. Require a distinct
canonical private authorization, owner reference and literal true correction
attestation. Accept only a bound prior `responses_http_401` terminal outcome;
preserve the old outcome and unknown cause, existing purposes and refusal rules.

Keep the same approved case, disclosure, clocks, project, ledger, request policy,
three-cent technical debit and one-child-per-predecessor rule. Keep current
account evidence and the existing no-UI Keychain lookup before debit/send. No
credential value, length, digest or other secret-derived identifier may be added.

Test invented installed-module success/refusal with complete fake HTTP framing,
fake Keychain and independent socket audit tripwire; missing/false/non-boolean
attestation, wrong project/predecessor/disclosure, duplicate/restart and denied
key without send/debit. Require independent exact-head review and supported CI.
No real credential, provider, account, private evidence or operational-state
access is part of this engineering task. Prepare a distinct private accepted
runtime only after reviewed merge; main separately verifies any operational use.
