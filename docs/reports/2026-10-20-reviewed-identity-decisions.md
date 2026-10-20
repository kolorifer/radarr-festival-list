# Generic reviewed source-identity decisions

## Authorization and scope

Owner explicitly approved identifying the reviewed Madame Bovary release as the
1949 film, through a generic reviewed-correction flow, without downloads. This
supersedes the earlier blanket removal of runtime decision data only for explicit,
source-bound owner approvals; film-specific code rules and the retired context
registry remain prohibited. Unrelated cleanup work remains untouched.

## Design

A private append-only approval/revocation ledger binds the exact tracker release,
filename title/year, conflicting asserted IMDb, failure reason and sanitized
source-evidence digest to an owner-approved IMDb/TMDb pair. No film names or IDs
are hardcoded in the implementation. Approval/revocation is an explicit local
operator command; the research worker has no write access. There is no automatic
approval or review UI exposed over HTTP.

The initial generic scope is exact-checked TorrentLeech listings whose asserted
identity conflicts with the filename title/year. Native external-ID assertions,
malformed/ambiguous listings, absent source evidence and other failure classes
cannot use this path. Changed source/evidence needs a new review. The approved
pair must still pass the normal unique IMDb-to-TMDb mapping, reverse IMDb check,
and filename title/year checks; conflicting local catalog identities remain blocked.
Ledger absence, corruption, unsafe permissions or revocation fail closed.

Identity approval creates no acquisition action. Future normal offers retain the
existing explicit download confirmation. Review-backed pending actions preserve
the exact source and decision marker and revalidate their current source/context
before any remote acquisition write. A revoked, changed or unavailable decision
cannot be used by an old confirmation form. Existing non-reviewed actions retain
their original behavior. No historical action state is restored.

## Verification and deployment

PR73 merged as `6ef6643f0965b9047f73ce0a3b69d722d0771d8d` after exact-head
CI Python3.12/3.13 passed. Implementation `e38dd51`; production clean at isolated
runtime `6bf176b96378ab3408a73b59b9b9af0caf97c51d`, based on live `49531b1`.
Actor code matches the tested implementation; unrelated catalog changes excluded.

Local full suite638 passed(two Linux-only skips); seedbox runtime621 and main638
all passed. Regression tests exercise absence/revocation, changed source identity,
filename/year/evidence, invalid target mapping, private permissions/symlinks,
unsupported failure types, actor integration without effects, review metadata in
future offers, and refusal of stale confirmation before any acquisition write.
Retired film-specific registry tests continue passing.

A live bounded metadata preflight confirmed the source evidence exactly matches
the evidence reviewed in this conversation, and verified the approved target pair:
IMDbtt0041615 / TMDb45184, Madame Bovary1949. An isolated ledger proved approval
and revocation before production activation. Private state/config backups and
config/catalog/dependency preflight passed. Only movie-intel restarted; collector
PID, installed collector/handoff/worker modules, settings and schedule unchanged.
A real confined worker proof denied both reading and writing the new decision
ledger, alongside existing protected-file/network/FD checks, with zero HTTP calls.
Local/public health200,1909movies; actor/collector active NRestarts0; timer active.

Exactly one authorized production decision was recorded, with owner-review note,
source/evidence hashes, target pair, ID and timestamp. Fresh deployed-actor lookup
returned verified_tmdb / owner_reviewed_source / Madame Bovary1949 / IMDbtt0041615 /
TMDb45184. The normal metadata observation and confined scan marked this source's
current collector/report route verified. The historical conflict proposal remains
stored and is explicitly not current; history was not overwritten or erased.
Research budget unchanged at4case versions/9GETs for the rolling week. Approval
state and downloader receipts unchanged; no acquisition capability was created,
no Radarr write/download or notification replay was triggered. No rollback needed.

## Limits

This is operator-mediated review, not automatic conflict correction. Only the
approved exact source/evidence version benefits; other releases need their own
review. Source-page edits can invalidate a decision conservatively. The legacy
film-specific registry remains disabled. Screenshot analysis remains human review.
No notification replay or live acquisition test is authorized/performed.

Ordinary listing/TMDb caches still apply (up to15minutes for successful cached
metadata); source changes invalidate a decision when observed. Screenshot links
are bound, not downloaded image bytes. Revocation blocks subsequent decision
revalidation but cannot undo an acquisition already in progress. Applying this
identity decision does not edit old Telegram messages or manufacture new buttons.
