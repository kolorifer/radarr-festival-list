# NFO tracks and alias corroboration in shadow

## Approved brief and implementation

Extract dotted-layout NFO runtime and all audio tracks separately, including
commentary. Refine alias corroboration, test/deploy only shadow, no downloads
or notifications. Multilingual scoring is a proposal, not enabled policy.

Parser normalizes field-padding dots, reads runtime only from a unique GENERAL
section, splits each AUDIO section, excludes subtitles, retains title/language
and marks explicitly labelled commentary. Other track roles remain unspecified.
The leading full filename is now checked against the exact release; mismatches
block. MediaInfo layout remains supported. Unsupported/ambiguous fields are
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

In progress. Added tests for padded fields, all four audio tracks, commentary,
missing/duplicate language, container-only runtime, filename conflict, and alias
support requiring agreeing year/IMDb/checked source/crosswalk.
