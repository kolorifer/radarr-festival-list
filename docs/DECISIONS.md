# Movie List decisions

This is the record of accepted product/architecture decisions and rationale.
The user and ChatGPT own these decisions. Codex implements them and records an
agreed change here; it does not turn an implementation convenience into policy.

For a new decision, record: ID, status, agreement date/source, decision, rationale,
consequences, and any superseded decision. Preserve the previous rationale.
The existing product baseline below was captured from the original
[PROJECT.md context](https://github.com/kolorifer/radarr-festival-list/blob/7e9c32f7ac5d8c9a310e69a706731a272f23c003/docs/archive/PROJECT-before-handoff.md), not newly invented by
the workflow documentation task.

## D001 — Discussion, specification, engineering, review

- **Status:** Accepted.
- **Agreed:** User workflow instruction, 2026-10-13.
- **Decision:** The user and ChatGPT discuss product design, architecture,
  recommendation logic, behavior changes, priorities, and analysis of outputs.
  Codex implements, debugs, tests, deploys, and technically verifies a clear
  agreed implementation brief.
- **Rationale:** Preserve design reasoning across long threads and avoid repeated
  explanation/manual translation or independent product decisions by Codex.
- **Consequences:** PROJECT_STATE.md records current stable behavior; this file
  records decisions/rationale; CODEX_TASK.md contains the currently assigned task
  only. Completed briefs and structured engineering reports stay in Git/GitHub.
  Routine technical choices are allowed; substantial ambiguity is flagged and
  interpreted conservatively. The user and ChatGPT review the result and decide
  the next iteration.
- **Boundary:** Repository persistence helps both tools recover context when
  given access or links. It does not automatically synchronize unrelated chats.

## D002 — Broad discovery and scored research remain separate

- **Status/source:** Accepted existing baseline; captured 2026-10-13.
- **Decision:** Preserve the broad, StevenLu-compatible IMDb Festival production
  feed. Keep narrower curated/scored experiments conceptually separate.
- **Rationale:** High-quality discovery should not silently shrink to a research
  model's current universe or replace a working broad feed.
- **Consequences:** Preserve production generated outputs and branch behavior;
  weights/threshold changes require an agreed product brief.

## D003 — Taste helps ranking without excluding unfamiliar films

- **Status/source:** Accepted existing baseline; captured 2026-10-13.
- **Decision:** Personal positive taste is a small positive tie-break/ranking
  signal. Unknown films receive no taste penalty.
- **Rationale:** Personalization should improve discovery without making past
  familiarity a hard gate.
- **Consequences:** Do not add negative unknown-film filters or retune scoring
  as incidental implementation cleanup.

## D004 — Watched state changes monitoring recommendations

- **Status/source:** Accepted existing baseline; captured 2026-10-13.
- **Decision:** Watched status does not remove canonical films or mean they are
  unworthy; it affects monitoring recommendations.
- **Rationale:** Recognition/quality and the owner's current acquisition needs
  answer different questions.
- **Consequences:** Keep canonical qualification independent of watch state.

## D005 — Resolve identity conservatively

- **Status/source:** Accepted existing baseline; captured 2026-10-13.
- **Decision:** Prefer explicit ambiguity/failure over a guessed movie identity
  or wrong-year match.
- **Rationale:** Incorrect movie additions/downloads are more harmful than a
  missed automatic resolution.
- **Consequences:** Preserve conservative title/year/TMDb matching and tests.
- **Implementation follow-up, 2026-10-18:** The user authorized implementing the
  tracker metadata investigation findings. Explicit movie IDs now require
  crosswalk/context validation, with optional exact-listing lookup and safe
  unresolved/review states; no manual crosswalk or relaxed text-search rule was
  adopted. See the [implementation brief](reports/2026-10-18-tracker-metadata-implementation-brief.md).

- **Narrow exception authorized, 2026-10-18:** [issue #45](https://github.com/kolorifer/radarr-festival-list/issues/45)
  permits only the reviewed Hamnet source-context repair and Not Not Jazz exact
  alias. Both require private exact-source bindings and unchanged unique
  IMDb/TMDb roundtrip/year checks; original release data remains immutable.
  No other mapping, generic alias/year heuristic or investigation queue is approved.
  Implementation and verified deployment are authorized by the
  [brief](reports/2026-10-18-reviewed-identity-brief.md).

- **Remembered identity proposals authorized, 2026-10-25:** The user requested
  persistent reuse of previous successful lookups and selected option 2: an exact
  source/title/year remembered match must be explicitly confirmed for each new
  torrent before enabling Grab Anyway. This permits private bounded persistence
  of independently verified identities and proposals during temporary lookup
  failures, not automatic identity acceptance, fuzzy matching, contradiction
  overrides or learned owner exceptions. Identity confirmation and download
  approval remain separate; source links, rejections and film cuts remain
  specific to the new release. See the [brief](reports/2026-10-25-identity-memory-brief.md).

- **Short-title typo adjustment authorized, 2026-10-28:** The user approved
  broadening the existing exact-listing typo rule for Carrue/Carrie. Single edits
  on words of at least six letters remain subject to the existing unique IMDb and
  TMDb crosswalk, year and conflict checks, and do not approve a download. See the
  [brief](reports/2026-10-28-short-title-typos-brief.md).

## D006 — Audience ratings provide context

- **Status/source:** Accepted existing baseline; captured 2026-10-13.
- **Decision:** Audience ratings are informational context, not a hard
  qualification gate.
- **Rationale:** Ratings complement institutional/editorial signals without
  independently deciding discovery eligibility.
- **Consequences:** Turning ratings into a gate requires an agreed behavior change.

## D007 — Research outputs do not silently become production feeds

- **Status/source:** Accepted existing baseline; captured 2026-10-13.
- **Decision:** Historical 2000–2023 work and institutional/scoring simulations
  remain research/audit until explicitly promoted.
- **Rationale:** Candidate-universe limitations and false positives/negatives need
  evaluation before affecting automated acquisition.
- **Consequences:** Preserve auditable source signals and keep research separate
  from production refresh. Universe expansion is a review topic, not a chosen
  implementation in this handoff.

## D008 — Approval re-pushes the exact announced release

- **Status/source:** Accepted existing baseline; captured 2026-10-13.
- **Decision:** A suitable unknown-movie rejection may offer an expiring approval
  action. Confirmation uses valid Radarr root/profile choices, adds the movie
  without a general indexer search, then re-pushes the exact announced release.
- **Rationale:** The user approves a specific acquisition rather than an
  uncontrolled search or automatic addition on every rejection.
- **Consequences:** Keep private release references server-side, serialize
  confirmation within one process, prevent successful replay, and inspect remote
  history after an ambiguous timeout. Existing Radarr list automation is
  independent of this approval flow.

## D009 — Secret handling includes downstream systems

- **Status/source:** Accepted existing baseline plus explicit deployment
  constraints, captured 2026-10-13.
- **Decision:** Credentials, tracker/download URLs, passkeys, webhook secrets,
  and approval tokens must not appear in public artifacts, logs, or chat.
  Capability approval links are sent only through the intended private flow;
  their tokens are not reproduced in reports or provider request-path logs.
- **Rationale:** Redacting one application's messages does not protect another
  application's logs or an upstream proxy.
- **Consequences:** Private environment/state, explicit HTTPS origin, loopback
  application binding, request-path log suppression, and downstream/provider
  logging checks. Deliberate real notification/add/download tests require
  approval for the specific notification/movie/release, and still must respect
  secrecy constraints.

## D010 — Respect the provider and production boundary

- **Status/source:** Accepted existing baseline and deployment constraints,
  captured 2026-10-13.
- **Decision:** Use provider-managed Radarr and supported user services/proxy
  settings. Do not assume Docker/root control, reinstall Radarr, overwrite
  unrelated services, or merge runtime work into main under the current scope.
- **Rationale:** The seedbox is a shared managed environment with existing work
  and production discovery feeds.
- **Consequences:** Inspect before changing, back up replaced private settings,
  adapt installation paths, preserve feeds/scoring, and report rollback and
  deployment limits. A future change to this boundary needs an agreed brief.
- **Authorized rollout, 2026-10-18:** The user explicitly requested merging PR
  #42, deploying tested code, enabling TorrentLeech lookup with dedicated private
  credentials, and health/matching verification without downloads. The
  [deployment brief](reports/2026-10-18-tracker-metadata-deployment-brief.md) records
  this scope; other services, scoring and unrelated cleanup remain unchanged.

- **Authorized narrow rollout, 2026-10-18:** Issue #45 and the current user request
  authorize a reviewed PR, tests and safe production deployment of only the two
  identity corrections in its [brief](reports/2026-10-18-reviewed-identity-brief.md).
  Live acceptance is read-only metadata/context verification; no notifications,
  approval creation or acquisition tests are included.

## D011 — Compare audience weights without choosing production policy

- **Status:** Accepted experiment specification, 2026-10-13.
- **Source:** Current user brief and clarification replies.
- **Decision:** Compare IMDb + Letterboxd at a 150-point and a 200-point maximum
  on one frozen universe. The user confirmed 0.75 × the shared component sum
  for Audience=150 and the unscaled sum for Audience=200.
- **Rationale:** Supply evidence for a later product decision, without choosing
  a preferred cap during engineering.
- **Preserved behavior:** Existing TSPDT/Sight & Sound correlation adjustment
  remains identical in both runs, as explicitly confirmed by the user.
  Existing critics-group/broad-critic implementation is reused.
- **Constraints:** Other family weights are fixed. European Recognition's
  requested weight of 200 uses 2 × its existing normalized 100-point score.
  Qualification, production feeds, runtime deployment and main are unchanged.
- **Review boundary:** Diagnostic bands and dominance examples provide evidence
  for discussion; they do not introduce qualification rules.

## D012 — Final research Evidence Score model

- **Status/source:** Accepted user/ChatGPT decision, current integrity brief, 2026-10-13.
- **Decision:** Audience uses IMDb + Letterboxd at 150 points, proportionally
  weighted 0.75 × their existing calibrated component sum. The effective fully
  eligible Evidence Score ceiling is 1000.
- **Preserved:** All other family weights, existing canon correlation, and
  qualification logic remain unchanged. No threshold is selected in this task.
- **Rationale:** Product review has selected the model; identity/data quality is
  audited before threshold calibration. D011 remains the historical comparison.
- **Boundary:** Research-only until explicit production merge/deployment approval.

## D013 — Standing authorization for routine engineering

- **Status/source:** Accepted explicit user instruction,2026-10-13.
- **Decision:** Codex completes agreed engineering work autonomously, including
  repository edits, scripts/tests, Git operations, SSH, log/service inspection,
  API queries and non-destructive debugging.
- **Rationale:** Avoid unnecessary repeated command confirmations.
- **Boundary:** Ask for missing credentials/access or uncovered product choices,
  and before destructive/difficult-to-reverse actions, important data deletion,
  meaningful external cost, or production behavior beyond the agreed task.
  The existing specific live-test and production boundaries still apply.

## D014 — Anthology and combined-work attribution

- **Status/source:** Accepted explicit user/ChatGPT qualification-calibration brief, 2026-10-13.
- **Decision:** An award given to an anthology or combined work is not allocated
  to individual component films unless the awarding body explicitly attributes
  it to that component.
- **Consequence:** No arbitrary allocation of Small Axe or combined Nymphomaniac
  recognition. Existing unresolved records remain explicit. This task simulates
  qualification policies without altering score weights or production behavior.

## D015 — Deployed 224 is the authoritative qualification baseline

- **Status/source:** Accepted explicit user/ChatGPT final calibration brief,2026-10-14.
- **Decision:** The 224 deployed qualifiers at c7a458241b4a8a2acbd4d4f5a957d71e5198adc1
  are authoritative for existing-production retention. The 255 research set
  remains diagnostic; its 31 additional records are not implicitly grandfathered.
- **Scope:** Compare only deployed qualification OR Evidence Score>=225 and
  deployed qualification OR Evidence Score>=250. Preserve D012/D014, score
  values and production behavior. No final threshold chosen in this experiment.

## D016 — Final qualification policy for the current iteration

- **Status/source:** Implemented and deployed, 2026-10-14.
- **Decision:** Future qualification uses the current deployed 224 films as a
  grandfathered set, plus any new film with Evidence Score >=225. The threshold
  is inclusive.
- **Rule:** `qualified = grandfathered_production_224 OR evidence_score >= 225`.
- **No extra guards:** Do not add an Audience-share cap, family-count minimum,
  age normalization, or other qualification rule on top of the 225 threshold.
- **Legacy rules:** Existing convergence/corroboration qualification rules are
  not a continuing admission path for new films once this policy is implemented.
  They may remain as historical provenance/diagnostic metadata, but must not
  independently qualify future additions.
- **Rationale:** The final P225/P250 comparison showed that 225 adds 36 supported
  films beyond 250, with no Audience-only newcomers. The additional cohort has
  substantial non-Audience evidence and includes the festival/cinephile discovery
  profile the project is intended to capture; 250 mainly reduces discovery
  without demonstrating better taste precision.
- **Grandfathering:** The 31 research-only comparator additions are not
  grandfathered. They qualify only if they independently satisfy Evidence Score
  >=225. The authoritative grandfathered set remains the actual deployed 224 from
  D015.
- **Implementation authorization:** The subsequent user brief explicitly authorizes
  implementation, validated merge to main and seedbox deployment. This supersedes
  D010's earlier no-merge scope for this iteration.
- **Implementation:** `production_scoring.py` and `production/movie-catalog.json`
  are authoritative. Active routes are `grandfathered_production` and
  `evidence_score_225`; both are recorded when applicable. Legacy routes are
  audit metadata only. All 224 IDs/routes are frozen from c7a4582.
- **Acquisition boundary:** No bulk Radarr additions/searches/downloads or
  import-list refresh. The existing approved exact-release flow and public
  festival/curated feeds remain independent.
- **Annotation correction:** La Ciénaga, Uncle Boonmee and Elephant were selected
  to watch, not watched. Their existing-schema state is unknown; this has no
  score/qualification effect.
- **Verified result:** All 1,909 frozen scores unchanged; 224 grandfathered +
  163 naturally admitted = 387 qualified. PR #6 merged; runtime activated at
  8e357b9edc90307c6af3e64f1c334527a11a5227. No acquisition/list refresh.
- **Verification/report:** [Production engineering report](reports/2026-10-14-d016-production.md).

## D017 — Radarr Movie List membership and score-band synchronization

- **Status/source:** Accepted implementation brief on main a4c9066, 2026-10-14;
  implemented and deployed; initial reconciliation verified.
- **Decision:** Every D016-qualified film has movie-list and exactly one managed
  score-band tag. Existing matching movies receive tags retroactively; missing
  movies are added monitored with movie search disabled.
- **Bands:** ml-below-225, ml-225-249, ml-250-299, ml-300-399, ml-400-plus.
  Use the full Evidence Score at inclusive 225/250/300/400 boundaries.
- **Preserved:** Existing monitoring/profile/root/files/Overview and unrelated
  tags. Numeric scores remain in the catalog; no exact-score tags. D012/D014/D016
  formulas, identities, qualification and public feeds are unchanged.
- **Future reconciliation:** Replace only stale managed bands; remove only
  managed tags from films that cease qualifying. Never delete/unmonitor them.
- **Authorization:** The assigned brief authorizes the initial apply after a
  clean live dry-run, provided identities, write plan and root/profile are
  unambiguous. No search/grab/download/import-list-refresh commands are authorized.
- **Implementation:** radarr_movie_list_sync.py; private credential launcher;
  a single daily user-systemd timer. Run dry-run before first writes; require
  idempotence and zero acquisition commands before activating the timer.
- **Evidence:** [Assigned brief](reports/2026-10-14-radarr-movie-list-sync-brief.md);
  [engineering report](reports/2026-10-14-radarr-movie-list-sync.md).

- **Verified implementation:** PR #7 merged at a587e25; 107 tests (25 new).
  152 existing movies tagged, 235 missing records added, 387 correctly tagged,
  zero unresolved and zero second-run changes. All original settings/files/
  Overview/unrelated tags preserved. Search disabled on every addition.
- **Scheduler:** movie-list-sync.timer, daily 03:43 UTC + up to 15min delay, one
  user-systemd path with a private overlap lock. Installed oneshot completed
  successfully with zero additional writes.

## D018 — Private read-only Radarr snapshot bridge

- **Status/source:** Explicit assigned brief on main65d1b8b, implemented/deployed2026-10-14.
- **Decision:** Reuse the existing successful daily reconciliation and private
  Radarr credentials to publish one sanitized current-state file in private
  kolorifer/radarr-state; no additional scheduler or Radarr integration.
- **Boundary:** Snapshot generation makes only read requests. Strict schema
  excludes credentials, server details, filesystem paths, Overview and
  queue/release/downloader information. Never publish it in the public project.
- **Failure behavior:** Failed export/publication is reported separately, never
  repeats reconciliation or changes Radarr as an export side effect.
- **Verified:** PR #8 merged at93a5761;133 tests. Live990-row private snapshot,
  deterministic content except generation time, zero Radarr writes, seedbox
  publisher and existing GitHub connection readback verified. Normal GitHub
  commit versions remain; only one current-state file is maintained.
- **Report:** [Implementation/deployment](reports/2026-10-14-radarr-snapshot-bridge.md).

## D019 — One-time additive watched annotations in Radarr

- **Status/source:** Explicit assigned brief on main00cb386;implemented/applied2026-10-14.
- **Decision:** Apply watched additively to the user's exact private IMDb target
  manifest. No title matching, removals, monitoring changes or acquisition.
- **Safety:** Require unique exact live matches, clean recorded dry-run, fresh
  state checks and preservation of all other movie data/tags. This is a one-time
  user-state operation, not a new recurring sync or qualification rule.
- **Privacy:** Authoritative manifest and all per-film audits remain private.
  Public reports contain aggregate counts only.
- **Verified:** 271 targets tagged,0 missing/ambiguous,0 second-run changes;
  1 tag creation +1 additive editor request; no other writes/acquisition commands.
  All settings/files/metadata and unrelated tags preserved. Private snapshot
  refreshed and verified through existing GitHub connection. PR #9 merged;
  151 tests (18 new) and CI pass.
- **Report:** [Aggregate implementation/deployment](reports/2026-10-14-watched-tagging.md).

## D020 — Watched/unmonitored state for the new Movie List import cohort

- **Status/source:** Explicit assigned87-film private cohort brief on main70c9312;
  implemented/applied2026-10-14.
- **Decision:** Exact verified cohort targets remain qualified/in Radarr with
  Movie List and band tags, receive watched additively and become unmonitored.
  Watched is user state and does not affect score/rank/qualification.
- **Boundary:** Cohort-only guarded true-to-false monitoring transition.
  Preserve all files/settings/metadata/unrelated tags and non-target movies.
  No acquisition/add/delete commands, monitoring-on support or scheduler change.
  General sync API restrictions remain unchanged.
- **Persistence:** Merge the verified cohort into the private canonical manifest
  after apply verification; retain cohort provenance and refresh private snapshot.
- **Verified:** All87 tagged/unmonitored;0 second-run changes/missing/ambiguous.
  Canonical271 +87 −0 overlap =358. Normal sync387 already correct with0 changes;
  existing watched/unmonitored preservation regression passes. PR #10 merged;
  167 tests (16 new), CI and deployed health checks pass.
- **Report:** [Aggregate implementation/deployment](reports/2026-10-14-watched-new-import.md).

## D021 — One Telegram stream for movie notifications

- **Status/source:** Explicit user choice, 2026-10-18; applied and read back on
  2026-10-18. Temporary API keys revoked, including authentication cache.
- **Decision:** Remove overlapping movie events (PUSH_REJECTED, PUSH_APPROVED,
  PUSH_ERROR) from autobrr's built-in Telegram notifier. The movie-intel webhook
  remains responsible for those events; retain built-in connection/update alerts.
- **Rationale:** Both notifiers target the same bot/chat and duplicate movie
  messages make enrichment and approval-button behavior appear inconsistent.
- **Boundary:** Preserve webhook credentials, destination, all unrelated event
  settings, filters/actions and Radarr/list automation. No acquisition permission
  is created by this notification routing change.


## D022 — Changed-case-only Telegram investigation digest

- **Source/status:** Explicit user approval on 2026-10-19; implemented and enabled.
- **Decision:** Send current review cases once and then new/materially changed
  investigation cases through movie-intel's existing Telegram path. Keep identity
  corrections subject to review and preserve all Radarr/Grab safeguards.
- **Boundary:** Informational messages only; no buttons, approval tokens or
  automatic corrections. The research worker receives no Telegram credential or
  expanded permissions. Research timing/budgets remain unchanged.
- **Delivery:** Private durable deduplication; uncertain acknowledgements require
  inspection before resend, explicit rate rejection may retry. Daily reports and
  five-minute polling determine notification latency.
- **Evidence:** [Deployment report](reports/2026-10-19-identity-digest.md).


## D023 — Record selected action attempts, not all movie announcements

- **Source/status:** Owner's issue60 and explicit implementation/deployment request,
  2026-10-19; selected-only notifier/configuration enabled.
- **Decision:** Record releases that matched enabled autobrr filters and attempted
  an action, including Unknown Movie rejection and action errors. Action acceptance
  is not evidence of completed download or verified movie identity.
- **Boundary:** Preserve actor notifications, Add & Grab, retries, daily bounded
  research and digest; collector remains metadata-only and confined. Keep history
  and all ledgers. No automatic purge or new identity correction.
- **Coverage:** Action-result events miss pre-action failures, no-action matches,
  nonreturning actions and transport losses. Retained comparison showed no newly
  dropped accepted class; natural end-to-end verification was unavailable during
  the quiet bounded window and remains pending.
- **Evidence:** [Engineering report](reports/2026-10-19-selected-intake.md).

## D024 — Permit replacement after an explicitly confirmed alternative grab

- Source: owner message, 2026-10-19: “if radarr automatically replaces old file - it’s ok for me.”
- Supersedes issue62’s initial never-replace requirement for owner-confirmed alternative releases only. The confirmation must disclose possible Radarr replacement.
- Owner subsequently explicitly approved: “Approve restricted helper and Radarr replacement.” Reuse existing qBittorrent credentials through a restricted local helper, submitting only the individually confirmed exact release into the existing `radarr` category. No automatic grabs, live test downloads, generic search or quality-profile changes.
- The interface restriction is not a new OS sandbox against the same-user actor. Preserve collector/research isolation. Durable source receipts block repeat/uncertain submissions across capability expiry.

## D025 — Daily bounded metadata recovery

Owner explicitly requested fixing the week-long retry budget bottleneck and digest
clarity on 2026-10-20. Implement bounded rolling daily retry capacity: 60 GETs total,
20 tracker and 40 TMDb, retaining provider pacing/cooldowns/auth holds and per-case
attempt limits. Preserve all ledgers and migrate only pending budget waits. No
identity correction, acquisition, deeper-research budget or schedule change.

## D026 — Exact-source Bruce spelling correction

On 2026-10-20 the owner approved Bruce Almiighty (2003) to Bruce Almighty (2003),
bound to the verified IMDb/TMDb identity and exact release provenance. Use the
existing private reviewed-context registry; preserve all acquisition safeguards.
No generic typo tolerance, other identity correction or live download test.

## D027 — Automatic minor tracker-backed filename typos

Accepted by explicit owner request on 2026-10-20: identify minor filename typos
when verified tracker IMDb, unique TMDb mapping and year agree. Preserve explicit
download confirmation and existing safeguards; test/deploy without downloads.
Initial conservative implementation accepts one letter edit/adjacent transposition
in one word (both spellings at least six letters, candidate title at least eight
alphanumeric characters), excluding numeric/Roman numeral changes and word additions.
Checked listing provenance is mandatory; native-only IDs/title searches stay strict.
An operator switch can revoke this policy independently. D026's exact reviewed
binding remains available; arbitrary/larger corrections still need review.

## D028 — Generic actor identification only

Accepted by explicit owner request on 2026-10-20: no film-specific exceptions,
only generic identity rules. Supersedes D026's Bruce exception and the earlier
Hamnet/Not Not Jazz reviewed actor context repairs; also supersedes D027's
retention of those bindings. Remove the exception registry and runtime path,
not merely their current entries. Preserve generic typo acceptance and standard
ID/title/year checks, explicit download confirmation and historical private state.
Former exception cases require normal metadata agreement or remain unresolved.
No automatic notifications, downloads, replay or historical state rewriting.

## D029 — Bounded retries for missing TMDb mappings

Accepted by explicit owner request on 2026-10-20. Retry missing IMDb-to-TMDb movie
mappings using the existing durable metadata-only bounds; include the retained
Insomnia case without renewing its original expiry or resetting request history.
Identity conflicts such as Madame Bovary stay blocked. No new matching exception,
search fallback, download, acquisition approval creation or notification replay.

## D030 — Generic conflict investigation, proposals only

Accepted by explicit owner request on2026-10-20, starting with Madame Bovary.
Allow strongly correlated title/year/identity conflicts into bounded research;
search alternatives even when the tracker IMDb already maps to a movie. Retain
all conflicting assertions and gather catalog director/cast/runtime/language.
Missing independent source corroboration is an explicit evidence gap. Conflicting-ID
overrides remain subject to review; no automatic identity acceptance, exception,
download or notification replay. Existing research budgets, isolation, selected-only
intake and Radarr/Grab safeguards remain. Normal changed-case digest may surface
new proposals; no historical replay is forced.

## D031 — Generic torrent-page research evidence

Owner explicitly requested automatic collection of torrent descriptions, NFOs and
embedded screenshots on2026-10-20, retaining reviewed conflicting-ID corrections
and testing/deployment without downloads or notification replay. Owner selected
screenshot references for visual review rather than a new image-analysis service.
Collect bounded inert source evidence through the existing actor/observer boundary;
keep research isolation, budgets, identity gates and acquisition safeguards intact.
No film-specific rule or automatic conflicting-ID override is authorized.

## D032 — Explicit reviewed source-identity decisions

Owner approved the reviewed Madame Bovary release as the1949 identity on2026-10-20
and requested applying it via a generic flow, without downloads. Permit private,
revocable owner decisions bound to exact source/evidence and verified target IDs.
No film-specific code or old context registry; all other conflicting identities
remain blocked. Identity approval does not approve downloading; existing explicit
acquisition confirmation and safeguards remain. This narrows D028's ban on stored
repairs only for explicitly approved generic reviewed decisions.

## D033 — Evidence and choices, never persistent identity exceptions

Explicit owner clarification and implementation request,2026-10-20. Supersedes
D032: revoke the persistent Madame Bovary approval, retain history, and prohibit
future persistent source approvals. Gather reusable types of evidence through
generic collectors; use existing strict agreement/typo rules for automatic
identification. Inconclusive supported conflicts present source evidence and
candidate movies for explicit owner selection for that occurrence only. A later
encounter, even the same torrent, must undergo generic resolution or fresh review.
Identity selection remains separate from download confirmation. No live downloads
or notification replays during testing/deployment. Broader automatic conflicting-ID
rules require a separately justified generic evidence policy; no invented scores.

## D034 — Generic corroborated torrent-evidence identification

Owner explicitly approved implementation/testing/safe deployment on2026-10-20,
starting with Aayirathonnu Nunakal. Permit automatic identification where a checked
ID-less listing's documented title/alias, NFO runtime/audio language, unique
IMDb–TMDb mapping and documented release year agree, with no conflicting source
IDs or equally supported candidates. A later release year needs catalog evidence,
not a tolerance or filename assertion. Use cross-linked structured Wikidata dates
when TMDb lacks the later date; no film-specific facts or exception is embedded.
Missing/ambiguous evidence remains for review. Preserve explicit download approval;
no downloads or notification replays during deployment. D033 occurrence-only
human choices and conflicting-ID review remain unchanged.

## D035 — Completed human review is occurrence-scoped workflow state

On 2026-10-20 the owner explicitly requested marking today's Madame Bovary review
complete without making the 1949 choice permanent. Store an exact occurrence
review receipt for audit and distinguish it from automatic verification. A new
accepted source event reopens the case with fresh evidence and a choice, even for
the same torrent. Preserve the conflicting source assertions, history, existing
matching rules and explicit download confirmation. No live downloads are authorized.

## D036 — Explicit watched label in enriched movie notifications

Owner requested on 2026-10-27 that the unclear “POTENTIAL FALSE NEGATIVE” warning
be removed and “Watched” shown when the movie has that tag in Radarr. Display
the current tag state, without inferring it from monitoring or qualification.
The watched label replaces the model assessment; other movies retain their
existing qualification information without the warning. Qualification, movie
state, identity safeguards and download authorization are unchanged. Missing
or unavailable tag evidence does not establish watched state.
