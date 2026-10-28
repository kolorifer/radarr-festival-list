# Observer timeout and sanitized diagnostics

User request: fix the observer timeout mismatch, add sanitized failure diagnostics
and regression tests, and merge into main. Do not deploy. Keep the existing
24-hour collector monitor running and preserve actor/shadow configuration.

Scope: align the asynchronous observer transport timeout with the collector's
two-second local writer wait and five-second connection lifetime. Preserve the
same-UUID durable retry behavior, commit-before-ack semantics, existing backoff,
bounded memory queue, configuration schema and disabled behavior. Diagnostics may
include only fixed stages/reasons, validated numeric HTTP status and bounded
elapsed time; exclude raw exceptions, payloads, URLs, headers, credentials, event
identifiers and response text.

Acceptance: reproduce the half-second timeout failure with a real synthetic
collector write held beyond that timeout, demonstrate the fix, test HTTP
backpressure and retry/deduplication, distinguish transport and outbox ACK failures,
prove diagnostic redaction, and pass focused/full tests and current-head CI.
Leave the unrelated active cleanup task and production configuration unchanged.
