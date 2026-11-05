# Responses compatibility review — 2026-11-05

## Result and scope

The parser rejected several documented metadata variations before reaching the
selected answer. This patch projects required fields from the bounded envelope,
discards other top-level metadata, and keeps unknown output actions/content
refused. It changes parser compatibility and finite diagnostics only. Request
construction, transport, admission, correlation, response/answer limits, usage
ceilings, budget and retry rules are unchanged. No runtime installation or live
request occurred. The historical rejected field remains unknown.

## Official-source audit

Sources were read on November 5, 2026; SDK main is a changing reference, not proof
of a historical wire response. The independent invented fixture does not use
the older minimal simulated-response builder.

| Documented shape | Prior incompatibility | Selected treatment |
| --- | --- | --- |
| Optional `image` metadata | Unknown top-level key refused, even null | Bounded envelope projection discards it |
| Zero hosted-tool counters | Any nonempty tool-usage object refused | Only known, strictly typed zero counters accepted; output tools still refused |
| Optional message `phase` | Exact message keys refused null/final_answer | Accept absent/null/final_answer; refuse commentary and unknown values |
| Optional format `description` | Exact format object refused null/string | Discard description; require exact selected name/type/schema and literal strict=true |
| Cache options with implicit mode | Exact ttl-only dictionary refused mode | Permit implicit mode and null comparison only; preserve selected ttl |
| Nano zero cache-write additions | Cached-only dictionary refused additions | Validate only zero writes and zero/null partition; retain cached-only accounting |
| Optional write partition | Generic parser required dictionary even for zero writes | Normalize missing/null only when explicit write total is zero |

References: [response envelope and tool/cache metadata](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/response.py),
[message phase](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/response_output_message.py),
[format description](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/response_format_text_json_schema_config.py),
[usage counters](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/response_usage.py),
[reasoning item](https://github.com/openai/openai-python/blob/main/src/openai/types/responses/response_reasoning_item.py).

The SDK's top-level output_text convenience property is not required wire data.
If present as an additive field, it is ignored; only the selected nested output
text supplies the answer. No response metadata is evaluated or executed.

## Deliberately retained constraints

Completed status, exact model, error/incomplete absence, store=false,
background=false, no tools and selected structured schema remain mandatory.
Conversation, previous response and prompt references remain refused. Unknown
or nonzero tool counters remain refused. No-tool echoes and output validation
remain required even with zero counters; counters alone do not prove no activity.

Non-null cache retention/key/diagnostics, explicit caching, nonzero Nano writes
and generic nonzero writes without their exact permitted partition remain
refused. These are privacy/accounting boundaries, not universal API compatibility.
Plaintext reasoning, annotations, refusals, extra answer parts, commentary and
unknown output actions remain refused. Opaque reasoning is bounded and discarded.
The existing maximum three output items, response limits and 8192-byte answer
bound are unchanged. A documented response outside these selected constraints
can still refuse; this is not a guarantee of successful live completion.

HTTP audit retains one POST, fixed origin/TLS, strict JSON content type, identity
encoding, unique valid Content-Length or chunked framing, no CL/TE conflict,
bounded reads, truncation checks, finite deadlines and request-id validation.
No HTTP code changed. Existing framing/size/authority tests are retained.

## Validation and limitations

Eight new tests cover complete envelopes for both model profiles, discarded
metadata, safety rejections, tool counters, cache partitions, actual HTTP framing
(length/EOF/chunked) and the genuine installed module with dummy input. The latter
reaches a deliberately invalid usage sum after all earlier compatibility gates.
The positive in-process wire path verifies completion, one POST, exact debit,
receipt, no opaque persistence and refusal before a second prompt.

Initial focused run: 53 of 54 passed; new installed test had a missing fixture
import and stopped before the intended path. The import was corrected; all seven
new tests then passed. Full local suite, independent review and exact public-head
CI results are recorded in the completion checkpoint/PR. No dependency changes.
The unrelated assigned cleanup task and operational project-state document are
preserved. This report is the scoped implementation-state record.


### Precise unresolved cache-policy boundary

The fixed Nano request (`credit_test.request`) sends store=false but does not
select prompt_cache_retention. Current official response types document
in_memory/24h defaults depending on organization policy. Null in the positive
fixture is a selected-contract scenario, not evidence of the account default.
Both documented non-null values have explicit negative tests on both profiles.
The parser will still refuse them. Resolving that discrepancy requires a
separately established permitted retention contract; this pass neither assumes
an organization policy nor changes the request/privacy gate. A successful
positive fixture must not be used to recommend another live attempt.

Projection preserves the audited known checks; it cannot interpret future
provider context or billing fields. Newly documented material semantics require
review. Existing instruction/sampling/truncation echo handling is unchanged;
the fixed request and local correlation remain the authority for selected input.

Initial public-head CI ran 1752 tests and found one older integration assertion
that required rejecting a zero cache-write field. The assertion now requires
acceptance with identical accounting for zero and refusal for nonzero writes.
No runtime change was needed; the corrected head requires fresh CI.
