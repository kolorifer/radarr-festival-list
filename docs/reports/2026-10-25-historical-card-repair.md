# Engineering report: historical retry card repair

**Specification:** [brief](2026-10-25-historical-card-repair-brief.md).
**Result:** both owner-specified existing Telegram cards corrected and verified.
**Date:** 2026-10-25. **Runtime:** unchanged at
`72a04701d110c2b6f54cfd67c25861e6bf997a4c`.

## Findings

Both successful retry records lacked original payloads and Telegram receipts;
message state remained waiting with zero edits. After Yang recovered at 01:25
and Christmas in August at 01:30 Warsaw time (CEST, before the clock change).
After Yang originally asserted a different IMDb ID with no TMDb mapping;
Christmas in August originally encountered listing_temporary_http.

Fresh exact-listing and IMDb/TMDb checks passed for After Yang (tt8633464,
TMDb585378) and Christmas in August (tt0140825, TMDb26935). After Yang's 2021
festival date is documented alongside its canonical 2022 date. NFO95/TMDb96
minutes are compatible at whole-minute precision. Christmas in August has no
parseable NFO runtime in the retained projection; no runtime confirmation is
claimed. Its source ID/title/year crosswalk passed, with TMDb runtime97 minutes.

## Applied and verified

The existing message in each user-provided link was edited via editMessageMedia.
Telegram acknowledgements confirm the same message, chat and topic, a poster,
the correct IMDb/TMDb links, removal of stale failure text and no approval button.
Normal catalog text is used. The exact original rejection prose came from the
user's screenshots; release names came from retained observations.

The retained retry records do not include the original private download reference,
and no existing action exists for either release. No new capability was invented.
The captions explicitly explain why no download confirmation is available.
Recovered receipt/prepared presentation fields are saved; both message states
are now edited. Original payload fields remain absent rather than fabricated.

Private script, planned records and Telegram responses are audited under
~/.local/state/historical-card-repair-20261025; keep them private. No new messages,
approvals, acquisitions, service restart, configuration change or deployment.
Production remains clean at the same revision; health200,1909movies.

## Validation and limits

Fresh metadata checks, caption dry-run, actual Telegram response verification and
SQLite readback passed. This operations-only task did not rerun the runtime test
suite. Missing acquisition provenance remains the reason for absent buttons;
this repair does not promise recovery of the old downloads. The underlying
original receipt-loss cause remains historically unproven. Project state updated;
the unrelated CODEX_TASK cleanup assignment is unchanged.
