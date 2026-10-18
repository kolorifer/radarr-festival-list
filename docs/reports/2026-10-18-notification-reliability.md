# Engineering report: notification and exact-release approval reliability

**Specification:** [User brief](2026-10-18-notification-reliability-brief.md),
D005/D006/D008/D009/D010. **Status:** implementation, deployment and end-to-end
technical verification complete. User review of the Telegram presentation remains
separate from technical acceptance. [Draft PR #41](https://github.com/kolorifer/radarr-festival-list/pull/41).

## Diagnosis

Inspected main 564a022 and clean deployed main 92afda3 independently. The latter
was active/running with NRestarts=0 and includes PR #34. Later main commits concern
supervisor infrastructure, not this service. Reviewed issue #33, PR #34 and the
2026-10-13 Marty Supreme live report; that historical test is not post-fix evidence.

Production journal since October 16 had 87 HTTP POST 200 entries, but no per-stage
reason codes. Autobrr retained 83 rejected and 4 approved actions in that window.
There were 45 distinct Unknown Movie title/year pairs: 30 had cached TMDb metadata
and 15 did not. All retained Unknown Movie releases had download references. Only
one of these distinct films matched the local intelligence catalog, so the other
cards cannot currently provide local IMDb/Letterboxd/recognition data. Missing
cache is not proof of TMDb ambiguity or outage. User explicitly approved additional read-only TMDb lookups; they are now complete.

Concrete examples include malformed Hamnet 2025 (2016), localized titles, and
uncached Insidious (2010), Nocturne (2020), Lake Mungo (2008). Do not guess their
identities or relabel all failures as duplicate ambiguity. Cached resolved films
were incorrectly described as “outside or unresolved”; this is a rendering bug.

Both enabled autobrr TELEGRAM and WEBHOOK notifications include movie events;
the built-in Telegram destination matches movie-intel's bot and chat. This creates
two notification streams. The user explicitly approved removing overlapping movie events while keeping
connection/update alerts (D021); applied and verified after deployment.

Read-only live selection_context timed out fetching the entire Radarr movie
collection, after root/profile reads had succeeded. That optional defaults lookup
can prevent the confirmation page from opening even with valid live choices.

Code reproduction also found posters discarded above 950 characters, release names
truncated at 220 characters, malformed result shapes failing the notification,
and uncertain pushes left retryable. These are independently tested defects;
not all were observed in the recent production events.


Approved fresh TMDb replay classified the uncached baseline: Snowman now resolves
to 372343; Hamnet with correct input resolves to 858024 and malformed input remains
unresolved. Four title/year inputs disagree with TMDb release years (Insidious,
Lake Mungo, The Lie, Haunted Heist); three localized titles fail exact English/
original-title equality; Withnail and I differs from Withnail & I; four music
documentary searches plus malformed Hamnet have no returned candidates. Nocturne
has duplicate exact matches without the required 10x AND 10-point lead. A newer
Fragmentos event also has ambiguous exact duplicates. These exclusions obey D005;
no year guessing, translated-title inference or weakened popularity rule was added.

## Implemented changes

- Distinguish safely resolved/outside-catalog from unresolved identity; optional
  malformed rating data does not suppress the card. No new ratings provider or
  invented award data. Existing local ratings/recognition remain authoritative.
- Routine profile/cutoff rejections skip remote enrichment and posters. Unknown
  payload shapes pass through as redacted plain text without an action.
- Keep full release names. Long cards use bounded messages plus a separate poster;
  buttons remain with card text. Photo failures preserve the text notification.
- Fixed diagnostic codes and a release-name digest explain identity, local
  coverage, action eligibility, Telegram delivery and approval outcomes. No URLs,
  payloads, titles, credentials or capability tokens are logged.
- Validate original reference scheme, protocol, timestamp and exact release name
  before offering approval and again before adding. Recheck Radarr TMDb identity.
- Persist an executing marker before mutations; uncertain results block further
  GET/POST approval with 409. Confirmed rejection can retry; success/expiry remains
  410. Duplicate webhooks reuse the same retained action. Private store writes are
  flushed/fsynced; corrupt stores fail closed rather than being overwritten.
- Live root/profile choices no longer depend on fetching the library. Single
  choices default automatically; multiple choices require explicit selection.

## Validation and deployment

Final local full suite: **335 tests passed** on Python 3.12 (125.196 seconds).
Focused unit regressions passed; pip check, production_scoring.py --check,
py_compile and git diff --check passed. Catalog remains 1,909 / 387 qualified.
Integration regression tests use local synthetic servers. The full seedbox suite
also passed **335 tests** (19.219 seconds), alongside preflight, pip check and the
frozen catalog check. PR CI passed on Python 3.12 and 3.13.

With explicit user approval, deployed runtime commit
`dcae919acbc87f1a33de84b7c6b628668b400b07` from PR #41 over
`92afda3004af075c165886b6705b9f79f219706d`. Backed up private environment,
cache/actions and notification settings on the host. Restarted only
movie-intel.service. Environment, movie-intel unit, sync service/timer and nginx
configuration hashes were unchanged. Live checkout remains clean at the tested
runtime commit; later documentation commits do not require another restart.

Final local/public health: HTTP 200, ok=true, Radarr configured, 1,909 movies.
Service active/running, NRestarts=0. Both local/public existing approval pages
returned 200 in approximately 0.05 seconds, with full release, no private reference,
no-store, one live root and eight live profiles; profile selection is explicit.

## Notification routing applied

Removed PUSH_REJECTED/PUSH_APPROVED/PUSH_ERROR only from autobrr Telegram notifier
1. IRC_DISCONNECTED, IRC_RECONNECTED and APP_UPDATE_AVAILABLE remain enabled.
Webhook notifier, built-in notifier, all other fields and filter routes were
verified unchanged. No autobrr restart was needed.

The user explicitly approved a temporary private API key because no key existed
and browser control was unavailable. Used loopback API Update to refresh live
routing, then API Delete to revoke both the database entry and authentication
cache. Verified absence and denied reuse; no temporary key or key file remains.
The configured browser prefix is not the loopback API prefix. Also, an omitted
empty event_sounds map is serialized as null by API Update; supplying the original
empty map explicitly preserved the original field exactly. Final readback passed.

## Explicitly approved live add/grab

The user approved sending a retained real Unknown Movie event and acquiring only:

**The Boxtrolls (2014), TMDb 170687**

`The Boxtrolls 2014 2160p HULU WEB-DL DDP 5 1 H 265-PiRaTeS`

- Retained autobrr release 375 was verified against its pending action, including
  exact private reference equality. Movie was absent from Radarr before the test.
- Replayed that retained event through the deployed public webhook. HTTP 200
  reported mode=enriched, poster=true and action=true. Journal
  confirmed resolved/local_catalog/action created/photo_sent. Rendering included
  IMDb link, IMDb and Letterboxd ratings, recognition and the full exact release.
  The existing unexpired token was reused. Telegram accepted the photo/card/button.
- Public confirmation page returned 200 with the full release and no private
  reference. Submitted the single live root and Ultra-HD profile (ID 5).
- Verified deployed add code uses searchForMovie=false; execution logged
  started_search_disabled. Approval returned 200 in 3.87 seconds and logged
  exact_release_approved. Radarr created movie 1020 with TMDb 170687/profile 5.
- Command snapshots showed RefreshMovie and ordinary background
  ImportListSync/ProcessMonitoredDownloads/RefreshMonitoredDownloads. No search
  command appeared. This is paired runtime/code evidence, not a captured wire
  trace of the add request. No search, import-list refresh or downloader command
  was independently launched by the verification scripts.
- Radarr's grabbed history contains the exact announced release name and the
  exact original downloadUrl, compared privately on the host. The download first
  appeared as downloading/ok, then completed and imported with the same download
  ID. hasFile=true; the actual file exists and its size matches Radarr:
  **9,064,876,594 bytes, WEBDL-2160p**. This is a completed download/import, not
  only an accepted release decision.
- The successful token was removed. Subsequent GET and empty POST both returned
  **410**, without submitting another acquisition form.
- A genuine retained Nocturne (2020) event was replayed read-only through deployed
  logic. Fresh resolution returned ambiguous_exact_matches, with no identity,
  action or button. Telegram/state writes were mocked for this negative case;
  it was not another live notification or acquisition.

Private test evidence remains on the seedbox in a mode-700 directory with
mode-600 files. Direct qBittorrent inspection was unavailable because Radarr's
configuration API masks its password. Completion is independently established
by matching grab/import history and the actual imported file, without changing
credentials or download settings.

## Privacy and operational limits

Nginx movie-intel route suppresses access and error logs. Radarr uses debug logging;
1,086 retained release-push log lines included 724 URL-bearing lines. No exact
current retained action download reference matched inspected Radarr logs. Its
.apps ancestor is mode 700, restricting other-user access. This is not a general
claim that downstream logging removes every private URL. Credentials and action
state stayed on the server; reports contain only aggregates and movie/release names.

An uncertain attempt needs a private operator check of Radarr/downloader history;
there is no automatic retry/unlock. Rollback to old code must not make executing
or needs_review actions retryable: keep those capabilities blocked/retired before
running a revision that does not understand their status. Preserve current state,
never restore an older action snapshot over completed acquisitions.

Remaining limits: optional local ratings/recognition are unavailable outside the
catalog; conservative title/year/duplicate rules intentionally leave some real
events unresolved. No broader identity heuristic or additional data provider was
introduced. User visual/product review is separate from the successful technical
test. PR #41 remains draft and unmerged; no merge was requested. The unrelated
cleanup assignment in CODEX_TASK.md is preserved and was not executed.
