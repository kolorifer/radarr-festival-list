# Engineering report: selected-action identity intake (issue60)

**Specification:** [Approved brief](2026-10-19-selected-intake-brief.md).
**Status:** Implementation complete; deployment/verification pending.

## Source semantics and measured coverage

Running autobrr binary SHA256 matches the official1.88.0 release. Its
[release service](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/release/service.go)
emits release.new before filters. `runAction` emits approved/rejected/error after
an action returns. This includes Unknown Movie rejection without a download.
Accepted means action acceptance, not completed download. Pre-action persistence/
filter failures, matches without enabled actions and same-client dedup skips do
not produce a separate action event. Retry actions use the same event path.

The two live enabled filters (Movies Remux and Movies WEB) each have one enabled
Radarr action to the same client. Two historical downloader actions are disabled;
no external checks or per-filter notification overrides exist. Notification
routing is global; future filter overrides replace global routes and must include
both actor and selected-intake notifications as needed. All539 retained releases
had completed statuses, zero releases without an action status, zero pending/error
statuses in that snapshot.534 movie-category actions include357 Unknown Movie
rejections and one movie-category episode conflict. All have stable source IDs.
No actual missing selected-action class was demonstrated in retained data.

Within the same observed live broad-intake cohort,188 movie release fingerprints
were recorded;77 had retained selected-action evidence.111/188 (59.0%) would avoid
recording under selected-only intake. This is a release-cohort estimate, not a
claim of an equal reduction in bytes or every incoming IRC announcement. The
retained database does not contain all pre-filter releases. The intake database
was1,073,152 bytes (+32,768 SHM; WAL0); switching will not delete historical rows.

## Implementation

Dedicated authenticated `/v1/selected`, explicit event/status/source/type guards,
capability-free projection and fixed selected outcome codes. Additive table stores
selected filter ID and hashed action identity separately from movie evidence.
UUID duplicates and equivalent new-UUID action observations are distinct counters;
multiple actions/filters never split a release into film identities. Strong source
correlation includes selected observations; weak IDs stay non-actionable. Apollo-
style movie-category episode contradictions quarantine without admitting real TV.

`source_mode=selected_only` rejects the old announcement route. Existing actor
outcome/export routes and worker format remain compatible. No actor handler,
Telegram, digest, retry, research, sandbox, catalog or acquisition logic changed.

## Validation / deployment

Focused synthetic checks cover all event types, Unknown Movie in both arrival
orders, historical overlap, dedup, metadata changes, multiple filters/actions,
missing/source IDs, true TV, Apollo, timestamps, secret stripping, BUSY/FULL,
HTTP failure/authentication and reversible migration/configuration. Full CI,
seedbox, confinement and natural selected samples are pending; no live cutover
has been made at this report revision.

## Limitations and retention

Webhook transport lacks a durable upstream outbox, so transient delivery loss
remains possible. Action IDs are absent from the webhook; equivalent repeated
attempts cannot be distinguished from new-UUID duplicates. Filter-only matches
without an executed action intentionally remain uncaptured. Current retained
coverage cannot prove absent historical pre-action failures. Unknown Movie live
end-to-end proof will be claimed only if a natural new event is observed.

Old announcements, four seeds, closed pilot and all action/research/digest ledgers
remain intact. Optional future cleanup requires owner approval and measurement on
a private copy; no deletion or automatic retention policy is included.

## Project context

The unrelated CODEX_TASK and supervisor queue are unchanged. Final tested/merged/
deployed revisions, notifier readback, actual natural traffic and private-state
preservation checks will be added after gates complete.
