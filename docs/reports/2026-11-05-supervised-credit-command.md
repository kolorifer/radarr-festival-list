# Supervised synthetic command: completed offline implementation

## Scope and result

Connect the accepted dormant count and generation components into one local
command. No real calls, credential/account access, production activation or
merges. Published PR147 remains unchanged. This is an executable mocked flow,
not a live-ready agent or a claim that a caller evidence file authenticates facts.

`python -m ai_movie_investigator.supervised_credit --state ABSOLUTE_PRIVATE_ROOT enroll`
explicitly enrolls one existing owner-private state root once. It creates one
shared credit journal and two explicit attempt directories and records their
identities. Re-enrollment refuses. There is no automatic reset or enrollment.

`python -m ai_movie_investigator.supervised_credit --state ABSOLUTE_PRIVATE_ROOT run --evidence ABSOLUTE_PRIVATE_EVIDENCE --slot 1`
validates the private evidence record and the real gate before prompting or
mutating state. Today that gate refuses unconditionally, so this command requests
no key and consumes no slot. Do not bypass or monkeypatch it for a real call.

With only the absent verifier preflight and HTTP boundary replaced in tests, the
same command runs: no-echo credential prompt -> durable count reservation ->
fixed count receipt -> trusted-parent context -> durable generation reservation
-> fixed synthetic generation -> validated retained result. The root lock serializes
all steps; an attempted slot remains consumed across restart or interruption.
A count timeout never triggers generation or a count retry.

The key is an in-memory ExplicitCredential only. Real terminal checks and treating
getpass fallback warnings as errors prevent echoed input. No argv/env discovery,
key file, logging or serialization. Public failure output contains no exception
or remote response. Exact request/model/schema and existing project header remain
bound; no movie inputs, tools, model upgrades or automatic retries are accepted.

## Credit accounting

Each count request conservatively reserves a full cent, and generation reserves
another cent in the same existing five-cent ledger. One successful supervised
count+generation therefore holds two cents, not one. Count price evidence must
establish a maximum no greater than one cent before any prompt, reservation or
HTTP; missing fee/coverage evidence refuses. This does not assume counting is
free. Each generation retains its full cent even when output/accounting is
unknown. Only two explicit supervised slots are exposed; no automatic replay.
The ledger is the sole supervised writer's intact pinned journal. No adversarial
owner-proof anti-rollback service is introduced; missing/replaced files refuse.

## Verification and remaining live prerequisites

Seven executable command tests and the existing related tests pass on available
system Python 3.9 (64 focused tests total). The independent existing reviewer
accepted the connected command and repeated all seven command tests against an
isolated installed package. Review found and verified the closed-gate-before-
prompt/debit correction. Runtime hashes match the declared closure.

Both retained supported Python 3.12 and 3.13 installations fail before collection
because standard-library encodings are missing. No cause is attributed; no
runtime repair/download occurred. These are environment failures, not test
failures. Supported exact-head CI is required for this candidate.

Remaining live prerequisites are precise: resolve the existing merge block;
establish an authoritative count-fee policy and complete count coverage for the
selected model; supply a restricted key through the local no-echo prompt; and
review the narrow live authorizer that verifies the operator's dated account
facts and exact operation rather than trusting a JSON assertion. The generic
production gate stays closed. The command connection itself is implemented;
external authority is deliberately not fabricated. The existing Default project
is adequate absent a concrete permission/isolation conflict; no new project is
required merely by this code. Current account/project observations remain private.
