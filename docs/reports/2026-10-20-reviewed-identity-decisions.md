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

Pending tests, pinned runtime deployment and exact-source verification.

## Limits

This is operator-mediated review, not automatic conflict correction. Only the
approved exact source/evidence version benefits; other releases need their own
review. Source-page edits can invalidate a decision conservatively. The legacy
film-specific registry remains disabled. Screenshot analysis remains human review.
No notification replay or live acquisition test is authorized/performed.
