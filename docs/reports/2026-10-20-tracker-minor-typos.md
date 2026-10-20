# Tracker-backed minor filename typo identification

## Approved scope

Owner requested automatic identification of minor filename typos when tracker
IMDb, TMDb mapping and year agree, preserving download confirmation and all
existing safeguards. Test/deploy safely without downloads. No other identity
repair, research-budget change, history replay or automatic acquisition.

## Implementation

Conservative initial policy: one alphabetic insertion, deletion, substitution or
adjacent transposition in exactly one word. Both versions of that word must have
at least six letters; the candidate title must contain at least eight alphanumeric
characters. Word count/order remains fixed; numeric and Roman-numeral tokens cannot
be repaired. This intentionally excludes short/ambiguous words and larger changes.
Exact title normalization, catalog aliases/translations and documented release
years retain their existing behavior.

Only a successfully checked exact TorrentLeech listing enables the new resolver
option, with the actor switch `MOVIE_INTEL_TRACKER_TYPO_ENABLED=1` (default off).
The listing IMDb must map uniquely to one movie and round-trip from TMDb; year,
expected ID, nonmovie and local identity conflicts still block. Native-ID-only
and title-search callers remain strict. No extra metadata calls are required.

`tmdb_resolver.py` isolates typo-enabled/strict cache entries and records
`identity_title_basis=tracker_minor_typo` on accepted metadata. The service checks
canonical local identity as well as original context. Existing reviewed bindings
remain intact and take precedence. `deployment_config.py` validates the switch.
`test_tracker_typos.py` covers all four edits, larger changes, short words, sequel
numbers, year/ID/crosswalk conflicts, native IDs, source-name conflict, cache mode
separation, local conflict and unchanged release payload, with action/send guards.

## Validation and rollout

Implementation `a0509c7`; isolated runtime based on prior live `3d842b1`.
PR: https://github.com/kolorifer/radarr-festival-list/pull/68
Targeted 47 tests passed. Full local suite: 624 tests, two Linux-only skips.
Seedbox isolated runtime: all 607 tests passed. CI Python 3.12 and 3.13 passed at
implementation head. PR68 merged as `39e1b5fe35661a5b1baa352ab8e44651885ffa4f`.
An initial rollout preflight expected 608 tests instead of 607 and stopped before
changes; the actual passing log was verified and the count assertion corrected.
Production is clean at `0cc5f3fec5ccfa97af3977b9987c46d708c2b68b` with the
switch enabled. Runtime differs from `3d842b1` in the four implementation/test
files only and is byte-equivalent to the tested PR for those files. Private
state/config backups were taken; dependency, catalog and configuration checks
passed. Only movie-intel restarted. Local/public health200, 1909 movies;
actor/collector active NRestarts0, collector PID unchanged, daily timer active.
Protected research/helper/collector/configuration hashes, prior reviewed rules,
approval state and download receipts remained unchanged. Only the new switch
was added to the actor environment. Rollback was prepared but not needed.

Fresh read-only tracker/TMDb verification through deployed context-building code
returned `verified_tmdb` / `external_id_verified` / `tracker_minor_typo` for Bruce.
The specific reviewed override was bypassed only in that verification process,
proving the general rule independently; production bindings were preserved.
Action creation, Telegram and acquisition methods were fail-fast guarded and
not called. No live download or notification test, webhook replay or ledger reset.
The unrelated active cleanup brief remains untouched; project state and decision
D027 record this completed scope.

## Limits and rollback

This is conservative typo tolerance, not proof that a tracker association is
always correct. An incorrectly attached IMDb ID plus a very similar title/year
could still pass; short words, sequel identifiers, larger differences and ID
conflicts remain blocked to limit this risk. Human download confirmation remains
mandatory. Other trackers/native-only IDs, split/merged words and multiple typos
remain outside this initial policy. Historical closed review outcomes and old
Telegram messages are not rewritten or replayed.

Disable the new environment switch and restart only movie-intel, or roll back
code/config to the backed-up prior version. Never restore old acquisition state
or reset research/retry ledgers. No live acquisition test is authorized/performed.
