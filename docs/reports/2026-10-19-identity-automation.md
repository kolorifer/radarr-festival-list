# Engineering report: automatic movie-identification investigations (#57)

**Specification:** [approved brief](2026-10-19-identity-automation-brief.md), [issue #57](https://github.com/kolorifer/radarr-festival-list/issues/57).
**Result:** automatic retries and daily bounded research deployed; identity corrections, Telegram digest and review controls remain unapproved.
**Verification date:** 2026-10-19, local Python 3.12, seedbox Python 3.13 and CI 3.12/3.13.
**Implementation:** [PR #58](https://github.com/kolorifer/radarr-festival-list/pull/58). Production is pinned to tested runtime **`4c55f2a29314fa18c5131c4199aa9bf53966bd35`**; the PR link tracks merge status independently of the production pin.

## What changed and why

Actual identification failures now reach an automatic pipeline: movie-intel outcome → durable private spool → authenticated, source-correlated collector selection → bounded actor metadata retry or confined research handoff → independent recurring research ledger → private changed-case review report. Source announcements alone are not failures. Research results never become approved identities or acquisition instructions.

| Component | Behavior |
| --- | --- |
| Tracker/TMDb adapters and selection | Fixed safe reasons separate missing IDs, malformed/conflicting IDs, authentication, redirects, 404, 429 and transient failure. Missing IMDb on an otherwise validated exact listing is `listing_id_missing`, eligible for research. |
| Actor retry store and request gate | At most 3 extra attempts per unchanged evidence version in 24 hours, delayed 15 minutes → 1 hour → 6 hours, with durable reservations, deduplication, expiry and Retry-After/auth suspension. Extra traffic capped at 10 GETs per rolling week globally, at most 5 per provider. Completion and sanitized outcome commit atomically. |
| Apollo presentation | Movie-category/episode contradictions retain original parsed type, enter diagnostic quarantine and receive one concise non-actionable message. No raw JSON or approval button. No blanket promotion of episodes. |
| Confined handoff | A separate clean process preconnects only to the existing loopback collector, applies Landlock/seccomp, GETs a strict sanitized export and writes only the worker's incoming directory. No Stage1 database, tracker/action credentials, worker token or old pilot access. |
| Recurring worker | Separate `recurring-v1.sqlite3`, never resets/reopens the closed pilot. Daily scan, only new/materially changed eligible versions, 5 case versions / 25 TMDb GETs per rolling 7 days, max 5 GETs per version. Failed/unknown reservations count. Over-budget jobs stay queued. |
| Operator report | Every currently assessed lane, first-observed age, evidence freshness, source ID assertions, current/historical proposals, candidates, supporting/conflicting facts and next review requirement. Quiet scans do not erase the last changed report. No digest/control activation. |

The helper may make at most three fresh confined attempts per scan, each bounded to 15 seconds with five-second gaps. These retry only local evidence transfer, not research. A failure after all three stops that scan; the next daily activation can try again. The worker has no reconnect, redirect, arbitrary URL, tracker or action capability.

## Aberfan: natural event, exact listing and live research

The observer began **09:27:40.253570 Europe/Warsaw**. Aberfan's actual source event was **10:24:47**, after activation. Logs recorded `listing_id_invalid`, unresolved identity and unavailable action. The original announcement and natural outcome were both stored with **strong source-ID correlation**; selection quarantined the case. The original event was not replayed into a notification/action handler. This closes PR54's previously missing natural positive observer/correlation check.

The exact private listing returned HTTP200 with **no IMDb field and no other valid IMDb reference**. Absence was incorrectly conflated with malformed ID. Two initial diagnostic listing GETs were made (the first diagnostic script needed a local bytes conversion); one subsequent, explicitly bounded metadata-only revalidation using the deployed parser returned `listing_id_missing`. It committed through the existing outcome spool and became eligible, preserving the original quarantine history. No TMDb call, notification or action was made by that revalidation.

The confined worker then automatically admitted that eligible version and made **two TMDb GETs**: movie search and TV search. Movie search returned **TMDb 1796471**, *Aberfan: The Village That Fought Back*, dated **2026-10-19**; TV search returned no rows. This is a **search-only, unverified candidate**, not an approved movie identity or proof that TV classifications are absent.

The first research pass missed the candidate because its title comparator did not tolerate the colon. Punctuation handling was corrected **only for research candidate discovery**, with a regression proving that it requests candidate details and remains review-only. The existing response is now exposed as a search candidate in the report without refetching, reopening the completed case, rewriting its original result or resetting its budget. The original `no_supported_candidate` result remains historical evidence. Detail metadata, IMDb crosswalk, director/runtime and media type still need review/new evidence before any runtime correction.

The BBC programme page could not be fetched during public context checking. The linked [Nation.Cymru article](https://nation.cymru/news/aberfan-survivors-fight-for-change-brought-to-light-ahead-of-60th-anniversary/) says October 21, while the issue and TMDb search date say October 19. Broadcast and catalog dates are not interchangeable proof of identity.

## Actual intake and research accounting

Final rollout readback, before any unattended daily tick:

| Metric | Observed |
| --- | ---: |
| Source releases observed | 576 |
| Source releases without an outcome | 571 — unassessed |
| Live accepted source announcements | 126 |
| Outcome events | 6: five natural outcomes plus one Aberfan metadata revalidation |
| Assessed source-release cases / strong correlations | 5 / 5 |
| Verified cases | 3 |
| Eligible cases / automatically researched versions | 1 / 1 — Aberfan |
| Current quarantine cases | 1 — *2018 Everyone Is A Hero* (2023), `listing_id_invalid` |
| Current retry-later / review-only cases | 0 / 0 |
| New recurring review results | 1, awaiting evidence/review |
| Recurring cases / GETs / unknown requests | 1 / 2 / 0 |
| Extra GETs on unchanged rescan | 0 |
| Changed cases on unchanged rescan | 0 |
| Live retry admissions / recoveries / extra GETs | 0 / 0 / 0 |
| Historical seeds / closed pilot requests | 4 / 19, all original table hashes unchanged |
| Collector storage failures since final restart | 0 |
| Outcome spool persisted / delivered / pending | 6 / 6 / 0 |
| Recovered delivery failures / duplicate deliveries | 1 / 1, deduplicated without another event |
| Oldest unresolved case at rollout | About 71 minutes; first-observed age is separate from refreshed evidence |

There are **two currently assessed unresolved cases**, not 571 failed movies: one eligible/researched and one quarantined. The four historical seeds/proposals remain separate. The eligibility transition for this already-notified Aberfan case used the authorized metadata-only revalidation; a fresh naturally eligible case after the new parser deployment has not yet been observed. The natural observer chain itself is proven independently.

The collector's `automatic_research_enabled=false` metric describes its own passive, no-outbound process. The separate worker and timer are enabled; its independent ledger/report supplies execution metrics. Source health was `stale_or_quiet`, not a claim of complete delivery. Original pre-activation announcements remain unassessed. Process/pre-persistence loss cannot be reconstructed after restart.

## Tests and release gates

- Runtime release `0f17617`: **544 tests**, all pass on seedbox and both CI versions; local 542 pass / two Linux-only skips. The final historical-proposal display guard and explicit Apollo/18½ fixtures pass **546 tests** on seedbox and CI 3.12/3.13; local 544 pass / two Linux-only skips.
- Real kernel proofs: Landlock ABI6; protected read/write, symlink, inherited-fd, `/proc`, metadata mutation and new TCP/UDP/Unix socket denials. Surviving-fd connect syscall denied. The helper successfully read the fixed authenticated loopback export and wrote its own incoming artifact; worker could use its own private SQLite state and certificate-verified TMDb TLS connection. Proof requests to TMDb: zero.
- Live confined handoff, empty enabled epoch with zero GETs, disabled worker with token removed, source-correlated Aberfan admission, proposal-only research and unchanged rescan all passed. No security boundary was relaxed.
- Regressions cover request reservations after crash, stale leases, source expiry, SQLite BUSY, simulated FULL before transport, strict material deduplication, failed/unknown requests, weekly/per-version caps, auth/cooldown, complete-or-fail export, Apollo non-actionable HTTP presentation, true-TV exclusion and original fraction-title rejection.
- Frozen scoring unchanged: 1909 candidates, 224 grandfathered, 163 new and 387 qualified. Dependency check passed. Existing reviewed bindings/configuration and collector boundary remain unchanged. Changed-file privacy checks and diff checks passed; private scripts, URLs, credentials and source IDs were not published.

## Deployment, rollback and scheduling

PR54 was freshly reviewed and merged as **`e11469988d867ce3edde449c0f81c639ce2f49bb`**, initially preserving runtime `28d65ed5a6ec26825386b9be1bb7d52a27c2acef`.

Issue57 first deployed `841c2524f6cb0b43ebab2ba1bfa59aaa29042859` with retries in shadow and research disabled. After the actual handoff/security/disable gates, the new epoch was enabled separately. One subsequent handoff failed; its exact cause was not identified by the initial generic diagnostic. The rollout guard was exercised successfully: timer off, worker token removed, verified code/config restored, all ledgers and action state preserved. An isolated confined probe then succeeded in 0.043 seconds. Fixed safe stage/reason diagnostics and bounded local handoff retry were added; no permission or timeout boundary was widened in the collector.

The successful rollout pinned **`0f17617fff6a754e7eac03eea7c8e257c4b6af68`**, enabled actor metadata retries and the daily scan timer, and verified actor local/public health 200 with 1909 movies and collector health/storage. It preserved the old pilot, reviewed identity bindings and all Radarr/Grab safeguards. The first unattended timer deadline is **2026-10-19 12:08:34 CEST** (daily noon host time plus up to 15 minutes jitter). It had not fired at rollout verification; manually starting the same service exercised the full scheduled path. A later timer readback showed **12:01:11 CEST**, still within the authorized noon-to-12:15 jitter window.

The final report-only refinement was deployed as **`4c55f2a29314fa18c5131c4199aa9bf53966bd35`** after all 546 gates passed. Only the report module changed in production; movie-intel kept the same PID. A further confined rescan produced zero changed cases and no new GETs. Proposals for cases that later resolve are explicitly marked historical.

Backups cover prior code, private configuration and observation/pilot state. Disable procedure: stop/disable the scan timer/service; set worker disabled and remove its token; set actor retry mode off and restart only movie-intel. Roll back code/configuration if needed. **Never restore old action state, erase request reservations or reset ledgers to retry work.** Rollback was tested by the actual guarded failure above. The runbook contains the installed paths and commands/behavior.

No deliberate Telegram notification test, Radarr read/write, movie add, search, release push, approval-token creation, download or catalog write was performed. Metadata revalidation never invoked a notification/action handler. Ordinary production activity remains allowed.

## How cases and proposals reach the owner

Existing Telegram failure notifications continue immediately. Temporary problems enter bounded metadata retry; a recovery updates investigation evidence without retroactive Grab buttons. New/materially changed eligible failures enter the daily bounded research run. All assessed lanes appear in the private worker `review-report.json`; the last changed scan is retained in `review-changes.json`. IDs/source assertions are evidence, not approval.

A changed-case-only Telegram digest is **recommended but not enabled**. Issue57 explicitly requires product sign-off on an example before sending it or enabling review controls. Sanitized proposed format:

> Identity review: Aberfan: The Village That Fought Back (2026). Possible TMDb movie: 1796471; title/year agree. Detail metadata and source crosswalk remain unverified. Review required. No correction or download performed.

This is a presentation example, not a sent message or ready approval control. All identity corrections remain separate decisions.

## Remaining limits and related issues

- No upstream publisher outbox/all-announcement guarantee; there is also a short actor pre-persistence memory window. Collection is limited to configured source allowlists and valid, correlatable outcomes. Unsupported/malformed events are not fabricated into movie identities.
- Complete-or-fail transfer cap: 100 eligible / 1000 assessed cases / 1 MiB. Capacity, stale snapshots and exhausted handoff attempts stop safely and remain operational failures, not empty successful scans.
- An unchanged attempted research version is not repeatedly researched, even after a transient provider failure. New material can reopen it; an explicit approved follow-up can be designed without resetting historical budgets. Over-budget unattempted cases remain queued.
- No live transient retry recovery has yet occurred; failure→success is covered by controlled regression tests. The first unattended daily tick remains to be observed.
- Aberfan is a plausible search candidate only. The other current case remains quarantined. Unchanged historical seeds retain all prior proposals; changed source identity facts reopen review, never overwrite history.
- Apollo's `10½` and 18½ context repairs remain unapproved. The fixture captures autobrr/rls v0.8.1's episode 2/movie-category contradiction. Recommend an upstream numeric-fraction parser regression/fix, not episode promotion or a runtime identity exception.
- [Issue53](https://github.com/kolorifer/radarr-festival-list/issues/53): passive bridge merged; natural correlation gap closed. [Issues55](https://github.com/kolorifer/radarr-festival-list/issues/55) and [56](https://github.com/kolorifer/radarr-festival-list/issues/56): earlier read-only findings remain valid; transient retry and diagnostic presentation are implemented, while conflicting identities and fraction-title corrections remain review-only. Their [historical report](https://github.com/kolorifer/radarr-festival-list/blob/6507ca6/docs/reports/2026-10-19-identity-incidents.md) is retained. These issues remain open for product reconciliation rather than falsely closing unresolved identity decisions.

## Project context

Archived brief/report and deployment runbook updated. Project state records the verified enabled pipeline separately from product acceptance. The unrelated active CODEX_TASK assignment was left intact. No automatic messages were sent to other chats; this report is the handoff.
