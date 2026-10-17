# Movie List project state

Last verified: 2026-10-14. Read [decisions](DECISIONS.md),
[active task](CODEX_TASK.md) and [engineering instructions](../AGENTS.md).

## TMDb duplicate exact-match resolution — 2026-10-17 (local review)

Issue #33 / supervisor task 1 implemented locally on automation/issue-33-worker,
from clean a7017dd. Duplicate exact normalized title/original-title + year
matches resolve only with both >=10x popularity and >=10 points of lead over
the strongest runner-up. All exact candidates need finite nonnegative numeric
popularity; missing/invalid evidence and close candidates stay unresolved.
Unique-match behavior and existing title/year filtering remain unchanged.

TESTED offline: 42 focused resolver/notification/action/pending-action tests
pass. Full discovery with a socket-denying audit hook: 283 tests, 273 passed,
10 socket tests skipped under the task's network prohibition. Supplied Snowman
popularity values select TMDb372343; synthetic unique Hamnet (2025) selects
858024; malformed Hamnet remains unresolved. These are mocked identity checks,
not live TMDb observations. No dependencies installed.

No network/seedbox access, deployment/restart, live notification or Radarr/media
mutation. Runner owns Git/PR publication. Product acceptance and live validation
remain pending. The unrelated legacy CODEX_TASK.md assignment is unchanged and
was not executed. No next implementation task inferred.
[Completed brief](reports/2026-10-17-tmdb-duplicate-exact-brief.md) ·
[Engineering report](reports/2026-10-17-tmdb-duplicate-exact.md).

## Supervisor communication extension — 2026-10-16 (local review)

Issue #30 / supervisor task 2 corrects both PR #31 review findings locally on
automation/issue-30-worker from cde534ae5e34da13a4de6ac44484cfa3c01a61ae.
Initial checkout was clean; read-only remote branch inspection matched that SHA.
Receipt failure now preserves existing task retention and captures any new
failure baseline only from the exact validated execution checkout. A checkout
creation failure cannot generate launcher-based continuation. Terminal publication
requires confirmed atomic claim ownership; conflicts/ambiguous responses retain
local consumption and bounded diagnostics without private writes or public
WORKER_RESULT. Claims and task numbers are never retried or reused.

TESTED locally: 105 focused / 272 full tests pass in the existing isolated Python 3.9.6
environment. Separate launcher/issue worktrees exercise matching tar/index
backups and actual next-task continuation; two synthetic hosts exercise stale
discovery, claim conflicts and lost responses. Full-suite results are recorded
in the [task-2 report](reports/2026-10-16-supervisor-communication-task2.md).
No Git publication, launcher/LaunchAgent changes, merge, deployment, live private
fixtures/services or schedule access by this worker. Prior live evidence below
is preserved; acceptance of these fixes remains pending review and later live work.

Schedule context supplied by the task-2 owner: user enabled an hourly supervisor
heartbeat in the current Work/Codex chat; creation returned ACTIVE. No scheduled
wakeup has yet been observed. Original cloud ChatGPT schedules remain unverified.
This is supplied account-side status, not a local test or worker observation.
[Task-2 brief](reports/2026-10-16-supervisor-communication-task2-brief.md) ·
[Corrected protocol](../automation/SUPERVISOR_PROTOCOL.md).

Task-1 implementation and evidence (historical; corrected as above):

Issue #30 / supervisor task 1 implemented locally on automation/issue-30-worker,
from b294cec (initial checkout and read-only public main agree). Parent-owned
PRIVATE_INPUTS now requires exact commit/blob/SHA256/path/alias, validates before
reservation, stages outside the public checkout without an input writable grant,
and checks immutability. Private-input tasks refuse public code/history publication.
Separate PRIVATE_DIAGNOSTIC grants one exact structured terminal JSON destination
using private CAS/readback. Public status exposes stable reason/receipt availability
only; required receipt failure cannot produce successful READY.

TESTED locally: 97 focused / 264 full tests pass on isolated Python 3.9.6; pip
check and diff checks pass. Synthetic integration uses real temporary Git/files
and a Python child behind fake GitHub/Codex boundaries. No live private repository,
Radarr, seedbox or media access; no launcher/LaunchAgent/state evidence changes,
Git publication, deployment or schedule activation by this child. Earlier PR #27/
#29 and issue-28 live evidence below remains historical and preserved.

EXPECTED BY DESIGN, pending later OBSERVED LIVE: deployed CLI reads staged aliases,
parent publishes new output/receipt loop, and original ChatGPT account schedule
wakes/reviews it. Prepared exact prompt/checklist requires inspecting existing
Codex Supervisor Sync and Phase B Output, enabled/next-run verification and one
actual wakeup. Local tests/LaunchAgent do not prove cloud activation.

This scoped task is complete for review; no next implementation task inferred.
The unrelated legacy CODEX_TASK.md is retained unchanged and was not executed.
[Brief](reports/2026-10-16-supervisor-communication-brief.md) ·
[Report and recovery limits](reports/2026-10-16-supervisor-communication.md) ·
[Account handoff and later harmless live plan](../automation/SUPERVISOR_HANDOFF.md).

## Supervisor infrastructure stabilization — 2026-10-16

[PR #27](https://github.com/kolorifer/radarr-festival-list/pull/27) merged;
verified runtime e56ff969a9c621b6e02083604408f53e3f322d55 deployed on launcher main.
Installed LaunchAgent remains --once discovery every 60 seconds; plist unchanged.
Existing issue-26 worktree, stash, journals and permanent claims preserved.

Exact-path private output authorization, host CAS/readback verification,
snapshot-bound continuation with private backups, fixed public result text,
filtered child credentials/config, high reasoning default and local heartbeat
are implemented. 65 focused / 232 full tests pass; CI 3.12/3.13 passes.
Real authenticated quota probe succeeded after a synthetic stale-entry condition;
failure/cooldown paths remain synthetically tested.

OBSERVED LIVE: harmless issue #28 automatically executed two high-reasoning tasks:
intentional NEEDS_USER with preserved partial work, then exact snapshot continuation
without stash/reset, host private publication/readback and sanitized READY_FOR_REVIEW.
Active process/heartbeat and both held locks were observed. Backup remains intact;
smoke checkout is clean. No Radarr/seedbox/media access or movie state changes.
Original cloud ChatGPT supervisor schedule activation remains unverified; no local
automation entry was found and available tools cannot enumerate that cloud schedule.

[Engineering evidence and limitations](reports/2026-10-16-supervisor-stabilization.md).
[Current protocol and precise schedule handoff](../automation/SUPERVISOR_PROTOCOL.md).


## Local GitHub worker dispatcher-v2 — 2026-10-16

Issue #24 / supervisor task 1 implemented locally on automation/issue-24-worker.
Omitted --issue now discovers eligible owner-created open issues and selects one
oldest valid outstanding task per poll. Clone-wide flock supplements per-issue
locks/atomic claims; retained task worktrees preserve the launcher checkout.
Missing/stale quota telemetry now triggers a safe minimal read-only probe before
claims, with a 30-minute failure cooldown; fresh quota and <=15% guard preserved.
Dry-run prints safe identifiers and creates no worker/probe/state/publication.

52 focused runner tests pass. Full local suite: 219 tests, 218 passed and one
missing-bs4 dependency error; no project virtual environment present. Installed
LaunchAgent read-only inspection confirms --once without --issue, compatible
without plist edits. No agent/service changes or deployment; live quota-refresh
success/unattended dispatch not verified. Runner owns publication; supervisor
activation and product acceptance remain pending. Unrelated active task retained.

[Brief](reports/2026-10-16-dispatcher-v2-brief.md) ·
[Engineering report](reports/2026-10-16-dispatcher-v2.md) ·
[Automation setup](../automation/README.md).

## Approved private review batch 2 — 2026-10-16

Issue #20 / SUPERVISOR_TASK 4 completed 7/7 authorized record removals after
fresh exact identity and protection checks; skipped: 0. All 8 KEEP records and
all unrelated full movie rows remain unchanged. Media deletions: 0; import
exclusions created: 0. Configuration hashes and independent final live readback
passed. Private before/after evidence and execution report are retained privately.

Technical execution is complete; product acceptance remains with the
user/supervisor. No deployment, runtime, service or recurring policy changes.
Runner owns publication. The unrelated active task remains untouched.

[Brief](reports/2026-10-16-review-batch-2-task4-brief.md) ·
[Engineering report](reports/2026-10-16-review-batch-2-task4.md).

## Approved private review batch reconciliation — 2026-10-16

Issue #20 / SUPERVISOR_TASK 2 reconciled all 15 exact private targets through the
existing unattended SSH path. Fourteen end states already satisfied: 13 removal
targets absent and the preserved target present, watched-tagged and unmonitored.
One removal target failed the identity safeguard and remains untouched. Newly
completed: 0; skipped/blocked: 1; media deletions: 0. No Radarr mutations occurred.
Repeated full collection readbacks and configuration hashes show no unrelated
state changes during Task 2. Exact original/current/final evidence is private.

Safely partial and ready for supervisor review; the full 14-removal end state is
not achieved. No deployment, service changes or publication. Product acceptance
remains with the user/supervisor. Existing unrelated task brief is unchanged.

[Brief](reports/2026-10-16-review-batch-1-task2-brief.md) ·
[Engineering report](reports/2026-10-16-review-batch-1-task2.md).

## GitHub supervisor / fresh local Codex worker — 2026-10-15

Issue #11 / SUPERVISOR_TASK 1 implemented on automation/issue-11-worker for
supervisor review. The local Python runner uses fresh GPT-6.1 Sol / Medium Codex
processes, GitHub issue state, atomic claim refs, durable duplicate protection,
flock, an eight-iteration limit, and a <=15% 5h-quota pause. Dry-run and once modes,
28 offline tests and macOS auth/start/stop docs are included. No daemon enabled,
no deployment, and no Radarr/seedbox/media operation performed.

Local runner tests pass; the full local suite has the baseline sandbox/socket
and missing-dependency limits documented in the report. CI verifies supported
Python versions separately. Existing unrelated CODEX_TASK.md is preserved and
was not executed or cleared by this issue. No production behavior change.

[Setup](../automation/README.md) ·
[Brief](reports/2026-10-15-github-worker-brief.md) ·
[Engineering report](reports/2026-10-15-github-worker.md).

## Watched state for the newly imported Movie List cohort

D020 implemented/applied on production/watched-import-state, PR #10 merged45c3311.
All87 private-cohort exact IMDb IDs matched unique existing movies and were proven
against the original235-film import audit, qualification and Movie List/band tags.
Added watched tag9 and set monitored=false for all87; all other fields/tags and
non-target movies are unchanged. No scoring/qualification or acquisition change.

Second independent cohort dry-run:0 pending/missing/ambiguous. Normal Movie List
dry-run:387 already correct,0 changes/unresolved, no re-monitoring. The normal
sync runtime/write restrictions are unchanged; an explicit regression proves
existing qualified watched/unmonitored films remain unmonitored.

Canonical private watched manifest:271 prior +87 cohort −0 overlap =358 unique
targets. Cohort preserved as provenance. Private snapshot refreshed immediately,
992 records, all87 watched/unmonitored confirmed through GitHub. Count was992
before/after apply; two additions since prior iteration predate this operation.

167 tests (16 new), Python3.12/3.13 CI, pip/preflight/frozen catalog/privacy checks
pass. Unit hashes/cadence unchanged, timer active; same active movie-intel PID,
NRestarts0, local/public health200. No new recurring watched enforcement rule.
No blocker remains; task idle.

[Runbook](../deploy/WATCHED_IMPORT.md) ·
[Aggregate engineering report](reports/2026-10-14-watched-new-import.md).

## One-time watched tagging

D019 completed on production/watched-tagging, PR #9 merged at35dcdf0.
The validated private manifest contains271 unique exact IMDb targets, all matching
one current Radarr movie. Initial dry-run:0 already tagged,271 to-tag,0 missing/
ambiguous. Created watched tag9 and applied it additively to all271 movies.
Monitoring/files/settings/path/metadata and every unrelated tag are unchanged;
all non-target movies are unchanged. No movie-add/delete/acquisition commands.

Second independent live dry-run:271 already tagged,0 changes/missing/ambiguous.
Private radarr-current.json refreshed immediately (990 movies); GitHub connection
confirms all targets tagged and identical blob. No private target list is public.

151 tests (18 new), Python3.12/3.13 CI, pip check/preflight/frozen catalog/privacy
checks pass. Existing timer/unit hashes unchanged, active/waiting. Movie-intel
same active/running process, zero restarts, local/public health200.
One-time operation only; no new recurring watched rule or scoring/watch schema
change. Existing daily Movie List sync preserves watched as an unrelated tag.
The implementation task is idle.

[Runbook](../deploy/WATCHED_TAGGING.md) ·
[Aggregate engineering report](reports/2026-10-14-watched-tagging.md).

## Private Radarr read-only snapshot bridge

D018 implemented on production/radarr-snapshot-bridge, PR #8 merged at93a5761.
Deployed runtime is the validated merge; the subsequent documentation handoff
preserves runtime bytes. The same daily Movie List sync exports/publishes only
after successful reconciliation, with no second timer or Radarr credential store.

Private kolorifer/radarr-state/radarr-current.json has990 records. Live seedbox
publication and GitHub-connection readback are verified; all IDs/flags/tag labels
match, repeat exports are deterministic except timestamp, and generation made
zero Radarr writes. Snapshot/config/GitHub credential stay private with mode600.
One pre-existing missing IMDb ID remains null. Only schema-v1 allowlisted library
fields are exported; no Overview, paths, queue/releases or connection credentials.

133 tests (26 new), Python3.12/3.13 CI, pip check, preflight and frozen-catalog
validation pass. Existing timer/unit bytes are unchanged. movie-intel remains
active/running, same PID, zero restarts, local/public health200.
No manual reconciliation/apply or real download was triggered.
The first naturally scheduled hook run has not yet elapsed; its actual CLI
integration is tested and the deployed publisher is separately live-verified.
No access blocker remains. Keep the state repository private; token expiry can
cause stale snapshots without stopping/repeating reconciliation.

[Runbook](../deploy/RADARR_SNAPSHOT.md) ·
[Engineering report](reports/2026-10-14-radarr-snapshot-bridge.md).
Current implementation task is idle.

## D017 Radarr Movie List membership and score-band sync

Implemented on production/radarr-movie-list-sync, PR #7 merged at
a587e25ff32820cc5da6bf5bbbd07f3c2ad238b5. Source 34c0bdc passes 107 tests
(25 new), pip check, frozen-catalog validation and configuration preflight.
Main's subsequent handoff keeps runtime/scoring/catalog bytes unchanged.

Live dry-run: 387 qualified; 152 existing to tag; 235 missing; 0 unresolved.
Applied:152 existing tagged and 235 monitored records added with searchForMovie=false.
All 387 have movie-list and exactly one score band:
below225: 51; 225–249: 48; 250–299: 104; 300–399: 96; 400+: 88.
Membership tag 3; band tags 4–8. No exact-score tags/Overview changes.
Root /home/kolorifer/movies and profile 7 Ultra-HD-Remux were the single conventions
used by all 755 existing movies; they are frozen in private sync configuration.

Radarr has 990 movie records. All original 755 retain monitoring/profile/root/path/
file IDs/Overview and unrelated tags. A second live dry-run has 387 correct and
zero changes/unresolved; the installed oneshot repeats with zero writes.
No search/grab/download/import-list-refresh command was issued by this sync.
Queue remained 0 and no new grab/download history events occurred during apply.
Radarr's existing scheduled ImportListSync and normal monitored-download
bookkeeping ran independently; they are documented separately.

One unrelated existing record (Cativeiro, Radarr 675, no IMDb ID) was already
incomplete and remains untouched. All 387 qualified identities are exact/unique.

One user-systemd timer: movie-list-sync.timer, daily 03:43 UTC with up to 15min jitter,
Persistent=true. Shared private flock prevents overlapping CLI/timer runs.
Movie-intel remains active/running with the same PID and 0 restarts; health 200.

[Runbook](../deploy/RADARR_SYNC.md) ·
[Engineering/deployment report](reports/2026-10-14-radarr-movie-list-sync.md) ·
[Machine verification](reports/2026-10-14-radarr-movie-list-sync-verification.json) ·
[Applied members CSV](reports/2026-10-14-radarr-movie-list-members.csv).
The implementation task is idle. D012/D014/D016 and public feeds remain unchanged.

## D016 production implementation

Implementation branch: production/d016-qualification, based on main 696420a.
[PR #6](https://github.com/kolorifer/radarr-festival-list/pull/6) merged.
Implementation: 87873dafe2c08d8f1ce13163cb57efd15c2b7b50.
Runtime activated: 8e357b9edc90307c6af3e64f1c334527a11a5227.
The main handoff adds documentation/audit clarification without changing runtime
code, scoring inputs, frozen baseline, expected scores or generated catalog.

movie-intel.service is active/running, with the same process since activation
and NRestarts=0. Local and public HTTPS health return 200 and 1,909 movies.
Read-only Radarr status/roots/profiles, Telegram getMe/getChat and TMDb
configuration checks return 200. Autobrr notification 2 remains enabled WEBHOOK,
matches the private movie-intel target and includes PUSH_REJECTED.
No real notification/add/search/download was deliberately triggered.

82 tests pass, including 29 new regressions, on seedbox and Python 3.12/3.13 CI.
pip check and configuration preflight pass. Artifact regeneration is byte-identical;
all 1,909 score/family/rank values and the exact 224 deployed IDs/routes verify.
Privacy/doc/scope checks pass. The current task is idle.

The authoritative rule is exactly:
`qualified = grandfathered_deployed_224 OR Evidence Score >=225`.
Threshold inclusive. Frozen baseline is the 224 deployed at c7a4582; the 255
research comparator and 31 additions are historical diagnostics only.
Active routes: grandfathered_production, evidence_score_225; both may apply.
Legacy convergence/corroboration/canon never independently admit future films.

[Production data and reproduction](../production/README.md) replace movie-intel's
simulation qualifier dependency. All 1,909 frozen scores match PR #5, producing
387 qualified =224 retained +163 new. Of research31,11 naturally pass225 and 20
remain unqualified. D012 weights/Audience150/effective ceiling1000, canon
correlation and D014 anthology attribution are unchanged.

The runtime loads a validated production catalog without network scoring calls.
Unknown-movie Telegram messages show active D016 routes. A verified IMDb ID from
existing conservative TMDb resolution can join the catalog when an announcement
uses another title spelling. Approval/token/Radarr exact-release behavior remains
the deployed implementation, with automated HTTP integration coverage.

Read-only Radarr inspection found no import list consuming qualification,
research outputs or backcatalog. Existing festival lists are independent.
The D016 score promotion performed no movie additions/searches/downloads or
list refresh. D017 above separately authorizes monitored record reconciliation.
Public festival/curated/backcatalog list IDs/order remain unchanged.

## Watch annotations and data limitations

La Ciénaga and Uncle Boonmee were incorrectly watched; they are now unknown,
matching selected-to-watch without adding a visible state. Elephant was already
unknown and is regression-covered. Scores and qualification are unaffected.

IMDb coverage1909/1909; Letterboxd1900/1909. Nine gaps remain explicit.
Award-source unresolved counts: NSFC0, NYFCC0, LAFCA1, Critics Choice22,
EFA8, Gotham1. Small Axe and combined Nymphomaniac remain unallocated.
The five PR #3 TSPDT identity corrections are retained. No new enrichment,
identity resolution, formula or source interpretation was introduced.

## Live Telegram add-and-grab integration verified

On 2026-10-13 the real production path was successfully tested end to end using
an autobrr/Radarr `Unknown Movie` rejection for **Marty Supreme (2025)**.
The Telegram notification exposed the live **Add to Radarr & grab this release**
action for the exact announced TRiToN 2160p UHD BluRay Hybrid REMUX release.

Opening the action loaded the confirmation page with the resolved movie/poster,
exact release, Radarr root-folder selector and quality-profile selector. The live
test used `/home/kolorifer/movies` and `Ultra-HD-Remux`. Submission returned
**Added and sent to downloader** and reported that the exact announced release was
re-pushed with no indexer search. The user then confirmed successful completion in
the real Radarr/downloader flow.

Therefore this path is now live-verified, not merely synthetic/test-suite coverage:

`real autobrr rejection -> movie-intel webhook -> enriched Telegram notification -> approval page -> Radarr movie add -> exact release re-push -> downloader`

The single-use replay/HTTP 410 behavior was not separately re-demonstrated in this
live test; it remains covered by the automated service tests. No private tracker
URL, API key, webhook secret or action token is recorded in project documentation.
See [live integration report](reports/2026-10-13-live-add-grab-test.md).


## Research and engineering history

Research PRs remain unmerged audit history:
[identity cleanup #3](https://github.com/kolorifer/radarr-festival-list/pull/3),
[qualification calibration #4](https://github.com/kolorifer/radarr-festival-list/pull/4),
[final P225/P250 #5](https://github.com/kolorifer/radarr-festival-list/pull/5).
Validated handoff9c5a0f0; D016 decision906ff64.
Their large simulation artifacts are not production runtime/build dependencies.

[Current production brief](reports/2026-10-14-d016-production-brief.md) and
[engineering/deployment report](reports/2026-10-14-d016-production.md) record
tests, revision/PR references, deployment checks, privacy and rollback.
