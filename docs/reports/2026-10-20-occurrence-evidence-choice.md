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

Pending final checks/deployment. The one persistent Madame Bovary decision was
revoked on production with a private backup; its original record and revocation
are retained. No notification, Radarr mutation or download was involved.

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
research case to permanently resolved or suppress future reviews. The daily report
may lag the actor's latest source observation until its normal scan. No historical
Telegram message is edited or replayed; review buttons appear on new notifications.
A duplicate delivery also gets a fresh review; acquisition duplicate safeguards
are still separate and unchanged.
