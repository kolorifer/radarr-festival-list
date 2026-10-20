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

## Initial verification

An isolated seedbox check identified 1001 Nunakal through the new rule using the
announced alias,104 minutes,Malayalam,IMDbtt16103640 and TMDb1035029. TMDb's canonical
date is2022; cross-linked Wikidata supplies2023 as a later release year. That check
made one TMDb search,one details GET,one IMDb find and one Wikidata GET, plus the
existing listing fetch. All acquisition/notification functions were blocked.

Final tests, merge, activation and silent queue reconciliation pending.

## Limits

This initial parser supports a complete single-audio MediaInfo NFO, exact displayed
minute runtime, and at most three complete search results. Unsupported layouts,
missing IDs/aliases/languages, larger searches, unavailable providers or conflicting
years require review. Screenshots remain human-review references, not machine
identity proof. Wikidata is corroborating structured metadata; its absence or
conflict does not authorize guessing. Ordinary listing/identity cache TTLs apply.
No provider data is edited to manufacture agreement, and no automatic download or
self-training from user choices is introduced.
