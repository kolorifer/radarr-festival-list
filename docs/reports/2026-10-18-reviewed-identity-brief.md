# Issue #45: two reviewed identity context repairs

**Authorization:** [issue #45](https://github.com/kolorifer/radarr-festival-list/issues/45)
and the user's instruction to implement, regression-test and safely deploy.

Implement only Hamnet's reviewed source-specific title/year correction and the
exact Medeski Martin Wood Not Not Jazz alias. Bind each to the private reviewed
source/release fingerprint and IMDb/TMDb pair. Require successful exact listing
validation and the existing unique movie-ID roundtrip/title/year checks. Preserve
original release data, notification rendering and exact-release action safeguards.
Corrections must be auditable and revocable, without a general fuzzy, prefix or
multiple-year rule. Keep exact references/IDs/evidence outside public Git.

Revalidate private #44 evidence and reproduce old failures, test positive/negative
contexts, action eligibility without real action creation, immutability, provider
conflicts and prior controls. Run full tests/CI, dependency, scoring/frozen-catalog
and effective-config preflight. Create a reviewable PR; deploy its tested revision
after verifying main/tree and production independently. Back up private config and
state, stop/restart only movie-intel, and roll back code/config on failed health
without restoring stale action state. Verify live exact-listing/context GETs with
all notification/action/acquisition paths blocked in the probe process.

No changes to the four other unresolved identities, persistent queue, other
services, credentials, media or acquisition policy. No real test notifications,
webhook replay, approval tokens, Radarr calls, additions, searches or downloads.
The unrelated CODEX_TASK.md cleanup remains untouched.

**Technical design:** two fixed context transformations in `reviewed_identity.py`;
private owner-only schema-v1 bindings selected by `MOVIE_INTEL_REVIEWED_CONTEXT_FILE`.
Missing/removed/invalid bindings leave the original conservative resolver behavior.
Read the file on each eligible lookup so cached identities cannot defeat revocation.
An applied fixed rule marker is logged and retained in future action metadata;
private evidence digest/reference never enters the notification or log.

**Report:** [implementation and deployment](2026-10-18-reviewed-identity.md).
