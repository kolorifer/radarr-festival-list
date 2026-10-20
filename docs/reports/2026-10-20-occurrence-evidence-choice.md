# Evidence and choices for individual occurrences

## Approved brief

Replace persistent reviewed identity exceptions with reusable evidence gathering,
existing generic automatic identification, and owner choice when evidence conflicts.
Revoke the persistent Madame Bovary approval. Every later encounter of the same
unresolved torrent requires fresh review. Test/deploy without downloads or
notification replays. Preserve acquisition safeguards, intake and research.
The unrelated active cleanup brief is untouched.

## Implementation

- Actor no longer reads persistent decisions; approve is refused, lookup/apply
  return no correction. Legacy review-backed acquisition actions fail closed.
- Each supported conflicting notification creates a new expiring identity-review
  capability and a labelled Telegram button. It is not an acquisition approval.
- Evidence page shows filename/year, tracker assertion, description, NFO, image
  links, truncation/unavailable-image counts and matching research candidates,
  with dates/IDs/runtime/director/cast/language, contradictions and evidence gaps.
  Historical research is labelled; absence does not silently become confidence.
- Explicit choice verifies unchanged checked source/evidence and normal target
  IMDb/TMDb/title/year/local-catalog consistency. It updates only that occurrence.
- A separate step can prepare the existing download confirmation; no selection
  or GET downloads anything. Acquisition revalidates the selected occurrence and
  source/target, preserving existing deduplication and uncertainty blocks.
- Existing generic exact-ID/title/year/minor-typo automatic rules are unchanged.
  No new arbitrary score or automatic conflicting-ID override is introduced.
- Collector, worker, handoff, schedules, budgets and research ledgers unchanged.

## Validation and deployment

PR [#74](https://github.com/kolorifer/radarr-festival-list/pull/74) merged as
`a8d5d9ac609b219062b2f5bed4f652b55a679b74`; implementation `cf8b2fa`.
Production is pinned to isolated runtime
**`3a6c2cc9e2613a60719ba7030e5968895d14d7f2`**, based on previous live `6bf176b`.
Main-only catalog/operations changes were not deployed.

- Local complete suite:647 tests,2 Linux-only skips. Seedbox isolated runtime:630
  tests passed; seedbox main implementation:647 passed. Python3.12/3.13 CI passed.
- Tests cover fresh review on identical repeated release, explicit consent, escaped
  candidate rendering, private-reference omission, source/mapping changes,
  expiration, retired approvals, separate preparation and unchanged duplicate
  acquisition protection. Synthetic HTTP GET/POST confirms no Radarr/Telegram/
  download calls during movie selection.
- Dependency, configuration and production-catalog preflights passed. Local/public
  health200,1,909 catalog movies, actor active/NRestarts0. Only actor restarted;
  collector PID/config/modules, worker/handoff/schedules remained unchanged.
- The one persistent Madame Bovary decision was revoked with a private backup;
  its original record and revocation remain. All existing actions and downloader
  receipts were unchanged across deployment and live verification.
- Fresh deployed lookup: `needs_review/year_conflict`, review available,279
  description characters,1,409 NFO characters,3 image references and3 matching
  historical research candidates. Target1949 IMDb/TMDb crosswalk was checked
  read-only, then another generic lookup remained blocked. No choice/token was
  created. The private evidence page was rendered without replaying a webhook.
- No live downloads, Radarr writes, notification replays, budget resets or new
  research runs. No production collector outcome/history was rewritten by the
  read-only proof; a new natural notification supplies its fresh outcome.

Private configuration/state backups are retained. Rollback would preserve the
revocation and current acquisition state, marking new review/choice capabilities
blocked before returning to old code so they cannot be misinterpreted.

## Limitations

Review offers initially cover exact-checked TorrentLeech title/year conflicts with
bounded description/NFO evidence. Invalid/ambiguous source assertions, native-ID
conflicts and local catalog conflicts continue to fail closed. The selected target
must pass ordinary filename title/year rules; choosing an arbitrary different title
or year is not enabled. Those cases still need chat/operator investigation.

Images are allowlisted references for human viewing, not model analysis or fetched
video content. Tracker text can repeat a wrong association; runtime differences
are not proof of identity. Additional evidence sources/rules can be proposed after
review, but the system does not train itself from a user's selection.

Review choices expire with the existing capability TTL. They do not change a
research case to permanently resolved or suppress future reviews. The research report retains historical observations until a new natural outcome and
normal scan refresh it; the actor never uses that historical status as an approval. No historical
Telegram message is edited or replayed; review buttons appear on new notifications.
A duplicate delivery also gets a fresh review; acquisition duplicate safeguards
are still separate and unchanged.
