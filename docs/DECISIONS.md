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

- **Status/source:** Accepted explicit user/ChatGPT qualification-calibration brief,2026-10-13.
- **Decision:** An award given to an anthology or combined work is not allocated
  to individual component films unless the awarding body explicitly attributes
  it to that component.
- **Consequence:** No arbitrary allocation of Small Axe or combined Nymphomaniac
  recognition. Existing unresolved records remain explicit. This task simulates
  qualification policies without altering score weights or production behavior.

## D015 — Deployed224 is the authoritative qualification baseline

- **Status/source:** Accepted explicit user/ChatGPT final calibration brief,2026-10-14.
- **Decision:** The224 deployed qualifiers atc7a458241b4a8a2acbd4d4f5a957d71e5198adc1
  are authoritative for existing-production retention. The255 research set
  remains diagnostic; its31 additional records are not implicitly grandfathered.
- **Scope:** Compare only deployed qualification OR Evidence Score>=225 and
  deployed qualification OR Evidence Score>=250. Preserve D012/D014, score
  values and production behavior. No final threshold chosen in this experiment.
