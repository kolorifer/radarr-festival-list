# Bounded observation after one synthetic POST

The fixed synthetic HTTP path now obtains a120s observation allowance only from
the active held-root session's consumed opaque token, exact body, credential,
project and responses endpoint. Existing full authorization checks still run
before DNS, connect and POST and retain the prompt-derived at-most60s deadline.
Other paths receive no allowance and keep their original25s total timeout.

The existing POSIX timer begins with the original25s setup/send deadline. After
one POST returns, it verifies that bound has not expired, then makes a single
transition to a deadline anchored at that POST-completion monotonic timestamp.
Socket receive timeout is set to the remaining observation budget. Header and
body reads never restart it; the same absolute timer and checks cover all120s.
No new deadline service, polling, request retry, model parameter or endpoint was
introduced. A proposed120s bound is not measured provider latency or a guarantee
of completion.

The timer callback and explicit checks distinguish finite local setup and
observation deadline reasons. The CLI classifies both as
`local_deadline_outcome_unknown`; ordinary network timeout remains separately
unknown. No raw exception/header/body/key is exposed. The existing diagnostic
journal records the last observed phase without changing consumed reservations.
Generic timer callers retain their previous behavior.

Receipt validation continues correlating the frozen permit, request/project,
HTTP result, parser and accounting. It does not renew send authority: a bound
receipt can complete after that authority expires, while attempts to use the
expired/consumed token for another send still refuse. Cleanup and parser guards
are unchanged.

Six new offline tests passed: a real26s response delay through fixedHTTP and
framing/parser, one POST, absolute trickled-body cutoff, setup still bounded,
expired authority with a valid late bound receipt, real alarm reasons/restoration,
single observation transition and actual installed-module safe output. Slow body
and expiry tests use explicit simulated clocks; the26s test uses real elapsed
time and the actual timer. Fixtures replace network I/O only and use invented
state/dummy input. Independent review and exact-head CI are recorded in the PR.

No installed runtime, real evidence/journal, key, account or provider was changed
or accessed. All four live opportunities and nine-cent reservations remain
consumed. Historical request completion/charge remains unknown; the patch cannot
recover discarded details or authorize another live attempt. The unrelated active
cleanup task and all production/model/request behavior are preserved.
