# Snapshot assessment: status/candidate contract correction

The original final-result schema permitted `supported_candidate` with a null
candidate, or `unresolved`/`blocked` with a non-null candidate. The existing
semantic validator correctly rejects those combinations. The corrected request
uses a nested, closed-object `anyOf`: a supported result has the exact eligible
IMDb/TMDb pair; unresolved or blocked has a null candidate. If there is no
eligible pair, a supported variant is absent. All existing local result,
citation, conflict, freshness, identity, privacy and receipt checks remain in
force. The unmodified v1 request is reproducible byte-for-byte for existing
records; new requests use the corrected contract.

OpenAI's [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
describes nested `anyOf` as supported while requiring an object at the root.
This does not prove that a particular live API call will accept or complete the
schema; the installed tests use invented transport responses.

## One explicitly selected correction

A separately reviewed trusted-main authority may attach exactly one `correction`
object to the existing snapshot authority. The correction is available only for
a selected latest original v1 snapshot attempt whose unique terminal diagnostic
is `candidate_status` at `receipt_recorded`, has a matching persisted receipt,
and has no completion or cleanup uncertainty. It never reconstructs the prior
response. The new request changes only its output schema and must retain exactly
the earlier request input, instructions, policy, selected evidence, case/version,
source projection, observation clocks, local context and disclosure. It consumes
one new attempt and a new ordinary reservation; old records and reservations
are unchanged. A child cannot have a child. Arbitrary repeats, changed evidence,
relabelled timestamps and a generic retry remain refused.

`correction` has exactly `kind` = `snapshot_candidate_status_correction_v1`,
`prior_slot`, `prior_start_sha256`, `prior_grant_sha256`,
`prior_terminal_sha256`, `prior_attempt_sha256`, `prior_receipt_sha256`,
`prior_credit_sha256`, `prior_credit_count`, `prior_request_sha256`,
`root_prefix_sha256`, `new_request_sha256`, and `reviewed` = true. The owner
scope is `snapshot_correction_scope_v1` and adds `prior_slot` to the earlier
single-call scope. The reviewed main record includes `correction_sha256`.
The trusted-main context, exact root lock, selected account, owner scope,
source/local-context pins, installed runtime and exclusive output identity
remain necessary. A copied correction record or hash alone grants no authority.

Use the existing unissued snapshot wrapper and documented exact issuance path.
The original snapshot, source observations and their true clocks must still be
valid throughout the guarded operation; expiry is a refusal, not a reason to
extend or relabel an observation. A newly acquired source, if separately
permitted, requires a separately reviewed matching route; this correction does
not silently change its disclosure. Any ambiguous or interrupted new attempt
remains consumed, with no automatic replay.

## Validation boundaries

Invented tests cover schema status/candidate combinations, the frozen v1 request,
prior receipt and credit pins, prior terminal conditions, single-child refusal,
and retained history. An installed fake-I/O correction test is included. One
local attempt at that installed test stopped at the existing evidence read-time
ctime guard before allocation; its cause is not established, and it was not
retried. Prior independent installed-path results apply to the earlier route, not
to this corrected executable. Supported exact-head CI, independent review and
the main supervisor's actual guarded preflight are separate gates. No keychain,
provider, live source, ledger or production operation is performed by this
implementation.
