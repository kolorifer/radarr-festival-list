# Issue #33 / supervisor task 1 — TMDb duplicate exact matches

**Source:** Control issue #33 and latest issue-owner supervisor task 1 supplied
to this fresh implementation worker. **Status:** Implemented for review;
[engineering report](2026-10-17-tmdb-duplicate-exact.md).

## Authorized objective

Change only the duplicate-exact-match decision in `tmdb_resolver.py`, with
focused tests and documentation. Allow the most popular exact normalized
title/original-title + year candidate only when its popularity is dramatically
dominant. Require both a substantial relative lead and absolute lead; preserve
fail-closed behavior for ambiguous or incomplete evidence.

## Acceptance and verification

- Preserve unique-match behavior and return `None` for zero exact matches.
- Reject near ties and missing/None popularity in duplicate matches.
- Document and test an explicit conservative dominance rule, including bounds.
- Verify Snowman (2017) selects TMDb `372343`, and Hamnet (2025) selects `858024`.
- Leave malformed `Hamnet 2025 (2016)` unresolved without recovery heuristics.
- Run focused resolver and movie-intel notification/action tests, plus the
  repository suite within the worker's offline restrictions.

## Boundaries and handoff

No network access (including socket-based integration tests), seedbox access,
deployment/restart, Radarr/media mutations, live notifications, daemon setup,
ChatGPT Work, or additional worker/runner launch. No payload parsing,
Telegram/action logic, matching expansion, or recommendation/scoring changes.
Runner owns commit, push, PR and issue reporting; the worker leaves a reviewed
local diff. The unrelated `docs/CODEX_TASK.md` assignment is not authorized here
and remains untouched.
