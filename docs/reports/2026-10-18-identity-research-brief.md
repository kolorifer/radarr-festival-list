# Stage 2 bounded identity research — completed brief

Status: implemented, tested and finite pilot completed; owner review pending.
[Engineering report](2026-10-18-identity-research.md).

Owner authorization: [issue 51](https://github.com/kolorifer/radarr-festival-list/issues/51)
and the user's 2026-10-18 instruction. Implement and test a separate proposal-only
worker; perform frozen replay, then one finite metadata-GET pilot if isolation,
health and CI gates pass. Start with the four known unresolved seeds; select up to
ten additional cases only with affirmative unresolved evidence. Provisional
Stage1 groups alone are ineligible. No permanent scheduling, automatic identity
correction, catalog writes, notifications, approval tokens, Radarr operations or
media acquisition. Do not execute the unrelated CODEX_TASK cleanup assignment.

Preserve movie-intel 30adc20 and collector 3a20907, original Stage1 v1 schema,
source observations, reviewed corrections, existing exact-release safeguards and
observer OFF. Diagnose the historical storage warning without claiming an
unproved cause. Test concurrent intake/metrics, durable commit/ACK and recovery.

Implementation: separate private SQLite research state and a manually invoked,
default-disabled Linux worker. Fixed TMDb TLS origin, GET-only endpoint client,
Landlock and libseccomp after trusted preconnection; no tracker cookie, no action
state or acquisition credentials. Token is the existing approved TMDb read token.
No unconfined runtime entrypoint. Refuse unsupported kernel/library/layout or any
failed effective denial check. Never relax the collector boundary.

Hard aggregate pilot limits: 4 seeds + 10 confirmed unresolved additions; 100
metadata HTTP reservations total across all invocations/restarts; 10 cases and 50
reservations per invocation. TMDb receives the entire provider allowance; tracker
allowance is zero. At most two evidenced title variants, one movie/TV search page
each, three candidate detail records/case. All initial source assertions, private
candidate IDs, competing identities, observations and proposal versions retained.
Typed failures, global cooldown/auth suspension, expiring leases, request-before-
transport commit, material evidence deduplication and review-only results.

Deliver: reviewable PR (no merge authorization inferred), exact tested/pilot SHA,
local/CI 3.12/3.13/seedbox results, real installed denial proof, private per-case
trail plus sanitized findings, measured pilot/candidate/intake denominators,
remaining uncertainty and recommendations requiring later approval. Back up only
triage config/state; disable and close the finite pilot afterward. No timer.
