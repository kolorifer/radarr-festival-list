# Engineering report: notification and exact-release approval reliability

**Specification:** [User brief](2026-10-18-notification-reliability-brief.md),
D005/D006/D008/D009/D010. **Status:** implementation and validation in progress;
production acceptance is not complete.

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
connection/update alerts (D021); application is pending.

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
All integration tests use local synthetic servers. No acquisition has been triggered.
Deployment and post-fix live acceptance are pending; this report will be updated.

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

Remaining acceptance: apply the approved notifier adjustment, deployment health,
genuine post-fix notifications and specific approval for a full add/grab with
downstream/replay evidence. Preserve unrelated task docs.
