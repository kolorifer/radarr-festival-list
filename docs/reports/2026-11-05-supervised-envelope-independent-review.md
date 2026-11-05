# Independent review: bounded synthetic response envelope

Reviewed the local envelope change based on `a1cc436030d5b14f3db1f377a0197e4d0e818080`. The larger one-mebibyte response and opaque-string limits are selected only for the fixed synthetic request through its existing active, root-locked session and consumed bound token. The parser accepts that profile only for the exact immutable HTTP result registered in that session; caller-supplied model names or fabricated results retain the generic limits. The response object is held transiently in the session and cleared on scope exit. The parser discards opaque content and the reviewed flow does not write it to the journal.

The complete raw and canonicalized envelope remain bounded at one mebibyte. The separate usable-answer limit remains 8,192 bytes; generic response and opaque limits remain 32,768 and 16,384 respectively. The fixed HTTP reader validates declared and observed length and rejects ambiguous length/transfer framing. This is a local resource bound, not a guarantee about provider response size or completion.

Eight independent synthetic Python 3.12 envelope tests passed before the final transfer-encoding refinement, including exact and over-limit bodies, length/missing/chunked framing, malformed framing, generic-profile refusal, unchanged answer limits, opaque-content non-persistence and the installed-module path. The final refinement compares the transfer-encoding value exactly as the underlying HTTP parser does. One independent run of the new active-result-binding test stopped at the initial HTTP gate with `supervised_authorization_refused`, before its assertions; the underlying cause was not established and the test was not repeated to obtain a pass. Runtime and test manifest hashes matched the reviewed files, and the runtime installation closure matched the manifest.

Reviewed SHA-256 values:

- `ai_movie_investigator/bound_send.py`: `63ca4085ac9de50e736cbb0282331ed14afd97ccfbb608b05dcc3669d5796845`
- `ai_movie_investigator/responses_http.py`: `65aadb7470eea8f4b61e08b24b95f227772cc218bc96d92a70029e818a237cfa`
- `ai_movie_investigator/responses_protocol.py`: `06bc8b14af9067f31c46224e5f06b846320bd522bca02ce4d4a999e9cbf0369c`
- `ai_movie_investigator/supervised_authorization.py`: `bc10e2e56f7aff8b88115ebd82903772ea56d7791b23e57c58d46edfacee3d96`
- `ai_movie_investigator/supervised_credit.py`: `0bd9485e0fb7b37a2b10d3b1fc8fe47ce98b56919b7c32a06fe93364ed8b7c8d`
- `test_supervised_diagnostics.py`: `47d43ca7ab13373b3c963bf1900dfd76e06e7918df5b794e130bdb3805be8565`
- `test_supervised_envelope.py`: `1b9ae1a6df95a6bed458796e4f444114b5e3e6870a178dc4c188d7330610f7e7`

No code blocker was found in this bounded offline review. Supported exact-head CI remains required. No actual runtime, history, account evidence, credential, provider or network was accessed, and no extra opportunity or expenditure was authorized by this review.
