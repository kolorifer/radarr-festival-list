# Fixed synthetic generation without token counting

## Agreed brief

The owner approved a three-cent per-generation reservation within the unchanged
five-cent total. Replace the supervised count-and-generation flow with one fixed
Nano generation. Retain existing one-cent reservations and consumed slots, exact
request/project/model binding, interactive no-echo credentials, private evidence,
expiry, no retries or fallback, and closed unattended/movie paths. No real keys,
API calls, deployment, account changes, new workers or operational grants.

## Implementation

The exact fixed request remains unchanged: gpt-5-nano-2025-08-07, standard tier,
4,096 maximum output tokens, no tools, no background/store/stream, truncation
disabled, and nonsensitive synthetic input. The documented 400,000-token context
is a conservative input upper bound. At USD0.05/M input and USD0.40/M output,
the bound is USD0.0216384. The command durably reserves USD0.03 before HTTP.
The model's full 128,000-token output is not enabled.

Current selected private evidence must match the exact model, standard policy,
400,000 context, input/cached-input/output prices and dated account, model-access,
pricing/context, credit-only billing and owner references. No count-fee or count
coverage field or request is needed. This is checked metadata supplied by the
trusted supervisor, not account authentication from arbitrary JSON.

The live authorizer permits only POST /v1/responses and requires the exact
three-cent reservation and 400,000 input bound. Legacy count primitives remain
for retained fixtures but cannot receive supervised HTTP authority. The shared
ledger validates each old one-cent or new three-cent debit and sums persisted
amounts against USD0.05. It never multiplies record count by a new price, refunds,
resets, discards old debits or reuses consumed slots. A second three-cent attempt
cannot fit after a first; with two old one-cent debits one new attempt fits exactly.

All original storage/ACL, held-transaction, prompt, wall/monotonic expiry and
credential/request binding checks remain. Existing enrollment and evidence pins
remain strict; this change does not migrate or refresh a previously enrolled
selection. Unknown response or invalid accounting retains the full debit.
Only the Nano usage parser accepts its 400,000-token input ceiling; generic
historical model limits remain unchanged.

## Validation and limits

82 focused tests passed on the existing bundled Python3.12.14. Regression cases
cover generation-only/no count, exact request and debit, legacy-budget summation,
consumed legacy slots, restart/timeout, invalid usage, stale/mismatched evidence,
endpoint refusal, private filesystem checks and generic authorization refusal.
Independent exact-content review and Python3.12/3.13 CI are required before merge.
An initial local run encountered the already documented fail-closed evidence
ctime change; no guard was relaxed. A subsequent focused run passed.

No real evidence file, key provisioning, enrollment, spend or provider call was
performed. Secure owner key input and fresh validated account/model/pricing/credit
facts remain prerequisites. The old unknown count fee is no longer a dependency.

Official facts: https://developers.openai.com/api/docs/models/gpt-5-nano
