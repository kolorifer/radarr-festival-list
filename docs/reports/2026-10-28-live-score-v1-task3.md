# Engineering report: issue #86 — Live Movie Score, Task 3

**Specification:** [completed supervisor Task 3 brief](2026-10-28-live-score-v1-task3-brief.md)
and latest trusted owner Task 3 supplied to the worker.
**Result:** implemented preparation packet, **READY_FOR_REVIEW**;
private paired IMDb/Letterboxd trial **blocked / NOT_RUN**.
**Repository revision:** `automation/issue-86-worker`, clean starting/unchanged HEAD
`489ce4e3e005dbb15fadebf8ac27e6c181cf3a98` (Task 2 / PR #88).
**Verification date:** 2026-10-28, isolated local standard-library Python 3.9.6
venv `/private/tmp/live-score-task3-venv`; no repository venv was present.

## What changed

Added a separate manual source-validation packet. Default execution reads only
synthetic fixtures. The sole live mode requires explicit IMDb personal-use opt-in
and conditions acknowledgment, makes one bounded official export GET, processes
it entirely in memory and emits only aggregate/schema/provenance information.
No authenticated MDBList adapter was invented: its full response schema and
upstream/downstream rights could not be established. An explicitly synthetic
internal observation validator and injected-transport rehearsal exercise pairing,
identity, numeric/semantic/freshness checks, quota/stop rules and redaction.

The one authorized **real IMDb check succeeded: 8/8 exact IDs, 8/8 valid pairs**.
No rating/count values were printed, persisted or used for a new score. Export
Last-Modified, ETag, compressed SHA-256, byte size and request/retrieval times are
in the sanitized gate report. Individual measurement times are unknown for all
eight. Fresh values were discarded at process exit; this packet reproduces the
method and synthetic verification, not a fixed unpublished observation dataset.

The audit distinguishes personal-use permission from redistribution. Public
MDBList docs advertise a free key/tier but do not establish the necessary
Letterboxd semantics, downstream permission, refresh policy or 30-day retention
right. Its documented account-retention policy is not a client-cache license.
Authenticated stages remain NOT_RUN, zero film operations. The packet includes
one unsent enquiry and a precise later private local setup contract. Code
readiness and advertised quota are not proof of authenticated sampling success.

## Files and components changed

| File/component | Purpose |
| --- | --- |
| `simulations/live-score-v1/source-validation/validate_sources.py` | Offline validator/aggregate output; synthetic trial stop rules; one opt-in in-memory IMDb check |
| `source-validation/test_validate_sources.py`, `fixtures/synthetic.json` | 18 synthetic test methods and explicit invented observation envelope |
| `source-validation/cohort.json` | Eight exact baseline IDs/TMDb joins/release context and retained evidence hash |
| `source-validation/source-audit.json` | Dated operation permissions, field/scale/count/freshness audit, official URLs and honest gaps |
| `source-validation/gate-report.json` | Sanitized real check metadata, separate synthetic results and readiness gates |
| `source-validation/README.md` | Commands, provider practicality, storage contract, unsent enquiry and minimum next owner action |
| `docs/PROJECT_STATE.md` | Narrow research preparation/verification/review status |
| This report and completed brief | Recoverable implementation handoff |

Paths abbreviated `source-validation/` above share the first row's research root.
No previous packet, scoring module, public feed, decisions or active task changed.

## Acceptance criteria and evidence

| Criterion | Result | Evidence / limit |
| --- | --- | --- |
| Private personal vs public redistribution | Audited | Official IMDb, MDBList and Letterboxd URLs dated 2026-10-28; unclear rights labeled, no legal guarantees |
| Single private IMDb exact-ID check | Passed | One GET, eight valid pairs in memory; hash/version/schema/aggregate only published |
| Accurate source timing | Passed within schema limits | Dataset modified time separate from retrieval; all eight per-film times unknown |
| MDBList/Letterboxd full field contract | Unresolved and explicitly gated | Indexed request/rate summary available; full schema inaccessible; no guessed live field mapping |
| Free-tier practicality | Conditional | Eight candidate GETs fit published quota, but actual allowance and Letterboxd inclusion untested |
| No credential/account acquisition/auth call | Preserved | Authenticated stages NOT_RUN; no key reader/config discovery, signup or contact |
| Exact eight-film manifest | Passed | Hash-pinned retained identity evidence plus Task 2 identity regression; conflicts retained |
| Offline default/manual bounded tool | Passed | Zero-request default test, dual opt-in gate, fixed URL/no redirect, byte/time bounds, no retry or writer |
| Validation edge cases | Passed synthetically | Same-response pairs, ranges, missing/zero, invalid values, count meaning/precision, identity/time, failures and redaction |
| Privacy/storage | Implemented for current tool; later writer conditional | Aggregate allowlist; no observation persistence/auth mode; explicit outside-checkout destination contract for future writer |
| Practical packet/enquiry/readiness | Completed | README, machine audits, manifest and go/no-go table; enquiry unsent |
| Production/live paired scoring | Not authorized/not run | No new rankings/calibration, integration, deployment or runtime changes |

## Tests run and results

All commands below ran for Task 3. `PY` denotes
`/private/tmp/live-score-task3-venv/bin/python`. No dependencies were changed or
installed. A repository venv was absent, so a fresh standard-library venv was
created outside the checkout with the available Python 3.9.6.

| Command | Actual result |
| --- | --- |
| `PY -m unittest discover -s simulations/live-score-v1/source-validation -p 'test_*.py' -v` | **18 passed**, final run after validation fixes |
| `PY simulations/live-score-v1/source-validation/validate_sources.py` | Offline synthetic aggregate, two pairs, zero requests; no live-data claim |
| `PY simulations/live-score-v1/source-validation/validate_sources.py --imdb-personal-check --accept-imdb-conditions` | **One real GET**, eight exact IDs/pairs; values not emitted/stored; exit 0 |
| `PY -m unittest discover -s simulations/live-score-v1/task2 -p 'test_*.py' -v` | **14 passed**, preservation regression only |
| `PY -m unittest discover -s simulations/live-score-v1 -p 'test_*.py' -v` | **20 passed**, Task 1 preservation regression only |
| `PY production_scoring.py --check` | Passed, unchanged 1,909 candidates / 224 grandfathered / 163 new / 387 qualified |
| `PY -m unittest -v` | **515 run, 68 errors, two skips**, 189.457 seconds; not a suite pass |
| `git diff --check` plus explicit new-file whitespace/JSON/link checks and source/diff inspection | Passed; public-safe scoped additions only |
| Byte comparison to pinned Git blobs | All **25** retained Task 1/2 packet/report files unchanged; active task and production files unchanged |

The full-suite errors were 60 missing `requests`, four missing `bs4`, one absent
`OperationalError.sqlite_errorcode`, one absent `sqlite3.SQLITE_BUSY` and two
`RemoteDisconnected` failures in the unchanged HTTP storage-error paths. The
Python/dependency limitations match the pinned Task 2 categories; these are
fresh Task 3 results, not recycled results. No supported Python 3.12/3.13 run or
dependency-complete CI pass is claimed. This root discovery does not discover
the hyphenated isolated research folders; the explicit research commands above
test them. `pip check` was not required/run because dependencies did not change.

Focused tests use synthetic provider-like envelopes and injected transports,
not an authenticated service. They also check target identity against retained
Task 2 results. Request-time changes never promote stale/unknown measurement
times. Numeric pair validity does not certify freshness or permission. Synthetic
secret canaries are not proof about a future HTTP adapter/provider's logging.

Documentation/JSON parsing, whitespace/diff review and unchanged-baseline checks
passed. No additional live IMDb request is
needed for code changes or test reruns; network edge cases use mocks.

## Deployment result

Not authorized or performed. No seedbox, Radarr, tracker, downloader, media,
Telegram, private identity/configuration or production service access; no
notification/download/list-refresh test. No collector/cache, background task,
daemon, account/key acquisition, paid request, provider message, merge or push.

## Unexpected findings

IMDb personal-use export access worked without authentication and demonstrated
all eight exact pairs, despite the earlier public-packet acquisition gate.
This resolves private availability for that dataset revision, not redistribution
rights or per-film measurement time. No observations survive in this checkout.

MDBList's current static guide advertises a viable free request allowance;
full Swagger/schema access did not succeed. The web reader showed a single
back-link, indexed official docs supplied an endpoint/rate summary, the linked
schema had unsupported content type, and direct doc paths returned 403. These
are documentation access failures, not failed authenticated film lookups or a
reason to bypass access restrictions. No upstream permission was inferred.

## Unresolved issues and risks

The owner needs an explicit permission answer for MDBList-mediated Letterboxd
private derived scoring and 30-day retention, verified source field/count/scale
and exact-ID semantics, free-tier inclusion, and source refresh/measurement-time
meaning. Then a later task can authorize a reviewed adapter and private trial
with a locally supplied free key and explicit owner-private destination. No key
should be sent through chat/GitHub. The enquiry is ready but unsent.

Until then, paired source readiness is blocked. No fallback source, new
calibration or production step is commissioned. Snapshot retrieval success does
not establish subsequent availability. Permission findings are engineering
interpretations, subject to provider conditions, not legal guarantees. Full
supported-version CI remains separate review evidence.

## Commit and PR reference

Comparison baseline: [Task 2 commit](https://github.com/kolorifer/radarr-festival-list/commit/489ce4e3e005dbb15fadebf8ac27e6c181cf3a98),
[PR #88](https://github.com/kolorifer/radarr-festival-list/pull/88),
[control issue #86](https://github.com/kolorifer/radarr-festival-list/issues/86).
The worker did not query/change publication state or commit/push/post comments;
parent owns publication and supplies the containing change reference. HEAD and
branch remain the pinned starting revision.

## Project context updates

Project state records implementation, technical verification, absent deployment
and pending review separately. Completed Task 3 brief/report are archived here.
`docs/CODEX_TASK.md` stays untouched because it assigns unrelated cleanup;
decisions stay unchanged because no policy was approved. Tasks 1/2 and all prior
artifacts are preserved. Next owner action is permission/schema clarification,
not another scoring run. No prior chat/session history was read or worker spawned.
