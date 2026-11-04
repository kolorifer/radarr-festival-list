# Manual expanded input with unknown identity

## Completed brief

Allow explicitly null IMDb and TMDb in the expanded retained-case manual workflow so an unidentified case reaches a supplied unresolved review. Preserve legacy input requirements, malformed-ID rejection, occurrence and supplied-identity bindings, private storage, and production refusal. No catalogue or search observation may be invented from absence. No new source, provider call, worker, spend, or deployment is authorized by this change.

## Implementation and state

Expanded inputs accept explicit null IDs; retained IMDb fields must themselves be present and agree. Absent catalogue methods appear as `not_observed`, and missing IDs appear in required missing facts. Lookup rows still require their valid supplied identity bindings. Legacy packets still require IDs. The supervised validator already permits an unresolved result with a null candidate and refuses unsupported proposed candidates; its runtime code is unchanged.

## Validation

Focused tests on Python 3.12 and 3.13 cover prepare, a clearly synthetic supplied unresolved reply, completion and retained report, invented-candidate refusal, malformed IDs, absent keys, legacy refusal, and supplied binding mismatches. The existing accepted historical run was reconstructed read-only at its original preparation time: selection, request and model input matched exactly, its answer still validated, and all retained artifact hashes were unchanged. No completion was replayed. Full supported-version CI is required on the published head before merge.

## Review and limits

Independent review identified the difference between absent retained IMDb fields and explicit nulls; the parser now rejects omitted fields and regression tests cover each omission. The unknown-ID route also refuses other supplied source/original identity fields that it cannot project, rather than silently hiding them. Synthetic test replies are not genuine model assessments or provider receipts. Historical source authenticity and actual reply authorship still require external review. Production, activation, privacy/storage guards, scoring and acquisition policy are unchanged. This is an offline manual input correction, not deployment or approval of any movie.

The unrelated current implementation task remains untouched. This scoped report records the implementation state without republishing unrelated historical project-state material.
