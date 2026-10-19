# Grab Anyway — existing Custom Format score rejection

Owner authorized support for the exact Radarr rejection “Existing file on disk
has a equal or higher Custom Format score: N”, with explicit replacement consent
and no live acquisition test. Previously this reason was absent from the strict
allowlist, so the Masters of the Universe notification had no button.

The allowlist now accepts that full anchored reason with an integer score,
including zero and negative scores. Every reason must still be approved; mixed
profile/language/identity or malformed reasons fail closed. Identity, exact-source,
existing-file, confirmation, helper, durable receipt and replacement safeguards
are unchanged. Existing Telegram messages are not rewritten or replayed.

Regression coverage includes zero/positive/negative scores, malformed and mixed
rejections, unresolved identities, and the actual Custom Format reason through
explicit/concurrent HTTP confirmations. All acquisition transports are synthetic.

Validation and deployment results will be recorded after the required gates pass.
