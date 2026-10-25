# Persistent verified identity memory — implementation brief

User requested storing previous successful identifications and reusing them for
later torrents of the same movie, using repeated The End of Oak Street events as
the example.

Current verified state: external-ID validation and exact tracker-listing caches
are process-local, last 15 minutes, and do not reuse a movie match across different
torrent references. Consequently a new torrent can still fail at source lookup.

Authorized foundation implemented: optional private, bounded persistent storage
of successful exact-ID/context validation results, surviving service restarts.
Failed/ambiguous results are not durable positive matches. Changed supplied IDs,
title, year and typo mode must not hit an earlier key. Cache faults fall back to
the current resolver. No downloads, notifications or production change yet.

Pending design choice sent to the user: for a new torrent with the same exact
source/title/year but no readable metadata, can a unique previously verified
match enable Grab Anyway, or must the user confirm the remembered identity first?
D005 currently requires source/context verification and disallows title-only
fallback when the source lookup fails. The new cross-torrent behavior will not be
implemented or enabled until the user resolves this question. Download approval
will remain separate in either design; film-cut evidence stays release-specific.

Acceptance for the foundation: durable hits avoid provider calls; seven-day
expiry is not extended by reads; 1,024 entries / 32 KiB bounds; private 700 parent
and 600 file; expired/corrupt/inconsistent data cannot bypass fresh validation.
Preserve production revision 99d81d8 and existing action/retry state.
