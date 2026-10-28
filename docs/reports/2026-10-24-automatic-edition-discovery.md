# Automatic edition evidence discovery — shadow only

## Correction and approved scope

The prior manually populated edition/member list did not meet the owner's intent.
Owner requested replacing it with bounded automatic gathering/interpretation,
starting with Bond 50, caching sourced findings and retaining inconclusive cases
for review. Deploy in shadow only, no downloads. Existing production matching,
request caps, explicit confirmation and October27 pilot deadline remain unchanged.

## Implementation

Deleted `edition-evidence.json`. There is no collection-name, movie or product-ID
registry in runtime code. `edition_discovery.py` derives a bounded leftover label
when a verified candidate's full catalog title occupies an edge of the release
title. Only candidates with agreeing IMDb crosswalk/year/runtime/film audio and
no identity blocks qualify. Pure numeric/Roman sequel additions and overlapping
or ambiguous interpretations are rejected.

An unfamiliar label is searched automatically on the public Blu-ray.com US
catalog. A first exact collection-name result must have a year range containing
the movie year. At most one product page is read. Its canonical URL and heading
must agree; only the structured per-film subtitle/disc-member section establishes
membership. Review text, recommendations and unrelated links cannot do so. All
supported member titles are extracted; membership in this one sourced edition
is sufficient packaging evidence, not a claim of exhaustive edition discovery.
Existing exact single NFO filename, matching tracker description and scoring
guards remain mandatory. Actual ID conflicts and incomplete rivals stay blocked.

Network: maximum two additional GETs, sharing the existing ten/run and forty/day
shadow limits. No reserve if two requests do not fit. Fixed HTTPS host and product
paths, no redirects, cookies, credentials or environment proxies; response at most
1MiB, bounded timeouts/read deadline, provider cooldown/auth suspension retained.
Only the inferred public label is searched, not the torrent URL or full filename.
No provider access is added to production movie-intel or the research worker.

Private `edition-cache.json` records source URL, fetched timestamp, SHA256,
member names, extraction section, query scope and outcome. Positive findings last
seven days; inconclusive/errors last one day. At most100 live entries and2MiB
read bound; atomic writes and no stored raw HTML. Cache hits require no public
requests. The cache is keyed by label/movie/year: repeated cases reuse evidence;
different movie/year queries may still need another lookup. Missing information,
changed markup, provider failures or absent membership remain review-only.

## Evidence and validation

Development fetched two public pages (search/product) without tracker credentials.
The parser independently discovered the Bond50 product URL from the label and
extracted22 members including Goldfinger; no product URL or member list was
provided to discovery. The pages are development inputs outside the repository;
no private torrent links are published.

Tests cover unfamiliar labels, positive/negative cache and expiry, budget
deferral, unavailable providers, matching year ranges, canonical and heading
checks, restricted URLs, recommendations rejected as membership, ID conflicts,
pack descriptions, NFO binding and ordinary sequel/title safeguards. Six new
discovery tests plus eight edition-scoring tests; existing historical scores
must stay unchanged. Full results and deployment follow below.

## Limitations

Automatic discovery currently supports one public catalog and its collection
layout; it is not unrestricted web search or model-based understanding. Missing
sources or unrecognized edition layouts remain reviewable rather than prompting
manual collection entries. Exact member-title matching is conservative. A single
NFO is evidence of one file, not inspection of torrent payload contents. No
weights changed, no identities approved, no downloads or notification tests.
Live automatic discovery awaits normal refresh admission; development parsing is
not a live shadow identity result.


## Final validation and deployment

Revision **bade2d6bf961572882f1997052505400a75192a9** passed755 local tests
(145.491s, two Linux-only skips),755 isolated seedbox tests(46.624s), and both
Python3.12/3.13 CI jobs(run40093370456). A development replay using the two
captured public pages and the Goldfinger scoring fixture discovers22 collection
members, selectsTMDb658 at100 and reuses cache on repetition with no new fetch.
This is not a live seedbox metadata refresh or a new live score.

Deployed exact tested archive to the shadow unit; source manifest matched.
Private backup edition-shadow-backup-dxu83968. Fourteen focused tests pass from
the installed checkout. Health200; movie-intel, collector and research timer
active. Actor remains23202815754ba2d97a86608003ca276251f1ae9c. Actor/config/actions,
request and refresh ledgers, timer configuration and pilot deadline hashes are
unchanged. Existing shadow timer resumed; no manual provider refresh was run.
Deployment used zero provider requests, no downloads and no notifications.

Retained Goldfinger score40 remains until the normal freshness/budget-admitted
run. Monitor follows first actual automatic-discovery evidence and cached outcome.
No permanent identity correction or production scoring activation. PR78 remains
draft. Rollback should prefer ab88fbd if abandoning this feature (f67f60c had the
rejected manual list); preserve all ledgers and caches. Unrelated CODEX_TASK
remains intact. This report supersedes the manual-list implementation report.
