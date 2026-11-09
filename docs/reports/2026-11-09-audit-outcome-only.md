# Qualified producer-verified check without a prior selected notification

## Agreed behavior

For the explicit producer-verified identity CHECK only, retain a new authenticated
outcome with an external release ID even when its current correlation is
`outcome_only`. A separate earlier selected notification is not required to
independently question that producer assertion. This does not approve identity,
remembered-identity reuse, acquisition, or production promotion.

## Implementation

The audit capture accepts only `verified` with `strong_source_id` or
`outcome_only`, the exact unknown_movie/verified_tmdb/external_id_verified filter,
and an external release identity. Original envelope, source, latest event,
evidence/material, configuration, startup, expiry, private-file and one-case
checks remain mandatory. All conflict correlations and quarantined/reviewed
routes remain excluded. Generic unresolved capture is unchanged.

Audit receipts carry an explicit correlation/source-support qualification. The
trusted captured wrapper binds that qualification into the reconstructed packet,
minimized request and private unsent report; it cannot be relabeled as strong
correlation. The matcher status remains an assertion rather than independent
identity approval. No pending-body queue, replay or later-selected recapture is
introduced. Missing qualification on this new audit receipt is refused.

## Validation and deployment boundary

55 focused tests passed locally on Python 3.12, including actual Handler/SQLite
outcome-before-selected, duplicate/new-event burn behavior, conflict/name-fallback
refusals and installed-only capture-to-admission-to-fake-wire-to-qualified-report
checks. The fake-wire path uses serialized response framing/parser and external
network tripwires. Exact-head 3.12/3.13 CI and independent review gate merge.
No broad local suite was run, per this task's explicit instruction.

No live source read, deployment, restart, capture, provider operation or spending
is part of this code change. A selective operational package remains held for
separate exact main inspection. Prior empty capture and count-only diagnoses
remain evidence, not proof of every historical failure cause.
