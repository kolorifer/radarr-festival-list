# Engineering report: contextual typos and runtime variation

**Specification:** [approved brief](2026-10-28-contextual-typos-runtime-brief.md).
**Status:** implementation complete; validation/deployment in progress.

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

Final test, CI, deployment and exact-source reconciliation results follow after
verification. No live test acquisition or Telegram replay is authorized.

## Limitations

Minor runtime agreement does not prove an edition or the actual video contents.
Unknown/malformed NFO layouts remain unavailable evidence. Both identities still
need all ordinary validation and a separate explicit download confirmation.
The unrelated CODEX_TASK assignment is preserved.
