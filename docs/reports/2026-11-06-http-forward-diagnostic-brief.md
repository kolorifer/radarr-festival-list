# Finite HTTP rejection diagnostics and one explicit forward observation

Implement fixed non-200 refusal labels at the existing HTTP reader, without
reading error headers/bodies, following redirects, retrying or changing success
acceptance. Preserve older generic rejection causes and billing outcomes as unknown.

Permit one separately selected canonical forward authorization with purpose
`observe_http_rejection_with_finite_diagnostics` only after an exact retained
`responses_http_rejected` at `http_response_received`. A predecessor may itself
be a renewal. Preserve append-only history, exact content and source clocks,
project/account/credit boundaries, original policy and one child per predecessor.
Neither a newly classified refusal nor an arbitrary failure qualifies.

Use invented fixtures only, including the installed module entry with fake
Keychain and full HTTP framing behind an independent network tripwire. Independent
review and supported exact-head CI precede merge. No actual credential, evidence,
private state, provider operation, deployment or automatic future execution.
