# Engineering report: reviewed Hamnet and Not Not Jazz corrections

**Specification:** [issue #45 brief](2026-10-18-reviewed-identity-brief.md), D005,
D008, D009 and D010. **Status:** implementation complete; validation/deployment
results will be recorded after verification. No other identity or queue changes.

## Implementation

Two fixed transformations correct only the reviewed observed title/year contexts.
Private bindings require the exact listing URL, full release name, parsed title,
parsed year, TorrentLeech source and source IMDb association fingerprint, plus the
expected TMDb identity and private evidence digest. Both rules deliberately use
the exact reviewed release scope; new releases/variants do not inherit an alias.

The existing listing adapter must succeed before a repair is considered. Native
IDs alone cannot substitute for the reviewed listing provenance. The corrected
context passes through the unchanged unique IMDb-to-TMDb movie lookup, expected-ID
agreement, reverse IMDb check and canonical/recorded-year validation. Conflicting
local catalog identity also blocks repair. Original payload/reference is untouched.

`reviewed_identity.py` contains only the two permitted context transformations;
private identifiers/fingerprints live outside the checkout in a validated owner-only
file. There is no generic mapping, editable title/year override or search fallback.
Rules are reread per eligible lookup; removing either binding revokes future use,
even when corrected identities are cached. Existing pending approvals are not
rewritten or backfilled. New eligible actions retain the fixed applied-rule marker.

| Component | Change |
| --- | --- |
| `reviewed_identity.py` | Fixed, exact-provenance context repairs; strict private schema/permissions and revocation. |
| `movie_intel_service.py` | Pass approved context through existing external-ID validator; fixed audit reason and action provenance. |
| `deployment_config.py` | Offline validation of optional private bindings. |
| `test_reviewed_identity.py` | Synthetic positive/negative, immutable-reference, revocation, config and action-eligibility regressions. |
| Deployment documentation | Configuration, revocation and rollback boundaries; no credential changes. |

## Validation and deployment

Pending final recorded results. The former 375-test baseline is historical, not
acceptance evidence for this change. Live verification will use provider metadata
GETs in a separate process, not the notification/approval endpoints. No full live
Telegram/Grab test is authorized or claimed.

## Remaining boundaries

Fragmentos, Steve Howe, Syd Barrett and Rainbow remain unresolved/non-actionable.
The persistent investigation queue is not implemented. Tracker session expiry,
markup changes, rate/busy handling and existing provider logging limits remain.
Exact fingerprint scope intentionally misses new variants/releases; these require
separate review rather than a broader heuristic. No credential/session changes.

For rollback, disable the private bindings or restore the recorded prior runtime
and changed configuration only, restarting movie-intel. Preserve current actions
and caches; never restore an old action snapshot over completed or uncertain work.
Private bindings can be removed without restarting because the file is reread;
removing its environment setting requires the normal service restart.
