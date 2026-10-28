# Brief: generic title typos and NFO runtime handling

User request, 28 October 2026: implement generic fixes for the two newly reviewed
false rejections, including MediaInfo Length parsing; test and deploy while
preserving protection against confusing a short with a feature.

- Permit one edit in a five-letter word only with an additional unchanged
  alphabetic title word of at least six letters. Preserve existing six-letter
  standalone handling, exact tracker binding, unique IMDb/TMDb round trip,
  documented year, local identity checks and explicit acquisition confirmation.
- Parse the General section's Length (file size for duration) and Duration/Runtime
  formats with seconds/milliseconds, stopping before Video/Audio/Text tracks.
  Do not guess between multiple or malformed General durations.
- Owner explicitly selected bounded runtime variation: 5% of the catalog
  runtime, capped at five minutes, retaining the existing one-minute precision
  allowance. Apply only to an exact checked listing with matching IMDb ID and
  a unique verified TMDb identity whose title/year checks succeeded. Larger
  differences remain blocked; runtime agreement never establishes identity.
- No film-specific aliases, hard-coded identity corrections, approval creation,
  historical Telegram edits, live test notifications or downloads.
- Test the main-based implementation and the exact minimal actor deployment
  revision. Preserve the separately installed collector contention fix and shadow
  services. Update only affected review outcomes through the existing collector
  boundary if the exact saved source can be freshly verified; preserve history.
- Record the main PR, actual deployed actor revision, test results, health,
  reconciliation evidence and limitations. Keep the unrelated CODEX_TASK intact.
