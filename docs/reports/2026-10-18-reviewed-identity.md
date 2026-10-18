# Engineering report: reviewed Hamnet and Not Not Jazz corrections

**Specification:** [issue #45 brief](2026-10-18-reviewed-identity-brief.md), D005,
D008, D009 and D010. **Status:** implemented, merged, deployed and verified on
2026-10-18. No other identity or queue changes.

**Tested/deployed code:** `30adc20b7d46bbe89bb14728d778d9d1142c57c6`.
[PR #46](https://github.com/kolorifer/radarr-festival-list/pull/46) merged as
`cba8d79cd889311d3e27715774c2888f78641d0d`; merge and tested trees were equal.
Later reporting-only commits do not move the production checkout.

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

## Validation

| Check | Actual result |
| --- | --- |
| Original private evidence audit | Both retained exact source contexts and live listing IMDb associations unchanged; both reproduce `title_conflict` on the old runtime. Canonical reviewed context passes the existing external-ID checks. |
| Focused identity/adapter suite | **54 passed**, including all 16 new issue #45 regression tests. |
| Full local suite, Python 3.12 | **391 passed**, 97.819 seconds, no skips. |
| Full isolated seedbox suite, Python 3.13 | **391 passed**, 20.541 seconds, no skips. |
| CI | Python 3.12 and 3.13 passed on the exact implementation head; [run](https://github.com/kolorifer/radarr-festival-list/actions/runs/39140210169). |
| Dependencies and frozen scoring | `pip check` passed locally/seedbox; `production_scoring.py --check` unchanged at 1,909 candidates / 387 qualified (224 grandfathered + 163 new). |
| Configuration | Private schema, ownership/permissions, exact two-rule set and effective deployment configuration passed before activation. Running process uses the new binding path. |
| Sanitized diff | Only scoped runtime, regression, configuration/runbook and context documents changed; private case IDs, exact references and evidence were not added to new public artifacts. |

Synthetic tests cover wrong source/ID/year/title/reference, conflicting/ambiguous
movie lookup, TV results, broken reverse linkage, local identity conflict, changed
listing IDs, adapter failures, revocation with warm caches, insecure/invalid files,
unapproved rules, original payload immutability and exact-reference action eligibility.
Hamnet title-only correction still returns `year_conflict`; both reviewed context
fields must agree. Not Not Jazz has no generalized prefix stripping. Existing
Snowman/ambiguous controls, notification/HTTP tests and retry/replay/old action-path
regressions ran in the full suite. Acquisition behavior was exercised only against
synthetic integration fixtures.

The first local full run had 18 errors because the sandbox denied binding local
HTTP fixture servers. No application assertion failed in that run; rerunning with
loopback permission produced the passing full result above. The old 375-test
baseline is historical and is not this rollout's acceptance evidence.

## Production deployment

Starting production was clean at `a2049938b7c2cc77017de3920f1140c220108a5d`.
An isolated seedbox checkout first passed all tests, preflight and live metadata
verification. A tree guard initially refused a stale seedbox `origin/main` ref
before any runtime changes. Explicitly fetching the remote-tracking ref corrected
that stale ref; the merged and tested trees were then proven identical.

Deployment checked for active approval/systemd operations, stopped only
`movie-intel.service`, and took a consistent owner-only backup of private state
and configuration. It pinned the live checkout to the exact tested head, installed
the two mode600 private bindings, and added only their configuration path. All
unrelated configuration and dedicated tracker credentials were preserved. Effective
preflight passed before restart. Code/config rollback was prepared without any
restoration of stale acquisition state; no rollback was required.

| Production check | Result |
| --- | --- |
| Actual deployed commit | **`30adc20b7d46bbe89bb14728d778d9d1142c57c6`**, clean detached checkout. |
| Service | Active/running, new process, NRestarts=0. Only movie-intel was restarted. |
| Local/public health | Both HTTP200, `ok=true`, 1,909 movies. Health's Radarr field indicates configuration only; no Radarr API was contacted. |
| Private bindings | Exactly two loaded, mode600; credentials and all unrelated configuration unchanged. |
| Activation state | Action/cache hashes unchanged while stopped and after restart; all prior actions unchanged and zero new actions during activation. |
| Final journal check | Zero approval attempts and zero tracebacks in the inspected five-minute window. |

## Live read-only acceptance

The complete source-listing-to-context check ran both in the isolated candidate
checkout and again on the actual deployed commit with its active configuration.
Each run made 16 exact listing GETs and 36 TMDb GETs. It used retained private
release provenance, not webhook replay; original payloads were compared before
and after. Network calls were restricted to the metadata providers. Notification,
approval creation, Radarr/acquisition and persistent action/cache write functions
were explicitly blocked in the probe process.

**Final production outcome: 16/16 expected results pass**, comprising **12 verified
identities and four unchanged unmapped IMDb associations**. The two approved cases
now verify; Fragmentos, Steve Howe, Syd Barrett and Rainbow still remain unresolved
and non-actionable. Snowman remains a passing control and is not counted as an
improvement. This is **2/2 approved repairs verified**, not a claim of universal
identification coverage.

**Four additional negative/revocation checks pass:** changing each reviewed source
year blocks correction, and disabling bindings in the probe process restores each
original title conflict despite warm identity caches. The production binding file
and running configuration were not modified for these negative checks. Action and
legacy cache hashes remained unchanged throughout the production verification.

No deliberate Telegram messages, approval tokens, pending-action backfill, Radarr
reads/writes, movie additions, searches, release pushes or downloads were performed.
Normal authorized production operation continued independently. This is a live
metadata/context verification, **not a live Telegram/Grab test**. PR #41's historical
end-to-end acquisition test is not claimed as a new test of this rollout.

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

## Project context and evidence

The brief/report, PROJECT_STATE.md and the narrowly approved D005/D010 scope were
updated. CODEX_TASK.md's unrelated cleanup assignment was not executed or changed.
Issue #44's four pending identities and queue proposal remain separate. Private
evidence, bindings, probe outputs and backups stay outside public Git. The isolated
validation checkout and unused staging binding are removed after acceptance;
active configuration and rollback backups are retained. The report's containing
documentation commit supplies its final publication reference.
