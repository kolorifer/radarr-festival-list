# Stage 2 movie identity research — engineering report

**Implemented and finite live pilot completed; proposals await owner review.**
[PR52](https://github.com/kolorifer/radarr-festival-list/pull/52) remains unmerged.
[Issue51](https://github.com/kolorifer/radarr-festival-list/issues/51) ·
[Authorized brief](2026-10-18-identity-research-brief.md) ·
[Operation/safety runbook](../../deploy/IDENTITY_RESEARCH.md).
No recurring research, catalog writes or automatic identity corrections activated.

## Revisions and production boundary

- Final implementation/tested and installed-disabled revision: `2de1ba88d2a8be6fcbd87e0db2a15a089a0baa4a`.
- Actual live pilot worker: `efcad3fdb6ce44469bc7087b1ccc1800b3bc4290`.
  The later comparison-only refinement separates absent metadata from conflicts;
  all four saved live responses were replayed offline, with **zero additional GETs**.
  Original pilot proposals/evidence are preserved, not rewritten. The final disabled
  installation changes only the comparison module; boundary files are identical
  to the actual installed proof. Disabled startup leaves the ledger at19requests.
- movie-intel remains clean at `30adc20b7d46bbe89bb14728d778d9d1142c57c6`, same
  running process, observer OFF. Local/public health 200,1,909 movies.
- Collector remains `3a2090703f9b4b85d5a3982b0e99ef452a625420`, installed files and
  config unchanged, active/running, same PID, NRestarts=0. Original Stage1 schema v1
  and provisional/unresolved-only CHECK remain intact.
- Separate research worker is inactive/default-off, no timer/enabled target;
  copied TMDb credential removed and finite pilot ledger permanently closed.
  Only triage configuration/observation state was backed up. No action snapshot,
  notification replay, approval token, Radarr request, addition, search or download.

## Four findings and proposed next actions

The short review labels below are public labels; exact case/candidate IDs, source
hashes and method/query/result trails are retained only in private evidence.
The fresh observations below are **TMDb GET results**. Publisher/IMDb corroboration
comes from the earlier issue44 private evidence, captured starting14:02UTC; those
public sites were not freshly fetched during this pilot.

| Review case | Fresh TMDb findings | Proposal and unresolved questions |
|---|---|---|
| S01 — Fragmentos (2025) | `/find` still lacks the IMDb movie crosswalk. The Alejandro Rangel feature has 2025-09-04 release, 108 minutes and no IMDb ID. Three previously investigated same-name candidates inspected;18 distinct same-title candidate IDs recorded, detail limit reached. One competing record lacks director/runtime; another has different directors. | **Strong proposal for the Rangel film**, supported by historical director/cast/story/country/date evidence. Review a catalog crosswalk correction; preserve108/110/111-minute disagreement. No local override or acceptance. |
| S02 — Steve Howe Live Legends | `/find` still unmapped. Candidate **Steve Howe (2002)** is 52 minutes, Jonathan Glazier, no IMDb ID. Source title/year remain Live Legends/2003; candidate has 2002-04-19 date. | **Strong proposal**, supported by historical portrait/director/runtime evidence. Review title/alias and date provenance together with crosswalk; a crosswalk alone would not repair the current context checks. |
| S03 — Syd Barrett Up Close and Personal | Missing crosswalk. Two recorded variants, one movie and TV page each, produced no supported exact target; zero candidate detail requests. | **Unresolved target**, movie/documentary classification supported historically. Await better catalog/source evidence; do not substitute neighboring Pink Floyd/Syd Barrett films. Search limits do not prove catalog absence. |
| S04 — Rainbow In Performance | Missing crosswalk. **Rainbow: In Their Own Words (2006)** remains only a competing, unaccepted record: 75 minutes, absent director, different title; source announcement year 2025 conflicts with historical2006/2007 evidence and113-minute edition. | **Unresolved edition/identity**. Human/distributor review before any cross-map or context repair. Missing director is an evidence gap, not proof of a different director. |

Historical corroboration: [Fragmentos / Visor](https://visor.com.ve/filmography/fragmentos/),
[Steve Howe / Tubi](https://tubitv.com/movies/100052816/steve-howe-live-legends),
[Syd Barret / Tubi](https://tubitv.com/movies/561762/syd-barret-up-close-and-personal),
[Rainbow / Apple](https://tv.apple.com/us/movie/rainbow-in-performance/umc.cmc.2kerpxeqx3fn84nhiuujg2idf).
These are provenance references, not new pilot provider requests or instructions.

**Yield:**2 promising human-review proposals among 4 deliberately selected known
failures; zero accepted mappings or runtime corrections. The machine persisted 4
review results:3 candidate-review cases (including the rejected Rainbow alternative)
and1 missing-crosswalk case. Candidate-review status is **not** an identification.

## Additional sample and actual intake coverage

Candidate eligibility used affirmative source evidence, not the number of
provisional groups. Frozen Stage1 snapshot: 460 evidence versions, 349 provisional
groups, 4 explicit seeds,zero outcome-hook rows. Only 4 observations carried IMDb
IDs; native IRC records generally lack them. No tracker session was provisioned.

Read-only journal correlation found 15 distinct identity outcomes joined by release
name digest to retained observations: 14 `external_id_verified`,1 `skipped_routine`.
The predetermined first 3 distinct chronological joins were **Van Helsing (2004)**,
**Wes Craven's New Nightmare (1994)** and **The Onion Field (1979)**. All 3 already had
verified external identities, so were excluded without new provider calls.
**Zero additional genuinely unresolved cases were demonstrated.** No substitutions
or cherry-picked provisional groups were admitted to fill the allowed quota.
This is a small eligibility audit, not 3 additional live research cases.

At 18:43:39UTC, collector counters showed **8 actual release.new movies accepted**,
3 release.new rejections,450 retained accepted/4 quarantined,454 retained duplicate
attempts,4 seed admissions/4 seed duplicates. Store totals:458 distinct releases,
462 evidence versions,351 provisional groups. Maximum recorded live lag0.0833s;
recent delivery observed. Original observations and acquisition behavior preserved.
No identification percentage is claimed for 351 groups or undelivered announcements.
Observer remains off/lossy; autobrr lacks a durable publisher outbox and logging is
currently disabled. Quiet sources cannot reliably be distinguished from lost events.

## Pilot accounting and evidence

One live invocation (18:42:44–18:43:16UTC),4 admissions/4 attempts/4 review results, all awaiting evidence:

| Provider/method | Requests |
|---|---:|
| TMDb `/find` |4|
| TMDb movie search, page1 |5|
| TMDb TV search, page1 |5|
| TMDb movie details with appended metadata |5|
| **Total TMDb GETs** |**19**|
| TorrentLeech/other metadata providers |**0**|

All 19 reservations completed successfully. No HTTP errors, auth/rate failures,
retries, restarts, budget exhaustion or unrecorded HTTP request. One run stayed
under 10 cases/50 requests; the combined cap 100 has 81 unused reservations, now
inaccessible because the pilot is closed. The TLS boundary feasibility/final
proofs made handshakes only, no metadata HTTP; they are separate from this ledger.
Historical frozen replay:19 lookups/4cases/zero external requests. Final code replay
of actual pilot responses:4cases/zero extra requests. Reimporting the same4 inputs
returned4duplicates without changing attempts, proposals or request counts.

Private host evidence: `~/.local/state/identity-research-issue51-evidence/` contains
source/test manifest, triage-only backup, original proposal export, invocation and
sanitized audit. `~/.local/state/movie-identity-research/research.sqlite3` holds
immutable input versions, leased attempts, request ledger/cache and proposals;
owner-only modes700/600. Matching local private evidence is retained outside Git.
No raw descriptions, tracker URLs, capability links or private IDs appear here.

## Implementation and safety

New `identity_research_{store,provider,sandbox}.py`, `identity_triage_worker.py`,
manual unit/config/runbook and focused tests. Separate SQLite schema needs no
migration/rollback of Stage1. Validated frozen manifests explicitly identify seed,
unknown outcome, identifier contradiction or verified-resolver failure. This pilot
uses manual frozen admission, **not an automatically activated intake dispatcher**.

A singleton persisted ledger caps4seeds+10additional cases and100requests across
invocations; each run caps10cases/50requests. Reservations commit before transport;
crashed/unknown requests stay charged. Material dedup, append-only evidence/proposal
versions,600-second leases and fencing prevent stale workers rewriting new evidence.
Auth errors suspend the provider;429 persists Retry-After; temporary failures use
15m/1h/6h/daily positive jitter, missing mappings7d/30d. Due times do not run jobs.
Cache expiry1day; no new permanent retention/purge policy activated.

The installed worker initially opens one certificate-verified TLS connection to
fixed `api.themoviedb.org`, then applies Landlock ABI6/libseccomp before metadata
or credentials cross the connection. All inherited fds except clean stdio and
that socket are closed. Only own code/config/runtime are readable and own state
writable. Effective installed-process proof denied protected read/write, symlink
escape, inheritedfd access,/proc,newTCP/IPv6/UDP/Unix sockets, metadata mutation and
connect even on the surviving socket. Own config/SQLite WAL and verified TLS work.
Stage1 confinement is unchanged. Unsupported isolation fails closed.

Trusted client code allows only fixed metadata GET routes, no arbitrary URL,
redirect, pagination or reconnect. The kernel restricts network/filesystem
capabilities; it is **not an HTTP-method-aware firewall**. Requests have4-second
idle/10-second total deadlines,1MiB response bound, strict JSON/projection and
persisted1-second provider spacing. Worker has no tracker cookie, Radarr/Telegram/
autobrr-admin/downloader credentials or action state. The broader tracker-session
capability is deliberately not provisioned. No new broker/root privilege required.

## Technical verification

Final runtime `2de1ba8`: **481 tests pass on seedbox Python3.13 and both CI versions
3.12/3.13**. Local Python3.12:481 total,479 pass and2 Linux-only skips. Focused research
suite36 tests, including2 Linux kernel gates across the full project. No dependency
changes; pip check, frozen production scoring and deployment config preflight pass.
CI: [final runtime run](https://github.com/kolorifer/radarr-festival-list/actions/runs/39155611738).
Pilot runtime `efcad3f` independently passed479 full tests on seedbox/bothCI;
local477pass/2Linux-only skips before live activation.

Tests cover immutable Stage1 schema, duplicate/material version handling,
concurrency, busy/full rollback, permissions/symlinks, leases/crash fencing,
50/100 request and10/14case caps through restart, auth suspension,429/date/jitter,
cache expiry, response size/total deadline, hostile/duplicate JSON/secret echo,
fixed routes/redirect denial, TV/ambiguous/remake/source-ID/director/runtime/title
negatives and missing-context distinctions. Real installed boundary and disabled
startup were separately verified. This is not inferred from synthetic unit tests.
Initial local full run was blocked by sandbox loopback permissions; rerunning with
local test socket permission passed. No application failure was hidden by that retry.

## Historical storage warning

The previous single `storage_unavailable` warning has no saved exception reason;
root cause remains **unknown**. Heavy bounded synthetic import/live/metrics load
can reproduce SQLITE_BUSY. That supports contention as a possibility, not a
historical diagnosis. Busy transactions returned failure, then retried cleanly;
commit-before-ACK and quick_check passed. Production warning count stayed 1 across
preflight/pilot/postflight while actual intake continued. No current instability
was observed. No inference of zero upstream errors is made from disabled logs.

This PR adds fixed sqlite_busy/locked/full/io/readonly, permission/disk/path and
validation diagnostics without exception text. **Those collector diagnostic changes
are not deployed**: the collector remains on its previously verified version.
A later reviewed rollout can improve attribution without changing intake semantics.

## Recommendations requiring separate review

1. Approve or reject the two promising catalog/context proposals individually;
   preserve Syd Barrett/Rainbow unresolved until stronger evidence. Any external
   catalog write or exact runtime repair needs its own authorization/regression.
2. First review a sanitized outcome-correlation channel/selection workflow; do not
   enqueue all provisional groups or silently enable the current lossy observer.
   Until then, retain manual frozen admission and review-only operation.
3. After that review, consider a daily eligibility scan with **maximum 5 cases or
   25 TMDb GETs/day and100 GETs/week**,7d→30d missing-crosswalk rechecks. Pilot cost was
   19 GETs/4 cases; this is a proposal, not a recurring budget authorization. Keeping
   the closed finite ledger separate from future budget epochs requires a reviewed
   implementation change. No tracker research allowance proposed yet.
4. Suggested retention for approval:90days sanitized provider projections,
   180days source/attempt/proposal provenance, with reviewed resolutions/audit
   history retained longer. Keep1day cache freshness distinct from retention;
   no purge implemented or run now.
5. Stage3 review should show evidence age, source assertions, candidate IDs privately,
   missing support versus contradictions, competing editions, proposal version and
   approve/reject/defer decisions. No Telegram digest or action capability yet.

Remaining limits: incomplete source delivery/correlation; no eligible additional
unresolved cohort demonstrated; manual manifest admission; bounded searches/three
details rather than catalog exhaustiveness; no tracker refresh; historical publisher
evidence not freshly verified; one TLS connection per invocation; ABI6/libseccomp
host requirement; original warning unexplained. Technical safety/pilot success is
separate from owner acceptance of the proposed identities or recurring operation.
