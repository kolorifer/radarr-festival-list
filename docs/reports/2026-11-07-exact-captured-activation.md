# Exact captured-case wrapper activation

The captured request/transport/receipt/report route was connected but its real
activation gate was unconditional. A separately reviewed private operational
wrapper can now enter an exact-artifact-bound context. Ordinary commands and
environment settings remain closed; there is no caller-selected activation CLI.

The wrapper is the trusted local issuer. It must independently pin the actual
owner scope, main review, verified original capture and receipt, exact canonical
consent, selected source mapping, installed runtime closure and its invocation.
The API does not authenticate an arbitrary caller's hash or claim a cryptographic
owner signature. Arbitrary same-process code remains outside this trust boundary.
Only independently retained/authorized evidence and decisions may enter the
packet; missing evidence stays empty/unknown, never manufactured from a receipt.

The context checks stable private files, hashes, runtime closure, wall-clock
rollback/expiry and receipt-derived occurrence. Existing grant checks compare
the full accepted consent, while held-case validation reconstructs the canonical
packet from the exact body and source mapping. A matching original hash label
cannot conceal altered facts. Existing held/pre-wire checks revalidate the
context; root/case/credit locks, account/project selection, request bounds,
3-cent reservation, one-send/no-replay and receipt completion remain unchanged.

The private wrapper runs as its own one-shot process and enters the existing
supervised module via runpy with its real module spec and temporary __main__.
The existing Keychain one_shot_process check and watchdog remain unchanged;
no native/import/no-UI safeguard is relaxed. Direct imported Keychain calls
still refuse. The installed-copy test exercises this route with fake Keychain
and HTTP socket I/O, actual serializer/parser/receipt/report, and a separate
network/subprocess/native audit tripwire. It honestly records simulated
transport and generation_invoked=False; it is not an actual movie assessment.

Focused tests cover closed defaults, exact connected completion, artifact and
inode replacement, changed consent, altered normalized facts, expiry/runtime
mismatch, clock rollback, receipt/body mismatch, uncertain-send no-retry and
installed module entry. Invented filesystem reads replace ancestor/ACL I/O in
these tests so all fixtures remain in the isolated temporary checkout; they do
not prove production filesystem access. The production reader is unchanged.
Initial installed test failures were harness-only: ctypes' standard bootstrap
was initially caught before instrumentation setup, then a helper referenced the
wrong module. Both were corrected; no real provider request or retry occurred.
Independent review and supported exact-head CI are required before acceptance.

No real activation record, new movie disclosure, Keychain read or provider call
is created by this code change. Main must inspect actual capture/projection and
accept the exact private wrapper before one real request. Outputs remain private
and unsent, with no identity/acquisition approval or notification authority.
