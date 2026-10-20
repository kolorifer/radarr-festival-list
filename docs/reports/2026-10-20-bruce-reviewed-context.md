# Bruce Almiighty reviewed identity correction

## Approved scope

The owner approved one narrowly scoped spelling correction, bound to the verified
IMDb/TMDb identity, with safe deployment and no downloads. No other pending
identity, generic fuzzy matching, research schedule or acquisition policy changes.
The unrelated active cleanup task is preserved.

## Implementation and evidence

Live read-only exact-listing verification found the expected IMDb association;
the unique TMDb movie mapping and reverse IMDb association agree. The observed
spelling produces `title_conflict`; the canonical spelling/year produces
`external_id_verified`. Private evidence is retained on the seedbox.

`reviewed_identity.py` adds `bruce-almiighty-2003`: Bruce Almiighty (2003) to
Bruce Almighty (2003). The existing private registry binds the approved IMDb/TMDb
pair plus exact source, listing, release name and observed title/year fingerprint.
The registry now permits the three fixed approved rules. Prior rules remain intact.
Normal listing validation, unique movie mapping, reverse ID, title/year and local
identity checks still apply. No title-search fallback or general typo tolerance.

Regression tests cover the new correction, changed spelling/case/year/release/
listing, wrong expected TMDb ID, immediate revocation and three-rule coexistence.
Existing regressions cover conflicts, invalid configuration, source restrictions,
immutable release references and action gating. No real notifications or downloads.

## Verification and deployment

Implementation commit `b055628`; isolated runtime `3d842b1`, based on verified
production `09c3ab4`. Only reviewed_identity.py and its tests differ in the runtime.
PR: https://github.com/kolorifer/radarr-festival-list/pull/67

Seedbox runtime: all 601 tests passed. Local full suite initially encountered
sandbox-denied loopback binds; rerun with loopback permission passed 618 tests
(two Linux-only skips). CI Python 3.12 and 3.13 passed at implementation head.
PR67 merged as `012af5248aacf98fb2b934d48047491a99a87200`.

Production is clean at `3d842b1f2dfc355ba687022254d34d2c61a4236b`.
Private state/configuration backed up before activation; code/config rollback was
prepared but unnecessary. Dependency, catalog and deployment preflight passed.
Local/public health200, 1909 movies; actor and collector active with NRestarts0,
collector PID unchanged, daily research timer active. Protected collector/research/
helper/configuration hashes, approval state and download receipts unchanged.
The two existing reviewed bindings are preserved; only the new exact binding added.

A fresh post-deployment context build using live tracker/TMDb metadata returned
`verified_tmdb`, `external_id_verified`, and `bruce-almiighty-2003`. Acquisition,
approval creation and Telegram methods were guarded against invocation. This was
not a webhook replay and did not update retry/research outcomes or create a button.
No downloads or test notifications were triggered.

## Limits

The correction applies only to the reviewed exact release provenance. Another
edition/listing or changed source identity remains subject to normal checks and
review. Old messages and closed investigation outcomes are not replayed or reset.
A future eligible event can use the correction; any acquisition still requires
its normal explicit confirmation. No live download test is part of this work.
