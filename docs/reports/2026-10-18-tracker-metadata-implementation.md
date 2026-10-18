# Engineering report: tracker metadata movie identification

**Specification:** [implementation brief](2026-10-18-tracker-metadata-implementation-brief.md),
[investigation](2026-10-18-tracker-metadata-investigation.md), D005/D008/D009/D010.
**Result:** Implemented for review; not merged, deployed or activated.
**Repository revision:** `feature/tracker-metadata-identity`; containing commit/PR
provides the implementation reference. Investigation baseline: `258d9f9`.
**Verification date:** 2026-10-18, local Python 3.12 plus read-only seedbox/API probes.

## What changed

Autobrr can carry explicit movie IDs, but movie-intel previously ignored them.
The service now validates `meta_imdb`/`meta_tmdb` before using an identity. An IMDb
ID must produce exactly one TMDb movie, with the same canonical IMDb ID on the
movie response. A supplied TMDb ID and local identity must agree. Direct TMDb IDs
are checked against the movie endpoint and canonical external IDs.

The source title must match a canonical, alternative or translated TMDb title;
the source year must appear in the primary date or actual release-date records.
Unicode case/punctuation and `&`/`and` normalization apply only to this ID context.
There is no generic year tolerance or synopsis/prefix inference. Cards explain
when TMDb documents the announced year in addition to its canonical date.

Explicit conflicting/unmapped IDs never fall back to title search. New outcomes
are `verified_tmdb`, `imdb_associated`, `needs_review` and `unresolved`. A tracker
IMDb association is labeled as such, not independently verified IMDb metadata.
It cannot enable Grab. The original exact-title/year search and duplicate rule
remain the fallback when source IDs are absent and no applicable adapter is
enabled. Routine quality/existing-file rejections still skip enrichment lookups.

The optional TorrentLeech adapter addresses the current IRC path's missing IDs.
It is **disabled by default**. When enabled, it uses dedicated private session
cookies and fetches only the exact known listing on the allowlisted HTTPS host.
It checks structural release headings, one IMDb field, absence of a login form,
and no conflicting IMDb IDs. It rejects redirects, unsafe URLs, unexpected
content, changed markup, oversize bodies and unavailable authentication.

The adapter enforces one active fetch, a minimum one-second request interval,
1 MB decoded response limit, connect/read/streaming limits and Retry-After on
429. Busy/rate-limited callers fail safely rather than queue indefinitely. Two
separate bounded memory caches isolate listing associations from validated movie
identities and from the legacy title cache. Success TTL is 15 minutes; failure
TTL is 60 seconds; each holds at most 256 entries. Context and both supplied IDs
are part of identity keys. Cookie rotation invalidates listing cache entries.
No new persistent private state or migration is introduced.

Only verified new-path TMDb identities enter the existing action gate. Pending
actions retain source/year provenance. Original release references, explicit
confirmation, `searchForMovie=false`, durable attempt status and single-use/replay
safeguards are preserved. No scoring, ingestion, autobrr configuration or download
policy changes are included.

## Files and components changed

| Component | Purpose |
| --- | --- |
| `tmdb_resolver.py` | ID validation, movie crosswalk/context checks, isolated bounded cache. |
| `tracker_metadata.py` | Optional exact-listing fetch/parser, private auth and transport limits. |
| `movie_intel_service.py` | Source extraction, explicit states, safe rendering and action eligibility/provenance. |
| `deployment_config.py`, `deploy/environment.example`, `deploy/README.md` | Offline auth/config validation, disabled default, activation and rollback instructions. |
| `test_external_identity.py`, `test_tracker_metadata.py`, `test_movie_intel_http.py` | ID/parser/transport regressions and full native-ID approval workflow. |

## Acceptance criteria and evidence

| Criterion | Result | Evidence |
| --- | --- | --- |
| IDs resolve without title popularity guesses | Passed | Exact pair/round-trip tests; Nocturne resolves in fresh read-only comparison. |
| Wrong IDs/context cannot acquire | Passed | Conflict, wrong title/year, malformed ID, non-movie, ambiguous mapping and action-gate tests. |
| Translation and documented years work | Passed | Fresh comparisons for German titles, Insidious, The Lie, Lake Mungo and Haunted Heist. |
| No cache bypass of new conflicts | Passed | Tests isolate supplied pairs/title/year from legacy title cache; expiry and credential rotation tested. |
| Listing is exact and safely bounded | Passed locally; one real page verified | Parser/URL/auth/redirect/login/body/time/rate tests; Fragmentos page's two structural headings matched the retained release and returned IMDb `tt33503751`. |
| Exact-release approval remains intact | Passed locally | Native-ID webhook creates no acquisition until explicit confirmation, then pushes original reference with search disabled and returns 410 on replay. Existing durable-state HTTP regressions retained. |
| Production remains verified | Passed read-only | Clean `dcae919acbc87f1a33de84b7c6b628668b400b07`, active/running, NRestarts=0, loopback health200, 1,909 catalog movies, Radarr configured. |

### Fresh read-only sample comparison

The new resolver ran in an isolated in-memory process on the seedbox against the
same 16 public IMDb/title/year inputs as the investigation. It did not import the
service, modify its caches/state, create actions, send notifications or acquire
anything. The optional parser fetched one retained listing using the existing
investigation session in memory; this did not provision production adapter auth.

Of the **15 previously unresolved** inputs: **9 verified TMDb identities**, **4
unmapped IMDb associations**, and **2 review cases**. The Snowman control also
verified, so 10 of all 16 inputs verified. This is a bounded sample, not a general
recall or false-positive estimate.

| Input | New result |
| --- | --- |
| Insidious (2010) | Verified TMDb 49018; documented 2010 release. |
| Nocturne (2020) | Verified TMDb 643550. |
| The Lie (2020) | Verified TMDb 539649; documented 2020 release. |
| Lake Mungo (2008) | Verified TMDb 27374; documented 2008 release. |
| Withnail and I (1987) | Verified TMDb 13446. |
| Haunted Heist (2025) | Verified TMDb 1384040; documented 2025 release. |
| Ein Mann auf den Knien (1979) | Verified TMDb 183635; authoritative alternative title. |
| Ice Age 4 Voll verschoben (2012) | Verified TMDb 57800; translated title. |
| Ice Age 2 Jetzt tauts (2006) | Verified TMDb 950; alternative title. |
| Fragmentos (2025) | IMDb association `tt33503751`; no TMDb mapping. No hardcoded 1356955 override. |
| Syd Barrett Up Close And Personal (2007) | IMDb association only; no TMDb mapping. |
| Rainbow In Performance (2025) | IMDb association only; no TMDb mapping. The investigation's IMDb year discrepancy remains a limitation. |
| Steve Howe Live Legends (2003) | IMDb association only; no TMDb mapping. |
| Medeski Martin Wood Not Not Jazz (2024) | Review: performer-prefixed source title does not match TMDb titles. |
| Hamnet 2025 / source year 2016 | Review: malformed source title (and unexplained year). No automatic repair. |
| The Snowman (2017), control | Verified TMDb 372343; already resolved by previous implementation. |

## Tests run and results

- `.venv/bin/python -m unittest -v`: **373 passed**, no skips (117.394s).
- Focused preliminary resolver/notification/action/HTTP/config suite: **92 passed**.
- Final `test_external_identity` + `test_tracker_metadata`: **36 passed**.
- `.venv/bin/python production_scoring.py --check`: passed (1,909 candidates /
  387 qualified), with no policy/data changes.
- `git diff --check`: passed. No dependencies changed.

Initial validation caught a fixture cache-isolation mistake and a test insertion
indentation error; both were corrected. The sandbox initially denied loopback
HTTP server binding, so the offline HTTP/full suites used approved local socket
access. These were development/test issues, not production incidents.

## Deployment result

**Not deployed or activated.** Production remains at verified runtime
`dcae919acbc87f1a33de84b7c6b628668b400b07`; no restart, production checkout edit,
configuration write, action/cache rewrite or deliberate Telegram/download test.
The earlier PR #41 Boxtrolls live test is historical evidence for the unchanged
acquisition path, not a live test of this implementation.

Activation requires dedicated session provisioning, account-limit review and the
normal deployment/preflight/backup/health process. Disabling the adapter restores
the existing no-ID fallback; native-ID validation remains active in this code.
Full rollback uses the prior verified revision and preserves current action state;
never restore an old snapshot over completed/uncertain acquisitions.

## Unexpected findings and remaining limitations

- The stricter automatic title check recovers nine unresolved samples, compared
  with ten human-corroborated candidates in the investigation. The extra performer
  prefix is deliberately not stripped or matched through synopsis text.
- The tracker is an association source, not an independent IMDb metadata provider.
  Four unmapped inputs remain non-actionable. No new IMDb/Letterboxd ratings,
  recognition data, or independent IMDb-year verification is supplied.
- Current TorrentLeech IRC notifications still have no native IDs. The default-off
  adapter therefore must be provisioned/activated before those production cases
  benefit. A dedicated production cookie has not been tested or created.
- HTML/session changes, auth expiry, busy requests and rate limits can prevent
  enrichment. Failures preserve readable notifications without approval. Only one
  real listing exercised the new parser; transport failure cases are synthetic.
- Memory caches and rate backoff clear on restart. No persistent negative cache
  or durable cross-process rate coordination is claimed; the deployment is a
  single movie-intel process. Request ceilings are not tracker rate guarantees.
- Historical webhook bodies were not retained; upstream field-loss conclusions
  remain source/config inference as detailed in the investigation.
- Existing provider/downstream logging limitations remain. This change makes no
  universal guarantee about Radarr or downloader logging of release URLs.

## Commit and PR reference

See the containing implementation commit and draft PR on
`feature/tracker-metadata-identity`. No merge or production activation is requested
by this report.

## Project context updates

Saved this report and the implementation brief; updated PROJECT_STATE to separate
implemented/tested/read-only evidence from deployment. D005 remains the governing
conservative identity decision. The unrelated cleanup assignment in CODEX_TASK.md
was neither executed nor cleared. Product presentation/activation review remains
with the user and main ChatGPT conversation.
