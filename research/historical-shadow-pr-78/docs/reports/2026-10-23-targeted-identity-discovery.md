# Verified-ID targeted discovery in shadow

## Approved brief

Implement bounded discovery from checked tracker IMDb, original title and year,
starting with The Beast. Preserve visible plausible rivals, actual ID conflicts,
existing request caps, explicit download confirmation and shadow-only operation.
Test and deploy without downloads or notifications. Preserve the unrelated
active cleanup assignment in CODEX_TASK.md.

## Changes

A single-title release can use targeted discovery only after its exact tracker
IMDb maps uniquely to a movie and detailed metadata plus bound NFO agree on an
exact catalog title, source year, positive runtime and film-audio evidence. The
candidate must have no ID, NFO, source or crosswalk blocks. AKA handling remains
on the existing comparison path.

The targeted queries are source title/source year, original title/source year,
and original title/primary catalog year, deduplicated to at most three. This
includes a catalog premiere year distinct from the torrent's supported year.
It is explicitly scoped discovery, not exhaustive coverage of every title in
the catalog. When strong ID/evidence prerequisites fail, broad discovery remains.

Every returned first-page candidate remains visible, including fuzzy or
unexpected results. At most four candidates receive full details; unknown rivals
retain conservative upper bounds. Pagination, inconsistent summaries, incomplete
rivals or inadequate score margin still require review. No result is discarded
by popularity or silently assumed irrelevant. Targeted query scope/year and
completeness are recorded alongside results. At most 61 candidates can be
retained across three pages plus the direct ID; no extra pages are requested.

Maximum provider requests remain ten: tracker page, IMDb mapping, up to three
queries, up to four unique details and at most one additional leader mapping.
The direct candidate detail lookup is reused. Daily cap remains 40. A scheduled
refresh now starts only when the full ten-request allowance remains, preventing
a partial attempt from wasting the last few requests or replacing retained
results with a budget error. Unused allowance is not spent or reserved; the
existing hourly timer rechecks after the UTC daily reset. At most nine daily
requests can remain unused under this conservative admission rule.

Historical `local_identity_conflict` may clear only for an otherwise accepted
targeted result whose current local catalog has at least one matching title/year
record and whose matching records all agree on IMDb and any recorded TMDb ID.
Missing/unreadable catalog evidence or any disagreement keeps review. Every
retained release/outcome ID assertion remains independently checked. No other
historical conflict category is automatically cleared.

## Starting evidence and limitations

Read-only inspection found The Beast's installed local catalog record agrees
with the current tracker IMDb tt14407336. Its historical reason is
`local_identity_conflict`, with no retained asserted IMDb/TMDb. The existing
fresh score is 100 for TMDb 914206, but broad discovery remains incomplete.
This observation alone is not a new accepted shadow decision.

The daily shadow ledger is already 38/40. A complete fresh validation requires
more than two requests. No reset, increased allowance, fabricated search result
or provider replay is authorized. Deployment verification will test the code and
budget deferral; actual targeted search results must come from the next normally
admitted scheduled refresh. The existing 100-point review result remains until
then. The unchanged October 27 pilot deadline still applies.

## Tests and deployment

New regression tests cover scoped source/original-title
years, exact-ID prerequisites, missing/conflicting evidence, visible unchecked
rivals, pagination, four-detail/ten-request bounds, catalog agreement/conflicts,
and admission with insufficient daily allowance.


## Components and validation

- `refresh.py`: verified-ID query planning, bounded detail reuse, scoped search
  audit, explicit installed-catalog recheck, independent conflict guards and
  whole-refresh daily admission.
- `fresh.py`: retains up to 61 results only for the three-query targeted scope;
  existing broad discovery limit and scorer upper bounds remain unchanged.
- `test_fresh_identity_scoring.py`: five additional methods with adversarial
  subcases; targeted module passes 39 tests.

Final runtime **ab88fbd**, built on initial implementation 0c91d3d. Seedbox full
suite: **741 tests passed, 47.177s**. Python 3.12/3.13 CI passed on that exact head
(run 39924410859). The initial implementation passed 741 tests locally in
146.758s with two Linux-only skips; final local/deployment results follow below.

The catalog recheck explicitly receives the installed actor directory. It does
not read the shadow checkout's potentially different catalog, and tests assert
that binding. No production code/catalog or identity state is changed.


## Deployment result — 2026-10-23

Final local suite: **741 tests passed**, two Linux-only skips, **149.404s**.
Shadow **ab88fbd** deployed from the tested isolated archive; code hashes match.
Private backup: `identity-scoring-shadow-backup-6w7v4fci`. The shadow service ran
successfully and its existing timer resumed. Local movie-intel health returned
HTTP 200; movie-intel, collector and research timer remained active. Production
actor remains **658d8f838aed7a03db7d01244254362fba99369a**.

Protected actor/config/action state, research timer, pilot deadline, shadow
request ledger and retained refresh ledger were byte-for-byte unchanged. The
verification made **zero provider requests**, triggered no research, downloads
or notifications, and did not restart the actor. Code rollback restores only
the previous shadow unit/archive, preserving ledgers and action history.

Read-only exact-occurrence and installed-catalog checks confirm one local record
agrees with The Beast's retained IMDb tt14407336 / candidate TMDb 914206. The
current shadow result remains **review, score 100**, from the earlier broad
search. No real targeted search has yet run under the new code. The old broad
rivals and their review reasons remain visible; they were not retroactively
removed or replaced with synthetic results.

The current 38/40 daily allowance cannot admit a complete refresh. The normal
hourly worker will use targeted discovery when both the daily budget and existing
24-hour evidence freshness window permit. No refresh timestamp was reset to
force admission. Tests prove the query/scoring path and budget deferral, while
live targeted candidate coverage remains **pending**. This distinction is the
main remaining verification limitation. The installed generic rule may still
return review if actual targeted searches paginate or leave plausible rivals
unchecked; no specific outcome is guaranteed.

China II, China III and Genealogies retained proposals are unchanged. Pilot
coverage remains eight historical snapshots plus four new cases. PR #78 remains
draft, and production matching has not been activated. The passive monitor now
tracks the first actual targeted result without repeating the known budget wait.
D044 and project state were updated; the unrelated active cleanup task remains.
