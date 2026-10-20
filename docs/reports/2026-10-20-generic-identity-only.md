# Generic movie identification only

## Approved scope

The owner explicitly rejected all specific exceptions and requested generic rules
only. Remove the three actor reviewed-context repairs (Bruce, Hamnet, Not Not
Jazz), retaining standard exact-ID/title/year checks and the approved minor-typo
policy. Preserve acquisition confirmation, private history and unrelated catalog/
research operation. No downloads or notification replay.

## Implementation

Deleted `reviewed_identity.py` and removed its registry/context transformation
from `movie_intel_service.py`. New action records no longer gain the obsolete
identity_correction field. Existing action records are preserved as historical
state. `deployment_config.py` explicitly rejects the retired registry environment
setting. Deployment will remove that binding; private historical evidence remains
retained but has no code path into identification.

The generic typo resolver is unchanged. Bruce uses that rule without an override;
Hamnet's extra title/year and Not Not Jazz's performer prefix no longer receive
special treatment. They must satisfy standard catalog title/year checks; otherwise
they remain review-only. This does not alter the movies themselves or their files.

`test_generic_identity_only.py` replaces the deleted exception tests with proof
of generic Bruce matching, switch revocation, no Hamnet title/year repair, no Jazz
prefix stripping, normal exact contexts still passing, no payload mutation and
no notification/acquisition calls. The typo service test no longer mocks a
per-film hook. The legacy configuration is tested to fail preflight explicitly.

## Validation and deployment

Implementation `dd94cf9`, PR69. Isolated runtime `c025aad64cbab6b5f891aac96a11b708f0fc077c`
based on verified live `0cc5f3f`, excluding unrelated catalog changes.
Targeted 33 tests passed. Full local suite: 610 tests, two Linux-only skips.
Exact runtime on seedbox: all 593 tests passed. CI Python 3.12 and 3.13 passed at
implementation head. PR69 merged as `832131e6f1827eb0952c468362c8447a614919cf`.

Production is clean at `c025aad64cbab6b5f891aac96a11b708f0fc077c`. Private state
and configuration backed up; dependency/catalog/configuration preflight passed.
Only movie-intel restarted. The old registry environment binding was removed;
all other environment values and protected collector/research/helper settings
are unchanged. Historical private registry evidence is retained, never loaded.
Local/public health200, 1909 movies; actor/collector active NRestarts0, collector
PID unchanged, daily timer active. Approval state and downloader receipts unchanged.
Code/config rollback was prepared but unnecessary; no old state restored.

Live read-only Bruce context returned verified_tmdb / external_id_verified /
tracker_minor_typo using fresh tracker/TMDb metadata. No override mock was needed:
the verification confirms the registry setting, module and callable are absent.
Notification/action/acquisition methods were guarded and not called. No downloads,
notification replay, queue resets or action backfill. The unrelated active cleanup
brief is unchanged. Runbook, project state and D028 record the completed scope.

## Limits

The generic typo bounds remain conservative: short words, added/removed words,
changed numbers/Roman numerals, larger differences and invalid ID/year assertions
remain blocked. Historical review outcomes/messages are not rewritten. Existing
approval records remain unchanged; this removal affects new identity resolution.
The independent curated festival catalog is outside this actor matching change.
No new mechanism for film-specific overrides is introduced.
