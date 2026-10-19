# Approved brief: automatic movie-identification investigations (#57)

Specification: https://github.com/kolorifer/radarr-festival-list/issues/57 and the owner's explicit instruction to implement it autonomously.

1. Trace Aberfan's natural post-activation notification through the observer, outbox and correlated collector evidence; inspect only its exact private listing.
2. Finalize PR54 after fresh checks; preserve the currently verified deployment until replacement gates pass.
3. Add bounded actor-side metadata-only retries, typed safe reasons, durable deduplication/reservations and no notification/action replay. Conservative additional-request budget: 10 GETs per rolling week globally, at most 5 per provider; at most 3 attempts per unchanged evidence version in 24 hours; 15-minute, 1-hour, 6-hour delays. Authentication/permanent conflicts require review.
4. Route movie-category/episode-type contradictions to sanitized quarantine and one concise, non-actionable diagnostic. Preserve original parsed type; Apollo and 18½ identity repairs remain unapproved.
5. Introduce a separate recurring-v1 ledger, confined loopback manifest handoff and daily eligibility scan. Research only new/materially changed eligible cases: 5 case versions / 25 TMDb GETs per rolling week, maximum 5 GETs per version. Failed/unknown reservations count. Preserve the closed 19-request pilot and all four proposals.
6. Produce a private changed-case report including all current assessment lanes, freshness, evidence, candidates/conflicts and review requirements. No Telegram digest or review controls until a sanitized example receives product sign-off.

Release gates: complete local and seedbox suites; CI Python 3.12/3.13; frozen scoring; actual Landlock/seccomp and narrow-transfer proofs; private backups and disable/rollback verification; healthy actor/collector. No acquisition, catalog writes, new approval tokens, historical Grab enablement or widening of security boundaries.

Unrelated active CODEX_TASK assignments are outside this brief.
