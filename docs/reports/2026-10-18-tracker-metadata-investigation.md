# Engineering report: tracker metadata and movie identity

**Result:** investigation complete; implementation proposal for product review only.
No identity-resolution implementation, deployment, acquisition or live test notification
was performed. The diagnostic CLI exception and its cleanup are documented below.

**Verified 2026-10-18.** Repository main: `a7c2e132b881c841e64ec10b81a512c7c9c988b4`
(merged [PR #41](https://github.com/kolorifer/radarr-festival-list/pull/41)).
Production remains `dcae919acbc87f1a33de84b7c6b628668b400b07`.
Applicable decisions: D005, D006, D008, D009 and D010; no new product decision adopted.

## Findings and recommendation

TorrentLeech has useful movie IDs that its current IRC announcement path does not
collect. Installed autobrr **v1.88.0** can already serialize `meta_imdb` and
`meta_tmdb` when populated; its TorrentLeech IRC definition does not populate them.
Movie-intel would also ignore those fields if they arrived. Both gaps matter.

Recommend **native external-ID consumption plus a bounded, authenticated lookup of
the exact known TorrentLeech listing when IDs are absent**. Validate the association
and the canonical cross-link before making an action eligible. Preserve the existing
conservative title/year fallback and all PR #41 acquisition safeguards.

Measured on 15 currently unresolved cases: **15 listings had valid IMDb movie IDs;
11 mapped to exactly one TMDb movie and round-tripped to the same IMDb ID**.
Ten have corroborating title/localization and release-year context; one, malformed
Hamnet, still needs review. Four IDs have no TMDb movie mapping. These are observed
lookup results, not a promise of 11 automatic approvals or a population-wide rate.
Simply extracting new webhook fields would recover **zero of these current IRC
cases**, because those fields are not populated on this source path.

## Fragmentos root cause

The actual retained event is autobrr release 429, supplied by **TorrentLeech via IRC**:

`Fragmentos 2025 BluRay 1080p x264 DTS-HD MA 5 1-MTeam`

MTeam is the release-group suffix, not the announcing indexer. The authenticated
listing contained the exact release name and `input[name=imdbID] = tt33503751`.
Only that IMDb ID appeared on the page; no TMDb ID was found. Access used an existing
TorrentLeech session held by Prowlarr, with no new login or credential change.
An unauthenticated HTTP 200 was a login page, so status alone was not treated as evidence.

IMDb’s official 2026-10-18 public datasets identify **tt33503751 as Fragmentos
(2025), a 111-minute movie directed by Alejandro Rangel (nm8360872, born 1997)**.
Thus the listing contains a real, specific film identity, not just a plausible name.
The title/crew/name records corroborate one another. [IMDb dataset documentation](https://data.imdb.com/non-commercial-datasets/)

TMDb’s fresh IMDb lookup returned zero movie results (and zero TV results).
The title/year search instead produced these exact-name 2025 candidates:

| TMDb | Director/context | Runtime | IMDb cross-link | Observed popularity |
| --- | --- | --- | --- | --- |
| 1530349 | Horacio Alcalá; Spain | 90 min | tt30332642 | 4.055 |
| 1377801 | Brazil; director unavailable | unavailable | absent | 1.3019 |
| 1356955 | Alejandro Rangel; Venezuela | 108 min | absent | 1.29 |
| 1492389 | Nathan Soares / Miguel Duarte; Brazil | unavailable | absent | 0.4441 |

The top lead is only about 3.11× and 2.75 points, failing the required 10× **and**
10-point rule. More importantly, IMDb’s crew data confirms the top candidate’s
director is a different person (nm3407897). Choosing maximum popularity would
select the wrong film.

[TMDb 1356955](https://www.themoviedb.org/movie/1356955) is a strong research candidate:
same title/year and director name, whose TMDb birth date is 1997-12-09. However,
neither that movie nor its director has the IMDb cross-link, and runtime differs
(108 versus 111 minutes). No automatic crosswalk was established or written.
The safe conclusion is **IMDb identity established; TMDb mapping needs confirmation
or upstream metadata correction**. It may support an IMDb-only informational card;
it must not enable the existing TMDb-dependent Grab action yet.

The site’s movie listing/catalog provides this information. The BitTorrent tracker’s
peer-announcement service is a separate function and was not queried. No torrent,
magnet or peer-tracker endpoint was fetched.

## Actual pipeline and payload evidence

The running autobrr executable’s SHA-256 exactly matched the binary in the official
v1.88.0 Linux x86-64 release archive:
`eb8e3e466a7b6edef87e8b6aa3372a3be1760c2c23a2772fe1a0a9b35d49158f`.
This establishes the installed version independently of historical startup logs.
[Official release](https://github.com/autobrr/autobrr/releases/tag/v1.88.0)

| Stage | Verified evidence | Implication |
| --- | --- | --- |
| TorrentLeech listing | Exact release matches; `imdbID` input present | The site knows a specific IMDb association. |
| IRC/parser | Standard v1.88 definition captures category, release name, uploader, freeleech, listing base and torrent ID; no film-ID capture or listing-metadata fetch | Listing IDs never enter this IRC release object. |
| Installed configuration | Only TorrentLeech enabled, IRC source; RSS key configured; no custom definitions or external filters | No configured metadata-injection path fills the gap. |
| Autobrr internal release | Supports MetaIMDB/MetaTMDB; stored release table lacks these columns and internal JSON tags exclude them | Database absence alone would not prove in-memory absence; parser/source evidence is needed. |
| Built-in webhook | v1.88 copies MetaIMDB/MetaTMDB to `data.release.meta_imdb/meta_tmdb`, both `omitempty`; includes `info_url`, `download_url`, release name/title/year and indexer | Populated IDs would be forwarded; empty ones are omitted. `external_id` is the torrent ID, not a film ID. |
| Live notification configuration | Enabled WEBHOOK, POST/default, target exactly matches movie-intel; no body-template column | This is the built-in structured notification, not an arbitrary custom payload template. |
| Movie-intel | `build_movie_context()` obtains IMDb only from local catalog and calls `resolve_movie(title, year, imdb_id=...)` | Tracker IDs are not read; neither info_url nor tracker external_id is used for identity. |
| Existing IMDb resolver | `/find/{imdb}` movie lookup followed by movie details; rejects conflicting explicit IMDb identity | Useful foundation, but no direct TMDb-input contract/provenance/conflict merge exists yet. |

Source evidence: [TorrentLeech parser](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/indexer/definitions/torrentleech.yaml),
[release fields/parser](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/domain/release.go),
[webhook schema and mapping](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/domain/notification.go),
[notification construction](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/notification/service.go),
[deployed movie-intel consumer](https://github.com/kolorifer/radarr-festival-list/blob/dcae919/movie_intel_service.py),
[deployed resolver](https://github.com/kolorifer/radarr-festival-list/blob/dcae919/tmdb_resolver.py).

**Historical wire-payload limitation:** Fragmentos has empty retained action raw/log
fields. The service deliberately does not log raw webhooks, and pending actions
retain only an allowlisted subset. No historical request body was recoverable.
Therefore omitted film-ID fields are a conclusion from the verified installed
parser/serializer and actual configuration/event provenance, not a claimed packet
capture. No live payload logging, packet interception or notification replay was enabled.

A separate local synthetic probe supplied both metadata fields to the deployed
consumer code, with all resolution mocked. Its actual call remained
`resolve_movie('Fragmentos', 2025, imdb_id=None)`. This confirms the consumer gap;
it is not evidence that production received those fields on Fragmentos.

## Representative failures and measured coverage

Frozen cohort: retained Unknown Movie events from October 16 through release 429
(October 18), latest release per distinct title/year. Of **46** distinct pairs,
30 had cached successful metadata and 16 did not. All 16 uncached listings were
inspected, avoiding selection only of promising cases. Fresh conservative lookup
resolved The Snowman, leaving **15 current failures**. All 16 were outside the local
Movie List catalog and all 16 listing IDs were present as movies in IMDb’s official
title dataset. This is one-indexer, cache-miss-biased sampling, not all-tracker coverage.

| Retained title/year | Listing IMDb ID | TMDb by IMDb | Finding |
| --- | --- | --- | --- |
| Fragmentos (2025) | tt33503751 | No movie result | IMDb identifies Alejandro Rangel’s film; no TMDb IMDb mapping. Candidate 1356955 needs cross-link confirmation. |
| Insidious (2010) | tt1591095 | 49018 | TMDb primary year 2011; IMDb year and TMDb festival dates support 2010. |
| Nocturne (2020) | tt11044858 | 643550 | Direct IMDb mapping distinguishes the duplicate title/year matches. |
| The Lie (2020) | tt7945440 | 539649 | Primary year 2018; TMDb digital-release dates support the incoming 2020. |
| Lake Mungo (2008) | tt0816556 | 27374 | TMDb primary year 2009; IMDb year and TMDb festival date support 2008. |
| Withnail and I (1987) | tt0094336 | 13446 | IMDb primary title uses “and”; original/TMDb title uses “&”. |
| Medeski Martin Wood Not Not Jazz (2024) | tt6845204 | 1271630 | Maps to Not Not Jazz; TMDb synopsis corroborates the named band. No alias-stripping rule proposed. |
| Syd Barrett Up Close And Personal (2007) | tt7343706 | No movie result | Valid IMDb movie, 2007; no TMDb movie result for its IMDb ID. |
| Rainbow In Performance (2025) | tt32360791 | No movie result | Valid IMDb movie, 2007, versus incoming 2025; no TMDb movie mapping. Year requires review. |
| Steve Howe Live Legends (2003) | tt35303243 | No movie result | Valid IMDb movie, 2003; no TMDb movie result for its IMDb ID. |
| Haunted Heist (2025) | tt34890565 | 1384040 | TMDb primary year 2026; IMDb year and TMDb festival date support 2025. |
| Ein Mann auf den Knien (1979) | tt0078445 | 183635 | TMDb lists the incoming German alternative title. |
| Ice Age 4 Voll verschoben (2012) | tt1667889 | 57800 | TMDb de-DE title normalizes exactly to the incoming German title. |
| Ice Age 2 Jetzt tauts (2006) | tt0438097 | 950 | TMDb alternative titles include the incoming German title. |
| The Snowman (2017) | tt1758810 | 372343 | Control: deployed duplicate rule already resolves this film; not counted among 15 failures. |
| Hamnet 2025 (2016) | tt14905854 | 858024 | IMDb and TMDb identify Hamnet (2025); incoming year 2016 has no supporting TMDb release date. Review required. |

The five TMDb primary-year disagreements were investigated independently:
Insidious has a 2010 Canadian premiere; Lake Mungo a 2008 Australian premiere;
Haunted Heist a 2025 US premiere; The Lie has 2020 digital-release dates. Those are
exact-ID release-date records, not a proposed generic “±1 year” heuristic.
Hamnet’s incoming 2016 has no corresponding date; IMDb and TMDb agree on 2025.
Rainbow adds another year problem (incoming 2025, IMDb 2007) among the four unmapped IDs.

**Non-overlapping primary classification:** A=0, B-only=0, **C=15**, D=0, E=0.
Here C means ID verified on the exact listing but not collected into the current
IRC notification. The task’s broad B wording also covers these same 15; they are
not counted twice. There is no separate demonstrated case where autobrr already
received a film ID and then dropped it during webhook serialization. No sampled
listing lacked an IMDb ID, and no contradictory pair of external film IDs was
observed. Year/label problems above are reported separately rather than being
misclassified as proven wrong-ID assignments. This does not establish a universal
zero false-assignment rate for TorrentLeech.

**Expected improvement, bounded by evidence:**

- Native-field consumption alone: 0/15 current source-path failures recovered.
- Exact listing lookup: 15/15 obtain an IMDb association; all validate as real movies.
- Direct IMDb→TMDb lookup: 11/15 unique, round-trip-consistent movie mappings.
- Of those 11, six have no year conflict; four more have an authoritative date
  explanation; malformed Hamnet remains a review case until policy is approved.
- Four still lack a TMDb movie mapping: Fragmentos and three music releases.
  Identification and informational enrichment can improve without enabling Grab.
- No change to IMDb/Letterboxd ratings, recognition coverage, or acquisition
  eligibility was implemented. IDs do not create missing catalog enrichment.

## Options and recommended architecture

| Option | Reliability / measured coverage | Cost, maintenance and privacy | Assessment |
| --- | --- | --- | --- |
| A: consume external IDs | Exact IDs can remove duplicate/title/year ambiguity; current TL IRC yields none | Low processing cost, TMDb lookups/cache; conflicting or incorrectly assigned IDs still require checks | Implement as a general foundation after approval; insufficient alone here. |
| B: improve propagation | Serializer already preserves populated IDs; Torznab/Newznab paths populate them | Templates/macros cannot invent a missing ID. Feed changes alter timing/duplicate behavior; a custom upstream enrichment patch adds maintenance | No simple notification setting fixes TL IRC. Evaluate upstream work separately. |
| C: exact listing lookup | Observed 15/15 IMDb IDs and 11/15 TMDb mappings | One authenticated lookup per uncached listing; bounded retries and negative caching; site HTML/session changes require maintenance | Preferred source-specific fallback, with provenance and strict URL/auth boundaries. |
| D: bounded research | Needed for missing crosswalks, malformed data and conflicts | Slower/manual, no reliable universal coverage estimate; public metadata only, no private links sent to research providers | Keep research conclusions separate from automatic action eligibility. |

Autobrr supports MetaIMDB/MetaTMDB macros and Torznab ingestion. Its external
filters consume status/output, not a documented response-to-release-metadata patch.
The installed Prowlarr TorrentLeech definition contains `selector: imdbID`; its
official definition also maps the site's JSON browse results to IMDb IDs. This
offers a possible feed-based route, but does not prove a stable, supported exact
torrent-ID lookup API or justify changing live ingestion. The exact authenticated
listing GET is the lookup actually verified here. The site's browse endpoint is
site-internal; no published per-account API limits or stability guarantee were verified.
[Autobrr macros](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/domain/macros.go),
[Torznab ingestion](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/feed/torznab.go),
[external-filter implementation](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/filter/service.go),
[Prowlarr definition](https://github.com/Prowlarr/Indexers/blob/master/definitions/v11/torrentleech.yml).

Proposed identity order and checks, requiring product approval:

1. Collect supplied external IDs with issuer/source and exact-release provenance.
   Distinguish torrent IDs from movie IDs; validate formats and movie media type.
2. Require IMDb→TMDb cardinality one and a matching external-ID round trip. For
   direct TMDb IDs, inspect that movie's canonical external IDs. If multiple supplied
   IDs, local identity or authoritative evidence conflict, stop for review; never
   silently prefer one source or fall back to a convenient title match.
3. Check the listing association and metadata context: exact known release/listing,
   canonical or authoritative localized/alternative titles, and release-year
   evidence. Festival/digital dates can explain a mismatch; unexplained discrepancies
   remain visible. Wrong assignment tests must pass even when an ID is syntactically valid.
4. When IDs are absent, use an approved source adapter for the known info_url/release
   reference. Require HTTPS, configured host/path allowlists, bounded bodies/timeouts,
   no cross-origin credential forwarding or redirects, and never fetch download_url,
   torrent/magnet content or peer-tracker URLs. Do not trust arbitrary webhook URLs.
5. Preserve current exact-title/year search and duplicate rule as the no-ID fallback.
   An explicit conflicting/unmapped ID must not be discarded to pick another film.
6. Return distinct outcomes: verified TMDb identity; verified IMDb-only identity;
   conflicting metadata requiring review; unresolved. Only the verified TMDb state
   can reach existing action eligibility, which still requires the original reusable
   release and explicit user approval.

Use a private provenance cache keyed by source/listing and canonical IDs, with
expiry, bounded negative caching and correction invalidation. A title/year key
must not override conflicting IDs or let one Fragmentos film contaminate another.
Deduplicate simultaneous lookups; obey 429/Retry-After and session-expiry failures.
Choose operating limits after checking account terms; no rate guarantee is assumed.
Use dedicated appropriate authentication for any implementation rather than coupling
production permanently to Prowlarr's private session database. Credentials, listing
URLs and original download references remain private. Log only stage/reason codes,
field-presence/provenance summaries and safe correlation digests.

IMDb bulk datasets were used for this investigation, not proposed as a per-event
download dependency. IMDb-only enrichment needs an approved metadata source/cache
and accurate labeling; a tracker assertion alone must not be presented as independently
verified metadata for future unseen cases.

## Implementation and regression plan — not executed

| Component | Proposed work |
| --- | --- |
| movie_intel_service.py | Extract/validate external IDs; invoke bounded adapter when needed; display explicit identity states and reasons; gate actions on verified identity. |
| tmdb_resolver.py | Typed ID-first resolution, direct TMDb validation, conflict handling, media-type checks, provenance-aware cache, strict fallback semantics. |
| New tracker metadata adapter | Source-specific exact listing fetch/parser, origin/redirect safeguards, independent private authentication, timeouts/rate control and caching. |
| deployment_config.py / deploy docs | Validate optional adapter settings and secret paths; feature disabled by default; describe rollback and diagnostics. |
| Existing notification/resolver/HTTP/action tests | Add fixtures and checks below while preserving PR #41 exact-release behavior. |
| pending_actions.py / radarr_client.py | Preserve current transaction/replay/reference guarantees; add provenance assertions only if needed, without changing acquisition policy. |

Proposed regression cases: same and conflicting IMDb/TMDb pairs; wrong film assigned
to a valid ID; title/year cache conflict; non-movie IDs; zero/multiple find results;
missing/malformed metadata; duplicate title/year films; localized titles; festival
versus wide/digital release years; malformed Hamnet; absent crosswalk despite valid
IMDb identity; login HTML returning 200; missing/duplicate listing IDs; wrong listing;
changed markup; oversized response; hostile URL/redirect; timeout/429; secret redaction;
no available metadata preserving readable notification; routine rejection bypass.

Retain HTTP regressions for explicit approval, live roots/profiles, searchForMovie=false,
the identical original release reference, no search command, executing/needs_review
blocking, successful/expired 410 and no unsafe retry. Add assertions that lookups never
send a notification, create an action, add a movie or download a torrent by themselves.

Rollout only after product approval: local fixtures/focused and full tests, an opt-in
read-only comparison mode with sanitized decisions, reviewed sample outcomes, then
the existing preflight/backup/health process. Do not backfill or rewrite existing
pending actions or silently turn old unresolved notifications into acquisition capabilities.
Any future deliberate live notification/download needs specific approval.

Rollback: disable the new metadata feature/adapter, preserve current private action
state and PR #41 attempt/replay safeguards, and return runtime to verified dcae919
if necessary. Never restore an old action snapshot over completed downloads.

## Remaining ambiguities and product review

- Fragmentos: IMDb identity is established; confirm/correct the missing TMDb link
  before using candidate 1356955 for acquisition. Display the verified IMDb identity
  and explain why Grab is unavailable; do not label the movie wholly unidentified.
- Syd Barrett / Rainbow / Steve Howe: established IMDb movie records, no TMDb
  crosswalk found. Research existing TMDb records/metadata corrections; do not create
  a replacement movie ID or use popularity. Rainbow's year also needs explanation.
- Hamnet: ID points to 2025 while parsed year is 2016. Keep the discrepancy visible;
  select a correction/approval rule explicitly rather than introducing broad year recovery.
- All sources can misassign IDs. Add a correction/review workflow and preserve the
  unresolved notification with specific reasons rather than hiding it.

Review decisions: approve ID-first validation and the bounded listing adapter;
choose treatment of documented alternate release years versus malformed years;
approve IMDb-only informational states and the authentication/metadata source.
No decision above changes current production policy until approved.

## Verification, operational exception and repository status

Evidence collected: read-only SQLite/configuration inspection; exact running-binary
checksum; installed-version source tracing; 16 authenticated listing reads plus
targeted Fragmentos diagnostics; fresh TMDb movie/person/release-date lookups with
no cache writes; official IMDb title/crew/name records; one local mocked consumer
probe. No new runtime test suite was necessary for this documentation-only result;
the earlier 335 tests and live Boxtrolls test remain baseline evidence, not rerun claims.

An unsupported CLI version probe briefly started a separate empty default autobrr
instance in the checkout. The timed-out process was terminated. Four newly created
default config/database files were checked against the previously clean checkout,
verified to contain no releases/indexers/actions/clients, and removed. The actual
instance continued to use its separate .apps configuration, whose modification time
predated the probe. Subsequent version identification used a binary checksum only.
This was a diagnostic deviation from the read-only intent, not a production deployment.

Final production checks: dcae919, clean checkout; movie-intel PID 3171396 unchanged,
active, NRestarts=0; local/public health HTTP 200. No identity policy, notification
routing, acquisition state or live service configuration was intentionally changed.
The temporary probe files are gone. No new API keys were created.

Only the local investigation report, archived brief and project-state note are
changed. No implementation commit, PR, merge or deployment is proposed as already
performed. The unrelated CODEX_TASK.md assignment remains untouched.
