# Deploy movie-intel

The existing seedbox service uses Python 3.13, user systemd, a private
environment/state directory and loopback 127.0.0.1:40714. HTTPS proxying is already
configured. Radarr is provider-managed; do not reinstall it.
The real Telegram approval/add-and-grab path passed on 2026-10-13:
[live verification](../docs/reports/2026-10-13-live-add-grab-test.md).

## Updating an existing deployment

Use a validated main/implementation revision. Inspect the worktree first, record
its revision and save private configuration/state under a mode700 backup folder.
Run the full suite, pip check, production_scoring.py --check and --check-config
before activation. Stop only movie-intel for a consistent private state snapshot,
switch the clean checkout to the tested revision, then start that service.
Do not reinstall its unit/proxy/environment for a code/data-only update.

The production catalog is loaded at startup; invalid/missing qualification data
fails preflight. Check local/public health200, active/running and NRestarts after
startup, then perform read-only representative lookups. Preserve all existing
Radarr import-list settings. Do not trigger list refresh or searches. The separately authorized D017
[Radarr sync](RADARR_SYNC.md) adds missing monitored records with search disabled
after a verified dry-run; it is not part of movie-intel startup.

Rollback code/data by stopping movie-intel, checking out the recorded prior
revision and starting movie-intel. Preserve current private action/cache state;
the notification reliability update adds durable approval attempt status. Before
rolling back to older code, privately retire/block every `executing` or
`needs_review` capability so old code cannot retry an uncertain acquisition.
Never restore an earlier action snapshot over current completed acquisitions. Recheck local/public health.
Only restore private configuration if that configuration was actually changed.

## Install on the host

Use SSH from a machine with access to the seedbox. Keep the current `movie-intel`
checkout, or clone it if absent; inspect existing work before switching branches.
The commands below assume the checkout is `~/radarr-festival-list`. Python 3.12
(original CI) and 3.13 (seedbox) are supported by the service tests. Use the
validated production revision and verify that `deploy/README.md` exists before proceeding.
No Docker or Radarr installation is needed.

```sh
cd ~/radarr-festival-list
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -m unittest -v
install -d -m 700 ~/.config/movie-intel ~/.local/state/movie-intel
# Create only if absent; preserve any existing private configuration.
test -e ~/.config/movie-intel/environment || install -m 600 deploy/environment.example ~/.config/movie-intel/environment
```

Edit the private environment file on the host. Set every blank required value.
Generate any missing webhook secret directly into private configuration without
printing it; copy it only to the private autobrr webhook settings.
`TELEGRAM_TOPIC_ID` is optional. `TMDB_API_TOKEN` is a TMDb read access token.
`RADARR_URL` is the actual Radarr application base URL, including its provider
prefix if present. `RADARR_API_KEY` comes from Radarr settings.
`MOVIE_INTEL_PUBLIC_BASE_URL` must be the complete HTTPS route to movie-intel,
including the chosen path prefix. Do not put HTTP basic-auth credentials into it.

The launcher reads this file without evaluating shell commands. It supports
`NAME=value`, empty assignments, comments on separate lines, and quoted values.
It does not expand `$HOME` or other variables; use absolute paths for overrides.
The same format works with systemd's EnvironmentFile. Treat all files in the state
directory as private: actions contain tracker URLs. Run exactly one process using
a given action store; its transaction lock is within that process.

```sh
.venv/bin/python deploy/run.py --check-config
```

This checks syntax, required names, and writable state paths without contacting
Telegram, TMDb, or Radarr. A passing preflight does not verify credentials or
connectivity. Outbound access is needed to `api.telegram.org`,
`api.themoviedb.org`, and the actual Radarr host. Telegram fetches posters from
`image.tmdb.org`; the browser also uses poster/public movie links.

## Optional TorrentLeech metadata

Native autobrr `meta_imdb`/`meta_tmdb` movie fields are validated automatically.
The TorrentLeech IRC definition does not populate them. For that source only,
`MOVIE_INTEL_TL_METADATA_ENABLED=1` enables a read-only exact-listing fallback
when both fields are absent. It defaults to `0`; no ingestion or autobrr changes
are needed. This setting does not disable native-ID validation.

Before enabling, supply `MOVIE_INTEL_TL_COOKIE_FILE` as an absolute path to a
dedicated private JSON object mapping cookie names to values. Keep it outside the
checkout and web roots, in the private configuration directory, owned by the
service user and mode 600. Symlinks and group/world access are rejected. Obtain
appropriate session credentials through the normal account login; do not couple
the service to Prowlarr's database or copy credentials into examples/reports.
Preflight validates the file offline, not whether the session is still valid.

The adapter accepts only the canonical HTTPS `www.torrentleech.org` listing
path with a numeric torrent ID, no query/fragment/credentials/port. It requires
TorrentLeech as indexer, verifies the exact retained release heading, and consumes
one IMDb input field. It never requests a download URL. Redirects, login forms,
multiple/conflicting IDs, changed markup and unavailable authentication fail
closed; the notification remains readable, without approval.

Operational bounds: one active listing fetch, at most one new request per second,
1 MB decoded body, 3s connect/5s read timeout and a 10s streaming budget (a pending
read can add up to 5s). A 429 pauses requests for at least 60s or the longer
Retry-After duration. These are implementation ceilings, not a tracker account
rate guarantee; check the account's applicable limits before enabling. There are
no automatic retries or login attempts. Concurrent callers receive a safe busy
outcome instead of waiting in an unbounded queue.

Listing results and independently validated TMDb identities use separate bounded
in-memory caches (256 entries each; success 15 minutes, failures 60 seconds).
Listing keys include a digest of source URL, full release name and credentials;
cookie rotation invalidates cached session failures. Identity keys include both
IDs and exact title/year context; neither cache reads or writes the legacy title
cache. Restarting clears these caches and rate backoff, so avoid repeated restarts
during a provider rate limit. No private persistent cache migration is needed.

The accepted source IMDb ID must map to exactly one TMDb movie and round-trip
correctly. Supplied TMDb IDs and local identity must agree. Canonical, alternative
or translated titles must match, and the announced year must appear in the primary
date or TMDb release-date records. Title comparison folds Unicode case/punctuation
and `&`/`and` only in this ID context; existing title-search rules are unchanged.
No synopsis matching, performer-prefix stripping, year tolerance or hand-entered
crosswalk is used. An unmapped tracker IMDb assertion is labeled an association,
not independently verified IMDb metadata; it cannot enable Grab.

Inspect fixed `tracker_metadata` and `identity` decision reasons for diagnostics;
do not log response bodies, cookies, listing URLs or approval tokens. Turning the
adapter off restores the existing no-ID fallback, while native IDs still undergo
validation. A full rollback uses the previously verified runtime revision and
preserves current action state, following the rollback instructions above. No
historical notification replay or action backfill occurs on startup.

## Generic identity rules only

Per-film reviewed context corrections are retired. There is no runtime registry
or fixed title/year repair. Remove `MOVIE_INTEL_REVIEWED_CONTEXT_FILE` from the
actor environment; preflight rejects it if still set. Old private evidence may
be retained for audit, but is never loaded by the matcher. Existing action history
is preserved; no old notification/action is replayed or backfilled.

Use the standard exact-ID/title/year checks and the optional generic tracker typo
policy below. Unsupported prefixes, title differences and conflicting years stay
unresolved unless ordinary catalog metadata satisfies the same generic rules.

## Keep the service running

If `systemctl --user` works, install the user service. It expects the paths above;
adjust them if the existing checkout lives elsewhere. Inspect an existing service
before replacing it.

```sh
install -d -m 700 ~/.config/systemd/user
install -m 644 deploy/movie-intel.service ~/.config/systemd/user/movie-intel.service
systemctl --user daemon-reload
systemctl --user enable --now movie-intel.service
systemctl --user status movie-intel.service
```

The provider must support keeping user services alive after logout/reboots; ask
the provider if lingering is unavailable. If user systemd is unsupported, use the
provider's process supervisor with the following foreground command:

```sh
cd ~/radarr-festival-list
.venv/bin/python -u deploy/run.py
```

For a temporary manual run, use a persistent SSH terminal session. This is not a
verified reboot-survival strategy. Logs contain method/status, startup errors and fixed decision codes with
a release-name digest; do not enable payload or request-path logging in a supervisor/proxy.

## HTTPS route and autobrr

Keep the application bound to loopback. Use the provider's existing HTTPS reverse
proxy to route the chosen prefix to `127.0.0.1:40714`, stripping that prefix.
`nginx-location.conf` is a fragment for an existing HTTPS server if you control
nginx; do not replace the provider's full configuration. The proxy must disable
access/error logs for this route because webhook paths and action tokens contain
credentials. Avoid extra browser authentication on the webhook route unless
autobrr can supply it; action tokens are bearer capabilities and expire after
24 hours by default. Browsers and Telegram must be able to reach the HTTPS route.

Configure an autobrr generic webhook notification for `action.rejected`, with URL
`<MOVIE_INTEL_PUBLIC_BASE_URL>/webhook/<MOVIE_INTEL_WEBHOOK_SECRET>`. Keep it private.
The parser currently expects JSON shaped as:

```json
{
  "event": "action.rejected",
  "timestamp": "2026-10-12T10:00:00Z",
  "data": {
    "release": {
      "type": "movie", "title": "Arrival", "year": 2016,
      "name": "Arrival.2016.2160p.UHD.BluRay.REMUX",
      "protocol": "torrent", "timestamp": "2026-10-12T09:59:00Z",
      "download_url": "https://tracker.invalid/synthetic-example", "size": 123
    },
    "indexer": {"name": "Example", "protocol": "torrent"},
    "result": {"rejections": ["Unknown Movie"]}
  }
}
```

This synthetic fixture matches autobrr's upstream [WebhookEvent/WebhookRelease
definitions](https://github.com/autobrr/autobrr/blob/178fdd440fcad80cd6f5498e181d691ee55becc2/internal/domain/notification.go).
It is not proof of the provider's actual payload. Verify the real installed
autobrr version emits these fields. An approval requires a
resolved TMDb ID, an unknown-movie rejection, and a reusable download/magnet URL.
The exact link is retained only in the private action store and sent to Radarr
after confirmation. Notification text from external payloads redacts URLs and
configured keys; generated public IMDb/TMDb and approval links remain available.

The [Radarr release-push handler](https://github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Indexers/ReleasePushController.cs)
logs the pushed download URL at Info level. Radarr's own log cleansing masks
known credential patterns but does not remove every private URL. Before a real
push, verify the provider's Radarr/downloader log access, redaction and retention
controls for the actual tracker URL format. Movie-intel cannot guarantee what
another application's logs retain. Do not share those logs publicly or assume
movie-intel's redaction covers the provider's applications.

## Validate

```sh
# Local request; require HTTP 200, ok=true, and a nonzero movie count.
.venv/bin/python -c 'import json; from urllib.request import urlopen; print(json.load(urlopen("http://127.0.0.1:40714/health", timeout=5)))'
```

The `radarr` health field reports only whether configuration is present. It is not
a connectivity check. The test suite exercises real local HTTP calls against
synthetic Telegram, TMDb, and Radarr servers, including single-use tokens,
simultaneous confirmation, invalid selections, rejection handling, and redaction.
It sends no real notifications, adds no real films, and downloads nothing.

With the owner's authorization, complete the real test on one chosen unknown
movie: receive the autobrr event, confirm enriched Telegram text and approval link,
open the page and verify the actual root/profile choices, then confirm. Verify
Radarr added the movie without a general search and processed the exact release.
Reopening/resubmitting the used link must return 410. Inspect notification,
browser, and proxy/service logs for private URL/key leakage without sharing their
contents. A normal Radarr rejection leaves the action available to retry; verify
the reason first. A persisted attempt with an uncertain remote outcome returns HTTP 409 and
blocks further submissions, including after a restart. Inspect Radarr/download
client history privately before any new attempt: a remote request can succeed
even when its response is lost. Do not clear that marker merely to retry.
Successful/expired capabilities return HTTP 410. Multiple root/profile choices
require explicit selection; the confirmation page does not fetch the library
to guess defaults.

Keep the existing public feeds independent from the qualification catalog. Stop the service with `systemctl --user stop movie-intel` if
using the user unit. Back up the private state only to a private location.

## Stage 1 identity observation (default off; separately confined)

See [the separate collector runbook](IDENTITY_TRIAGE.md). Issue #47 permits only
observational storage, conditional on effective isolation from credentials/action
state. Issue #49 supplies a Landlock ABI6 boundary and socket activation after the
provider's namespace approach failed. Activation requires actual child denial
proofs and the runbook gates. Never weaken them to start the collector. The outcome
observer can stay off; existing movie-intel may remain pinned at its verified code.

### Automatic identity investigation (issue57)

`MOVIE_INTEL_IDENTITY_RETRY_MODE=off|shadow|active` defaults to off. Shadow
persists candidate retry jobs without extra provider calls; active permits only
metadata context rebuilding. Both require the existing authenticated observer.
The private retry spool is `~/.local/state/movie-identity-retries/outcomes.sqlite3`.
It reserves at most 60 additional GETs per rolling 24 hours globally: 20 tracker listing GETs and 40 TMDb GETs,
with at most 3 attempts per unchanged source version in 24 hours, then human review.
The delays are 15 minutes, 1 hour and 6 hours. It never invokes a rejection handler,
Telegram sender, Radarr action or approval-token creation.

The separate recurring worker configuration is the existing owner-only
`~/.config/movie-identity-research/config.json`, with `mode: "recurring"`, an
explicit `enabled` switch and only the existing TMDb read token. Its new ledger
is `recurring-v1.sqlite3`; never delete/reset it or reopen `research.sqlite3`.
Limits are 5 case versions and 25 GET reservations per rolling 7 days, max 5 GETs per
version. Unknown/failed calls count; unchanged attempted versions do not rerun.

A separate helper installation under `~/.local/lib/movie-identity-handoff`
receives only the existing loopback export key in its owner-only config, not
provider/action credentials. It preconnects to fixed loopback, then applies
Landlock and seccomp before GET `/v1/investigations`. It can write only the
worker's `incoming/` subdirectory. Copy the required standard-library modules
and their local dependencies from the same verified runtime; preserve 700
folders and 600 private files. Actual kernel proofs are mandatory. Do not
substitute direct Stage1 database access or broaden either sandbox.

`identity-investigation-scan.service` runs the confined handoff, then the worker
in a separate clean process. Its timer scans daily at 12:00 host local time plus
up to 15 minutes jitter, with persistent catch-up. Install it disabled; prove the
natural observer chain, fresh complete handoff, disabled-worker behavior and
security boundaries before activating research/timer. A stale (>1 hour),
partial or oversized export fails closed. Export limits are 100 eligible and 1000
assessed cases / 1 MiB; failure is visible in the service journal.

The private `review-report.json` includes every current assessed case, evidence
freshness, source ID assertions, candidate proposals and their current/stale
status, changed-case list, coverage gaps and budgets. `review-changes.json`
retains the last changed scan across quiet scans. Research proposals are never
approved identities. No Telegram digest or authenticated review controls are
enabled; product sign-off on a sanitized example is still required.

Disable/rollback: stop and disable the scan timer, stop its service, set the
worker `enabled` false and remove its copied token, set retry mode off and
restart only movie-intel. Preserve all ledgers and outcome spools. Restore the
previous verified code/configuration from private backups if necessary, then
check actor/collector health and confinement. Never restore an old action
store, erase request reservations, reset a budget or create fresh ledger names
to bypass limits. Existing collector data remains backward compatible.

Each daily scan retries only the confined local handoff, at most three fresh
processes with a 15-second process deadline and five-second gaps. Exhaustion
fails that scan; it never repeats the research worker as part of that retry.
The failure log contains only a fixed stage/reason. Daily timer invocation and
all manual invocations still share the same durable research ledger.

### Approved changed-case Telegram digest

`MOVIE_INTEL_IDENTITY_DIGEST_ENABLED=1` enables an actor-owned sender (default 0).
It polls the private `movie-identity-research/review-report.json` every five minutes,
using the existing Telegram bot/chat/topic. The research worker retains no Telegram
credential or outbound permission. Its `telegram_digest_enabled: false` field
means that the worker itself does not send; actor configuration is authoritative.
No collector/worker unit, research schedule or request budget changes are needed.

The first poll sends current review cases once; subsequent polls send only new or
materially changed evidence/proposals/status. Up to four cases fit one plain-text
message. Verified/routine cases are mentioned only if previously sent for review.
Unassessed announcements and unchanged historical seeds are excluded. Stale
proposals are labelled, and candidate IDs are explicitly unverified. No buttons,
URLs, approval tokens, corrections or acquisition calls are created.

The owner-only `~/.local/state/movie-identity-digest/deliveries.sqlite3` reserves a
version before sending. Confirmed Telegram acknowledgements become `sent`;
unchanged versions are suppressed across restarts. Explicit 429 rejection retries
no sooner than an hour or a longer Retry-After. Network/response ambiguity or a
crash after reservation stays `uncertain`, with fixed journal status/counts. Inspect
Telegram and that ledger before any operator-authorized resend: Telegram offers
no sendMessage idempotency key. Do not erase the ledger to force redelivery.
Reports older than 48 hours, unsafe permissions or invalid data fail closed with
`identity_digest check_failed`; this is a journal signal, not an independent alert.
Polling reflects the latest complete report, not every intermediate transition
between polls. Daily research timing still governs when findings reach the report.

Disable by setting the flag to 0 and restarting only movie-intel. Preserve the
ledger on disable/rollback. Health/preflight and the private-state backup procedure
above apply; no test download or Radarr access is needed for this feature.

The daily-budget upgrade migrates only pending, unexpired request-budget waits once, staggered by one minute. Existing reservations, attempts, source expiry and provider holds are retained. Digest wording changes preserve material-version delivery keys; they do not replay old messages. See [daily retry report](../docs/reports/2026-10-20-daily-identity-retries.md).

### Minor tracker-backed filename typos

`MOVIE_INTEL_TRACKER_TYPO_ENABLED=1` enables conservative typo context acceptance
(default off). Requires successful exact TorrentLeech listing validation, its
IMDb association, a unique TMDb movie mapping with matching reverse IMDb, and a
matching documented release year. One letter insertion/deletion/substitution or
adjacent transposition is allowed in one word only; both spellings must have six
letters, candidate title eight alphanumeric characters. Word additions, short
words, numeric/Roman numeral changes and larger edits remain blocked. Native IDs
without checked listing provenance and title searches stay strict. Local identity
conflicts and all approval/acquisition controls remain enforced. No per-film exception registry is supported. Disable this flag and restart movie-intel to revoke the
new policy. No history replay/backfill or extra metadata queries are required.


### Missing IMDb-to-TMDb mappings

The metadata retry worker also admits `tmdb_mapping_missing`. It uses the same
three-attempt limit, 15-minute/1-hour/6-hour delays, daily provider/request caps,
source expiry, deduplication and provider holds as transient metadata failures.
Persistent absence goes to review. Identity/year/title conflicts, ambiguous or
nonmovie mappings remain excluded and terminate an existing retry if discovered.
No notification replay or action creation occurs on recovery. Retained cases must
not be bulk reopened or budget history reset; the approved Insomnia admission is
recorded in the [report](../docs/reports/2026-10-20-missing-mapping-retries.md).


### Torrent-page investigation evidence

Unresolved exact-checked TorrentLeech lookups project bounded source description,
NFO text and public screenshot references into the existing private observer.
No separate fetcher or image-analysis service is enabled. The initial image-host
allowlist is i.ibb.co; links are never followed by the collector/worker. All
conflicting identities and visual evidence require review.

Deployment requires `torrent_research_evidence.py` in actor, collector, handoff
and worker code directories, plus compatible intake/selection/provider/worker
modules. Preserve the collector's selected-only revision when the actor runtime
is pinned separately. Install dependencies before restarting consumers, validate
actual isolation, and retain old records/ledgers. The schema extension is optional
for old records but all active consumers must understand new evidence before the
actor starts producing it. Source text does not grant authority or identity.
Reference-only images are private review material, not verified film contents.
