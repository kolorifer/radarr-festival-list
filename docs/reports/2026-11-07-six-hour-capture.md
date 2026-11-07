# Finite six-hour one-event capture horizon

## Agreed brief

The architect selected a six-hour maximum for one future capture on the already
selected source under the owner's one-case continuation instruction. Six hours
is an implementation choice, not a measured arrival guarantee or an owner quote.
Previous one-hour grants remain closed and immutable. No automatic rearm loop.

## Implementation

The collector accepts a finite future expiry at most 21,600 seconds from the
current accepted outcome. The existing source, strict envelope, privacy,
currentness, eligibility, process nonce, one-event burn and exclusive output
checks are unchanged. This is a remaining-horizon bound, not an issued-at claim.
An operational issuer must independently bind activation and a finite deadline.

## Validation and deployment

Seven invented Handler/SQLite checks cover expiry, exact six-hour horizon,
over-horizon, NaN and both infinities, and single-event retention. Independent
review and exact-head Python 3.12/3.13 CI gate merge. No broad local baseline
rerun is required by this task; full supported suites run in CI.

Deployment is held pending a concrete separately accepted selective update and
one controlled lifetime transition with fresh startup evidence. The prepared
parent must retain 121 observations/129 phases, a 180-second interval, one
21,600-second grant/deadline, and one disable/inspection. Existing locks and
protected output ancestors remain held during the longer wait. A finite wait
does not guarantee a qualifying event; interruption/in-flight limits remain.
No live deployment, restart, grant, provider request or notification is effected
by this repository change. The unrelated active task brief is preserved.
