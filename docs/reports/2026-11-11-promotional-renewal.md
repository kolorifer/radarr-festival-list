# Append-only successor promotional grant

## Agreed scope

An expired standing promotional grant blocks the selected private movie assessment even when fresh same-account, same-project free promotional credit is available. Add a single explicit successor-grant record; do not reenroll, reset, migrate, purchase credit, invoke credentials or send requests in renewal. Live state remains untouched during implementation.

## Implementation

`renew-promotional --evidence` validates fresh promotional-only evidence, same account/project, unchanged policy, later credit expiry and sufficient funds for retained reservations plus one request. It appends an exact original-grant/root-prefix/credit-prefix-bound renewal. The original grant and every attempt/reservation remain intact. Renewal is refused before old expiry, if already renewed, or if the latest attempt lacks a completion or diagnostic. A diagnostic does not refund an uncertain reservation.

Future attempts bind the renewal hash. Old slots retain original authority and cannot be revived. Cumulative charges remain deducted, including ambiguous attempts; there is no automatic retry. Preparation, retained-send checks and credential precheck use the applicable grant with the same policy and per-request debit. Fresh evidence still governs every later operation.

## Validation and delivery boundary

Focused tests cover append preservation, fresh successor acceptance, mismatched account/project, cash, stale/low balance, duplicate renewal, pending old attempts, ledger corruption and simulated serialized transport/no replay. Independent review and exact-head Python 3.12/3.13 CI gate merge. No live account/key/provider operation or state append is part of implementation; exact installed-runtime and operational acceptance are separate.
