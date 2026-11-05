# Explicit synthetic Nano retention — 2026-11-05

## Behavior and authority

The synthetic request previously omitted cache retention while the parser
required a null response value. The architect selected an explicit in_memory
policy for this non-sensitive offline integration contract. The fixed Nano
request and its POLICY now include that value; the parser requires its echo and
returns it in accounting. Missing/null, 24h and other values refuse. There is no
fallback to an omitted policy or a different model.

The parent admits the extra request field only in synthetic mode and already
requires every selected policy value in the request and in account, coverage
and pricing evidence. Exact request and context hashes continue to bind the
permit. Receipt validation independently reparses the original bound response
and compares accounting, so deleting or replacing the retention policy refuses.

This closes the local contract mismatch identified in the earlier compatibility
report. It does not prove live account/model acceptance, provider retention
behavior, Zero Data Retention or absence of caching. The generic movie profile
continues to use its original 30m cache-options contract and null-only retention
check. No real movie policy was selected.

## Primary documentation checked

The [official prompt-caching guide](https://developers.openai.com/api/docs/guides/prompt-caching)
uses prompt_cache_retention for earlier models and lists in_memory as the short
policy: typically 5–10 minutes inactive, up to one hour. Its model-generation
table states no additional cache-write charge for those models. The extended
retention list does not name Nano. The guide advises verifying model and
organization availability; no account check or live support claim was made.

The [official Responses request type](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/response_create_params.py)
confirms the exact parameter spelling and in_memory/24h values. The newer
prompt_cache_options parameter is documented for GPT-5.6 and later. Together
with the [Nano model reference](https://developers.openai.com/api/docs/models/gpt-5-nano),
this supports the selected earlier-model request contract, not an observed
provider acceptance. Sources were read on November 5, 2026. No SDK downloaded.

## Preservation and validation

Three runtime files change: credit_test.py, bound_send.py and
responses_protocol.py. The selected runtime manifest is refreshed. Invented
Nano fixtures now carry the explicit response policy; generic fixtures and
operational historical evidence are not rewritten.

Six new tests verify the new request/hash, refusal of old request hashes,
parent request/evidence policy checks, rejection of old selected owner evidence
before prompting or state change, receipt-policy tampering, and the full
chunked HTTP-to-parent path with invented sockets and a network tripwire.
Wrong response policies retain the reservation and prevent replay. The
compatibility regression separately confirms the unchanged generic contract.
All 76 focused integration, compatibility, supervised and framing tests passed
locally on Python 3.12.14. Full-suite and exact-head CI outcomes are retained in
the completion checkpoint; no dependencies changed or were installed locally.

No actual request, authorization, account evidence, state, runtime installation,
credential, provider response or budget ledger was accessed or changed. The
new request hash deliberately differs; historical omissions are not silently
reinterpreted or retroactively authorized. All consumed opportunities and
reservations remain unchanged. Merge is repository-only and does not trigger a
live handoff. The unrelated assigned cleanup task/project-state document remains
untouched; this report records the scoped implementation state.
