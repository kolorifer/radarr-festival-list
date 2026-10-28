# Collector SQLite concurrency fix

User request: fix the intermittent SQLite lock failures in collector concurrency
tests, add a regression that reproduces the cause, and merge into main. Do not
deploy. Preserve identity, acquisition, durability, rollback and failure-response
semantics. Keep the unrelated active cleanup brief unchanged.

Acceptance: identify the failing operation from original CI; demonstrate a
regression failure on the old implementation and a pass on the fix; retain
external-lock backpressure, bounded local waiting, commit-before-ack and exact
event deduplication; run focused/full tests and final-head CI before merging.
