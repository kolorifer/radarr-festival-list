# Dormant processed-input count preparation

## Agreed bounded scope

Prepare the next supervised fixed synthetic API test while PR147's merge is
blocked. Keep its published head unchanged. Reuse the existing HTTP transport,
no new service/launcher, real socket, key/account access, generation or merge.

## Implementation

FixedResponsesHTTP.count uses the same fixed origin, deadline, TLS, public DNS,
no-proxy/no-redirect/no-retry and unconditional real-authorization refusal as
post. The sole new route is /v1/responses/input_tokens. Local HTTPResult stamps
now include the endpoint path as well as request hash and project.

credit_test.count_request constructs all input-bearing fields from the exact
synthetic generation request, including instructions and output JSON schema.
count_receipt accepts only the fixed count route, request/project match,
nonempty request ID and documented object/integer shape within the existing
65,536 input ceiling. These local stamps bind transport observations; they are
not provider signatures or proof of live compatibility. No count was sent.

The independent reviewer found that count-shaped JSON from the generation route
could otherwise be accepted. A path stamp and wrong/missing path regression fix
that gap. Focused tests use fake DNS/socket/TLS objects or a socket tripwire.
The declared runtime hashes are refreshed. No dependencies changed.

## Executable verification

From the checkout, use the existing supported virtual environment:

    python -m unittest -q test_credit_count test_credit_integration test_historical_parent test_responses_transport

This is a credential-free, network-free check, not an activation command.

## Actual activation boundary

There is no executable live command yet. real_activation_refusal remains
unconditional. The remaining narrow integration must bind supervisor-observed
account facts, exact request/path/project/credential and expiry; reserve one
count attempt without automatic retry; bind its result to generation; and invoke
the existing complete_credit_test once after its durable cent reservation.
Count fee policy must be established before counting under the credit envelope.
A caller boolean or monkeypatch is never an activation method.

For a supervised fixed synthetic request, the existing Default project can be
used if its project permissions allow the model and required endpoints. Use one
explicit, sole-writer owner-private ledger, enrolled once and reused across
attempts. Missing/replaced journals refuse; do not add an adversarial owner-proof
rollback service without an actual uncontrolled writer. Automatic retry/reset
remains prohibited. The generic production path stays closed.

Secure provisioning is one restricted project key, entered by the owner into a
local no-echo prompt in the eventual reviewed one-shot process. Keep it in memory
for that process only; never use chat, argv, environment, repository or logs.
The prompt/entry-point integration is still unimplemented, not a completed setup.
The architect retains dated private account evidence and exact project selection
outside this public report. No new dedicated project is required by this change.

Reference: [count endpoint and fields](https://developers.openai.com/api/reference/resources/responses/subresources/input_tokens/methods/count).
