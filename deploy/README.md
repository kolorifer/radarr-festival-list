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
Radarr import-list settings. Do not trigger list refresh, searches or bulk adds.

Rollback code/data by stopping movie-intel, checking out the recorded prior
revision and starting movie-intel. Preserve current private action/cache state;
this iteration changes no state schema. Recheck local/public health.
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
verified reboot-survival strategy. Logs are limited to method/status and startup
errors; do not enable payload or request-path logging in a supervisor/proxy.

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
the reason first. For a connection timeout after a push, inspect Radarr/download
client history before retrying: a remote request can succeed even if its response
is lost.

Keep the existing public feeds independent from the qualification catalog. Stop the service with `systemctl --user stop movie-intel` if
using the user unit. Back up the private state only to a private location.
