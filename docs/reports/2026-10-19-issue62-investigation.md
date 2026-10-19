# Issue 62 — exact-release alternative downloads and film editions

## Updated owner decision

After reviewing the initial investigation, the owner explicitly said: **“if radarr automatically replaces old file - it’s ok for me.”** This supersedes issue62’s original keep-existing-file constraint for individually confirmed alternative releases. It does not authorize autonomous grabs, live acquisition smoke tests, quality-profile changes or general search. Confirmation must now disclose that Radarr may import and replace the existing file; never promise preservation.

Replacement permission does not resolve the transport limitation: installed Radarr’s manual ReleaseController only accepts a cached RemoteMovie (30-minute cache populated by that controller’s search/RSS mapping). ReleasePushController does not populate this cache. Its POST still applies RSS rejection decisions. There is no demonstrated native arbitrary-original-reference force endpoint.

The owner then explicitly approved **“Approve restricted helper and Radarr replacement.”** The restricted local helper now implements the exact-reference submission to the existing `radarr` category, with a fresh checkbox confirmation disclosing possible replacement. No live acquisition test is authorized.

## Scope and current status

Implementation includes curated edition annotations and the approved helper/confirmation flow. PR63 is merged and its isolated runtime fix `cd4e25f` is the deployment baseline. PR64 includes the main-line retry fix. Deployment validation/results are recorded below; unrelated main catalog updates must not ship with this actor change.

## Verified baseline

Read-only inspection on 2026-10-19: actor `8846f51`; collector previously installed
`23cacc8`; live Radarr `6.4.4.10685`. Two enabled autobrr actions are RADARR;
legacy direct Transmission/qBittorrent actions are disabled. The actor webhook
already receives PUSH_REJECTED, PUSH_APPROVED and PUSH_ERROR, so no new notification
routing is needed for accepted-release annotations. The actor previously enriched
only valid rejection events; approved events used passthrough.

The live Touch of Evil movie is IMDb tt0052311 / TMDb 1480 and has a 2160p Remux
file whose Radarr edition is **Theatrical Cut** (a metadata claim, not content
verification). Size 67,725,319,786 bytes; release group FraMeSToR.

## Rejections and exact-reference evidence

Retained action results include 13 pure “Existing file meets cutoff: Remux-2160p []”
rejections. Other records combine cutoff/equal-or-higher preference with quality
not wanted in profile, and there are unmonitored/language/custom-format/parse
failures. A free-text quality/profile substring is categorization only, never
permission. The future alternative path must require a validated full rejection
allowlist plus fresh same-movie/existing-file verification; reject any additional
unapproved reason. Mixed profile exclusions are not silently bypassed.

All 21 retained cutoff-bearing records have both original download and listing
references. This proves presence, not usability or lifetime; no tracker download
reference was fetched. No release-cleanup job is currently configured. Existing
approval capabilities expire after 86,400 seconds. Source references can expire
independently and must be validated again without substitution.

Raw webhook payloads were not retained in these action rows. Actual reason fields
and source-reference presence were inspected; webhook shape was checked against
installed autobrr v1.88.0 serializer source. Its edition/cut fields are arrays,
its release includes the original download reference, and its action identifies
name/type/client rather than a durable action ID. No secrets or private torrent
references are copied into this report or the triage database.

## Why the existing paths cannot promise keep-existing-file

Authoritative installed-version Radarr source pinned to
[a96bf7c](https://github.com/Radarr/Radarr/tree/a96bf7c3ecb23cb76993770727285dc17a613fbc):

- [ReleasePushController](https://github.com/Radarr/Radarr/blob/a96bf7c3ecb23cb76993770727285dc17a613fbc/src/Radarr.Api.V3/Indexers/ReleasePushController.cs)
  invokes RSS decisions and processes the decision. Re-pushing is not a force
  bypass. It also logs title and download URL: do not expand pushes or make new
  downstream privacy claims.
- [ReleaseController](https://github.com/Radarr/Radarr/blob/a96bf7c3ecb23cb76993770727285dc17a613fbc/src/Radarr.Api.V3/Indexers/ReleaseController.cs)
  manual POST requires a cached remote release; it is not arbitrary exact-URL
  download-only. Its override/download path still uses normal download handling.
- [UpgradeMediaFileService](https://github.com/Radarr/Radarr/blob/a96bf7c3ecb23cb76993770727285dc17a613fbc/src/NzbDrone.Core/MediaFiles/UpgradeMediaFileService.cs)
  removes an existing movie file during upgrade/import. Even copy-only does not
  mean keep both: existing-file removal happens first.
- [qBittorrent proxy](https://github.com/Radarr/Radarr/blob/a96bf7c3ecb23cb76993770727285dc17a613fbc/src/NzbDrone.Core/Download/Clients/QBittorrent/QBittorrentProxyV2.cs)
  filters queue reads by configured MovieCategory. Live category is `radarr`.

Autobrr v1.88.0's release action retry loads and reruns the original action; it
cannot choose a separate direct-download action without changing existing
configuration. Neither that retry nor a Radarr push supplies safe download-only
semantics.

## Implemented restricted helper

Only verified same-movie existing-file quality rejections with an intact TorrentLeech RSS reference qualify. Exact full-reason allowlists reject mixed failures. The helper accepts only an executing private action capability on stdin, revalidates movie/file/profile and source ID, fetches the exact original torrent without redirects, validates bounded torrent metadata, and submits its unchanged bytes to the existing `radarr` category. A durable source-ID receipt and infohash checks prevent repeat submissions across token expiry; ambiguous acknowledgements stay locked. No generic downloader endpoint, movie add, search, profile update or library write exists in this path.

The credentials remain in an owner-only helper config. This is a restricted process interface, not OS isolation from the same-user actor. Collector/research access and payload schema are unchanged. Read-only provisioning confirmed qBittorrent v5.1.4, existing `radarr` category and disabled external execution hooks. The helper repeats route/category/hook checks before each submission.

The page shows existing/announced release, quality, claimed edition, group, size and original rejection. It requires explicit approval of possible replacement. Unknown fields remain unknown. Queued requires a client hash readback but never means imported/replaced. Source failure or uncertain result is terminal pending private operator review; no fallback/retry. See [operator runbook](../../deploy/ALTERNATIVE_GRAB.md).

## Edition annotations

`film_editions.py` provides a small source-backed fact set and bounded claim parser.
`movie_intel_service.py` annotates verified curated movies in rejection and
accepted/error notifications, reads matching existing Radarr metadata, and creates
no approvals/outcomes/retries for accepted events. Non-curated accepted events
retain passthrough and ordinary ineligible routine rejections retain skipped lookups.
Existing Add & Grab behavior stays unchanged. Facts are escaped for Telegram and
unknown/conflicting claims remain explicit. No cut metadata affects selection,
scoring or acquisition.

Editorial references: [film editions](../FILM_EDITIONS.md).

Sanitized proposed examples:

- Quality rejection: “Radarr — Release Rejected / Touch of Evil (1958) / Multiple
  significant cuts exist / Announced: 1998 reconstructed (claimed) / Existing:
  1958 theatrical (claimed).” **⬇️ Grab Anyway** appears only after all eligibility checks. Final confirmation warns that Radarr may import and replace the existing file.
- Generic accepted Remux: “Radarr — Release Accepted / Touch of Evil (1958) /
  Multiple significant cuts exist / Edition of this release unknown.”
- Reconstruction: explanatory note says it follows Welles' memo, changes editing
  and opening sound, and was made after his death without his personal approval.

## Validation and deployment

Synthetic coverage includes strict negative source/identity/rejection gates, unchanged-file checks, exact-byte transport, durable replay blocking, uncertain outcomes, existing hash handling, explicit and concurrent HTTP confirmations, HTML/privacy handling and the unchanged normal Add & Grab path. No live webhook replay, Telegram test notification or torrent submission is permitted.

- PR64 merged as `d0bbf109bc5c39bcda3f323b6eae10cecd2f8bb9`; reviewed head `2188ecf455bdff0907ff6800e675566a4a06a442`. Python 3.12 and 3.13 CI both passed on that exact head.
- Full local suite: **609 tests**, 607 passed and two Linux-only skips. Exact isolated runtime: **592 tests, all passed** on the seedbox. The runtime has fewer tests because unrelated main changes are intentionally excluded. All changed runtime/test files are byte-identical to the merged implementation.
- Production is pinned to **`906a2cdc5c8fad2c62bb5e8ab46675ec290eb143`**, parent `cd4e25f96d1d5d0d6de5f953959bdb2ed10aa72a`. Only the 11 issue62 runtime/test/operator-document files changed. Existing catalog and installed research components were not upgraded from main.
- Dependency, catalog and enabled-config preflight passed. Catalog remains 1,909 candidates / 387 qualified. All 21 retained cutoff-bearing references passed the exact source validator; 13 contain only the known cutoff reason. These are structural eligibility findings, not proof that every historical release has a currently verified identity or live torrent.
- Private helper configuration reuses the approved existing credentials. The only actor configuration change enables that file. Actor/private state/config were backed up before activation; only movie-intel was restarted.
- Local and public health returned **200**, actor and collector remained active with **NRestarts=0**. Collector PID and protected collector/research/helper/config/timer hashes were unchanged. Installed collector remains `23cacc8`.
- Existing approval state was byte-identical across rollout. Digest ledger remained **2 sent**, and no helper receipt store was created: no helper submissions occurred. No webhook was replayed, no Telegram test message sent, no tracker torrent fetched and no download started.
- Postflight verified the deployed clean runtime and live Touch of Evil same-movie/file association. An in-memory synthetic confirmation and edition comparison passed without creating an action token or delivering a notification. Private backup/result evidence is retained under `~/.local/state/issue62-rollout/`.

## Remaining limitations and operation

The next eligible natural announcement can offer Grab Anyway; old Telegram messages are not rewritten and historical approvals are not backfilled. A fresh checkbox confirmation permits possible replacement of the existing file, including by a lower-quality alternative. Radarr may still reject import, and queue acknowledgement cannot establish imported/replaced status. End-to-end real download/import remains deliberately untested without a new per-release owner approval.

Only supported TorrentLeech original RSS references and bounded v1/hybrid torrents qualify; no generic fallback search or v2-only route exists. Strict pure-quality reason recognition excludes mixed failures and new/localized reason wording. Source lifetime is unknown until an explicit confirmation fetch. Refusal/uncertainty is durably blocked even across new tokens and needs private operator review before recovery. The helper is interface-restricted, not an OS sandbox from the same-user actor. Curated historical edition context currently covers Touch of Evil; labels in release/file metadata remain claims, not content verification.

The active unrelated `docs/CODEX_TASK.md` assignment was left intact. No new research task or schedule was started.

PR: https://github.com/kolorifer/radarr-festival-list/pull/64.
