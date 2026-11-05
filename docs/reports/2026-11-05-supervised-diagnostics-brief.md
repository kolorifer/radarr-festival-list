# Safe supervised failure diagnostics

Implement an offline repair for the proven loss of failure detail: multiple
fixed HTTP/parser refusals previously collapsed to an unclassified message.
Cover finite static refusal reasons and a bounded last-observed phase; retain a
safe terminal diagnostic through existing root journal mechanisms. Failure to
record it must neither mask the primary exception nor permit replay/refund.

Keep all authority, privacy, expiry, storage, response, accounting and parser
guards. Never retain/print raw exceptions, keys, headers, bodies, paths or
provider reasoning. Use the actual HTTP/framing/parser path with fake network
I/O, plus installed-module no-leak tests. Independent review and exact supported
CI precede a repository merge under standing authorization.

No real journals/runtime/evidence changes, live/account/source calls, real key
input, extra slot, renewal, refund/reset, budget extension or deployment. This
repair cannot reconstruct discarded historical details or authorize a new test.
