# Torrent-page evidence in automatic investigations

## Approved scope

Owner requested generic description, NFO and embedded-screenshot collection in
automatic investigations, retaining review for conflicting-ID corrections and
no downloads or notification replays. Owner selected screenshot references for
visual review; automatic image-model analysis is outside this implementation.
The unrelated current cleanup assignment is preserved.

## Implementation

The actor projects bounded evidence from its existing exact-release-checked
TorrentLeech HTML response. Source-derived description and NFO text stay separate;
URLs, credential-like text, controls and markup are removed. Each section has a
sanitized-content digest and 3,000-character cap. The description uses static
catalog fields, not ratings/account widgets, so routine page changes do not create
research versions. Native-ID identification failures also obtain listing evidence;
verified native-ID/routine results retain their existing short path. Existing
listing pacing, cache, retry request accounting and credential location remain.

NFO images are found independently of the separate screenshot gallery. Images
after its Screenshots marker are classified separately from preceding illustrations.
At most six deduplicated public image references cross the observation boundary;
the initial supported host is i.ibb.co with fixed image extensions and no queries,
fragments, userinfo, escapes or ports. Unsupported images are counted, not followed.
No images, torrents, scripts, trailers or linked pages are fetched by this flow.
References are private review evidence, explicitly not visually reviewed.

The actor's durable observer, collector, confined handoff and research worker
validate the optional evidence schema. Old records remain compatible. Source text
is inert data, not instructions. The worker compares NFO duration claims with each
catalog candidate and retains differences/ambiguity. Description metadata is not
independent confirmation of the tracker ID. Evidence availability replaces a false
claim of missing evidence with an explicit pending-review gap; other support gaps
and all ID/year contradictions remain. No matching score, identity exception,
automatic override, acquisition approval or notification replay is introduced.

Evidence participates in the existing material-version deduplication. Only new
observations/materially changed versions are considered; there is no bulk historical
replay or reset of research budgets. Existing changed-case digest policy is unchanged.

## Verification and deployment

PR72 merged as `99f18fb3869fabe6673202005dd7dfae7a2f65bf` after both exact-head
CI jobs passed (Python3.12/3.13). Implementation head `ad2c53c`; production is clean
at isolated runtime `49531b165ce597460b9f2c254faa595277ab360b`, based on prior live
`15e07b4`. Collector selection/intake come from the collector-compatible main
implementation, preserving selected-only intake. Worker and handoff receive the
new standard-library validator; no network or credential grants were added.

Final full suites: local627 tests passed with two Linux-only skips; seedbox actor
runtime610 and collector-compatible implementation627 all passed. Tests cover
embedded images despite an empty gallery, hostile references, redaction, bounds,
source-to-observer/outbox/collector/export/worker propagation, deduplication,
review-only results, native-ID failure evidence and omission for verified movies.
Evidence extraction failure cannot change the existing listing identity result.
One earlier Python3.13 CI run hit the existing concurrent SQLite lock timeout;
the final exact-head run passed without modifying that store/test behavior.

Private state/config/code backups were taken. Dependency/catalog/config preflight,
local/public health200 (1909movies), selected-only collector health and actual
Landlock ABI6/worker denial proofs passed. Worker negative proofs used zero HTTP
requests. Protected configurations, units, unmodified installed modules, approval
state and downloader receipts were preserved. Actor/collector active with
NRestarts0; daily research timer active and scan exit0. No rollback was needed.

### Live generic pipeline proof

A bounded read-only rebuild of the exact retained Madame Bovary source found279
characters of description,1409 of sanitized NFO and three i.ibb.co screenshot
references. The two unretained image links were the description IMDb icon and
NFO poster, not the three screenshots. NFO duration is114minutes; source/catalog
runtime differences remain visible (TMDb1949 candidate106minutes, linked later
film118minutes). The prior manual AFI comparison supports114minutes, but the
worker does not invent that external corroboration or hardcode this movie.

Only a fresh private metadata observation was published, with all acquisition and
Telegram methods guarded; no webhook handler/notification replay was used. The
installed confined handoff and normal bounded worker carried the new evidence into
the current review proposal. Case remains eligible for research, needs review for
identity/year_conflict; candidates remain review_required, runtime_correction false,
and all screenshots not_visually_reviewed. Existing job status awaiting_evidence
means the proposal is waiting for review/additional evidence, not that source text
is absent. Actor approval remains unavailable and action state unchanged.

Research consumed one new material case version (weekly3 to4 of5), reusing cached
catalog evidence: request ledger stayed9 of25, unknown requests0. No budget or
history reset. The normal changed-case digest may surface the new evidence; no
forced send or replay was performed.

## Remaining limits

Screenshots are references for human/operator visual review, not image analysis.
Unsupported hosts, missing/changed page structure, truncation and unavailable
source pages limit coverage. Screenshots can be mislabeled; runtime agreement is
supporting evidence only. Catalog runtimes may themselves be wrong. The worker
still contacts only TMDb using its unchanged confined connection and budgets.
Source-page collection adds no research-provider requests; native-ID failures may
use one ordinary listing GET under the existing actor/retry guards. Snapshot size
limits remain fail-closed; richer evidence can reach the existing one-MiB limit
with fewer cases. No historical evidence is silently reclassified as approved.
