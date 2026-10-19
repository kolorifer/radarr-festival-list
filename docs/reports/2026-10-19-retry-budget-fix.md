# Metadata retry budget deferral

## Scope and authorization
The owner requested a fix after inspecting the real Contagion (2011) notification. Fix budget waits consuming retry attempts and explain temporary lookup failures. No identity correction, extra request budget, deliberate notification or acquisition is authorized.

## Finding
Selected intake captured the Contagion release with strong source correlation. Its initial tracker listing lookup returned HTTP 5xx. The first retry made zero requests because the rolling weekly budget was already exhausted (5 listing + 5 TMDb requests). Previously that blocked retry counted as a failed attempt and published a generic provider-unavailable outcome.

## Implementation
Budget/cooldown deferrals now retain their audit row but zero-request waits do not count toward the three-attempt limit, including historical rows. Attempts with reserved requests and uncertain/crashed attempts still count. Deferral schedules the next available global/provider rolling-budget slot and honors provider cooldown, bounded by the original one-week job expiry. A blocked retry no longer publishes a misleading lookup failure or recovery. Authentication failures retain review behavior. Existing pending jobs are handled by the corrected code at their next scheduled wakeup; no state reset is required.

Telegram now describes temporary lookup/rate-limit failures explicitly, without promising recovery or suggesting conflicting identity. Approval remains unavailable. No lookup, approval, download, budget or investigation-isolation privileges are expanded.

## Verification and deployment
Regression tests cover persistent zero-request deferral, rolling budget reopening, partial requests, cooldowns, false outcome suppression and notification wording. Existing crash, lease, expiry and acquisition safety tests remain required. Final validation and deployment results are recorded below when complete.

Deploy the isolated runtime revision based on actor 8846f51 so unrelated catalog/collector changes are not activated. Keep collector 23cacc8 and research worker/helper unchanged. Private state/configuration backups precede actor-only restart; rollback restores only code, never earlier approval state.

## Limitations
The existing weekly caps and one-week source lifetime remain unchanged. If no slot becomes available before expiry, the case goes to review. This fix does not retry Contagion immediately, identify it by guesswork, edit its already-sent Telegram message or replay a notification.

## Verified results
- PR: https://github.com/kolorifer/radarr-festival-list/pull/63
- Prepared actor runtime: `cd4e25f` (parent `8846f51`, only retry/message/test changes).
- Local current-main suite: 581 tests run, 579 passed and two Linux-only skips.
- Exact actor runtime on seedbox: all 564 tests passed; dependency check clean; catalog check 1,909 candidates / 387 qualified; deployment configuration valid.
- A private SQLite backup of live retry state proves Contagion's historical zero-request block is excluded: next real attempt number is 1. Its budget deferral stays pending until the available slot, before its unchanged source expiry. No live resolver or notification was invoked.
- GitHub CI remained queued awaiting runners at this checkpoint. Merge and production activation are pending those gates. Current production actor remains `8846f5195d4094a337726d1f7829659ecdeb8f85`; installed collector remains `23cacc8`.
- Guarded rollout is staged privately on the seedbox with code-only rollback, state/config backups, protected-component hashes, action-state preservation and local/public health checks. It has not been activated.

## Completed production rollout — 2026-10-19 16:34 UTC

Both current-head CI jobs passed (Python 3.12 and 3.13). PR63 merged as
`4239e6396800e86d3e5d830c8397a911b83366f2`. Production actor is independently
verified at `cd4e25f96d1d5d0d6de5f953959bdb2ed10aa72a`; its three changed files
exactly match the merged fix. Catalog/collector changes from main were not deployed.

Private configuration/state backups preceded restarting only movie-intel.
Local and public health returned HTTP200, ok=true and 1,909 movies. Actor and
collector are active with NRestarts=0; the research timer remains active. Collector
PID and protected configurations/modules are unchanged; approval state is byte-identical.
The digest delivery ledger and metadata retry request ledger are unchanged.
No notification replay, deliberately sent notification, lookup test or download
was triggered. Existing production operation remains enabled.

Read-only Contagion verification at 16:34:49 UTC: pending / retry_request_budget,
one historical blocked attempt with zero requests, **zero counted attempts** under
the corrected accounting. The existing wakeup is still 19 October 16:45:40 UTC;
at that wakeup the corrected worker can defer until a budget slot opens. An isolated
copy proves the projected available-slot due time is 26 October 11:04:16 UTC, before
the unchanged expiry of 26 October 15:30:38 UTC. The live schedule was not forced or
rewritten. Budget availability may change; identity recovery remains unverified.

The CI/deployment monitor was disabled after completion. Private rollback evidence
is retained under ~/.local/state/retry-budget-fix; rollback restores code only and
must never restore earlier approval or delivery ledgers.
