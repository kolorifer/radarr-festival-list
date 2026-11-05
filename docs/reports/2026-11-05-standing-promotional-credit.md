# Standing promotional-credit preparation — 2026-11-05

## Behavior

The manual synthetic command can append one standing promotional-credit grant on
the same exhausted six-attempt history. It verifies retained directory and credit
file identities, all historical attempt hashes, request-to-ledger links and old
grant prefixes. It never reconstructs historical request hashes using the newer
retention policy. Original attempts and the retained fifteen cents remain intact.

A future run-next invocation checks fresh selected evidence and the retained
history under the existing root lock, prompts locally, validates secret format,
then allocates one distinct attempt. Invalid input leaves attempt and ledger
state untouched. It calls the existing one-shot transport once; no retry loop is
added. Partial preparation fails closed. A later manually started request gets a
new binding and preserves the prior attempt, including uncertain outcomes.

The grant binds account reference, project, fixed policy, initial remaining
promotional balance and credit expiry. Each request also requires fresh evidence
with promotional credit kind, no paid fallback, matching account/project/policy
and an expiry no later than the grant. References are operator-selected evidence,
not provider authentication or independent proof of account settings.

The cumulative reservation ceiling is the lesser of the initial selected balance
and each fresh remaining balance. All retained reservations, including the old
fifteen cents, count against it. This deliberately conservative rule may leave
credits unused; it releases no uncertain cost. Each request reserves three cents.
The original five-cent default and existing one-time extension caps remain
unchanged outside a root-locked standing session. The fixed synthetic Nano body,
no-tools policy, send deadline, response observation limit and privacy/storage
checks remain in place. Existing bounded history size/record limits still apply;
exhausting those limits fails closed rather than rotating or resetting history.

## Validation

Nine focused tests pass, covering distinct successful offline requests, uncertain
outcomes without retry, original byte preservation, old-policy request hashes,
cap exhaustion, fresh funds/expiry/account/project/policy refusal, interruption,
noninteractive invocation and malformed secret input. A preparation-versus-
consumption bug found by the initial run was corrected. Independent review found
and prompted the account binding and no-state-on-invalid-input corrections.

A broader focused run before those last corrections ran 76 tests: 73 passed and
three existing fixture setups refused with supervised_evidence_changed_read_ctime
(one fifth-slot and two sixth-slot tests). These failures are retained; their
external cause is unknown. No guard was relaxed or broad retry used to erase
them. Exact-change CI and final independent review results are recorded in the
completion checkpoint. No full local suite or dependency repair was performed.

## Scope and remaining work

Three existing runtime modules change; the same 39-file runtime manifest is
refreshed. The pure retained-ledger summation helper grants no spending authority.
The new CLI entries are authorize-standing and run-next; legacy run choices stay
unchanged. No actual state, evidence, runtime, account, credential, provider,
seedbox, source, service, notification or live handoff was accessed or changed.
Operational adoption needs fresh actual evidence and its separately controlled
handoff; this repository change neither supplies nor executes that handoff.
The unrelated active task and broad project-state document remain untouched;
this report is the scoped implementation/state record.
