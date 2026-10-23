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

Pending full checks. New regression tests cover scoped source/original-title
years, exact-ID prerequisites, missing/conflicting evidence, visible unchecked
rivals, pagination, four-detail/ten-request bounds, catalog agreement/conflicts,
and admission with insufficient daily allowance.
