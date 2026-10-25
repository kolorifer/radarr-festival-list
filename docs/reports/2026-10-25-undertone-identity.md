# Engineering report: Undertone identity contradiction

**Specification:** [brief](2026-10-25-undertone-identity-brief.md), user-confirmed card.
**Result:** implementation under validation; deployment and card correction pending.
**Verification date:** 2026-10-25.

## Verified cause

The 19:19:51 CET approval selected IMDb tt33498897 / TMDb 1471951, a 12-minute
short named Undertone with a 2025 date. The persisted exact-ID cache key proves
that short-film IMDb ID was supplied to the resolver; it was not selected by
remembered title matching. The journal reports listing_id_found, external_id_verified,
outside_catalog and photo_sent. The original raw listing response was not retained,
so the exact source of its earlier incorrect association cannot be reconstructed.

Fresh read-only listing evidence identifies the Ian Tuason feature, IMDb tt35892608 /
TMDb 1480387. Its NFO says 1 h 33 min and names the director in commentary credits;
TMDb records 94 minutes, a 2026 primary date and a 2025 festival release. Both films
can pass title/year checks. Previously, the ID path ignored runtime contradictions.
The current source differs from the retained verification; who changed it and when
are unverified. No hard-coded film mapping is introduced.

## Changes

- source_identity_guard.py: negative NFO runtime corroboration and fresh source
  identity revalidation, without title search or automatic replacement selection.
- movie_intel_service.py: guard before enrichment/memory/actions; no wrong poster,
  links or button on conflict; GET/POST approval revalidation before Radarr access.
- tracker_metadata.py / tmdb_resolver.py: explicit forced refresh bypasses success
  caches while retaining locks, rate limits, timeouts and no-redirect rules.
- alternative_grab.py: retain source identity and exact listing for new alternative
  actions; service approval gate checks them before invoking the helper.
- identity_memory.py: runtime conflicts quarantine remembered matches. Collector
  wire reason remains the compatible identity_conflict; collector is unchanged.

The General NFO duration parser excludes track/commentary durations, requires one
valid runtime and ignores missing/ambiguous/truncated text. Whole-minute differences
of at most one minute are inconclusive rounding; larger differences block identity.
Different cuts may therefore require review. Agreement does not establish identity.
Legacy alternative actions without source provenance retain their earlier behavior.

## Incident containment

The incorrect pending approval had no attempt marker. Its expiration was set to
zero; other approvals were unchanged. The exact incorrect-ID cache entry was
removed and the Undertone/2025 remembered match marked ambiguous. Private backup
and audit: ~/.local/state/undertone-identity-20261025-quarantine. An initial cache
key assertion stopped before mutation (configured typo mode was true); service
was restored, then the exact matching key was verified and containment completed.
No acquisition operation was invoked.

## Validation and deployment

Pending; results will be recorded after completion.

## Limits

Missing or malformed NFO runtime cannot detect this class of source error. Runtime
alone is never a selector. Provider failure during source revalidation blocks an
approval rather than trusting stale evidence. Research/collector isolation and
scoring are unchanged. Historical raw source response and exact change time are
unavailable. The unrelated CODEX_TASK cleanup assignment is preserved.
