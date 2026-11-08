# Dormant one-event producer-identity check

The existing capture and assessment paths intentionally skip producer-verified
outcomes. The owner’s coordinator adopted an explicit dormant alternative:
independently check one next `unknown_movie / verified_tmdb /
external_id_verified` outcome without relabeling it as unresolved.

## Implemented boundary

`first_verified_identity_check` is an exact opt-in grant filter. Capture still
requires a new accepted delivery, original strict raw envelope, selected source,
verified current material, strong source correlation, startup proof, nonce,
finite expiry, private storage and one total lifetime burn. Existing unresolved
modes retain their eligibility requirements. No production selection routes or
producer behavior change.

Assessment uses a separate explicit purpose. It omits only the automatic
producer-verified skip, preserves owner skip/completion/conflicting decisions,
and blocks remembered owner identity pending confirmation. Ordinary admission
and reconciliation still skip verified cases. Preparation, consent, exact
trusted-wrapper activation, reconstruction and completion bind the purpose.
The audit wrapper additionally pins the original grant and checks its hash,
source and exact filter against the native capture receipt.

Requests and reports retain the original producer status/category/reason/route
and identify them as assertions, not independent approval or automatic conflict.
Existing minimization, evidence freshness, citation, edition limits, fixed
transport, credit reservation, no-retry, correlated response and private unsent
report controls are reused. Native receipts and model-response correlation are
not cryptographic proof of producer authenticity or evidence truth.

## Validation and held operation

Focused invented tests cover real Handler/SQLite capture to original bytes and
receipt, exact audit admission, connected fixed transport response parsing and
report correlation, installed nonempty runtime closure, wrong triples/source,
missing correlation, owner decisions, altered purpose/grant/body, burn failures
and uncertain-response refusal. Existing unresolved capture, activation and
six-hour boundary tests are retained. Independent exact-head review and
supported Python 3.12/3.13 CI gate merge; results are recorded in the PR.

No remote source, account, credential or provider operation, deployment,
restart, live capture, notification or download is performed by this change.
The collector needs a separately accepted selective code update and one restart;
the private assessment runtime needs a fresh complete manifest. A specific live
scope/update decision and exact operational packet remain required. No automatic
seventh window or replay of the five historical aggregate outcomes is enabled.
