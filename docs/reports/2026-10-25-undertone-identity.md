# Engineering report: Undertone identity contradiction

**Specification:** [brief](2026-10-25-undertone-identity-brief.md), user-confirmed card.
**Result:** implemented, deployed and exact existing Telegram card corrected.
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

Runtime revision: `72a04701d110c2b6f54cfd67c25861e6bf997a4c`, deployed at
19:39 CET. [PR87](https://github.com/kolorifer/radarr-festival-list/pull/87) remains
open against isolated runtime/undertone-identity-baseline; no unrelated main merge.

- Full local `python -m unittest -v`: 726 tests, 156.545s, OK (two Linux-only skips).
  Two additional test-only regressions were added while that suite ran; the final
  27 focused tests passed, including real GET/POST handler refusal with zero writes.
- Final full isolated seedbox suite: 728 tests, 45.560s, all passed.
- [CI Python3.12 and3.13](https://github.com/kolorifer/radarr-festival-list/actions/runs/40222191820): passed
  on the exact deployed revision. Dispatch was explicit because this PR's isolated
  base is outside the workflow's main-branch trigger.
- Frozen scoring passed locally/server: 1909 candidates, 224 grandfathered,
  163 new, 387 qualified. Server pip check and actual private-config preflight pass.
  A local private-config check had no environment file; server validation is the
  deployment evidence. The initial unprivileged focused run could not bind local
  HTTP sockets; the full local suite passed with required loopback permission.
- Actual metadata replay: General NFO runtime93; short runtime12 blocked; feature
  runtime94 accepted, with the 2025 festival date independently verified by TMDb.
- Guarded deployment: clean pinned checkout, local/public health200,1909movies,
  active/running,NRestarts0; all21 existing actions and acquisition receipts unchanged.
  Protected configuration and collector PID/state unchanged. Backup/audit at
  ~/.local/state/undertone-identity-20261025-deployment. Code rollback preserves
  current action state and the expired wrong approval; never restore old actions.

## Existing-card correction

The user supplied the exact Telegram message link. A fresh source/ID recheck and
caption dry-run passed. Edited that same message in the same chat/topic via
editMessageMedia: correct feature poster, IMDb tt35892608, TMDb1480387, canonical
2026 year plus the documented 2025 release note, normal outside-catalog wording.
The source release is unchanged. A replacement pending capability points to the
correct film and expires no later than the old one. Other live actions are unchanged.
The original detailed Radarr rejection prose was not retained, so the corrected
card preserves the known Unknown Movie category without inventing detailed reasons.

Telegram acknowledgement verifies message/chat/topic, photo and correct button;
IMDb/TMDb URLs were checked in caption_entities. The first acknowledgement assertion
looked for HTML URLs in plain caption text and failed after the successful edit;
checking the saved entities resolved it without a repeat edit or new action.
Corrected page GET200; retired page GET410. Both identities remain absent from
Radarr; health200 and NRestarts0 after correction. No acquisition POST, movie add,
search, download, import, sendMessage or sendPhoto was invoked. This is not an
end-to-end download test. Private card audit is in the quarantine backup's
card-correction directory; it contains capabilities and must not be published.

## Handoff

Brief/report and PROJECT_STATE updated. The unrelated CODEX_TASK remains untouched.
Only documentation changes follow the tested/deployed runtime revision.

## Limits

Missing or malformed NFO runtime cannot detect this class of source error. Runtime
alone is never a selector. Provider failure during source revalidation blocks an
approval rather than trusting stale evidence. Research/collector isolation and
scoring are unchanged. Historical raw source response and exact change time are
unavailable. The unrelated CODEX_TASK cleanup assignment is preserved.
