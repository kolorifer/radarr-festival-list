# Live Movie Score — Task 3 source-verification packet

Prepared **2026-10-28**, against Task 2 / PR #88 at
`489ce4e3e005dbb15fadebf8ac27e6c181cf3a98`. No new calibration, ranking,
weights, confidence constants or award policy. Earlier packets remain unchanged.

The preparation packet is ready for review. A private eight-film **paired**
IMDb/Letterboxd trial is **blocked** by permission, field-contract and access
questions. Code readiness is not evidence of authenticated provider sampling.

## Run the tool

Standard-library Python 3.9+; no installation, dependency, service or daemon.
Run from repository root:

```sh
python3 simulations/live-score-v1/source-validation/validate_sources.py
python3 -m unittest discover -s simulations/live-score-v1/source-validation -p 'test_*.py' -v
```

Default execution checks two **invented** observations offline and prints an
aggregate. It reads only the committed cohort and synthetic fixture, discovers
no secrets, and makes zero requests. The proposed internal envelope is **not**
an asserted MDBList response schema or live adapter.

The only implemented network mode requires both explicit switches:

```sh
python3 simulations/live-score-v1/source-validation/validate_sources.py \
  --imdb-personal-check --accept-imdb-conditions
```

Recheck current terms before any later run. This command performs one official
IMDb dataset GET, no redirects/retries, 15-second socket timeout, 90-second
read-loop deadline, 64 MiB compressed / 256 MiB decompressed limits. Parsing is
bounded by decompressed size. It extracts only the fixed exact IDs in memory,
checks the complete file for duplicate target IDs, discards raw data at exit,
and prints only allowlisted aggregate/provenance fields. Failure exits 1 and
remains unavailable; it does not substitute archived observations. No per-film
rating/count output, file writer, authenticated mode or automatic refresh exists.
The timeout bounds are technical safeguards, not provider rate-limit claims.

## Actual source checks versus rehearsal

[gate-report.json](gate-report.json) is the sanitized record of the **one** live
IMDb check, not a fixture replay. Requested at 14:45:42 UTC and received at
14:45:43 UTC on 2026-10-28, it found **8/8 exact IDs and 8/8 valid pairs**.
The compressed export was 8,722,946 bytes; its SHA-256, ETag and Last-Modified
are recorded there. Last-Modified was 00:33:57 UTC that day. All eight original
measurement times remain **unknown**: dataset time and retrieval time are
separate from per-film observation time. No rating/count values were persisted,
printed or used for new scores. Reproducing this availability check later
requires another authorized download; the upstream export changes daily.

Information courtesy of IMDb (https://www.imdb.com). Used with permission.

Public official documentation was reviewed through the web reader/index, which
may be cached. MDBList overview/static docs/terms were readable; Swagger gave
only a back-link in the reader, while its indexed official summary exposed
endpoints and limits. The linked `/schema/` was unsupported by the reader.
Direct documentation GETs to `/docs/`, `/openapi.json` and `/schema/` returned
403. No workaround was attempted; these are **documentation** outcomes, not
account authentication or film API tests. Letterboxd API/use guidance was read;
no film pages were extracted. Authenticated MDBList and Letterboxd stages are
**NOT_RUN, zero film operations**, with no account, key or private state access.

The offline CLI's two valid synthetic pairs (one unknown measurement time, one
older than 30 days) and 18 focused tests are independent of those live results.
Regression tests for Tasks 1/2 verify preservation, not new sampling/calibration.

## Exact eight-film manifest

[cohort.json](cohort.json) copies retained identity evidence, hash-pinned to
`inputs/identities.json` at the baseline; tests also compare Task 2 identity rows.
No fuzzy lookup or new identity verification is claimed. Retained TMDb release
events and identity observation date (2026-10-25) remain in the manifest.

| Title | IMDb | TMDb | Retained year |
| --- | --- | ---: | ---: |
| Hamnet | tt14905854 | 858024 | 2025 |
| Anora | tt28607951 | 1064213 | 2024 |
| The Brutalist | tt8999762 | 549509 | 2024 |
| The Substance | tt17526714 | 933260 | 2024 |
| Sentimental Value | tt27714581 | 1124566 | 2025 |
| It Was Just an Accident | tt36491653 | 1456349 | 2025 |
| Nina Roza | tt29271639 | 1527449 | 2026 |
| I See Buildings Fall Like Lightning | tt38991615 | 1455247 | 2026 |

Nina Roza's retained evidence rejects similarly titled tt29893755. Buildings'
retained 2026-12-04 TMDb release event is future at this check; neither its year
nor release date establishes rating freshness. The ratings export supplies only
`tconst`; it does not independently reverify titles/TMDb/release dates.

## Permission and field audit

[source-audit.json](source-audit.json) provides dated URLs, operation-level
allowed/prohibited/unclear findings, field meanings and gaps. These are scoped
engineering interpretations, **not legal guarantees**.

| Proposed operation | Finding as of 2026-10-28 | Evidence |
| --- | --- | --- |
| Official IMDb export, individual personal noncommercial local use | Allowed subject to conditions and attribution; revocable | [Dataset documentation](https://developer.imdb.com/non-commercial-datasets/), [software-use terms](https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX), [conditions](https://www.imdb.com/conditions) |
| Republish fresh IMDb observations/movie database publicly | Prohibited under that personal-use route; not authorized here | Same IMDb software-use terms |
| IMDb website scraping | Prohibited | Same software-use terms |
| Free MDBList API reads | Documented capability; this authenticated stage unauthorized/unrun | [API guide](https://docs.mdblist.com/docs/api), [overview](https://api.mdblist.com/) |
| MDBList-mediated Letterboxd private derived scoring / 30-day observation retention | **Unclear**; no upstream/downstream permission verified | [MDBList terms](https://mdblist.com/static/legal.html) require third-party compliance; account retention text does not grant a client-cache license |
| Direct Letterboxd API for private analysis/recommendations | Access not currently granted to these uses | [API access](https://letterboxd.com/api-beta/access/) |
| Direct Letterboxd extraction/public redistribution | Forbidden in task; export/extraction restrictions apply absent authorization | [Terms §§6.8, 6.11](https://letterboxd.com/legal/terms-of-use/) |

IMDb's paired fields are `averageRating` (weighted average) and `numVotes`
(vote count) on the same `tconst` row. Source-decimal precision is retained;
weighted averages plus nominal vote counts are not raw individual ratings or
effective statistical sample sizes. Daily export publication is documented,
but per-film measurement timestamps are not provided.

[Letterboxd's own API schema](https://api-docs.letterboxd.com/) distinguishes
weighted `FilmStatistics.rating` (0.5–5, omitted with insufficient ratings) from
`counts.ratings` (members rating), watches, likes and reviews. These upstream
semantics **do not prove MDBList's fields or acquisition authorization**.
[FAQ guidance](https://letterboxd.com/faq/) on search crawlers/embeds does not
authorize this extraction. No direct acquisition adapter is provided.

For MDBList, exact Letterboxd field paths, scale, weightedness, rating-count
meaning/precision, null/zero/sentinel conventions, identity response fields and
per-source measurement timestamps/update cadence are **unverified**. No mappings
or conversions are guessed. Its [Score documentation](https://docs.mdblist.com/docs/score)
describes a combination with vote baselines; that composite, normalized scores
and TMDb ratings cannot fill either source half. The full response schema must
be reviewed before implementing a live adapter.

## Free-tier feasibility and stop rules

The [free-tier guide](https://docs.mdblist.com/docs/api) advertises 1,000 daily
requests. The [indexed official Swagger documentation](https://api.mdblist.com/docs/)
describes shared per-account quotas, fixed five-minute windows of 1,000 reads /
300 writes, daily reset at 00:00 UTC, remaining/reset response headers and 429
`Retry-After` in seconds. Some batch POST lookups count as reads. No account
quota, endpoint behavior or free-tier Letterboxd availability was measured.

A documented GET media-info endpoint is a candidate for eight sequential exact-ID
lookups; parameter enums and response schema were not verified, so **no live
MDBList adapter exists**. Eight reads fit the advertised quota arithmetically,
conditional on actual remaining shared allowance and source availability.
No subscription is necessary to evaluate that claim, but a free account/key
would still be required and was not acquired in this task.

`SyntheticTrial` rehearses a maximum of eight fixed-ID film operations (always
≤10), clamps to lower supplied/shared remaining limits, stops on 401/403/429,
timeout, invalid identity or other error, and never retries. A 429 records only
sanitized Retry-After seconds; it stops, so no request can precede that deadline.
A later manual run must also honor any still-active account hold/reset and lower
provider limits; the rehearsal creates no durable rate-limit state. Paired values
must come from one provider response, never stitched across calls. Missing halves
remain missing. Request time never advances measurement time. The 30-day age flag
is diagnostic only, not a selected confidence constant or production cache.

## Private versus public storage contract

Public checkout/commits may contain **only code, synthetic fixtures/tests,
documentation, exact-ID manifest and sanitized aggregate evidence**. No fresh
provider responses, observations or keys may be stored here, including ignored
files; there is no private output/upload permission in Task 3. The current tool
has **no persistent observation-output option** and no key-reading code.

For a later authorized trial the owner must explicitly designate a private
local destination **outside the entire public checkout**. Before adding any
writer, require an explicit destination, resolve symlinks, reject paths under
the checkout, use owner-only directory/file permissions and fail on ambiguous
paths. Do not rely on `.gitignore`. This is a future implementation prerequisite,
not a claim that a writer has already been implemented/tested.

The later reviewed authenticated adapter should accept an owner-supplied local
key through a hidden interactive prompt (`getpass`) or a specifically designated
private key file, never a URL/CLI argument, printed environment dump, browser
session or host-secret discovery. Do not put a key in GitHub/chat. Request URLs
may contain a provider-mandated key: disable URL/raw-body/exception logging,
reject redirects and publish only allowlisted aggregates. Synthetic secret
canaries exercise the rehearsal and IMDb wrapper's output boundaries; they do
not certify an unimplemented HTTP client or downstream provider logging.

## Minimum next owner action / unsent enquiry

The owner can review/send this **unsent** enquiry to MDBList; no provider was
contacted by this task:

> For a free, personal, noncommercial eight-film trial, is your Letterboxd data
> authorized for local derived scoring and retention of rating/count observations
> for 30 days, with no redistribution? Which fields give Letterboxd's weighted
> average (and scale), exact number of ratings (not watches/reviews/likes),
> missing-value rules and exact IMDb/TMDb IDs? Does the free tier include these
> fields, how often are they updated, and which timestamp identifies the source
> measurement rather than an API request or general metadata refresh?

Record an explicit permission answer covering upstream/downstream use, obtain
the documented response contract, and separately authorize a bounded private
trial with the explicit private destination and locally supplied free API key.
Neither a key nor a generic marketing reply is proof of permission. No secrets
need to be sent to the supervisor. If the response does not establish those
rights/semantics, the paired trial stays blocked; do not choose substitutes or
start another calibration automatically.

| Stage | Readiness | Remaining condition |
| --- | --- | --- |
| Offline preparation/test tool | GO for code review | Parent publication/review |
| Private IMDb availability | GO, checked 8/8 | No retained observations; later use must recheck conditions |
| Public fresh raw datasets | NO-GO | Outside authorization; rights not established |
| Eight-film MDBList/Letterboxd trial | CONDITIONAL / NOT_RUN | Permission, full schema, source freshness, local key, private destination, later authorization |
| New calibration / production integration | NO-GO in Task 3 | Separate agreed task after provider gates |
