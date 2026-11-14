# Bounded prose and one completed-result reassessment

The v3 snapshot response contract constrains both model prose fields to 1–600
characters and instructs the model to use a single short plain-text paragraph,
without URLs, paths, slashes, markup, control characters, opaque aliases or
credential terminology. The local response-schema validator also enforces both
string length keywords; the existing safe-text and whole-field withholding
checks remain in force. No prose is truncated or reconstructed. The frozen v1
and v2 request builders remain byte-for-byte compatible.

A separately reviewed trusted-main scope can authorize one distinct full v3
assessment after the exact latest completed v2 snapshot assessment when its
retained rationale has `status=withheld` and `predicate=length`, and its
uncertainty was retained. The predicate identifies the first matching filter
reason; it does not prove that the discarded text had no other unsafe content.
The retained structured verdict and prior report remain unchanged. The new
assessment may return a supported, unresolved or blocked result, subject to the
same source, conflict, citation and semantic checks; it is not instructed to
justify or reproduce the earlier result. The output labels both results and
states that the earlier rationale cannot be recovered. No identity, edition,
current queue, production or acquisition approval is implied.

The new authority contains a `reassessment` object with exactly `kind` =
`snapshot_prose_length_reassessment_v1`, `prior_slot`, `prior_start_sha256`,
`prior_grant_sha256`, `prior_completion_sha256`, `prior_report_sha256`,
`prior_retained_reply_sha256`, `prior_attempt_sha256`, `prior_receipt_sha256`,
`prior_credit_sha256`, `prior_credit_count`, `prior_request_sha256`,
`root_prefix_sha256`, `new_request_sha256`, `prior_status`, `prior_candidate`
and `reviewed` = true. Owner scope uses `snapshot_reassessment_scope_v1` with
the existing one-call case/version fields and `prior_slot`. The main-review
record binds `reassessment_sha256`. A trusted supervisor must independently
verify the owner instruction, these exact records and the actual sources; a file
or hash alone grants no authority.

The prior completion, report, retained reply, actual receipt, attempt, account,
credit and root prefixes must all match. The preceding v1-to-v2 status-correction
lineage is revalidated. Exactly one v3 child is allowed; a child of that child,
changed case, source, projection, local context or disclosure is refused. Old
request, timestamps, reports, attempts and reservations remain intact. The new
request differs in schema and the explicit prose instruction, and consumes one
new attempt and ordinary reservation. A missing, stale or uncertain input refuses
without relabeling clocks; an interrupted or uncertain send is not repeated.

The [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)
describes string-length constraints as unavailable for fine-tuned models; this
route uses the existing non-fine-tuned model. The guide's ordinary-model string
property list does not explicitly list these two keywords, so support for this
exact schema remains uncertain. A live schema rejection could consume the one
allowed reservation; acceptance by the live endpoint remains untested. Tests are invented, and simulated
credentials/HTTP do not establish live behavior. One local installed fixture
stopped at the pre-existing read-time ctime guard before allocation; its cause is
unestablished and it was not retried. Independent review, supported exact-head
CI, main's current-account verification and actual guarded issuance remain
separate gates. No live source, credential, ledger, provider or production
operation is performed by this implementation.
