# Individually confirmed alternative releases

Issue62 / D024 permits Radarr replacement only after the owner's explicit
per-release confirmation. This helper is disabled unless
`MOVIE_INTEL_ALTERNATIVE_GRAB_CONFIG` names its private JSON configuration.

The configuration has exactly `url` (existing HTTPS qBittorrent base), `username`,
`password`, `category` (`radarr` only), and `state` (absolute private receipt folder).
Keep it outside the checkout/web root, owner-only mode600, with parent mode700.
Reuse the approved existing client credentials. Never put real values in docs,
logs or command arguments. Offline preflight validates its shape/permissions.

The helper is a local subprocess with no network listener. Its only input is an
unexpired opaque action token on stdin; it requires an `executing` alternative
approval already durably recorded by movie-intel. It cannot accept arbitrary URLs,
client commands, categories, movie IDs or credentials from a browser. This is an
interface restriction, **not OS isolation from the same user's actor process**.
The independently confined research worker and collector receive no new access.

Eligibility requires a verified TMDb/IMDb pair, a matching monitored Radarr movie
with a file, a RADARR rejection event containing only the exact approved
existing-file quality reasons (including the exact equal/higher Custom Format score rejection), and a TorrentLeech original RSS download reference
whose numeric ID matches the release's external ID. Mixed profile/language/parse
rejections, Unknown Movie, unsupported sources and missing references fail closed.
No global profile/settings writes, library additions or searches occur.

The confirmation page compares existing and announced facts and explicitly warns
that Radarr may replace the existing file, including with a lower-quality copy.
Unknown metadata stays unknown. The existing movie/file/profile snapshot is
revalidated on viewing, confirmation, and immediately before client submission.
Source availability is not proven by an old URL: only after confirmation does the
helper fetch that exact reference, without redirects or fallback. It validates
bounded v1 torrent metadata/paths and submits the original bytes. V2-only torrents
are unavailable. The category and enabled Radarr client route must still agree,
and qBittorrent external execution hooks must be disabled.

Before any outbound submission a durable SQLite receipt reserves the source ID.
Client hash checks avoid modifying existing transfers. Acknowledgement plus hash
readback is required for `queued`; it does not prove completed download, correct
contents, Radarr import or replacement. A slow/missing readback stays uncertain.
A timeout, crash, refused fetch or prior receipt cannot automatically retry,
even through a newly created token after expiry. Inspect downloader history and
receipt privately before a separately reviewed recovery; do not erase receipts
or action attempts to make a retry work. Source availability failures are terminal
for this route until reviewed, deliberately favoring no repeated acquisitions.

Deploy only after synthetic tests and actual read-only client/route checks pass.
Back up actor state/config and receipts privately, preserve existing actions,
collector, research installation and schedule, and restart only movie-intel.
No test notification or download is authorized. Set the flag only for the tested
version. On rollback remove the new flag, retain all receipts/current action
state, durably mark every alternative capability `needs_review` before running an older actor that does not recognize this action kind, switch back to the recorded actor commit and verify health. Never restore
an old action store. Startup does not replay old notifications or make actions.


### Submission acknowledgement and reconciliation

The helper submits once, then makes at most five hash-filtered GET readbacks,
with delays of 0, 0.25, 0.5, 1 and 2 seconds and per-request connect/read timeouts
of 2/3 seconds. The enclosing helper process still has its 75-second limit.
A lost/negative add acknowledgement can be resolved only by an exact hash in the
`radarr` category. Missing, malformed, mismatched or unavailable evidence never
permits another add. `queued` remains a submission observation, not import proof.

Receipt migration preserves every original source/state/creation time and adds
private `infohash`, `detail` (fixed reason codes only) and `updated` columns.
The hash is committed before submission. Neither an expired action nor a process
crash clears the durable source barrier. No background replay or automatic
operator reconciliation is introduced.

For an owner-authorized reconciliation, inspect the exact receipt and existing
client torrent without fetching its source again. Require the client hash,
category, completion and Radarr import history download ID to agree with the
approved movie and current imported file. Legacy receipts without hashes need
additional exact release-name and submission-time correlation; do not infer
success from a similar title alone. Stop only the actor before editing its action
store, back up current private stores, mark the receipt `imported` with private
evidence, and retire only the corresponding capability. Preserve all other
approvals and the receipt itself. An old link then returns expired/used (410).
Never restore stale approval state or delete a receipt to enable a retry.
