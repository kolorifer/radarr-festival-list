# Engineering report: contextual typos and runtime variation

**Specification:** [approved brief](2026-10-28-contextual-typos-runtime-brief.md).
**Status:** implemented, tested and deployed; [PR #107](https://github.com/kolorifer/radarr-festival-list/pull/107) targets main.

## What changed

A one-letter typo in a five-letter word may now match only with another unchanged
alphabetic word of at least six letters, after the existing exact tracker/IMDb/
TMDb/year gates. Numeric and Roman-numeral changes, added words, standalone short
titles, wrong years, local identity conflicts and conflicting IDs remain blocked.

The NFO guard recognizes General-section MediaInfo Length (size for duration),
Duration/Runtime and clock formats with seconds/milliseconds. It stops before
Video/Audio/Text tracks, ignores file sizes and rejects ambiguous/malformed values.
Previously unsupported NFOs can now reveal a genuine runtime conflict.

Owner-approved runtime variation is max(1, min(5, catalog_minutes × 0.05)). The
one-minute floor preserves prior rounding behavior. The wider bound requires an
exact checked listing, matching IMDb, verified TMDb mapping and successful
title/year resolution; it never supplies identity. The same guard runs when
revalidating an existing action before acquisition. Large mismatches, including
12 versus 93 minutes in either direction, remain blocked.

## Components

- tmdb_resolver.py: contextual five-letter typo support.
- source_identity_guard.py: General Length parser and bounded verified runtime comparison.
- test_tracker_typos.py / test_source_identity_guard.py: positive cases, exact
  boundaries, ID/year/source failures, short/feature veto and GET/POST safety.
- Notification guide and decisions document the accepted behavior.

## Validation and deployment

Main implementation commit: `fc5c73a8387767b4a81441771a79d0c2cc90f04c`.
Minimal actor candidate: `d7487700ee8bb6eed86adefeca365945ecccc001`, based on
`46cccea3a119ca080e35f6cf071bd0351eba037a`. Only the two runtime modules and
their tests differ from the production actor. Main-only integration changes and
the separately installed collector/shadow runtimes are outside this deployment.

- Focused suite: 28 tests pass. Full local main-based suite: 922 tests pass
  with two Linux-only skips (Python 3.12). Exact minimal actor candidate: all
  757 tests pass on the seedbox (Python 3.13). Dependency, frozen production
  scoring (1,909 candidates / 387 qualified) and actual-config preflight pass.
- Python 3.12 and 3.13 [CI](https://github.com/kolorifer/radarr-festival-list/actions/runs/40752669475)
  passed on `e01c7d4`, which contains the final runtime code and initial docs.
- Deployed actor `d7487700ee8bb6eed86adefeca365945ecccc001` at 19:19 UTC.
  Final checks after maintenance: clean checkout, active/running, zero restarts,
  local/public health HTTP 200, 1,909 catalog movies. Existing 15 approvals,
  acquisition receipts and protected configurations were preserved. The
  separately installed collector remained on its existing PID/runtime, including
  the contention repair; shadow configuration/runtime were unchanged.
- Fresh exact-listing/TMDb verification succeeded before and after deployment,
  each bounded to two listing GETs and four TMDb GETs. Cache/memory writes,
  approval creation, notification, observer publication and acquisition functions
  were blocked during those metadata-only checks.

| Retained case | Verified identity | Runtime evidence |
| --- | --- | --- |
| Garden Of Love (2003) | IMDb tt0355473 / TMDb 12601 | NFO 89 min / catalog 86 min; within approved bound. |
| Charlie Victor Romeon (2013) | Charlie Victor Romeo, IMDb tt2489512 / TMDb 158933 | General Length 81:59.999 / catalog 80 min; contextual typo accepted and documented 2013 premiere agrees. |

## Silent investigation reconciliation

Prepared only the two exact retained source occurrences with the deployed actor.
A private database copy proved the existing collector would change exactly their
outcome versions to verified without changing unrelated cases. The morning report
was behind by 11 observations; its catch-up used existing observations and
read-only research evidence, with no new research jobs or provider requests.
Proof confirmed no additional unrelated digest sends would become eligible.

Paused the actor/digest and scan timer, required the scan inactive, backed up
state, rechecked source versions and published the two prepared outcomes through
the authenticated collector boundary. Added two honest `suppressed` digest
receipts and atomically refreshed the complete report. Both current collector
cases and report now say verified / external_id_verified. Original events and
proposals remain. Approval contents, retry history, downloader receipts and
research ledgers were checked unchanged; collector PID was preserved. Actor and
scan timer resumed and health was verified again.

No test notification, Telegram edit/replay, new approval, Radarr mutation or
download was performed. Old Telegram cards remain unchanged. Private deployment
backup: `~/.local/state/contextual-typos-runtime-20261028`; reconciliation evidence:
`~/.local/state/contextual-runtime-reconciliation-20261028`.

Rollback switches only actor code to `46cccea3` after stopping it, then restarts
and verifies health. Preserve current action/receipt/research state; do not restore
old snapshots over completed operations. If rolling back identity behavior, review
the two retained statuses again through the same bounded reconciliation process.

## Limitations

Minor runtime agreement does not prove an edition or the actual video contents.
Unknown/malformed NFO layouts remain unavailable evidence. Both identities still
need all ordinary validation and a separate explicit download confirmation.
The unrelated CODEX_TASK assignment is preserved.
