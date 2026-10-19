# Engineering report: automatic movie-identification investigations (#57)

**Specification:** [approved brief](2026-10-19-identity-automation-brief.md), [issue57](https://github.com/kolorifer/radarr-festival-list/issues/57).
**Result:** implementation under verification; production activation is not yet claimed.
**Verification date:** 2026-10-19.

## Verified live baseline and Aberfan

PR54 was freshly reviewed and merged as `e11469988d867ce3edde449c0f81c639ce2f49bb`; its runtime remains pinned at `28d65ed5a6ec26825386b9be1bb7d52a27c2acef` pending replacement gates. Observer activation: 09:27:40.253570 Europe/Warsaw. Aberfan's natural source event occurred at 10:24:47, with `listing_id_invalid`, unresolved identity and no action. Its original source announcement and outcome share strong source-ID correlation in the collector; selection quarantined it. Observer counters showed three natural outcomes persisted/delivered, no pending spool entries or process delivery errors. This is real production evidence, not a synthetic rejection replay.

The exact listing returned HTTP200 but contained neither an IMDb field nor any other valid IMDb reference. The parser previously conflated this absence with a malformed ID. The new typed `listing_id_missing` result makes explicit unresolved outcomes eligible for research, while malformed/conflicting identifiers remain quarantined. Two diagnostic listing GETs were made before implementation; the first diagnostic script needed a local bytearray-to-bytes fix. No notification or acquisition was replayed.

Public documentary context does not establish a TMDb movie identity. BBC programme access was unavailable; the linked Nation.Cymru article says October21, differing from the issue's October19 broadcast assertion. Documentary/movie/TV classification and canonical IDs remain questions for evidence and review.

## Changes

- Actor-owned metadata retries use a private durable ledger, source-version deduplication, leases and request reservations. Outcomes and retry completion commit together; delivery retries preserve event IDs. The resolver context builder is invoked directly, without notification/action handlers.
- Fixed safe status families distinguish missing IDs, malformed IDs, authentication, redirects, 404, 429 and temporary HTTP failures. Authentication/permanent conflicts route to review.
- Movie-category episode contradictions retain their original type and produce one concise non-actionable message plus quarantine evidence. No parser identity correction is applied.
- A confined helper can only GET the collector's authenticated loopback export and write the research incoming directory. It cannot read Stage1 SQLite, tracker/action credentials, the TMDb token or the old pilot ledger.
- A separate recurring-v1 database preserves the closed historical pilot. Unknown/failed reservations count against 5 case versions and25 requests per rolling week, max5 GETs per version. An attempted unchanged version never automatically reruns; new evidence creates a fresh version while preserving proposals.
- Daily eligibility scans produce private reports covering eligible, retry, review-only, quarantine and unassessed coverage. Telegram digests and review controls remain disabled pending product sign-off.

## Verification and deployment

Pending final tests, actual confinement proofs and deployment results. This section must be completed with actual evidence before claiming completion.

## Limits and review requirements

- Source announcements without an explicit outcome stay unassessed. There is still no publisher outbox guaranteeing all announcements; the actor's short pre-persistence memory window remains observable but not crash-proof.
- Transfer is complete-or-fail: maximum100 eligible /1000 assessed cases and1MiB. Overflow stops safely and must be reported, never silently truncated.
- Research is finite per evidence version. Unsupported/failed/ambiguous results remain reviewable; missing search results do not prove catalog absence.
- Existing seed material remains excluded from recurring work; materially changed source title/year/IDs reopen for review without resetting historical proposals.
- The private report exists independently of Telegram. A changed-case-only digest is a proposed product notification channel, not enabled functionality.
- Apollo's split numeric fraction and18½ context remain separate, unapproved identity repairs. Upstream recommendation: add fixtures for autobrr/rls v0.8.1 parsing `10 1 - 2` within a movie category; fix fraction parsing upstream, never blanket-promote episode types.

## Related issues

Issue53's natural correlation gap is resolved by Aberfan. Issues55–56's earlier historical diagnostics remain valid: transient failures may recover; conflicting identity/title/year cases remain review-only. See the [read-only incident report](https://github.com/kolorifer/radarr-festival-list/blob/6507ca6/docs/reports/2026-10-19-identity-incidents.md). Neither that report nor this implementation authorizes its proposed identity repairs.
