# Archived project context before the handoff workflow

This is the original PROJECT.md at runtime commit
`c7a458241b4a8a2acbd4d4f5a957d71e5198adc1`, retained for historical reasoning.
Its status statements and immediate-next-task section are historical.
Use [current project state](../PROJECT_STATE.md), [accepted decisions](../DECISIONS.md)
and [the active brief](../CODEX_TASK.md) for current work.

---

# Movie List Project — Shared Context

This file is the shared source of truth for design discussions in ChatGPT and implementation work in Codex. Read it before making project changes and update it when an agreed architectural or product decision changes.

## Goal

Build a free, maintainable movie-discovery and Radarr-assistance system that finds worthwhile films without depending on paid list services.

The project started as an IMDb Editors festival-list bridge for Radarr and has expanded into two related layers:

1. **Automated discovery feeds** for Radarr.
2. **Movie intelligence / decision support** for films encountered outside those feeds, especially autobrr/Radarr rejections.

The system should favor high-quality discovery over indiscriminate volume. Personal taste may improve ranking/tie-breaking, but should not become a hard gate that prevents discovery of unfamiliar films.

## User / deployment constraints

- Radarr is supplied as a preinstalled seedbox application; do not assume Docker control over Radarr.
- Avoid paid list services/subscriptions where a free reliable source is possible.
- The original feed must remain usable as a StevenLu Custom import list in Radarr.
- Radarr automatic-add configuration for the festival feed is intentionally conservative: add movies, do not automatically search on add.
- Do not expose tracker download URLs, passkeys, API keys, Telegram tokens, Radarr credentials, or similar secrets in notifications, logs, generated public files, or action URLs.
- Prefer auditable source data and explicit failure over silently publishing an incomplete or corrupt list.

## Current branches

### `main`

Production/public feed branch.

At the time this file was created, `main` is one automated list-update commit ahead of the merge base with `movie-intel` (`696420a`, `Update festival lists`). Do not blindly force-merge or overwrite generated JSON from `main` when integrating `movie-intel`; reconcile/rebase first.

### `movie-intel`

Current implementation branch for the expanded intelligence system. It is the baseline for future Codex work until intentionally merged.

Current head when this file was created: `4bac362` (`Test Telegram approval action plumbing`).

## What is already working

### 1. IMDb Festival feed

Files: `festival.py`, `festival.json`, `.github/workflows/update.yml`

- Combines IMDb Editors' annual **Festival Films You Need to Know** lists for 2024, 2025 and 2026.
- Produces StevenLu-compatible JSON for Radarr.
- Handles pagination and validates IMDb IDs.
- Fails safely rather than replacing the public feed with an empty/incomplete result.
- GitHub Actions refreshes the production list twice daily.
- Radarr has successfully consumed this feed.

The public festival feed remains a useful broad discovery layer and should not be replaced by the narrower scoring work below.

### 2. 2026 curated/scored feed

Files: `curated.py`, `curated.json`, `curated-details.json`

- Adds explicit film-level signals from Cannes, Berlinale, Venice and Letterboxd HQ to the IMDb festival baseline.
- Uses configurable scoring (`MIN_SCORE`) rather than a fixed list size.
- Deduplicates by resolved IMDb ID.
- Keeps a detailed audit output explaining why each film scored.
- This is an experimental/narrower layer; changing weights or threshold should be treated as a product decision, not incidental cleanup.

### 3. Historical back-catalogue audit

Files: `backcatalog.py`, `backcatalog_resolve.py`, `backcatalog.json`, `backcatalog-details.json`, `sources/tspdt-21c.json`

- Historical scope is currently 2000–2023.
- Uses TSPDT 21st-century canon as the base universe plus independent institutional signals such as Sight & Sound and major festival top prizes.
- Personal positive taste is a small positive tie-break/ranking signal only; unknown films receive no taste penalty.
- Watch state does not remove canonical films; it only affects monitoring recommendations.
- The historical model exposed an important limitation: a TSPDT-only universe can miss relevant films entirely. Example from evaluation: `Nocturnal Animals` is absent from the base universe; `Shame` demonstrated a low-score false-negative case. Future work should therefore prefer a union of credible source universes/signals rather than merely tuning the TSPDT cutoff.
- This layer was initially audit/research oriented and should not be connected to Radarr automatically without an explicit decision.

### 4. Scoring simulation / institutional expansion

Files include `simulate_scoring.py`, `scoring-simulation.json`, `simulation-qualifiers.json`, `sources/phase-b-institutional.json` and related simulation outputs.

- Research/simulation has been deliberately separated from the production list-refresh workflow.
- The branch includes expanded institutional signals and promotion/qualification routes.
- Exact title/year resolution is conservative; ambiguity and wrong-year matches should be rejected rather than guessed.
- The simulation artifacts are evidence/audit outputs and should not silently become production behavior.

### 5. Audience ratings data

Files: `audience_ratings.py`, `audience-ratings.json`, `.github/workflows/audience-ratings.yml`

- Provides audience-rating context used by the movie-intelligence layer.
- Ratings are informational/contextual, not currently a hard qualification gate.

### 6. Movie-intelligence service

Files: `movie_intel.py`, `movie_intel_service.py`, `tmdb_resolver.py`, `radarr_client.py`, `pending_actions.py`

The `movie-intel` branch implements the core of an enriched autobrr/Radarr notification service:

- Builds a local intelligence index from audience ratings, qualifiers, institutional signals and back-catalogue data.
- Resolves movies conservatively through TMDb when local information is insufficient.
- Classifies Radarr rejection reasons (`unknown_movie`, quality, existing, not-upgrade, other).
- Formats enriched Telegram notifications with ratings, recognition and model qualification context where available.
- For an **unknown movie** rejection, can persist a short-lived pending action and provide an approval URL.
- The approval page lets the user choose a valid Radarr root folder and quality profile.
- Approval adds the movie to Radarr **without launching a general indexer search**, then re-pushes the exact autobrr-announced release to Radarr.
- Sensitive tracker/release credentials are intended to remain server-side.
- Health endpoint and explicit configuration checks exist.

Deployment preparation now includes `deploy/README.md`, a private environment
template, a user systemd unit, an HTTPS proxy fragment, and a launcher that reads
the environment file without executing shell expressions. `--check-config`
validates required settings offline. Production startup fails on missing/invalid
settings; local development uses `--allow-unconfigured` on loopback only.
Webhook delivery fails closed without its secret. Approval URLs require an
explicit HTTPS public base URL; request headers cannot choose their origin.
Approval submissions are serialized within a single process to prevent replay.
Notification/error text redacts private URLs and configured credentials.

### 7. Tests / CI

The `movie-intel` branch contains focused tests for:

- local movie intelligence and rejection classification,
- service/action behavior,
- pending actions,
- Radarr client behavior,
- TMDb resolver behavior.

`test_movie_intel_http.py` additionally exercises the webhook → notification →
confirmation → exact-release flow over real local HTTP with synthetic external
services. This verifies service wiring without production side effects; actual
autobrr payload compatibility and seedbox integration remain unverified.

`.github/workflows/movie-intel-test.yml` runs the movie-intel tests.

## Current product decisions

These are intentional and should not be changed casually:

- Keep the broad IMDb Festival feed and the scored/curated experiments conceptually separate.
- Scoring thresholds/weights should remain tunable.
- Personal taste is a positive ranking/tie-break signal, not a negative filter for unseen films.
- Watched status is not evidence that a film is unworthy; it only changes what should be monitored/downloaded.
- Conservative identity resolution is preferable to false matches.
- Research/simulation outputs must remain separate from production automation until explicitly promoted.
- For unknown movies encountered by autobrr, approval should re-push the exact announced release rather than trigger a broad Radarr search.
- Secrets/private tracker URLs must never be sent to Telegram or exposed in public action links.

## What still needs to be done

### A. Finish real deployment/integration of `movie-intel`

The code and tests exist, but the remaining work is operational integration on the actual environment:

Cloud SSH access to the user's seedbox failed during preparation. No seedbox
deployment was performed. Python 3.13.5 and a running user systemd manager were
confirmed; service CI now covers Python 3.12 and 3.13. Confirm SSH access, the
actual Radarr URL, and a provider-supported HTTPS movie-intel route; enter credentials only in
the private host configuration. Use `deploy/README.md` for the prepared procedure.
Autobrr upstream webhook fields have been checked; the installed version still
needs a real payload check. Radarr itself logs pushed URLs and cleans only known
credential patterns; verify provider log controls before claiming the complete
deployment preserves secret-handling guarantees.

1. Reconcile `movie-intel` with the latest `main` generated-list commit before merge.
2. Decide how/where the HTTP service will run on the seedbox or another always-on host.
3. Configure the required environment variables/secrets (Radarr, Telegram, webhook secret, public base/path as applicable) outside the repository.
4. Connect the actual autobrr webhook/event payload to the service and verify the payload shape against the parser.
5. Provide a secure reachable HTTPS route for approval links if approvals are to be used outside the local network.
6. Perform an end-to-end test with a real unknown-movie rejection:
   - autobrr event arrives,
   - enriched Telegram notification is sent,
   - approval link opens,
   - valid root/profile choices are loaded from Radarr,
   - movie is added without search,
   - the exact announced release is re-pushed,
   - action token becomes unusable afterward,
   - no secret/download URL leaks into Telegram, browser URL, logs, or public files.
7. Only after successful real-world verification, decide whether to merge `movie-intel` into `main` or keep runtime/service code on a dedicated branch/deployment path.

### B. Improve discovery model after runtime work is stable

Do not solve this merely by lowering a threshold.

- Expand the historical candidate universe beyond TSPDT so good films absent from TSPDT can qualify through other credible sources.
- Evaluate false positives/false negatives using the user's watched/known sample, but preserve unknown-film discovery.
- Keep institutional/canon/editorial signals auditable and avoid opaque scoring changes.
- Decide whether/when historical qualifiers should become a Radarr import feed versus remaining recommendation/audit data.

### C. Documentation cleanup

`README.md` still mainly describes the original IMDb Festival bridge. After `movie-intel` deployment decisions stabilize, update README documentation so public/production instructions are accurate without exposing private deployment details or secrets.

## Collaboration workflow (ChatGPT ↔ Codex)

1. **Discuss product/design changes in ChatGPT.**
2. Once a decision is agreed, update this file (especially `Current product decisions` and `What still needs to be done`) if the decision materially changes project direction.
3. **Codex should read this file before implementation** and work from the current repository state rather than from an old chat transcript.
4. Codex should implement the smallest coherent change, add/update tests, and report exactly what changed plus any assumptions or unresolved deployment dependency.
5. Do not silently reinterpret product decisions while coding. If implementation reveals a meaningful tradeoff, return it for discussion rather than choosing a new product policy by accident.
6. Before parallel implementation work, check branch/commit state to avoid concurrent edits to the same files.

## Immediate next task for Codex

Treat the current `movie-intel` branch as the implementation baseline. First inspect the branch and tests, then prepare it for real deployment without changing selection/scoring policy. The first concrete engineering objective is to make the webhook → Telegram → approval → Radarr exact-release flow deployable and testable in the user's actual environment, while preserving secret-handling guarantees.
