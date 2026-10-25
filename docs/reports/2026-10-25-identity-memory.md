# Engineering report: persistent verified identity memory foundation

**Specification:** [brief](2026-10-25-identity-memory-brief.md).
**Result:** local implementation; cross-torrent identity policy awaiting user choice.
**Deployment:** none; production was verified at 99d81d8 with a clean checkout.

## What changed

Added optional private persistence for successful external-ID validation results.
Keys contain the exact title/year/IMDb/TMDb/typo-mode context. Entries survive
process restarts, expire seven days after verification, and never renew on read.
Conflicting input IDs/context cannot bypass validation through a cache hit.
Failures are misses, never positive identities. The legacy title-search cache
and exact tracker-listing verification remain unchanged.

## Files and components

- verified_identity_cache.py: private SQLite cache, expiry/size/capacity bounds.
- tmdb_resolver.py: reuse only verified results for the same input context.
- deployment_config.py and deployment documentation: optional setting and private-path preflight.
- test_verified_identity_cache.py: restart, context/ID conflicts, expiry, corruption,
  permissions, disabled operation, bounded capacity, inconsistent cached response.

## Validation

46 focused tests passed. Full local suite: 694 tests passed with two skips
in 144.253 seconds. Diff whitespace check passed.
All transports were synthetic; no live metadata queries, notifications or downloads.

## Remaining work and limits

This foundation alone does not solve the pictured failure for a different torrent
whose source metadata is unavailable. Reusing a movie identity by title/year
across releases changes the existing source-evidence rule; the choice between
automatic reuse and explicit identity confirmation is pending. The request is
therefore not complete. No production configuration, service or state was changed.
No previous source/approval/film-edition decisions were imported into the cache.
The cache is disabled unless its private path is explicitly configured.

## Project context

The completed Grab Anyway recovery report and unrelated active cleanup task are
preserved. No identity-policy decision is recorded as accepted without user input.
