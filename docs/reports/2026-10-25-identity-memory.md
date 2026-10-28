# Engineering report: remembered movie identity confirmation

**Specification:** [accepted brief](2026-10-25-identity-memory-brief.md), user option 2.
**Result:** implemented and deployed; live user confirmation not exercised.
**Deployed revision:** `89b1b72092e247c86e5a23b4ad25e0fd4e42f278`.
**Review:** [PR #84](https://github.com/kolorifer/radarr-festival-list/pull/84), open against the isolated runtime baseline.
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

- Full local suite: **712 tests passed, two skips**, 147.024 seconds.
- Full isolated seedbox suite: **712 tests passed**, 45.649 seconds.
- [CI passed on Python 3.12 and 3.13](https://github.com/kolorifer/radarr-festival-list/actions/runs/40196421955).
- Local/seedbox pip check passed; scoring reproduction passed with 1,909
  candidates / 224 grandfathered / 163 new / 387 qualified.
- Deployment configuration preflight and diff whitespace checks passed.
- Read-only replay of the exact original Oak Street release yields a remembered
  proposal while its identity remains unresolved pending owner confirmation.
  No review/acquisition action was created by this check.

## Deployment

Activated at **14:15 CET, 2026-10-25**. Clean checkout at the deployed revision;
movie-intel active/running with NRestarts=0; local/public HTTPS health 200 with
1,909 catalog movies. The running process's cache setting was verified.
All 34 preexisting approvals and acquisition receipts were unchanged. Protected
configuration and the identity collector PID/state were preserved.

Only the optional cache setting was added to private configuration. The dedicated
canonical cache directory is owner-only (700), with a 600 SQLite file. Five recent
source-verified retry results were seeded, including The End of Oak Street, with
their original verification timestamps. No old notification or approval was replayed.
Private activation backup/evidence: `~/.local/state/identity-memory-20261025-activation`.
Post-start checks found no traceback, memory-unavailable or retry-worker-stop errors.

The first activation preflight rejected the symlinked home-path spelling, even
though its directory permissions were already 700. The guarded script restored
code/configuration and kept acquisition state intact. Activation then succeeded
using a dedicated canonical private path; permissions were not relaxed. That
initial attempt's private backup is `~/.local/state/identity-memory-20261025`.
No live notification, torrent fetch, download, import or Radarr mutation was run.

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
runtime commit and PR are recorded above. The final report commit is documentation
only and is not deployed. Existing open runtime-stack PRs were not merged as part
of this work.
