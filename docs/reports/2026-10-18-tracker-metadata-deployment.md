# Engineering report: tracker metadata deployment and verification

**Specification:** [deployment brief](2026-10-18-tracker-metadata-deployment-brief.md),
[implementation report](2026-10-18-tracker-metadata-implementation.md), D005/D008/D009/D010.
**Result:** Merged, deployed, enabled and technically verified without test downloads.
**Production revision:** `a2049938b7c2cc77017de3920f1140c220108a5d`, clean detached checkout.
**Verification date:** 2026-10-18, local Python 3.12, seedbox Python 3.13 and live read-only providers.

## Changes and merge references

[PR #42](https://github.com/kolorifer/radarr-festival-list/pull/42) merged as
`cdb87615282f2b72c441dbd8f07d3a582cb1a1bc`. Its tested implementation commit
`760fef35f94bb0336c040c646b32214680730c6a` was deployed first with dedicated
TorrentLeech credentials and lookup enabled.

The complete listing-path check then found a presentation-markup issue missed by
the earlier single-page parser check: five listings append a separate FREELEECH
badge to their display heading. Their actual release names match exactly. The
parser now removes only that observed element with its exact expected text.
It does not strip words from release names or accept arbitrary/wrong headings.
Two regression tests cover the real markup and negative cases.

This correction merged in [PR #43](https://github.com/kolorifer/radarr-festival-list/pull/43)
as `65a695cf37400c7447f5333359847c18108df145`. Production is pinned to its exact
tested head, **`a2049938b7c2cc77017de3920f1140c220108a5d`**, whose tree matched the
merge result before activation. It includes PR #42 plus this narrow correction.
Later documentation updates do not change the production checkout.

## Dedicated authentication and activation

A fresh normal TorrentLeech login created a dedicated movie-intel session. Account
login credentials were read only in memory from existing private host settings;
they were neither printed nor copied into the repository. The resulting cookies
are stored in a dedicated owner-only mode600 file beneath the existing private
configuration directory. The service reads that file directly and has no runtime
dependency on Prowlarr's database or cookie storage.
Final read-only checks confirmed the dedicated cookie set differs from Prowlarr's
and the preexisting Prowlarr session still authenticates successfully.

`MOVIE_INTEL_TL_METADATA_ENABLED=1` and the dedicated cookie path were validated
offline and confirmed in the new running process's environment. All unrelated
configuration values were preserved. The cookie file successfully authenticated
exact listing reads; no download endpoints were requested.

Each activation stopped only movie-intel, took a consistent private state/config
backup in an owner-only directory, switched to the tested commit, validated the
effective configuration and restarted that service. Code/config rollback was
prepared for failed activation checks, without restoring old action snapshots.
The backups remain private on the seedbox.

## Acceptance and evidence

| Criterion | Verified result |
| --- | --- |
| Tested code merged | PR #42 and the narrowly scoped verification correction #43 are merged. |
| Pinned production version | Clean `a2049938b7c2cc77017de3920f1140c220108a5d`. |
| Service health | Active/running; NRestarts=0; fresh process after activation. |
| HTTP health | Loopback and public HTTPS health both 200; 1,909 catalog movies; Radarr configured. |
| Read-only Radarr connectivity | System-status GET succeeded. |
| Lookup activated | Enabled flag and dedicated cookie path confirmed in running process. |
| State preserved by activation | Action and legacy-cache hashes unchanged across each activation. |
| Read-only matching | All 16 expected outcomes passed using deployed code, current provider data and dedicated credentials. |
| No test acquisitions | Notification, approval creation, acquisition and persistent action/cache write functions blocked in the verification process. No webhook replay or approval submission. |
| Final matching state integrity | Private action store and legacy TMDb cache unchanged across the final verification. |
| Recent service log | Zero approval attempts and zero tracebacks in the final ten-minute inspection window. |

### Final live read-only sample results

Unlike the earlier ID-only comparison, this check traversed the full exact-listing
adapter and service context builder using retained release names, listing references
and title/year inputs. It ran in a separate read-only process against the deployed
code and active configuration; it did not submit requests to the notification route.

Of the 15 previously unresolved cases, **9 now verify**, **4 remain unmapped IMDb
associations**, and **2 require review**. The Snowman control also verifies: all
16 expected outcomes pass, with 10 verified identities total.

| Outcome | Movies |
| --- | --- |
| Verified TMDb | Insidious; Nocturne; The Lie; Lake Mungo; Withnail and I; Haunted Heist; Ein Mann auf den Knien; Ice Age 4 Voll verschoben; Ice Age 2 Jetzt tauts; The Snowman (control). |
| IMDb association, no TMDb mapping | Fragmentos; Syd Barrett Up Close And Personal; Rainbow In Performance; Steve Howe Live Legends. |
| Review required | Medeski Martin Wood Not Not Jazz (performer-prefixed title); malformed Hamnet 2025/source year 2016. |

Fragmentos remains non-actionable. No manual TMDb 1356955 override or other
research-derived acquisition mapping was added.

## Tests run

- Original PR #42 on seedbox: **373 passed**; pip check, production scoring and
  deployment configuration preflight passed.
- Final badge correction: **375 passed locally** (89.545s) and **375 passed on
  seedbox** (20.513s); no skips. Focused identity/adapter suite: **38 passed**.
- Final seedbox dependency check: no broken requirements. Scoring check: 1,909
  candidates / 387 qualified. Effective configuration preflight passed.
- [CI for PR #42](https://github.com/kolorifer/radarr-festival-list/actions/runs/39129559391)
  and [CI for PR #43](https://github.com/kolorifer/radarr-festival-list/actions/runs/39130527473)
  passed on Python 3.12 and 3.13.
- Final full-path read-only comparison: **16/16 expected outcomes**. These are
  identity/enrichment checks, not live approval/download tests.

## Unexpected findings

1. An initial activation preflight refused a stale seedbox `origin/main` reference
   before any production changes. Explicitly refreshing that reference resolved
   the mismatch; the tested tree and merged tree were then verified equal.
2. The first full listing-path check resolved only six cases: five headings
   included a separate FREELEECH badge. Inspection of those listings identified
   the exact markup, leading to the tested correction above. This supersedes the
   earlier assumption that a single real-page parser check covered the cohort.
3. A global action-store comparison changed during the first sample check because
   an ordinary incoming production notification created one pending approval.
   The legacy cache was unchanged; no prior action changed or disappeared, and
   all 46 actions at that inspection were pending. Service decisions showed normal
   notification processing, not an approval attempt. This was separate from the
   verification process, whose write/send/acquisition functions were blocked.
   The final sample comparison found both private stores unchanged.

## Remaining limitations and rollback

- Dedicated sessions can expire and currently require renewal through normal
  login; there is no automated credential refresh. Auth failure is safe and
  leaves notifications without an approval action.
- Four sampled IMDb associations lack a verified TMDb movie crosswalk, and two
  have unresolved context conflicts. No new independent IMDb/Letterboxd ratings
  or recognition source was introduced.
- Listing HTML may change again. Unknown badge markup or conflicting headings
  still fails closed. Busy/rate-limited requests may miss enrichment; caches and
  rate backoff are process-local and reset on restart.
- No new download test was run. The PR #41 Boxtrolls test remains historical
  evidence for the unchanged acquisition path; it is not this rollout's test.
- Existing provider/downstream release-URL logging limitations remain.

For a code rollback, use the recorded prior verified revision and its applicable
configuration backup, preserve the current action store and recheck health. To
disable listing lookups, set the adapter flag to 0 and restart only movie-intel;
native external-ID validation still applies. Never restore an old action snapshot
over completed or uncertain acquisitions.

## Project context

The deployment brief and this report archive the current instruction and result.
PROJECT_STATE and the D010 deployment authorization record were updated. Historical
implementation/investigation evidence remains intact and links forward to this
deployment result. The unrelated cleanup assignment in CODEX_TASK.md was not
executed or cleared.
The two temporary seedbox validation checkouts and unused staged environment were
removed after verification; active credentials and private rollback backups remain.
