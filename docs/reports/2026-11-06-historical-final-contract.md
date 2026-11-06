# Historical final-only correction: findings and verification

## Reproduced findings, not a retrospective diagnosis

Invented schema-valid answers passed the old parser but were rejected locally:
- null result: `pilot_one_generation_required`;
- wrong run alias: `pilot_run_alias_changed`;
- unknown citation or undisclosed claim: `pilot_citation_alias_unknown` or
  `pilot_citation_claim_not_disclosed`;
- inconsistent candidate/status, unsupported candidate or empty alternative
  citations: `candidate_status`, `candidate_evidence_missing` or
  `alternative_evidence_missing`.

Those exact Refusal names previously collapsed to `unexpected_exception`.
Slash-containing, overlong or credential-terminology rationale/uncertainty
instead produced the already-allowlisted `unsafe_text`; they do not explain that
recorded generic label. Ordinary exceptions remain another possible cause.
These examples do not identify the unretained actual answer or actual cause.

The request-side conflict is independently visible in source: the generic
instructions ask for retained lookups, and their schema permits lookup/null
results, while the historical route has one generation and no lookup action.
The new `historical-final-v1` contract explicitly requests one final, non-null
unresolved/blocked result, exact current run alias, null candidate and empty
lookups/citations/alternatives. Local privacy/text/identity validators remain
authoritative. Instructions state the existing 1–600 character text policy;
string constraints are not duplicated in the provider schema. Text-policy
failures can therefore still occur after receipt, with their precise phase.

## Bound correction, retained history

`correct_historical_final_contract_after_local_failure` requires the version,
25,000 allowance, canonical owner reference and all existing exact pins. Its
predecessor must be the old headroom purpose, without a versioned response
contract, with 25,000 tokens, one terminal `unexpected_exception` at
`receipt_recorded`, exactly reserved/attempted/receipt rows, the matching receipt
request hash, and no completion. One child per predecessor and duplicate-ID
checks remain. An expanded/versioned failure cannot automatically become another
correction. Earlier request reconstruction and purposes retain their behavior.

The selected instructions and schema come from the root-locked exact historical
grant. The request gate, initial parser and independent receipt validation use
that same schema. Generic instructions/schema and 4,096 defaults stay unchanged.
Only the new instructions/schema and correlation aliases differ from the pinned
predecessor request; disclosure, clocks, case, model, privacy, 25,000 tokens,
three-cent reservation, response/answer bounds and timeouts are preserved.

Three local phases now distinguish alias restoration, result validation and
report preparation. A finite literal list exposes existing local refusal names;
arbitrary exception/remote text and subclasses remain generic. Report validation
still precedes the irreversible completion append. A validated receipt is never
removed or misrepresented merely because local report acceptance fails.

## Answer recovery and scope

The bound receipt persists request hash, accounting, retained debit and time;
it does not persist the raw HTTP body or parsed answer. The answer is persisted
only by the later successful completion event. If that event and any separately
authorized answer artifact are absent, the receipt/request/accounting cannot
reconstruct the answer. No private artifacts were inspected in this engineering
work, and no remote retrieval, new call or replay is implied.

The schema uses documented objects, nulls, enums and `maxItems`, with all fields
required and additional properties disabled. See [official Structured Outputs
documentation](https://developers.openai.com/api/docs/guides/structured-outputs),
fetched November 6, 2026. This verifies documented syntax, not actual provider
acceptance or success of any future request.

Tests use invented history, fake Keychain, complete fake HTTP framing and an
independent socket tripwire. They cover request-diff limits, incompatible
version/pins, parser refusals before receipt, text-policy refusal after receipt,
truthful receipt preservation without answer retention, completion, duplicate
and restart refusal. Independent review and exact Python 3.12/3.13 CI remain
merge gates recorded in the PR. No real operation or production deployment ran.

Initial local focused run: seven of eight tests passed, including installed
completion, null-result parser refusal, wrong schema echo and altered authority.
The installed text-policy case stopped in old-lineage setup at the existing
ctime guard; it did not exercise its target. The added pure schema-narrowing
test passed separately. Those limitations remain retained, not retried away.

Final review tightened the first parser selection to the root-locked contract
helper, which defaults to the original generic schema outside that session.
A custom generic parent cannot choose a different parser schema merely by
changing its request. A focused regression exercises that refusal.
