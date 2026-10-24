# Grab Anyway confirmation and completed-attempt reconciliation

**Specification:** [Owner-authorized brief](2026-10-24-grab-confirmation-brief.md).
**Result:** implemented, merged, deployed, and the first completed attempt reconciled.
**Verified:** 2026-10-24, postflight after 12:36 UTC / 14:36 Warsaw.

## Finding

The first confirmed alternative, The End of Oak Street (2026), downloaded and
imported successfully but its action stayed `needs_review` and its receipt stayed
`uncertain`. The receipt was reserved at 12:00:59.581 UTC; the actor returned 409 at
12:01:00.426 UTC. qBittorrent added the matching transfer at 12:01:00, completed it
at 12:03:35, and Radarr recorded `downloadFolderImported` at 12:05:04. The library
file changed from ID 166 to 168. Replacement was explicitly permitted.

The deployed helper made only one immediate hash readback after a successful add.
An empty result or failed acknowledgement/readback permanently became uncertain.
Delayed client visibility is consistent with the sub-second failure, but the old
receipt stored neither the response nor a diagnostic reason, so the exact
historical exception cannot be reconstructed. It would be inaccurate to claim a
proven timeout. The installed qBittorrent is v5.1.4; its
[add handler](https://github.com/qbittorrent/qBittorrent/blob/release-5.1.4/src/webui/api/torrentscontroller.cpp)
acknowledges add success, which is separate from our subsequent hash readback.

## Changes

- `alternative_grab_helper.py`: one add request, followed by at most five GET-only
  checks of the exact hash. Delays: 0, 0.25, 0.5, 1, 2 seconds; per-read connect/read
  timeouts: 2/3 seconds. A lost or negative add acknowledgement can be resolved by
  exact hash plus `radarr` category evidence. Missing or conflicting evidence
  remains uncertain. No add retry, source refetch, search, or transfer mutation.
- Private `receipt_detail` records hash and fixed diagnostic codes, committed
  before submission. The original three-column receipt table and its source
  barrier are preserved, including compatibility with previous-code rollback.
- `test_alternative_grab.py`: delayed visibility, lost acknowledgement, transient
  read failure, bounded exhaustion, wrong hash/category, durable pre-add evidence,
  legacy receipt compatibility, and a real localhost HTTP delayed-visibility test.
- `deploy/ALTERNATIVE_GRAB.md`: bounds, evidence requirements and reconciliation
  procedure. The existing 75-second enclosing helper limit remains unchanged.

## Validation

| Check | Result |
| --- | --- |
| Focused final helper suite | 24 passed |
| Final full production-base local suite | 672 tests; 670 passed, two Linux-only skips |
| Exact final seedbox candidate full suite | 672 passed, no skips |
| PR80 CI, final head 64066782acc994378fe28a18e5c05579b63b04b4 | Python 3.12 and 3.13 passed |
| Dependency/configuration/catalog preflight | Passed; 1,909 candidates, 387 qualified |
| Diff verification | Clean; helper/test files identical between runtime and PR |
| Live new confirmation function | GET-only confirmation of the already existing exact hash passed |

All acquisition-path tests used synthetic transports. No new production torrent
submission, tracker torrent fetch, notification test, or Radarr mutation was run.
Reading the existing client's exported torrent metadata verified its infohash
without downloading the release again.

## Deployment

PR80 merged as `5eda30d9c4df620793eea3848c320b03603c3c90`.
Production is clean at **`f34cd4d401cedf1be671b11b00ba86bcc30bf15e`**, a focused
extension of the actual production baseline `23202815754ba2d97a86608003ca276251f1ae9c`.
Only the helper, its tests, runbook and brief changed; unrelated main catalog and
runtime changes were not deployed. Only movie-intel restarted. It is active/running
with NRestarts=0; local/public health200 and 1,909 movies. Protected actor/helper/
identity configuration and installed identity code hashes were unchanged; the
collector PID/status/restart count were unchanged.

Owner-only code/state/configuration backup and reconciliation evidence are under
`~/.local/state/grab-confirmation-20261024/` on the seedbox. Code rollback can use
`23202815`, preserving current approvals, receipts and diagnostic records. Never
restore stale action state or erase a source barrier to retry.

## Completed-attempt reconciliation

Immediately before reconciliation, verified the exact approved release name,
client add time within a second of receipt creation, completed transfer, `radarr`
category, exported-existing-torrent hash, Radarr import history download ID,
movie IMDb/TMDb association, and current file ID/scene name/size. These all agreed.
The hash and source fingerprint remain in private evidence, not this report.

With the actor stopped, backed up both stores, changed only that receipt from
`uncertain` to `imported`, recorded `operator_verified_import`, and retired only
its capability. Every other approval was byte-for-value preserved. The durable
source receipt remains, preventing another submission even through a fresh token.
Postflight confirmed the old link returns HTTP410, the same completed torrent
retains its original add/completion times, and Radarr still references file168.
No duplicate download occurred as part of this work.

## Limits and handoff

The historical failure's precise response is unavailable. Future calls that
outlast the readback/process limits, or produce contradictory evidence, still
require manual review. `queued` is not proof of import; automatic import tracking
or retroactive Telegram message editing was not added. The completed attempt was
reconciled using existing live evidence, not by replaying it.

Project state links this report. The unrelated cleanup assignment in CODEX_TASK
is preserved; this separately authorized brief is complete. No product-policy
change or new recurring task was introduced.

[PR80](https://github.com/kolorifer/radarr-festival-list/pull/80)
