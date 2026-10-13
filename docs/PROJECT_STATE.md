# Movie List project state

Last updated: 2026-10-13. This file describes the current architecture, behavior,
verified deployment facts, and known gaps. Accepted product decisions and their
rationale live in [DECISIONS.md](DECISIONS.md); only assigned engineering work
lives in [CODEX_TASK.md](CODEX_TASK.md). Historical reasoning is preserved in
[the original project context](archive/PROJECT-before-handoff.md).

## Purpose and ownership

Build a free, maintainable movie-discovery and Radarr-assistance system.
The user and ChatGPT agree design, behavior, recommendation logic, architecture,
priorities, and output interpretation. Codex executes engineering briefs and
reports evidence. The workflow is:

User + ChatGPT discussion → agreed task specification → Codex engineering
execution and report → User + ChatGPT review and next specification.

## Architecture and stable behavior

| Component | Role and behavior |
| --- | --- |
| [festival.py](../festival.py), [festival.json](../festival.json) | Broad IMDb Editors festival discovery feed, StevenLu-compatible. Production refresh is separate from intelligence and scoring research. |
| [curated.py](../curated.py) and curated outputs | Experimental scored 2026 feed with auditable institutional signals and configurable thresholds. |
| [backcatalog.py](../backcatalog.py), [backcatalog_resolve.py](../backcatalog_resolve.py) | Historical 2000–2023 research/audit, built from canon and institutional signals; no automatic promotion to production Radarr feeds. |
| [simulate_scoring.py](../simulate_scoring.py) and simulation outputs | Scoring/institutional expansion research, separate from production refresh. |
| [audience_ratings.py](../audience_ratings.py) and audience ratings | Informational audience-rating context, not a hard qualification gate. |
| [movie_intel.py](../movie_intel.py) | Local intelligence index and movie/rejection context from the existing artifacts. |
| [tmdb_resolver.py](../tmdb_resolver.py) | Conservative TMDb resolution and cache when local identification is insufficient. |
| [movie_intel_service.py](../movie_intel_service.py) | Authenticated autobrr webhook handling, enriched Telegram notifications, confirmation UI, health and configuration preflight. |
| [pending_actions.py](../pending_actions.py) | Private, expiring action storage and serialization of confirmations within one process. |
| [radarr_client.py](../radarr_client.py) | Read-only choices/status, approved movie addition without a general search, and push of the exact announced release. |
| [deploy/](../deploy/README.md) | Private-environment launcher, user systemd unit, proxy fragment and deployment runbook. |

For a genuine movie `action.rejected` event, the service enriches the notification
and classifies its rejection. A reusable approval action requires an unknown
movie, a resolved TMDb identity, and a reusable release download/magnet reference.
A quality rejection or an unmonitored existing movie does not create an
unknown-movie approval action.

An approval link opens a confirmation page with Radarr root-folder/profile
choices. The confirmed action adds the movie without initiating a general indexer
search, then re-pushes the exact announced release. Successful actions become
unusable; normal release rejection can leave an action available to retry.
A timeout is not proof that the remote operation failed: inspect Radarr/download
history before retrying.

Keep the broad festival feed separate from narrower scored research. Personal
taste is a small positive ranking signal, not a penalty for unfamiliar films.
Watched status affects monitoring recommendations, not canonical worth.
Ambiguous identity or wrong-year matches are rejected conservatively.

## Repository and handoff

- `main` is the production/public feed branch; do not overwrite generated feeds
  or merge runtime changes into it under the current scope.
- `movie-intel` is the implementation baseline for the service work.
- Deployed runtime commit: `c7a458241b4a8a2acbd4d4f5a957d71e5198adc1`.
  Branch HEAD may move independently; always inspect it before a new task.
- Workflow documentation is maintained through reviewable commits/PRs.
  A documentation branch does not imply runtime deployment.
- Root [AGENTS.md](../AGENTS.md) directs engineering sessions to read the state,
  decisions, current task and relevant runbook before acting.
- Use [the task template](templates/CODEX_TASK.md) for the next agreed brief and
  [the engineering report template](templates/ENGINEERING_REPORT.md) for results.
- Completed briefs/reports live under `docs/reports/`. They are historical
  evidence, not an active backlog or automatic authorization for another change.

## Deployment and verification snapshot

The seedbox deployment completed on 2026-10-13. Its private, host-specific record
and rollback script are outside the repository. No credentials, tracker URLs,
webhook secret values, or approval URLs are recorded here.

| Item | Verified result |
| --- | --- |
| Runtime | Python 3.13.5, checkout `~/radarr-festival-list`, pinned to the deployed commit above. |
| Service | `movie-intel.service` active and enabled; zero restarts at validation; one process bound to `127.0.0.1:40714`. |
| Persistence | Running user systemd manager with lingering enabled. |
| Credentials | Existing credentials reused; `~/.config/movie-intel/environment` mode 600, outside Git. |
| State | `~/.local/state/movie-intel/` mode 700; migrated action/cache files mode 600. |
| HTTPS route | Provider-supported user nginx fragment strips the application prefix; public base is explicitly configured in private environment. |
| Proxy privacy | Application route access logging off, error log directed to `/dev/null`; config validation and graceful reload succeeded. Shared proxy configuration preserved. |
| Dependency checks | Requirements installed; `pip check` passed. |
| Automated tests | Full unittest suite: 53 tests passed at the deployed commit. Synthetic HTTP tests perform no production notification/add/download. |
| Preflight | Private-environment launcher and service startup preflight passed. |
| Health | Loopback and public HTTPS HTTP 200; public also checked from the Mac. Snapshot index count: 1,237 movies. The health Radarr flag means configuration is present, not connectivity. |
| Read-only integrations | Radarr status/root folders/quality profiles, Telegram bot/chat access, and TMDb configuration succeeded. |
| autobrr | Installed v1.88.0; existing enabled webhook matches private environment and subscribes to rejection events. Other notification subscriptions preserved. |
| autobrr logging | Changed from DEBUG to disabled through live config reload to prevent transport errors logging secret webhook URLs; no production autobrr restart. This reduces diagnostic visibility. |
| Rollback | Previous checkout and private configuration/state backups preserved; rollback script syntax checked, not executed because validation passed. |

## Live observations after deployment

- On 2026-10-13 at 12:06:44 Europe/Warsaw, a real autobrr rejection reached the
  service with HTTP 200 and the user confirmed the corresponding enriched Telegram
  notification. The release was for an existing, unmonitored movie and was also
  rejected by its quality profile. No new pending approval action, movie addition,
  or download resulted. This verifies one live notification path, not the
  unknown-movie approval/download sequence.
- An earlier unexpected Radarr addition at 11:33:54 was traced read-only to the
  existing `StevenLu Custom` import-list sync. That list has automatic addition
  enabled and search-on-add disabled. Movie-intel received no approval POSTs and
  its private action store was unchanged during that incident. No list policy
  was changed.

## Known gaps and review topics

These are findings for the user and ChatGPT to prioritize, not independently
assigned implementation tasks.

1. A real unknown-movie rejection, confirmation, exact-release push, and
   single-use-token result remain unverified. Deliberate live tests require
   approval for the specific notification/movie/release.
2. Provider-edge request-path logging is outside the user-readable proxy
   configuration. Application-route suppression is verified; upstream privacy
   still needs confirmation before using real approval tokens through that edge.
3. Radarr still uses debug logging and its release-push path can log private URLs
   even at Info level. Downloader redaction/access/retention also remains
   unverified. Lowering Debug to Info alone does not resolve the URL exposure.
4. Application redaction does not guarantee secrecy in provider or downstream
   logs. Historical private logs were preserved; raw logs must not be published.
5. Reconciliation of generated `main` outputs is required before any separately
   agreed future merge; it was not part of deployment or the workflow task.
6. Research found that a TSPDT-only universe can miss relevant films (including
   the prior Nocturnal Animals/Shame examples). A replacement universe,
   threshold changes, and any promotion of historical outputs remain product
   decisions, not implementation cleanup.

## Maintaining this file

Codex updates this state only with implemented behavior and verified facts,
including their date/commit and limits. Proposed behavior belongs in a discussion
or draft brief until agreed. Product review can accept/reject an implementation
without rewriting the historical evidence. Record new accepted rationale in
DECISIONS.md and assign the next scoped change in CODEX_TASK.md.
