# Separate bounded response observation

Fix the reproduced synthetic timeout: the existing25s timer included waiting for
a reasoning response. Keep the at-most60s single-send authority and original25s
absolute setup/send bound. Only an already-authorized fixed synthetic request
gets120s absolute monotonic observation after its one POST returns, including
status, headers and body. No sliding renewal, second send, fallback or generic/
movie-route timeout change. Reuse existing timer/socket machinery.

Identify our own setup/observation deadline with finite safe reasons, distinct
from an OS/network timeout. All outcomes remain unconfirmed until exact receipt
validation; debit retention and no retry remain. Parser, correlation, cleanup
and late-bound-receipt behavior stay intact. No model/request/reasoning change.

Verify actual framing/socket flow with delayed valid response beyond25s, absolute
trickle cutoff, setup bound, expiry/no second send, timer restoration and genuine
module safe diagnostics. Same independent reviewer and exact supported CI before
standing-authorized repository merge. No actual state/runtime/evidence/key/provider
operation, fifth slot, refund/reset/re-enrollment or cap change.
