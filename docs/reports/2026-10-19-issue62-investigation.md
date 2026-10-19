# Issue 62 — exact-release alternative downloads and film editions

## Scope and status

Owner requested resumption of [issue 62](https://github.com/kolorifer/radarr-festival-list/issues/62).
Read-only acquisition feasibility investigation completed; display-only edition
implementation staged with synthetic tests. No production changes or acquisition
smoke tests. Grab Anyway remains unavailable pending the explicit credential-boundary
decision required by the issue. PR63 actor rollout remains separately owned by
its monitor; do not deploy this branch over it.

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

## Recommended implementation requiring a security decision

A narrow local helper would hold existing qBittorrent credentials separately from
movie-intel and the metadata-only research components. Its only write operation
would submit a freshly confirmed, privately bound exact release, with a fixed
non-Radarr category and separate download directory outside all library/watch
paths. Do not give the actor a general downloader API or pass client credentials
through the triage store. Explicit user approval is pending for this new boundary.

Before activation verify the client's global completion hooks, automatic torrent
management/category paths, all import/watch paths and duplicate-torrent behavior.
A category alone is not a filesystem isolation guarantee. Use per-approval private
subdirectories and validated torrent paths; reject unsafe/missing/expired source
references, redirects or identity mismatches. No acquisition test is authorized.

Reuse the existing private confirmation page and durable one-shot/uncertain-result
lockout; show existing and incoming facts, source availability, full sanitized
release name, claimed cut, quality, group and size. Submit only after fresh
identity/existing-file checks. Unknown client acknowledgement must lock the
capability rather than retry. Queued means download queued, never imported or
replaced. Manual import/replacement is a separately approved future design.

## Display-only staged implementation

`film_editions.py` provides a small source-backed fact set and bounded claim parser.
`movie_intel_service.py` annotates verified curated movies in rejection and
accepted/error notifications, reads matching existing Radarr metadata, and creates
no approvals/outcomes/retries for accepted events. Non-curated accepted events
retain passthrough and ordinary routine rejections retain skipped lookups.
Existing Add & Grab behavior stays unchanged. Facts are escaped for Telegram and
unknown/conflicting claims remain explicit. No cut metadata affects selection,
scoring or acquisition.

Editorial references: [film editions](../FILM_EDITIONS.md).

Sanitized proposed examples:

- Quality rejection: “Radarr — Release Rejected / Touch of Evil (1958) / Multiple
  significant cuts exist / Announced: 1998 reconstructed (claimed) / Existing:
  1958 theatrical (claimed).” **No Grab Anyway button yet**; route pending security
  decision. Final confirmed download wording must be “Download alternative; keep
  existing file.”
- Generic accepted Remux: “Radarr — Release Accepted / Touch of Evil (1958) /
  Multiple significant cuts exist / Edition of this release unknown.”
- Reconstruction: explanatory note says it follows Welles' memo, changes editing
  and opening sound, and was made after his death without his personal approval.

## Validation / deployment boundary

Focused parser and existing reliability/identity tests passed (41 tests at initial
checkpoint). Added synthetic HTTP coverage for accepted annotations with zero
approval creation, zero identity intake/retries, zero movie adds and zero release
pushes. Full local suite: 588 tests run, 586 passed and two Linux-only skips. A subsequent defensive input guard passed all 10 edition tests; the exact final revision will be checked on Linux before deployment. No live notification sent.

Do not deploy while PR63 is pending. Rebase/integrate its fix after merge and
revalidate the final actor revision; never reset the actor to this older base.
