# Engineering report: issues 55–56, eight identity incidents

**Specification:** [brief](2026-10-19-identity-incidents-brief.md),
[issue 55](https://github.com/kolorifer/radarr-festival-list/issues/55),
[issue 56](https://github.com/kolorifer/radarr-festival-list/issues/56).
**Result:** read-only investigation complete; implementation proposals await review.
**Date:** 2026-10-19; chronology uses Europe/Warsaw (CEST).
**Production examined:** `28d65ed5a6ec26825386b9be1bb7d52a27c2acef`.
No runtime change, deployment, accepted mapping or notification replay.

## Findings

These are not seven instances of the same matching defect. Historical fixed codes
show **two source HTTP failures, three year conflicts, one title conflict and one
missing IMDb→TMDb crosswalk**. Apollo is a separate parsing/presentation problem.
Three of the seven movie contexts now verify using unchanged code and fresh
read-only metadata; four still need investigation/review. This does not change
production identities or retrospectively mark their stored cases resolved.

| Case | Historical identity reason | Current read-only result and public catalog evidence | Prioritized proposal |
| --- | --- | --- | --- |
| The Killing (1956) | `listing_http_error` | Exact source metadata is available now; IMDb [tt0049406](https://www.imdb.com/title/tt0049406/) uniquely roundtrips through [TMDb 247](https://www.themoviedb.org/movie/247), with matching title/year. Another announcement of the same film already verified later that night. | Bounded metadata-only retry with a temporary-lookup message; no matching-rule relaxation. |
| Tres (2021) | `tmdb_mapping_missing` | The public IMDb reference [tt10375378](https://www.imdb.com/title/tt10375378/) still returns no movie crosswalk. A plausible [Out of Sync / Tres candidate, TMDb 856434](https://www.themoviedb.org/movie/856434), has **different** IMDb [tt13276160](https://www.imdb.com/title/tt13276160/). Title search is therefore a proposal, not a substitute mapping. | Investigate the identifier disagreement; never attach the candidate automatically. |
| Jeremy Fink and the Meaning of Life (2011) | `year_conflict` | Public IMDb [tt1710394](https://www.imdb.com/title/tt1710394/) maps to [TMDb 89894](https://www.themoviedb.org/movie/89894). Returned primary and country release dates contain **2012**, not 2011. Title/ID match; year check still blocks. | Review release-year evidence for an exact-context correction; retain the gate meanwhile. |
| Good **Mourning**, Lucille (reported as “Morning”) | `year_conflict` | Retained title is “Good Mourning Lucille”; public [TMDb 375991](https://www.themoviedb.org/movie/375991) / [IMDb tt2835334](https://www.imdb.com/title/tt2835334/) is “Good Mourning, Lucille.” Its returned dates contain **2014**, not the reported 2017. Punctuation already passes. | Review the source-year discrepancy; spelling/punctuation normalization is not the cause. |
| Jhilli (2023) | `year_conflict` | [IMDb tt20118774](https://www.imdb.com/title/tt20118774/) → [TMDb 903884](https://www.themoviedb.org/movie/903884) now verifies. Current dates include **2021 and 2023**, primary date 2023. | Refresh stale review evidence using unchanged validation before proposing any correction. |
| Legend of the White Dragon (2026) | `listing_http_error` | Exact source metadata is available now; [IMDb tt12446086](https://www.imdb.com/title/tt12446086/) → [TMDb 843352](https://www.themoviedb.org/movie/843352) verifies title/year with a 2026 date. | Same bounded retry path as The Killing. |
| 18½ (2021 label) | `title_conflict` | [IMDb tt7325622](https://www.imdb.com/title/tt7325622/) → [TMDb 796102](https://www.themoviedb.org/movie/796102) has canonical title **18½** and documented 2021/2022 dates. Parsed “18 1 and 2” fails the exact normalized title check. | Propose an ID-bound fraction alias with wrong-ID/year negatives; no generic fuzzy matching. |
| Apollo 10½ | No movie identity attempt; `payload:passthrough` nearby | Retained parsed type is **episode**, despite movie category. Title is split before episode 2. Public [IMDb tt7978758](https://www.imdb.com/title/tt7978758/) → [TMDb 664996](https://www.themoviedb.org/movie/664996) supports the full film title. | Quarantine the category/type contradiction and send a concise non-actionable notice; investigate the upstream parser separately. |

Spain's [ICAA record](https://sede.mcu.gob.es/CatalogoICAA/Peliculas/Detalle?Pelicula=103118)
independently supports the Tres/Out of Sync title pair, director Juanjo Giménez,
2021 production/release and 105-minute runtime. That supports the candidate's
context, **not equivalence of the conflicting IMDb IDs**. Direct IMDb pages were
blocked/challenged during this investigation; the discrepancy remains unresolved.

## Evidence and uncertainty

For all seven movie incidents, retained source evidence and release-name journal
digests align with the reported context and fixed identity/tracker reason codes.
The original raw rejection webhook is not retained. Stage1 metadata lacks native
film IDs; the observed listing-lookup branch also implies neither native film ID
was supplied to the actor under this deployed code path. This is stronger than
inferring ID absence merely from the autobrr database schema.

Nine exact listing reads (eight incident contexts plus the later Killing
announcement) all returned HTTP200 and passed the existing exact-heading/IMDb
parser. Seven independently supplied public references matched the corresponding
current associations; Lucille's public catalog identity was established from the
current lookup and roundtrip. Private source references/comparisons are retained
only in the operator bundle; none are published here.

Historical `listing_http_error` does **not** retain the HTTP status. It could
represent several non-200 classes; the cause cannot be narrowed to authentication,
404, redirect or server failure from those logs. The same pages work now, and a
separate Killing announcement verified later, so retry is justified as a proposal.
Do not claim a proven 5xx outage or a historically correct source ID from today's
response alone. A 429 has its own code and was not the recorded reason.

Jhilli's old provider response was not saved. Historical `year_conflict` and
current successful validation are both proven, but which upstream date/crosswalk
changed is not. No parser or matching change is needed to reproduce today's
success. Avoid retrospectively attributing the old event to a specific catalog edit.

Apollo's nearby passthrough log has no release digest, so exact event attribution
is supported by timing, retained parsed fields, the supplied screenshot and
reproduction, not a uniquely keyed passthrough log. No full raw payload was replayed.

## Chronology, queue and the earlier zero count

The observer actually started at **2026-10-19 09:27:40 CEST**, established from its
startup journal record. **All eight reported incidents occurred before it was
active.** Exact incident times remain in the private evidence bundle.

All seven movie incidents have Stage1 `release_new` observations with stable source
identities, but **zero recorded outcomes and zero selection rows** for those
incidents. Their actual status is **observed, unassessed, before activation**—not
eligible, successfully identified, or a demonstrated observer delivery loss.
Apollo has no retained movie evidence: typed episodes are rejected by the current
intake. There is no per-payload rejection record proving whether its particular
publisher delivery reached the collector; absence alone cannot establish that.

If equivalent outcomes arrived through the enabled observer, the current routing
would be:

| Historical reason | Count among the seven | Prospective lane; not actual historical admission |
| --- | --- | --- |
| `listing_http_error` | 2 | `retry_later` |
| `year_conflict` | 3 | `review_only` |
| `title_conflict` | 1 | `review_only` |
| `tmdb_mapping_missing` | 1 | `eligible`, provided strong source correlation and a valid IMDb assertion |

`retry_later` and `review_only` are durable holding states, **not scheduled work**.
The observer spool retries delivery, not metadata resolution. There is currently
no timer that rechecks these identities; a new source outcome can update the
projection, otherwise a separately approved bounded metadata investigation is
needed. The researcher export admits only eligible cases, never these two lanes.

At the final read-only health check:567 distinct source releases,117 live accepted
announcements, zero outcome events/eligible exports and zero pending spool items.
A journal count since activation likewise found **zero new actor identity
decisions**, explaining the zero fresh outcomes without assuming loss. These
screenshots do not contradict the earlier post-activation measurement. Incomplete
publisher coverage and the pre-persistence crash window still remain limitations.
No historical outcomes were inserted or inferred into the production queue.

## Apollo: version-specific parser and presentation boundary

The running autobrr binary still matches the previously verified v1.88.0 checksum.
Its [go.mod](https://github.com/autobrr/autobrr/blob/v1.88.0/go.mod) replaces the
parser with **autobrr/rls v0.8.1**. That parser's
[`NewEpisodeLexer`](https://github.com/autobrr/rls/blob/v0.8.1/lex.go) recognizes
hyphen-delimited numeric episode forms; `- 2` inside the rendered fraction fits
that pattern. Its [type inference](https://github.com/autobrr/rls/blob/v0.8.1/parse.go)
selects Episode when the episode field is nonzero. Autobrr's
[release mapping](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/domain/release.go)
copies the parsed type. The movie category does not rescue this case.

Our `valid_movie_payload` then rejects the episode type; the fallback serializes
sanitized JSON instead of a concise notice. The Stage1 normalizer independently
rejects it as non-movie, so it also misses the movie research pipeline. Source
inspection plus the actual retained parsed result establishes the boundary. No Go
runtime was available; this report does not claim a newly executed full Go parser
test. The new Python fixture reproduces the downstream behavior using that parsed
shape, with a synthetic release/source and no private data.

A future fix should preserve the raw parsed type, record a sanitized
`movie_category_type_conflict`, and keep it non-actionable. Do not promote all
episodes—or every movie-category record—to movies. Upstream fraction-tokenization
regressions and a downstream safe presentation guard are separate changes.

## Recommended next implementation sequence — approval required

1. **Bounded metadata-only revalidation and clear failure wording.** This is the
   prioritized fix for issue55 and applies to the two recovered lookup failures.
   Retain safe typed HTTP classes/status (never URLs, cookies or bodies); distinguish
   temporary/429 errors from authentication/not-found/redirect cases. Propose at
   most three attempts per unchanged case in24h with backoff and Retry-After,
   deduplicated by source identity/evidence version and charged to an explicitly
   approved request cap. Auth failures need operator attention, not blind retries.
   Use a narrowly scoped actor-side metadata path for source lookups; do not give
   the researcher tracker credentials or raw acquisition references. Never replay
   the notification handler or mint approval tokens during revalidation. Initially
   keep execution operator-triggered; no recurring schedule is authorized.
2. **Apollo contradiction handling and concise fallback.** Quarantine the sanitized
   movie-category/episode-type contradiction, retain original parsing, replace full
   JSON noise with a short non-actionable message and a fixed reason. Add upstream
   v0.8.1 fraction regressions without globally coercing TV into movies.
3. **ID-bound fraction context review.** Review the 18½ alias and Apollo's full
   title reconstruction only after unique ID roundtrip, exact private provenance
   and documented-year checks. Offline replay of the fetched responses validates
   both canonical contexts and still rejects a wrong year; this is evidence for
   review, not permission to deploy an alias or create an approval action.
4. **Review remaining catalog contradictions individually.** Refresh stale Jhilli
   evidence before proposing changes. Gather independent year evidence for Jeremy
   Fink and Lucille; do not add a generic ±year tolerance. Resolve the Tres IMDb
   disagreement before proposing a crosswalk. Put review-only cases in a visible
   operator review list rather than silently excluding them from attention.

The finite retry policy, review list, notification wording, fraction corrections,
parser change and any historical reconciliation require approval before production
implementation. No automatic identity correction or recurring research is included.

## Verification, files and production preservation

- **42 targeted tests pass**, including eight new synthetic incident
  characterizations plus existing external-identity and notification regressions.
  Covers lookup failure vs absence, missing/conflicting crosswalks, documented-year
  refresh, fraction titles, wrong IDs/years, ambiguous same-title results, Apollo
  raw fallback and actual-TV exclusion. These characterize current behavior and
  safety requirements; they are not deployed fixes.
- Two offline replays of already fetched fraction-film metadata validated canonical
  context and rejected a wrong year. Zero additional GETs for replay.
- Diagnostic activity: **9 listing GETs +18 TMDb GETs**. These are new authorized
  read-only diagnostic requests, distinct from the unchanged Stage2 pilot ledger.
  No torrent/download endpoint, notification/approval handler or Radarr API used.
- Actor and collector remain at `28d65ed`; both active, NRestarts0, local/public
  actor health200. Actual actor start remains09:27:40 CEST; no restart performed.
  Exact notifier/filter/API-key rows, environment other than the previously
  approved observer settings, reviewed bindings and installed collector hashes
  match the preceding deployment baseline.
- Worker stays at `2de1ba8`, disabled, empty token, no schedule; all installed files
  and every pilot table unchanged, closed ledger19. **Zero worker research GETs**
  is not a claim of zero diagnostic GETs.
- Only `test_incident_55_56.py`, this report/brief and project-state documentation
  were added/updated. No runtime code changed. A full runtime suite was not rerun
  for this investigation; prior510-test validation remains the deployment baseline.
- Private retained source evidence, correlated codes, responses and coverage
  comparisons are kept in an owner-only host bundle (700 directory/600 files).
  Public artifacts omit private source names/URLs, torrent IDs and payloads.

## Handoff

This investigation is isolated on `investigation/issues55-56-readonly`, based on
the examined PR54 code. No PR54 merge, modification or deployment is performed.
The report and synthetic fixtures are for review, not a new runtime rollout.
The unrelated cleanup task in `CODEX_TASK.md` remains untouched. No design decision
was promoted to accepted status; the next implementation sequence needs approval.
