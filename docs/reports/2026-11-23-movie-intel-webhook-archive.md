# Private autobrr webhook archive

The authenticated movie-intel webhook saves each complete valid JSON body in its
original bytes before any event or movie filter. Each delivery receives a separate
file, including repeated identical bodies. The normal action event and text
handling still run as before. Newly subscribed autobrr release, IRC, list, feed
and update events are archived and acknowledged without passing to the movie
notification or action flow.

The archive is beside the configured movie-intel action store, under
`webhook-archive/`. The directory is mode 0700 and each body is mode 0600.
The writer checks path components and opens directories by descriptor without
following symlinks. It recognizes the root-owned passwd-home alias used by the
seedbox, then checks its physical target and all descendants without symlinks.
Files are written privately, synced and published without overwriting an
existing file. Names contain only UTC receipt time and a random suffix. Nothing
expires automatically. The archive retains sensitive tracker URLs as delivered.
Keep it out of backups or transfers that cannot preserve the same privacy.

An archive failure emits only `webhook_archive write_failed` in the actor
journal. Existing business processing continues. Archive-only event types receive
503 when persistence fails. A normal response on an existing business event is
not an archive receipt. The archive cannot recover events the producer or proxy
never delivered, deliveries during downtime, or invalid, incomplete or oversized
bodies. Monitor archive failures and available disk space. A crash can leave a
hidden partial file, which is not a completed archive item. Never replay it.
Valid bodies that exceed Python's integer or nesting limit still archive after
an iterative syntax check. Their prior business error response is preserved.

## Retrieve exact bytes

On the seedbox, list completed filenames without printing contents:

```sh
find "$HOME/.local/state/movie-intel/webhook-archive" -maxdepth 1 -type f -name '*.json' -printf '%f\n' | sort
```

The deployed service's physical path is
`/home16/kolorifer/.local/state/movie-intel/webhook-archive/`. The passwd-home
alias points to the same directory. Transfer a specific filename with the
existing authenticated seedbox SFTP connection. On the local machine, set
`umask 077` and create an owner-only directory before opening SFTP. Then use
`lcd` to select that local directory, `cd .local/state/movie-intel/webhook-archive`
on the remote side, and `get <exact-filename>.json`. Verify mode 0600 on the
local copy. SFTP returns the stored bytes without interpreting or requesting any
URL. There is no HTTP download endpoint. Do not send these bodies to chat, logs
or Git. Compare SHA-256 on the two private copies if verifying transport.

## Subscription and rollout

Use the existing autobrr webhook destination once the code is deployed. In
autobrr v1.89.0, save all 13 selectable live event types in that one destination.
Keep the three existing push events. The additional types are `RELEASE_NEW`,
`IRC_DISCONNECTED`, `IRC_RECONNECTED`, `IRC_UNHEALTHY`, `IRC_HEALTHY`,
`LIST_REFRESH_SUCCESS`, `LIST_REFRESH_ERROR`, `FEED_REFRESH_SUCCESS`,
`FEED_REFRESH_ERROR` and `APP_UPDATE_AVAILABLE`. Avoid a second overlapping
destination. Save without clicking Test, which can dispatch synthetic events for
the selected types. Configured per-filter routes replace global routes for an
event that has that filter ID. The owner verified zero overrides in the current
setup. A future filter override can affect coverage. Sources:
[v1.89.0 event mapping](https://github.com/autobrr/autobrr/blob/v1.89.0/internal/domain/notification.go)
and [v1.89.0 routing and test implementation](https://github.com/autobrr/autobrr/blob/v1.89.0/internal/notification/service.go).

Prepare an actor-only patch against `1331107d0e31361a6f2dd7268faa2b78edd7bc0a`
for `movie_intel_service.py` and `webhook_archive.py`. Follow the
[actor update runbook](../../deploy/README.md). Verify the archive path guards
with invented local input, then observe natural deliveries after activation.
Check filenames, ownership, modes and failure counts without inspecting private
bodies in shared logs. Rollback should first restore the three prior subscription
types, then return to the previous actor revision. Preserve every archive file.
