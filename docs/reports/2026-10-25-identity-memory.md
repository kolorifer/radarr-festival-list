# Engineering report: remembered movie identity confirmation

**Specification:** [accepted brief](2026-10-25-identity-memory-brief.md), user option 2.
**Result:** implemented; final validation/deployment pending.
**Runtime baseline:** `99d81d8e89f7fac5a0545fc1303ea8dd278846f2`.

## What changed

Successful external-ID responses now have optional private persistence, keyed by
full title/year/IMDb/TMDb/typo-mode context. Independent source-verified movie
identities also populate an exact source/title/year memory. On temporary lookup
failure, a unique remembered match is offered for explicit identity confirmation.
It is never treated as proof that the new torrent contains the same movie/cut.

The first confirmation selects the movie for that occurrence only, with no
acquisition approval created. A separate step opens the existing download
confirmation, retaining the exact original release and rejection. Grab Anyway
still checks the current Radarr movie/file snapshot. The helper also verifies
that the remembered identity choice remains live. Used child capabilities are
not recreated by replaying the review form.

New contradictory assertions mark the movie key ambiguous atomically. Expired,
ambiguous or revoked memory/choices cannot enable acquisition. Owner choices,
research proposals and typo repairs never teach this memory. Errors and hard
source conflicts are not rewritten into successful matches.

## Components

| Component | Purpose |
| --- | --- |
| verified_identity_cache.py | Private SQLite persistence, seven-day expiry, size/capacity bounds, atomic ambiguity preservation |
| tmdb_resolver.py | Reuse successful verification for identical supplied-ID context |
| identity_memory.py | Source/title/year memory, proposal gating, occurrence binding, review rendering and revalidation |
| movie_intel_service.py | Learn independent results; offer and handle separate remembered-identity confirmation |
| alternative_grab.py | Retain the memory-choice binding; enforce it in the restricted helper too |
| deployment_config.py, deployment docs | Optional private cache path and preflight |
| test_verified_identity_cache.py, test_identity_memory.py | Persistence, expiry, conflicts, concurrency, exact release and HTTP/no-acquisition regressions |

## Acceptance and evidence

| Criterion | Evidence |
| --- | --- |
| Two separate approvals | Local HTTP webhook → identity choice → separate Grab Anyway page; all acquisition calls mocked and asserted unused |
| No wrong-release reuse | Original source/link/cut/rejection retained; modified binding or child source blocked |
| No implicit identity approval | Remembered candidate remains unresolved until explicit identity POST |
| No conflict override | Native/listing IDs, ambiguous histories, mixed rejections, TV fields, expiry and revocation tested |
| Replay safety | Review retains the same child token even after that child is consumed |
| Persistence | Memory-reset, expiry, corruption, permissions, bounds and history timestamps tested |

## Tests

89 focused integration/regression tests passed before the final concurrency test.
Final complete local/seedbox and CI results will be appended after completion.
The earlier foundation-only full suite passed 694 tests with two skips; this is
not claimed as validation of the completed review flow.

## Deployment

Pending. Five retained source-verified retry results, including The End of Oak
Street, were found read-only and are eligible for memory seeding with their
original timestamps. This does not send old notifications or recreate approvals.
No live notification, torrent fetch, download, import or Radarr mutation is part
of the deployment validation.

## Limits and rollback

Remembered matches are proposals, not fresh source proof. An unseen conflict can
still exist, which is why the user must confirm the movie for each new occurrence.
Film-cut evidence remains release-specific. Exact matching may miss alternate
spellings; authentication, malformed metadata and hard conflicts remain blocked.
No live user confirmation flow has been exercised; automated coverage is synthetic.

The feature is optional through MOVIE_INTEL_VERIFIED_CACHE_PATH. Rollback must
retire any outstanding remembered-review and child capabilities before running
older code that does not recognize their kind/identity marker. Never restore old
acquisition state over completed attempts. Existing unrelated approvals must be
preserved. Private cache data can be moved aside while the actor is stopped.

## Context and review

D005 records the user's selected confirmation policy. The unrelated active
cleanup assignment is preserved. This report and brief provide the handoff;
final commit, PR and deployment references will be added after validation.
