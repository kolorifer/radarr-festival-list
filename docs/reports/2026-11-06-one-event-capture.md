# One-event collector capture engineering report

Implementation only; not deployed or activated. The existing Handler passes
its authenticated bounded raw body to an optional transaction hook. Strict
known-field validation excludes torrent evidence and unknown raw fields.
Native delivery rowid, source UUID, selection-event digest, evidence and current
case version are bound inside the ingest transaction; delayed/future-clamped,
unmatched, reviewed, seeded, conflicting and non-admissible routes cannot be
captured. The receipt hashes the exact received bytes, not reconstructed JSON.

An explicitly prepared Server initializes one unpredictable in-memory nonce
once. Its globally locked lifetime latch cannot reset on config/grant reload,
toggle, failure or interruption. The grant is hash-pinned, private and bounded
to exact source/channel/status/reason, with explicit first_matching or
exact_external_id mode. The current configuration is rechecked before burn.
Reservation uses create-only private files and file/directory fsync. Only after
SQLite commit are body and receipt created. Raised capture-only failures and
cleanup errors do not alter ordinary intake ACKs. Grant I/O/validation exceptions
disable capture for the lifetime; failed reservation consumes it. A fresh server
rejects the old nonce even if no durable failure evidence survived.

Authenticated preparation health supplies a finite explicitly volatile phase,
nonsecret nonce and consumption state; it does not validate authority. Default
configuration/health behavior is unchanged, including no capture-file I/O or
nonce initialization. The documented collector closure now includes the one
new sibling module; no investigator runtime or sandbox changes.

Validation: 23 new focused tests pass, including real Handler + fake socket and
SQLite, races/restart/reload, reservation/fsync/commit/partial/cleanup failure,
raw receipt linkage, privacy/path checks, config revocation, atime-only versus
mtime/ctime/size changes, first-matching mode and isolated six-module startup.
Earlier focused regression run: 42/43 passed, one existing torrent-evidence test
could not import local bs4; retained, no dependency repair. Supported exact-head
Python 3.12/3.13 CI and independent exact-head acceptance remain merge gates.

Limitations: recognized-pattern filtering cannot prove arbitrary raw text has
no secret. Explicit body privacy approval is necessary and is never API
permission. Synchronous filesystem calls can stall past the existing HTTP
socket deadline; bounded kernel-I/O latency is not claimed. Uncertain ACK keeps
existing retry/duplicate behavior without replacement capture. Single live
nonforking instance verification is a future deployment prerequisite, not an
inference from these fixtures. Owner-created grants/destination and all actual
operations remain closed. Future activation contract is documented in
`deploy/IDENTITY_TRIAGE.md`. Unrelated current task documents were preserved.


Final closure correction: the shared store module is also pinned by the
existing 42-file investigator manifest. Its hash is updated without adding the
optional collector capture module to that installer. An isolated 42-file copy
passes installation verification and ordinary Store.ingest with capture=None;
no capture import occurs. Initial public head d8500891 omitted this manifest
update; retain its CI result. Only the corrected exact head may merge.
