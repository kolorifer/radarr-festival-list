# Reject identifier input before consuming a supervised slot

## Problem and bounded correction

The supervised command previously accepted an identifier-shaped value under its
broad header-character check and appended a slot-start record before validating
input. The hidden prompt did not distinguish a secret API key from a Tracking
ID. Existing HTTP rejection and network-completion-unknown refusal codes also
fell through to the CLI's unclassified category.

The prompt now explicitly asks for the secret API key, not a Tracking ID or
project ID. With the existing root transaction/exclusion held, the command
checks the existing bounded header-safe grammar and requires the `sk-` prefix
before appending a slot-start record. Invalid input or cancelled input exits
without a slot, reservation, network call or automatic reprompt. For accepted
shape, the durable slot/attempt/debit still precedes any network operation.
All account, private-file, context, project, request and monetary bindings and
the 900-second account/60-second prompt-authority limits remain.

This is a conservative mistake filter, not authentication or an exhaustive
future credential grammar. Official [CLI authentication examples](https://developers.openai.com/api/docs/libraries/openai-cli#authentication)
use `sk-...` and distinguish a key's `id` from its secret `value`. The
[API key guide](https://developers.openai.com/api/docs/guides/api-keys)
requires keeping secret values out of logs and client-visible output. No actual
credential or identifier was accessed; no provider authentication is claimed.
Generic transport header handling remains unchanged for other existing routes.

Three exact static CLI categories now cover credential-format rejection,
HTTP rejection, and network outcome unknown. No raw exception, input, response
body, header or path is printed. HTTP status distinctions are deliberately not
added: the result says HTTP rejected, not an inferred 401/authentication cause.
The run action continues to say request status unconfirmed. This cannot
retroactively diagnose an earlier unclassified failure.

## Verification and scope

Actual installed `python -m` PTY fixtures enter dummy tracking/project IDs and
malformed values, check no echo, and verify unchanged root bytes, empty attempt
directories and zero reservations with socket/DNS tripwires. Valid-looking dummy
input reaches the actual authorization guard and offline HTTP sink; injected
HTTP and network refusals produce safe distinct categories while preserving the
reservation. In-process checks cover no reprompt and cancellation. Existing
supervised authority, expiry, renewal and no-replay regressions remain.

Exact-head independent review, focused runs and Python3.12/3.13 CI are recorded
in the PR. The intermittent fail-closed evidence metadata guard remains unchanged.
No real runtime, evidence, state, key, provider request, refund, reset, new slot,
enrollment, cap increase or live retry is part of this repository-only repair.
