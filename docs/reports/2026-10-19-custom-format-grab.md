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

## Completed validation and deployment

- PR65 merged as `6c55c3cad17c4b706c51674aca24bb9b709d35fe`; both Python CI jobs passed on head `ad9ba8597e26ed00b7a7f578a3f98f39429744c7`.
- Full local suite: 611 tests, two Linux-only skips. Exact isolated runtime: 594 tests, all passed on the seedbox.
- Production runtime **`5e2758405962ea23a46df079f2ca34d503b5a276`**, based on previous production `906a2cdc5c8fad2c62bb5e8ab46675ec290eb143`. Only the allowlist module and its two test files changed; these match the merged implementation exactly.
- Dependencies, configuration and catalog preflight passed. Private state/configuration were backed up under `~/.local/state/custom-format-rollout/`. Only movie-intel restarted. No configuration changes were needed.
- Local/public health200; clean production checkout; 1,909-movie catalog unchanged. Actor/collector active with NRestarts=0; collector PID, protected research/config/timer files, approval state and helper receipts unchanged. Digest ledger remains two sent.
- Read-only postflight confirmed the actual retained Masters of the Universe (2026) rejection is now accepted by the deployed rule. This validates the rejection gate, not the remaining identity/file/source gates; all remain mandatory.
- No action token was created, notification replayed, source torrent fetched, or live download triggered. Explicit replacement consent remains required. No real acquisition/import smoke test was performed.

## Limitations and rollback

Existing Telegram messages do not gain a button retroactively. Future announcements
can offer it only after every eligibility check passes. New/localized rejection
wording and mixed unrelated reasons remain blocked. Queued still does not prove
import/replacement. Roll back only code to `906a2cd`, preserving current approvals,
receipts and configuration, and verify health; never restore old approval state.
The unrelated active task in `docs/CODEX_TASK.md` was left intact.
