# Finite identity research worker

This component is separate from Stage1 and movie-intel. It produces private
review proposals and cannot apply them. No timer or install target is supplied.
The pilot ledger is a singleton with fixed caps; changing/deleting it is not a
budget reset workflow and requires renewed operator authorization.

## Gates and layout

Requires Linux x86-64, Landlock ABI6+, system libseccomp.so.2, Python3.12/3.13 and
user systemd. Run full tests, pip check, scoring/config checks and actual installed
security proof before metadata requests. Preserve existing services and schema.

Install immutable tested copies of identity_triage_worker.py,
identity_research_{store,provider,sandbox}.py and identity_triage_{store,sandbox}.py
under ~/.local/lib/movie-identity-research (directory700, files600). The latter
modules are reused helpers; this does not change the installed Stage1 collector.
Private config ~/.config/movie-identity-research/config.json is mode600 under700,
with exactly enabled=false and tmdb_token="" initially. Provision only the existing
TMDb read token. Never copy the whole movie-intel environment or tracker cookies.

State ~/.local/state/movie-identity-research is700. input.json is a private600
frozen projection, validated by validate_case; include source digests, observation
times and affirmative unresolved eligibility. Use only recorded evidence-derived
variants and candidate IDs. No source URLs or downloader capabilities. Invalid
input is quarantined by refusing the complete run before HTTP; preserve the
operator's original input for inspection. No untrusted provider text is executed.

Install identity-research.service, reload the user manager, but do not enable it.
Trusted startup opens one certificate-verified TLS connection to api.themoviedb.org;
then closes inherited fds, applies Landlock and libseccomp, and tests denials before
reading input or sending credentials. The client exposes only fixed GET metadata
routes, no arbitrary URLs, redirects, pagination or automatic reconnect. Kernel
confinement denies all new IPv4/IPv6/UDP/Unix sockets, other home/config/action
files, /proc and metadata mutation. Only the existing TMDb TLS socket remains.
The kernel restricts filesystem/network capabilities; trusted client code enforces
GET routes, response size, total deadline and request accounting. This is not an
HTTP-method-aware kernel firewall. No privilege or third-party broker required.

The installed process must demonstrate actual protected-file and symlink denial,
inherited-fd closure, denied network creation, and allowed own SQLite WAL work.
Do not infer protection from NoNewPrivileges or a seccomp mode flag alone. An
unsupported syscall/library/kernel or failed denial makes startup fail closed.

## Finite operation and stopping

Back up only triage config/state. Enable the separate worker config for the
approved finite pilot and manually start its oneshot unit. One invocation is at
most540 seconds of dispatch (systemd hard bound600),10 cases,50 requests. All
invocations combined share100 request reservations,4 seeds and10 other admissions.
A reservation commits before transport; unknown/crashed requests remain charged.
Requests have10-second total/4-second idle limits,1MiB JSON response bound and
at least1-second persisted provider spacing. Closed TLS connections cannot reopen;
resume only within the existing finite ledger and authorization, never reset it.
Auth failures suspend the provider;429 persists the longer Retry-After/cooldown.
Do not clear auth suspension automatically. No authenticated error bodies retained.

The off switch is reread before every request. systemctl --user stop
identity-research.service stops immediately; already reserved requests remain
charged and leases expire. Disable config after the pilot and call close_pilot()
on that research store to make accidental later activation fail closed. A closed
pilot requires a separately reviewed future operating policy; no reset API exists.
Stage1 keeps collecting while research is stopped. Research state may be archived
privately; no migration or rollback of the original Stage1 inbox is required.
Never restore action state.

## Evidence and interpretation

Evidence and proposals are append-only; material duplicate inputs do not requeue,
new versions reopen and fence stale workers. Leases expire after600 seconds.
Permanent unresolved states are awaiting_evidence, with7d then30d proposed rechecks;
temporary failures use15m/1h/6h/daily positive deterministic jitter and longer
provider waits. These due times do not cause traffic: there is no scheduler.
Successful metadata cache entries expire after1d. All proposals need human review,
including a unique crosswalk; old source contradictions are not silently removed.
Searching no result does not prove catalog absence. The first three explicitly
stored candidates precede exact-title search candidates; candidate truncation and
all competing search IDs remain recorded. No popularity-based acceptance.

The collector's historical warning has fixed diagnostic codes in this PR only;
rolling out that collector-only diagnostic is a separate deployment choice. It
must not be confused with the unchanged collector installed for this pilot.
