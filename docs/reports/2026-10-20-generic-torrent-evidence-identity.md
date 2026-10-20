# Generic identification from corroborated torrent evidence

## Approved brief

Implement the agreed generic conjunctive rule, starting with Aayirathonnu Nunakal:
documented title/alias, agreeing NFO runtime/audio language, unique verified
IMDb–TMDb mapping, and a documented matching release year. Inconclusive/conflicting
cases remain for review. Preserve explicit download confirmation. Test/deploy with
no live downloads or notification replays and reconcile the affected queue status.
Unrelated cleanup tasks remain untouched.

## Implementation

New actor-only `torrent_evidence_identity.py`, default-off feature flag and startup
validation. Exact checked ID-less tracker source and matching NFO filename are
mandatory. Full MediaInfo general runtime and original audio language are compared;
subtitle metadata, multi-audio ambiguity and truncated text cannot justify a match.
A complete search of at most three candidates is inspected without first-result
or popularity selection. Crosswalk ambiguity, conflicting IDs, incomplete details
and unsupported date evidence fail closed. No film-specific rules or stored fixes.

Release dates come from TMDb or the candidate's linked Wikidata entity only after
that entity independently links the same IMDb and TMDb IDs. The fixed public JSON
endpoint is bounded, redirect-free and receives no credentials or tracker data.
It is actor-side only; research-worker network permissions and budgets do not change.
The existing retry metadata bucket pays for any such call during a guarded retry.

Source evidence is retained in the observation. An acquisition capability stores
its binding and rechecks matching before remote writes; disabling the feature
invalidates unused evidence-backed offers. Identity selection does not download.

## Verification and deployment

An isolated seedbox check identified 1001 Nunakal through the new rule using the
announced alias, 104 minutes, Malayalam, IMDb tt16103640 and TMDb 1035029. TMDb's canonical
date is 2022; cross-linked Wikidata supplies 2023 as a later release year. That check
made one TMDb search, one details GET, one IMDb find and one Wikidata GET, plus the
existing listing fetch. All acquisition/notification functions were blocked.

PR [#76](https://github.com/kolorifer/radarr-festival-list/pull/76) merged as
`f83ae692d5e4568facbaaa3ee4f02ced9ac6b480`. Tested production runtime is
`b4a8c1d0c6c43e5f05357db34e59ffb6d4c1894d`, isolated from unrelated main catalog
changes. The evidence flag is enabled; all other actor settings are unchanged.

Validation: 19 focused tests; full local suite 670 tests (two Linux-only skips);
seedbox main 670 and isolated runtime 649 tests passed. Dependencies, configuration
and catalog preflight passed. CI Python 3.12/3.13 both passed on head `99512c3`.
The first 3.12 run hit the unchanged collector concurrency test's SQLite lock
timeout; the failed job passed on rerun without code changes.

Private state/configuration were backed up. Only movie-intel was restarted for
rollout; local/public health returned 200 with 1,909 movies and no automatic
restarts. Protected collector, research, helper and review files were unchanged,
as were actions and downloader receipts. Collector PID was unchanged.

The same read-only proof on the deployed runtime verified Nunakal automatically.
A copied-database/digest proof preceded its one-case maintenance refresh: current
collector and review report now show `verified / external_id_verified`. Historical
records and the full research ledger remain intact. One suppressed digest receipt
prevents a maintenance notification; all previous delivery records are unchanged.
A naturally verified Locked arrival was included in the report without inventing
research. Madame Bovary remains `eligible / year_conflict`, Bruce remains verified,
and Aberfan remains skipped. Actor, collector and research timer are active.

No acquisition action was created, no download was triggered, and no notification
was sent or replayed by testing, deployment or maintenance. Future normal events
can offer explicit download confirmation; this identification rule never grants it.

## Limits

This initial parser supports a complete single-audio MediaInfo NFO, exact displayed
minute runtime, and at most three complete search results. Unsupported layouts,
missing IDs/aliases/languages, larger searches, unavailable providers or conflicting
years require review. Screenshots remain human-review references, not machine
identity proof. Wikidata is corroborating structured metadata; its absence or
conflict does not authorize guessing. Ordinary listing/identity cache TTLs apply.
No provider data is edited to manufacture agreement, and no automatic download or
self-training from user choices is introduced.
