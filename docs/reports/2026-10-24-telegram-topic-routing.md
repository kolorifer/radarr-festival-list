# Telegram action-topic routing

## Approved scope

Owner requested Add to Radarr & Grab notifications in topic1466 and Grab Anyway
notifications in1468, with existing default458. Preserve confirmation and exact
release safeguards. No live test messages or downloads.

## Implementation

`telegram_routing.py` supplies request/thread-isolated routing contexts.
`TELEGRAM_ADD_GRAB_TOPIC_ID` and `TELEGRAM_GRAB_ANYWAY_TOPIC_ID` override the
existing default, falling back when unset. `deployment_config.py` validates all
configured topic IDs as positive integers. Deployment example/runbook document
routing and historical-message behavior.

`movie_intel_service.py` routes Unknown Movie notifications (including temporarily
unverified identities) to the add-and-grab topic, so later successful retry edits
remain there. Alternative-release notifications route to Grab Anyway. Existing
stored action kinds also select the route when sending an actionable notification.
All text chunks, photo captions, failed-photo text fallbacks and supplemental
posters stay together. General alerts, passthrough and identity digests retain
the default. No change to browser confirmation, identity checks or download APIs.

Retry recovery still edits the saved original chat/message ID. Existing messages
stay in their original topic; no copying, replay, message deletion or migration.
No special topic field is added to Telegram edit operations.

## Validation

Exact runtime25eae80:678 local tests passed(144.278s,two Linux-only skips),678
isolated seedbox tests passed(45.026s), bothPython3.12/3.13 CI jobs passed
(run40109819146). Six new tests cover routing, concurrency, multipart/photos,
unknowns before an action exists, old receipt edits, config validation/fallback.
The initial restricted local HTTP tests could not bind loopback; the full suite
was rerun with loopback permission rather than counting those failures as passes.

The runtime patch is based on actual deployedf34cd4d, preserving separate Grab
confirmation and original-message recovery work. Draft PR82 compares against
that exact runtime baseline, not unrelated main catalog changes. A main-based
cherry-pick was abandoned because main lacks the already-deployed retry-recovery
change; the temporary review checkout was returned to its clean baseline.

## Deployment and limitations

Deployed **25eae809e63f734689a0ce2243c8140e2657b8d0**. Private backup:
telegram-topics-backup-rmnl6gnw. Only movie-intel restarted. Both local/public
health200; actor, collector, research and shadow timers active. Protected action
state, shadow code/pilot and research timer hashes unchanged; collectorPID
unchanged. Configuration changed only the two topic overrides:1466 and1468;
default458 and all credentials preserved. Live installed code/config generated
payload fields458/1466/1468 correctly without transmitting them. No live test
messages or downloads. Monitor updated to recognize the authorized actor revision.
Rollback restores prior actor code and the backed-up configuration only; never
restore old approval/retry state. No deliberate Telegram delivery test is authorized by
this change; local mocked transports validate request bodies, and the first
natural notification will verify the bot's access to the specified topics.
Historical messages are intentionally not moved. No downloads are triggered.
