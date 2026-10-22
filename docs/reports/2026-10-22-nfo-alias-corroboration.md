# NFO tracks and alias corroboration in shadow

## Approved brief and implementation

Extract dotted-layout NFO runtime and all audio tracks separately, including
commentary. Refine alias corroboration, test/deploy only shadow, no downloads
or notifications. Multilingual scoring is a proposal, not enabled policy.

Parser normalizes field-padding dots, reads runtime only from a unique GENERAL
section, splits each AUDIO section, excludes subtitles, retains title/language
and marks explicitly labelled commentary. Other track roles remain unspecified.
The leading full filename is now checked against the exact release; mismatches
block. Numbered AUDIO(n)/GENERAL INFO layouts and clock-form runtimes are also supported; seconds are retained as fractional minutes. Language qualifiers and commentary in OTHER INFO remain explicit. MediaInfo layout remains supported. Unsupported/ambiguous fields are
missing rather than guessed. Cantonese/Mandarin labels remain in track titles;
Chinese language fields are not silently converted into a specific variety.

An undocumented source alias can be corroborated when both complete alias
searches uniquely return the same candidate, at least one alias is a catalog
title, the year agrees and the checked tracker IMDb uniquely maps to that movie.
This is supporting evidence from TMDb, not two independent sources. All existing
source/ID conflicts, candidate completeness, sequel, threshold and margin guards
remain. Missing/disagreeing support stays review-only.

## Multilingual scoring proposal — not enabled

Keep at most10 language points per release. Award+10 when at least one positively
identified non-commentary film-audio track matches the candidate original
language. Additional dubs or commentary neither add points nor subtract them.
Award0 when the evidence is ambiguous, commentary-only, or only a different dub
is present; absence of original audio is not proof of a different movie.
Chinese alone cannot establish Cantonese or Mandarin; a clear track label can
supply that distinction after a separately tested generic language mapping.
This proposal needs review, especially whether an unlabelled track counts as film
audio. Current mixed-language score remains0, with unchanged weights/thresholds.

## Validation/deployment

Added tests for padded fields, all four audio tracks, commentary,
missing/duplicate language, container-only runtime, filename conflict, and alias
support requiring agreeing year/IMDb/checked source/crosswalk.


## Final tests and deployment

Implementation **db8c3c2** (includes76122bc); draftPR78 remains unmerged.
Full local728 tests passed(two Linux-only skips,155.942s), seedbox728 passed
(48.316s), CI Python3.12/3.13 passed run39836716068. Six new tests added to the
previous722 cover both layouts and constrained alias support;47 targeted tests
passed. Installed fresh/scorer/refresh hashes match the exact tested revision.

Shadow unit switched to isolated `~/.local/share/identity-scoring-shadow/db8c3c2`.
Final backup is `~/.local/state/identity-scoring-shadow-backup-k37arp_g`.
Actor stays **658d8f838aed7a03db7d01244254362fba99369a**; actor source/environment,
actions, original research timer and pilot deadline hashes unchanged. Local
health200; actor/collector/research timer healthy, shadow timer restored. No actor
restart, live identity/queue change, notification or download call.
Rollback restores only the previous shadow unit and reloads/restarts its timer;
do not restore earlier budgets or approval state.

## Actual verification and limitations

**ChinaIII:** fresh score **88.660714**, `would_identify` TMDb10619. Title30,
year20, trackerIMDb25, runtime13.660714 (NFO111min vs catalog112min), language0.
Margin88.660714 is versus zero for the sole candidate, not a probability or proof
no unseen rival exists. Both complete alias searches uniquely return this movie;
documented English title, year and unique checked IMDb mapping corroborate the
transliterated name. Existing conflicts were not overridden.

All four audio tracks retained individually: Chinese/Cantonese-labelled mono,
Chinese/Mandarin-labelled stereo, English5.1, English commentary. The fourth is
explicit commentary; other roles remain unspecified. Exact embedded filename
now binds to the release. Mixed-language points remain0 pending policy approval.

**ChinaII:** read-only replay of its retained real NFO extracts113min25sec and
five tracks: two Cantonese-labelled Chinese tracks, Mandarin-labelled Chinese,
English5.1 and English commentary. No fresh full score: its first alias query
currently returns4 results, exceeding unchanged combined-candidate cap3. Retained
score75 is not fresh verification. The candidate-search limit is separate from
NFO parsing; partial NFO extraction is not published by the standard refresh
runner until candidate collection completes. This remains a visibility gap for
failed searches, even though the parser now reads that NFO correctly.

Two initial rollout attempts automatically restored the previous shadow unit
when ChinaII hit the discovery gate. First failure consumed3 requests and was
recorded only as refresh_incomplete; diagnostic retry consumed3 and confirmed
candidate_capacity with4 returned results. No claim that the first failure's
exact cause was proven. Final rollout preserved that known recent failure without
requesting it again, and verified ChinaIII with5 GETs. **11 deployment requests**
total; existing daily ledger/caps, provider cooldowns and research history were
not reset. These were explicitly bounded deployment checks, not a new scheduled
retry policy. Runtime defaults still allow10/run and40/day; unchanged pilot ends
October27 at19:12Warsaw.

ChinaII broad-search handling and partial-evidence visibility remain follow-up;
this change does not silently discard rivals or enlarge budgets. Chinese alone
still does not identify a specific language variety. Other NFO layouts may remain
unsupported; missing or ambiguous facts are not inferred from the candidate.

PROJECT_STATE/D041 updated. Existing unrelated CODEX_TASK preserved. Monitoring
updated to the deployed revision and current findings, with no automatic policy
activation. Multilingual scoring proposal above is awaiting user review.
