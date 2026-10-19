# Engineering report: selected-action identity intake (issue60)

**Specification:** [Approved brief](2026-10-19-selected-intake-brief.md).
**Status:** Implemented and selected-only cutover enabled; natural selected-event
verification pending because the bounded comparison had no new source activity.
**PR:** [61](https://github.com/kolorifer/radarr-festival-list/pull/61).
**Collector runtime:** `23cacc8b9d1cab1cc463a3a554a1faaa1d2fcd01`.
**Actor runtime:** `8846f5195d4094a337726d1f7829659ecdeb8f85` (unchanged PID/checkout).

## Source semantics and measured coverage

Running autobrr binary SHA256 matches the official1.88.0 release. Its
[release service](https://github.com/autobrr/autobrr/blob/v1.88.0/internal/release/service.go)
emits release.new before filters. `runAction` emits approved/rejected/error after
an action returns. This includes Unknown Movie rejection without a download.
Accepted means action acceptance, not completed download. Pre-action persistence/
filter failures, matches without enabled actions and same-client dedup skips do
not produce a separate action event. An action interrupted by process failure or
never returning can also lack its result event. Retry actions use the same path.

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

577 tests pass on seedbox and CI Python3.12/3.13; local575 pass/two Linux-only
skips.17 new focused cases cover all event types, Unknown Movie in both arrival
orders, historical overlap, dedup, metadata changes, multiple filters/actions,
missing/source IDs, true TV, Apollo, timestamps, secret stripping, BUSY/FULL,
HTTP failure/authentication and reversible migration/configuration. Dependency,
offline actor preflight and frozen scoring checks pass (1909/224/163/387).

Actual installed collector child denial checks pass at Landlock ABI6: actor/action/
credential/backup reads and writes, symlink and inherited-FD escape, metadata
changes and new network operations are denied. The unchanged worker's fresh proof
passes the equivalent restrictions, with TLS only and zero research HTTP requests.
An additional isolated collector under the real service confinement accepted all
three synthetic selected events, strongly correlated Unknown Movie to an eligible
case, suppressed repeat observations after restart and rejected broad intake410.
No synthetic event was sent to production intake, the actor or any acquisition API.

Offline projection of all539 retained action records, without replay or persistence:
527 accepted, four pre-existing metadata/type quarantines, seven non-movie rejects,
and one newly retained diagnostic movie-category episode. The only change from
legacy projection is that diagnostic improvement; no previously accepted class is
lost.357 Unknown Movie records yield355 accepted, one pre-existing malformed
metadata quarantine and one episode-conflict diagnostic. These reconstructed
payloads are evidence from retained fields, not claimed raw live webhook captures.

The bounded720-second parallel notifier window had zero natural selected actions
and zero new accepted movie announcements. The temporary notifier was removed and
its private API key revoked. The initial natural-sample gate therefore did not
supply live proof. After the complete retained-cohort and actual confined functional
checks passed, the cutover proceeded under issue60's conditional authorization,
with natural verification explicitly pending rather than generating an event.

Only dedicated notifier4 changed to PUSH_APPROVED/PUSH_REJECTED/PUSH_ERROR and
`/v1/selected`; collector `source_mode=selected_only` was atomically enabled. Actual
API/database readback confirms the event list/route. All other notifiers, filters,
actions and routing rows are unchanged. The limited release authentication key is
preserved. There are four notifiers and zero API keys after cleanup. The existing
actor PUSH_REJECTED webhook remains globally routed alongside the metadata notifier.

Postflight: actor/public/local health200,1909 movies, actor/collector active with
NRestarts0; daily research timer active and unchanged. Actor PID and all protected
worker/helper/configuration/binding hashes unchanged, old action records changed0/
removed0. Digest stays sent2. All41 actor outcomes are delivered, zero pending;
21 cumulative failed attempts remain in its historical counter. Collector has zero
storage failures since its intentional restart; the older volatile failure counter
was not evidence of a permanent fix. Worker export validation passes unchanged.

Every pre-existing immutable row survives:473 cases,639 releases,643 evidence
versions,692 deliveries,45 outcomes, four seeds and45 selection events/history
entries at backup time. Previous collector code successfully read a private copy
of the additive schema. Closed19-request pilot table hashes are unchanged. No
historical database or action state was replaced. Backups and verification records
remain owner-only on the seedbox.

Final DB size1,093,632 bytes (+32,768 SHM; WAL0), compared with1,073,152 bytes at
inventory: +20,480 bytes including schema and normal intervening activity. This
feature reduces future recording; it does not reclaim disk. Broad accepted rows
added after cutover:0. Actual natural selected rows:0 at postflight, so there is
no measured post-cutover live reduction percentage yet;59% is the measured
pre-cutover cohort estimate above.

## Limitations and retention

Webhook transport lacks a durable upstream outbox, so transient delivery loss
remains possible. Action IDs are absent from the webhook; equivalent repeated
attempts cannot be distinguished from new-UUID duplicates. Filter-only matches
without an executed action intentionally remain uncaptured. Current retained
coverage cannot prove absent historical pre-action failures. Unknown Movie live
end-to-end proof remains pending until a natural new event is observed. The
existing malformed Unknown Movie record still cannot form a usable identity case;
this is not a newly introduced drop. No promise of complete capture is made.

Old announcements, four seeds, closed pilot and all action/research/digest ledgers
remain intact. Optional future cleanup requires owner approval and measurement on
a private copy; no deletion or automatic retention policy is included.

## Project context

The unrelated CODEX_TASK and supervisor queue are unchanged. PR61 contains the tested implementation and this report. Production collector
modules are pinned to the tested runtime above; the actor stays at its verified
digest revision. Documentation-only follow-ups are not deployed. The PR records
final merge status. No further identity correction or retention work is authorized.
