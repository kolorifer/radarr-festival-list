# Complete envelope bounds for the fixed synthetic route

The previous32KiB envelope cap could reject a complete response even when each
answer and opaque field satisfied its individual limits. The architect selected
a1MiB finite complete-envelope ceiling for this synthetic path. This is a local
resource choice, not a provider maximum or a guarantee of live compatibility.

HTTP selects the larger bound only after the existing active fixed-synthetic
opaque token has been consumed. The actual immutable HTTP result is registered
in that same held-root session after acquisition. Parser entry grants the wider
envelope and opaque-string bound only to that exact result object, its body and
request ID, and the integration model. No arbitrary flag, model name, fabricated
result or unrelated body gains that profile. The result reference is cleared on
session exit. Initial parsing and receipt validation both use this binding.

Opaque content is type/size checked then discarded, never persisted, hashed,
decrypted or forwarded. The usable answer remains8192 bytes, output4096 tokens,
and all schema/status/usage/privacy/correlation/action checks remain. Generic
responses retain32KiB overall and16KiB opaque bounds. No spending or send
allowance changes; setup, single-send and absolute observation timers remain.

The HTTP path rejects duplicate/invalid Content-Length, length plus transfer
encoding, and unsupported/duplicate transfer encodings with finite static
reasons. Declared-over-bound and observed-body-over-bound are distinct. Length
parsing avoids unbounded integer conversion. Chunked handling matches the HTTP
client's exact case-insensitive token interpretation. Truncation, content type,
identity encoding, status and request-ID checks remain. Diagnostics contain no
header value or response content.

Nine new parametrized tests cover one/two opaque items above16KiB; exact1MiB and
one-byte-over bodies with length, missing length and chunked framing; canonical
JSON expansion past the parser cap; malformed framing and truncation;8192/8193
answers; invalid schema/usage/incomplete/refusal/unknown output; exact active
result/body/model/ID binding; fabricated-result/default-profile refusal; and a
genuine installed-module command using dummy input and invented chunked I/O.
Every full-path fixture checks one POST, retained full debit, no retry, timer
restoration and absence of opaque data from all journals.

The initial eight tests passed. After adding the active-result binding test and
matching transfer-encoding interpretation precisely, all60 selected tests passed
(nine new plus transport, diagnostics and bound-send/integration regressions).
No unrelated long local suite was repeated; exact supported full CI is required.
Independent review is recorded separately. The39-file runtime manifest matches.

No actual pilot state, evidence, credential, account or provider was accessed.
No runtime was installed outside temporary invented test installations. All
prior real outcomes remain unknown; this code does not retry them, refund their
reservations, create another opportunity, or prove the historical rejection was
an oversized body. No production activation occurred. The unrelated active
cleanup task remains unchanged; this focused report is the project record.
