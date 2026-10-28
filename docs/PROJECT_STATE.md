# Movie List project state

## Contextual typos and runtime handling — 2026-10-28

The owner-approved contextual five-letter typo rule, General-section NFO Length
parsing and bounded verified-ID runtime variation are implemented; deployment
verification is pending. See the [report](reports/2026-10-28-contextual-typos-runtime.md).


## Collector writer contention — 2026-10-28

A bounded local writer queue fixes collector threads spending SQLite's 250 ms
lock timeout behind other transactions on the same Store. Read-only access and
external-lock backpressure remain. The regression reproduces the old failure for
distinct and duplicate events. [PR #105](https://github.com/kolorifer/radarr-festival-list/pull/105)
merged at `55f22402be9a4001f913677587aade203f49ac3f`; its store module alone was
deployed on 28 October at 18:47 UTC. Actual-service preflight, 77 host tests,
confined synthetic concurrent HTTP intake and health/integrity checks passed.
Actor `46cccea3` and shadow `4db4e38` configuration/runtime were preserved;
no downloads, Telegram tests or production POSTs were triggered. See the
[implementation](reports/2026-10-28-collector-locks.md) and
[deployment](reports/2026-10-28-collector-sqlite-deployment.md) reports.

Repository consolidation is recorded in the [current status map](REPOSITORY-STATUS.md)
and [report](reports/2026-10-28-repository-consolidation.md). The last verified
actor revision below is historical; this consolidation did not deploy.

Historical qualification research and the read-only issues 55–56 investigation
are retained without changing current scoring or production behavior. See the
[consolidation report](reports/2026-10-28-historical-research-consolidation.md).

The isolated shadow identity and cut research from PRs #78, #90 and #92 is
retained under `research/identity_scoring/`; its reports and decisions are
historical. This repository integration does not activate a pilot or change
the shared recurring research budget. See the
[consolidation report](reports/2026-10-28-shadow-research-consolidation.md).

## Live Movie Score — Task 3 source preparation, 2026-10-28

Issue #86 supervisor Task 3 adds an isolated manual validation packet at
`simulations/live-score-v1/source-validation/`, preserving Task 2 / PR #88 at
`489ce4e3e005dbb15fadebf8ac27e6c181cf3a98`. Offline by default, it includes the
fixed eight-film manifest, operation/field permission audit, synthetic tests,
private/public storage contract, unsent provider enquiry and readiness table.
No new calibration, rankings, policy, runtime collector/cache or authenticated
adapter. The unrelated active cleanup assignment and prior packets are unchanged.

One authorized official IMDb export GET processed entirely in memory found
8/8 exact-ID rating/count pairs. Only aggregate/schema/dataset-version provenance
was emitted; no fresh observations persisted or were published. All individual
measurement times remain unknown. IMDb personal-use access is distinct from
public redistribution. MDBList's documented free quota is promising, but its
Letterboxd field contract, permission for private derived scoring/30-day retention,
source update semantics, actual account access and free-tier inclusion remain
unverified. Authenticated MDBList/Letterboxd stages are NOT_RUN (zero film reads).

Technical verification: 18 focused synthetic tests, 14 Task 2 and 20 Task 1
preservation tests pass; frozen scorer check passes unchanged. Fresh isolated
Python 3.9 full suite: 515 tests, 68 errors/two skips (64 missing requests/bs4,
four SQLite/HTTP compatibility errors); no full-suite/supported-version pass.
Implementation is ready for code review; paired provider trial remains blocked.
Deployment/operational verification: unauthorized and not performed. Parent owns
publication; owner review and explicit provider permission/schema/access gates
precede any separately authorized private trial. No automatic scoring follow-up.

[Packet and source audit](../simulations/live-score-v1/source-validation/README.md) ·
[Engineering report](reports/2026-10-28-live-score-v1-task3.md) ·
[Completed scoped brief](reports/2026-10-28-live-score-v1-task3-brief.md).

## Live Movie Score v1 — separate Task 2 research, 2026-10-26

Issue #86 supervisor task 2 adds a separate offline packet under
`simulations/live-score-v1/task2/` against immutable Task 1 / PR #88 at
`b62f00de56b2f1aa488e9f41742b86617efcec72`. The same 24 exact-ID films and all
Task 1 files/rating pairs remain unchanged. New evidence includes 26 award
corroborations (25 primary-page reviews, one indexed primary), 11 components
upgraded to direct primary support across ten films, and 81 scoped checks.
These improve provenance/coverage without changing any same-variant subtotal.

Fresh paired ratings remain unresolved after current source-rights/access review:
IMDb zero fresh, 22 archived plus two stale indexed; Letterboxd zero fresh,
22 archived plus two unavailable. No new raw rating dataset was acquired.
The three exact strengths 0/1,000/10,000 and priors 7.25/3.65 use fixed evidence;
audience ranks compare only the unchanged 22 paired archival rows. Two ties
separate; all same-scenario ranks match Task 1. Overall scores/ranks remain null.
TIFF/screenplay sensitivity remains separate and off in base; no constants,
award extensions, production logic or completeness policy have been accepted.

Technical verification: 14 Task 2 and 20 Task 1 research tests pass, offline byte
checks and unchanged frozen scorer check pass. The isolated Python 3.9.6 full
suite ran 515 tests with 68 errors/two skips: 64 missing requests/bs4 errors and
four SQLite/HTTP storage-error compatibility failures. No full-suite or supported
3.12/3.13 pass is claimed. Deployment/operational verification: unauthorized and
not performed. Parent owns publication; product acceptance and lawful fresh
audience evidence remain pending. The unrelated active cleanup brief is unchanged.

[Task 2 findings](../simulations/live-score-v1/task2/report.md) ·
[Engineering report](reports/2026-10-26-live-score-v1-task2.md) ·
[Completed scoped brief](reports/2026-10-26-live-score-v1-task2-brief.md).

## Live Movie Score v1 research — 2026-10-25

Issue #86 supervisor task 1 has a separate offline calibration packet for review
on `automation/issue-86-worker`, based on `cc11595`: 24 films (2024:10,2025:10,
2026:4), twelve variants each, with the agreed Audience 50 / Recognition 50 caps.
The selected historical award-family rows at `9c5a0f0` are preserved and exactly
reconstructed; dated public evidence documents additional awards and source gaps.

Coverage is 22 archived IMDb/Letterboxd pairs, two indexed sparse IMDb
observations, two unavailable Letterboxd halves, 93 newly reviewed award facts
and 68 scoped checks. Original rating measurement dates and complete live award
coverage are not established. All overall scores remain null; reported observed
subtotals are conditional on the pinned evidence. No overall leaderboard or
production confidence/bonus policy is adopted.

Technical verification: 20 focused research tests pass; offline regeneration,
pip check and frozen production scorer check pass. The local full suite ran 687
tests with four errors and two skips under available Python 3.9; SQLite error
attributes/constants are missing on that interpreter, including the unchanged
HTTP storage-error paths. Supported Python 3.12/3.13 CI was not run by this worker.
Deployment/operational verification: not authorized or performed; no seedbox or
service access. Worker publication is delegated to the runner. Product acceptance,
provider rights/access, exact confidence parameters and new awards remain pending.

[Calibration report](../simulations/live-score-v1/report.md) ·
[Engineering report](reports/2026-10-25-live-score-v1.md) ·
[Completed scoped brief](reports/2026-10-25-live-score-v1-brief.md).
The unrelated active `docs/CODEX_TASK.md` cleanup assignment is unchanged.



The main/production integration and its validation are recorded in the
[integration report](reports/2026-10-28-main-production-integration.md). The
integration commit is not itself a deployed revision.

For the verified 28 October repository and deployment snapshot, see the
[repository status and review map](REPOSITORY-STATUS.md). Earlier entries below
are historical and may not describe the currently running revision.


## Grab Anyway confirmation and first import — 2026-10-24

[PR80](https://github.com/kolorifer/radarr-festival-list/pull/80) is merged and
production is clean at `f34cd4d401cedf1be671b11b00ba86bcc30bf15e`, preserving
baseline `23202815`. Bounded exact-hash/category readback resolves delayed client
visibility or a lost add acknowledgement without a second submission. Private
receipt diagnostics preserve the existing source barrier and rollback compatibility.

The first alternative, The End of Oak Street, was already downloaded/imported at
12:05:04 UTC (file166→168). Exact client-hash/Radarr-import/current-file evidence
now reconciles its receipt to imported and retires its approval (HTTP410), without
another download. Other approvals/configuration and collector state were preserved.

Final suites: 672 local tests (two Linux skips), 672 seedbox passes; final PR CI
3.12/3.13 passed. Actor active, NRestarts0, local/public health200, 1,909 movies.
The historical immediate-check failure is consistent with delayed visibility,
but its exact exception was not recorded. Queue confirmation remains distinct
from import; genuine uncertainty stays blocked. No new live acquisition test.
[Report](reports/2026-10-24-grab-confirmation.md) ·
[Completed brief](reports/2026-10-24-grab-confirmation-brief.md).


## Reviewed occurrence status — 2026-10-20

PR77 merged `8003775`; actor runtime `658d8f8`, installed collector selection
`d8cce25`. Madame Bovary is now **reviewed for this occurrence**, retaining its
source conflict and historical evidence. Its persistent approval remains revoked.
A new accepted encounter—even the same torrent—reopens review with a new version;
exact duplicate transport delivery does not. No matcher reads review receipts,
and no download approval is granted. Reports/digest distinguish this from verified.

Local679 (two skips), seedbox main679/runtime649 and CI pass. Copied live-case
reopening/zero-send proofs and live handoff/report/health checks pass. Services
active, health200; actions, downloader receipts and research ledger preserved.
No downloads or notifications. Only 2018: Everyone Is a Hero remains unresolved.
Operator closure is explicit; web choices do not automatically close workflow.
[Engineering report](reports/2026-10-20-reviewed-occurrence-status.md).

## Generic torrent-evidence identification — 2026-10-20

PR76 merged `f83ae69`; production actor `b4a8c1d` with the generic evidence flag
enabled. Checked ID-less listings can identify automatically only when documented
title/alias, matching NFO filename/runtime/original audio, unique IMDb–TMDb mapping
and documented release year agree. Conflicting/incomplete cases remain for review;
explicit download confirmation and occurrence-only human choices are preserved.

Live read-only verification identifies Aayirathonnu Nunakal as TMDb1035029 /
IMDbtt16103640 using the documented later 2023 release date. Its collector/report
status is now verified; history preserved and maintenance digest suppressed.
Madame Bovary still requires review; Aberfan remains skipped. No downloads or
notification replays. Local670 (two skips), seedbox main670/runtime649 and CI pass;
health200,1909 movies. Protected files, research ledger and action/receipt state
unchanged. Parser/provider limitations are documented in the
[engineering report](reports/2026-10-20-generic-torrent-evidence-identity.md).

## Investigation status reconciliation — 2026-10-20

PR75 merged `2dfedf9`. Production actor remains `3a6c2cc`; no matcher/schedule
change. Live collector and report now show Bruce Almiighty **verified** under the
generic typo rule and Madame Bovary **review required** (`year_conflict`).
The previous approved Madame Bovary status described below is historical and
superseded by D033 and this reconciliation.

A scoped maintenance helper and deployment gate now require affected-case refresh
after identity-rule changes. Exact source evidence is rechecked; old records are
preserved. Two silent digest receipts suppress only this maintenance refresh;
previous deliveries, actions, downloader receipts and research ledger unchanged.
Local651 tests(two skips), focused seedbox tests and CI3.12/3.13 pass. Services
active, health200; no notifications/downloads. No new recurring scanner.
[Report](reports/2026-10-20-identity-status-reconciliation.md).


## Reviewed source correction — 2026-10-20

Owner approved the exact Madame Bovary release as1949 via a generic reviewed flow.
PR73 merged (`6ef6643f`), implementation `e38dd51`; production clean at
`6bf176b96378ab3408a73b59b9b9af0caf97c51d`. A private append-only approval/revocation
ledger binds source/evidence to the approved IDs; no film-specific code or retired
registry. Normal target ID/title/year validation and explicit acquisition
confirmation remain. Changed/revoked review-backed actions fail revalidation.

Live lookup verifies Madame Bovary1949 / IMDbtt0041615 / TMDb45184 with source
owner_reviewed_source. Collector/report now verified; historical conflict proposal
preserved but not current. This supersedes the earlier blocked status for this
exact reviewed source only. No download, Radarr write, action creation or
notification replay. Research ledger unchanged4cases/9GETs; other conflicts untouched.

Local638 tests(two skips), seedbox runtime621/main638 and CI3.12/3.13 pass.
Health200,1909movies; actor/collector active NRestarts0, collector PID/configuration
and timer unchanged. Actual worker denied read/write access to the new private
ledger with zero HTTP proof requests. Approval state/receipts preserved.
[Engineering report](reports/2026-10-20-reviewed-identity-decisions.md).

## Torrent-page investigation evidence — 2026-10-20

PR72 merged (`99f18fb3`), implementation `ad2c53c`; production clean at
`49531b165ce597460b9f2c254faa595277ab360b`. Generic unresolved-case evidence now
includes bounded separate description/NFO text and embedded screenshot references
for visual review. No image model, automatic conflicting-ID override or per-film
rule. Collector-compatible selection/intake preserve selected-only behavior;
worker/handoff confinement, credentials, budgets and timer remain unchanged.

Final local627 tests(two skips), seedbox runtime610/main627 and CI3.12/3.13 pass.
Actual collector ABI6/worker denial proofs, config/catalog/dependencies and
local/public health200 pass. Actor/collector active NRestarts0; actions/receipts
and protected settings unchanged. No downloads or notification replays.

Madame Bovary now has a current proposal containing its279-character description,
1409-character NFO and three screenshot references awaiting visual review. NFO114min
vs TMDb1949 candidate106min remains explicit. Identity still blocked year_conflict;
no correction applied. This supersedes the earlier statement that source evidence
was missing: it is now collected and awaiting review. Weeklyresearch4cases/9GETs
(no extra research GETs because catalog evidence was cached). Normal changed-case
digest can report this material update. Unsupported image hosts remain counted;
images themselves are not fetched or analyzed. No historical bulk replay.
[Engineering report](reports/2026-10-20-torrent-research-evidence.md).

## Generic conflict investigation — 2026-10-20

PR71 merged (`0f27ec7b`); actor and research worker use tested runtime
`15e07b446637f21049f9a673b80c543e945fa0ac`. Collector identity_selection uses
082a1ca to preserve selected-only intake; other installed collector modules remain
unchanged. Strongly correlated title/year/ID conflicts enter bounded proposal-only
research. Actor identity and approval gates remain blocked; no override is applied.
Local616 tests(two skips), seedbox actor599/collector-compatible616 and both CI
versions pass. Installed collector ABI6 and worker denial proofs pass; health200,
actor/collector active NRestarts0, timer preserved, acquisition state unchanged.

Madame Bovary pilot used5requests, retained the linked2015 film, and proposed
TMDb45184/IMDbtt0041615 (1949, Vincente Minnelli) for human review. Independent
source corroboration is missing; conflicting IMDb remains explicit. Still
needs_review/year_conflict, with no action creation/download or notification replay.
Weekly research usage3cases/9requests; limits unchanged. New proposal evidence
uses the existing changed-case digest policy. No per-film exception introduced.
[Engineering report](reports/2026-10-20-conflict-investigation.md).

## Bounded missing-mapping retries — 2026-10-20

PR70 merged (`c061989d`), production clean at tested runtime
`c2ae4e12e67486d4651db863e5132213715246f6`. Missing TMDb mappings now enter the
existing bounded metadata retry path; conflicts remain excluded. No budget,
identity-policy or notification behavior expansion. Insomnia's authorized retained
case recovered on its first normal worker attempt (one listing/two TMDb GETs),
collector updated to verified, original expiry preserved. Madame Bovary remains
year_conflict and unqueued. Prior request/attempt history and approval state
preserved; no downloads or notification replay. Local613 tests (two skips),
seedbox596, CI3.12/3.13 pass. Local/public health200, actor/collector active
NRestarts0, collector PID and protected configuration unchanged.
[Engineering report](reports/2026-10-20-missing-mapping-retries.md).

## Generic identification only — 2026-10-20

PR69 merged (`832131e6`); production clean at tested runtime
`c025aad64cbab6b5f891aac96a11b708f0fc077c`. All three per-film actor exceptions
and their registry code are removed; legacy environment binding removed. Bruce
live-verifies through the generic typo rule without any override. Hamnet/Jazz
must satisfy ordinary catalog ID/title/year checks; no special repairs remain.
Local610 tests (two skips), seedbox593 and both CI versions pass. Local/public
health200, actor/collector active NRestarts0, collector PID unchanged. Protected
components, approval state and download receipts preserved. No notifications or
downloads triggered. Historical audit evidence remains private and inactive.
This supersedes earlier statements that the three reviewed bindings are active.
[Engineering report](reports/2026-10-20-generic-identity-only.md).

## Automatic minor tracker-backed typos — 2026-10-20

PR68 merged (`39e1b5fe`); production clean at tested runtime
`0cc5f3fec5ccfa97af3977b9987c46d708c2b68b`, typo switch enabled. Conservative
single-letter/adjacent-transposition acceptance requires exact tracker listing,
unique IMDb/TMDb roundtrip, matching year and no local identity conflict. Short
words, numbers, added words and larger changes remain blocked; download still
requires confirmation. Existing three reviewed bindings preserved. Local624 tests
(two Linux-only skips), seedbox607 and both CI versions pass. Read-only live Bruce
verification independently passed the general typo path. Local/public health200,
actor/collector active NRestarts0; approvals, receipts and protected components
unchanged. No downloads, notifications, history replay or research schedule change.
[Engineering report](reports/2026-10-20-tracker-minor-typos.md).

## Reviewed Bruce spelling correction — 2026-10-20

PR67 merged (`012af524`); production is clean at tested runtime
`3d842b1f2dfc355ba687022254d34d2c61a4236b`. Exact-source private binding repairs
Bruce Almiighty (2003) to Bruce Almighty (2003), preserving normal ID roundtrip,
context and approval safeguards. Existing two rules preserved. Local618 tests
(two skips), seedbox601 tests and both CI versions pass. Live read-only context
returns verified_tmdb; local/public health200, actor/collector active NRestarts0.
No notification replay, action backfill, ledger reset or downloads. Historical
review status remains unchanged until normal observation/report refresh.
[Engineering report](reports/2026-10-20-bruce-reviewed-context.md).

## Selected-only identity source intake — 2026-10-19

[Issue60](https://github.com/kolorifer/radarr-festival-list/issues/60) is implemented
in [PR61](https://github.com/kolorifer/radarr-festival-list/pull/61). Collector modules
are deployed at tested `23cacc8b9d1cab1cc463a3a554a1faaa1d2fcd01`; actor remains clean
at `8846f5195d4094a337726d1f7829659ecdeb8f85`, PID unchanged. Dedicated Identity shadow
intake now receives only PUSH_APPROVED/PUSH_REJECTED/PUSH_ERROR at `/v1/selected`;
source_mode selected_only rejects new broad announcements. No other notifier,
filter, action, research/digest/retry setting, binding or acquisition record changed.

577 tests pass seedbox/CI3.12/3.13; local575 pass/two Linux skips. Actual collector/
worker denials and isolated confined selected-intake/correlation/restart checks
pass. All539 retained action records were projected offline, with no newly lost
accepted class and one improved diagnostic episode quarantine. In the measured
broad cohort,111 of188 releases (59%) lacked selected-action evidence. No history
was deleted; database size grew20,480 bytes including schema/intervening activity.

The720-second natural comparison saw no new actions or accepted movie announcements.
Its temporary notifier/key were removed. Cutover followed passing functional and
security checks; **natural selected/Unknown Movie end-to-end capture is pending**.
Postflight selected rows0, new broad accepted rows0. Local/public health200,1909
movies, actor/collector active NRestarts0, timer active, outcome outbox drained.
Existing malformed metadata, pre-action failures, nonreturning actions, no-action
matches and upstream webhook loss remain explicit limits; per-filter overrides
can replace global notification routing. Four seeds/closed pilot/digest preserved.
[Report](reports/2026-10-19-selected-intake.md) ·
[Brief](reports/2026-10-19-selected-intake-brief.md).
Unrelated CODEX_TASK and supervisor queue remain untouched.

## Changed-case Telegram review digest — 2026-10-19

Explicitly approved, implemented and enabled at verified production runtime
`8846f5195d4094a337726d1f7829659ecdeb8f85` ([PR59](https://github.com/kolorifer/radarr-festival-list/pull/59)).
The actor polls complete private research reports every five minutes and sends
new/materially changed review cases through its existing Telegram chat/topic.
One initial message covering two cases was acknowledged; both versions are marked
sent, with zero uncertain deliveries and zero sends after reopening the ledger
against the unchanged report. Aberfan remains an unverified candidate; all identity
corrections still need review. No correction/download controls were introduced.

560 tests pass on seedbox and CI 3.12/3.13; local 558 pass/two Linux-only skips.
Only movie-intel restarted. Local/public health200, 1909 movies, NRestarts=0;
collector PID, protected worker/helper/collector configuration/code, bindings and
daily timer unchanged. Research budget unchanged at one case/two GETs. No task
metadata lookup, Radarr operation or download. Production stays on the tested
runtime, excluding documentation-only follow-ups and unrelated catalog updates.

Daily research cadence still governs findings; unchanged historical seeds and
unassessed announcements are excluded. Network-ambiguous Telegram sends remain
uncertain for manual inspection; only explicit 429 rejection retries. Journal
signals are not an independent alert. Latest-state polling can coalesce intermediate
changes. [Engineering report](reports/2026-10-19-identity-digest.md) ·
[Approved brief](reports/2026-10-19-identity-digest-brief.md).
The unrelated active CODEX_TASK remains untouched. This entry supersedes earlier
statements that the digest is pending product approval.

## Automatic identity investigations — 2026-10-19

Issue57's approved automatic pipeline is deployed at verified runtime
`4c55f2a29314fa18c5131c4199aa9bf53966bd35` ([PR58](https://github.com/kolorifer/radarr-festival-list/pull/58)).
PR54 merged as `e11469988d867ce3edde449c0f81c639ce2f49bb` after fresh gates.
Bounded actor metadata retries are active. The confined daily eligibility/research
scan is enabled: 5 new/materially changed case versions and 25 TMDb GETs per rolling
week, max 5 GETs per version. Retry traffic separately caps at 10 extra GETs/week,
max 5 per provider and 3 attempts per unchanged source version in 24 hours.
No identification correction, acquisition, digest or review control is automatic.

Aberfan's natural 10:24:47 event was received after the observer's 09:27:40 start,
strongly correlated and initially quarantined. Its exact listing had no IMDb
field; typed absence is now distinct from malformed ID. One authorized
metadata-only revalidation entered the live eligible queue without replaying its
notification. Research used 2 GETs and found the unverified search candidate
TMDb 1796471, *Aberfan: The Village That Fought Back*, dated 2026-10-19. Details,
source crosswalk and media type still require review. Research punctuation
handling was corrected; the existing response was surfaced without rerunning
unchanged evidence or resetting budgets.

Live readback: 576 source releases / 571 unassessed; 6 outcome events (5 natural,
1 metadata revalidation), 5 strongly correlated cases: 3 verified, 1 researched
eligible, 1 quarantine (*2018 Everyone Is A Hero*, listing_id_invalid). Current
research ledger: 1 case, 2 GETs, 1 review result, no unknown requests; unchanged
rescans spend zero GETs and report zero changes. Live retry recoveries: 0; tested
synthetically. The historical pilot remains closed at 19 GETs with all four
seed proposals/table hashes unchanged. No actor/collector health or storage
failure after successful deployment; local/public actor health 200, 1909 movies.

Final runtime: 546 tests pass seedbox/CI 3.12/3.13; local 544 pass and 2 Linux-only
skips. Actual Landlock/seccomp proofs pass. A failed local handoff exercised the
code/config rollback successfully; diagnostics and a strict three-attempt local
handoff limit were added without relaxing either boundary. Final report-only
update kept the actor PID unchanged. Timer is active; first unattended tick is
pending (latest deadline 12:01:11 CEST, within the daily noon plus 15-minute jitter).

Private changed-case reports are generated automatically. A proposed Telegram
digest example is in the [engineering report](reports/2026-10-19-identity-automation.md);
it still requires product sign-off. Source publisher/pre-persistence coverage
gaps remain; no all-announcement guarantee. Apollo/18½ and other conflicting
identities remain separate reviewed corrections. [Approved brief](reports/2026-10-19-identity-automation-brief.md).
The unrelated active CODEX_TASK assignment is untouched. Earlier sections below
are retained historical states, superseded by this entry where they differ.

## Passive identity eligibility — 2026-10-19

PR52 merged as `fba7a0767cc94c5f77613880d893c82502bf567b`; issue51 closed.
[PR54](https://github.com/kolorifer/radarr-festival-list/pull/54) separately implements
issue53 and remains unmerged. Tested `28d65ed5a6ec26825386b9be1bb7d52a27c2acef`
is deployed to movie-intel and the five-module collector, with passive outcome
observation/selection enabled. Collector confinement and notifier/filter rows are
unchanged; actor public/local health200, reviewed bindings preserved.510 tests:
all pass seedbox/CI3.12/3.13; local508 pass/two Linux-only skips.

Research worker remains `2de1ba8`, disabled/token empty; all pilot tables unchanged,
ledger closed at19 GETs, zero new research requests. No schedule/correction/action.
Final 270.9-second readback:566 source releases,116 live accepted announcements, zero fresh
outcomes/eligible admissions, four existing unresolved seeds. These releases are
unassessed, not 565 failures or successes. Natural live positive correlation is
still pending; isolated integration tests pass. Committed observer messages retry,
but pre-persistence crash loss and incomplete publisher coverage remain explicit.
A weekly cap of5 changed/new cases and25 GETs is proposed only, not activated.
[Report](reports/2026-10-19-identity-selection.md) ·
[Brief](reports/2026-10-19-identity-selection-brief.md).

Earlier sections below describe historical deployment states.

## Stage2 bounded research — 2026-10-18, finite pilot complete

[PR52](https://github.com/kolorifer/radarr-festival-list/pull/52) is ready for review,
unmerged. Tested final code2de1ba8 is installed separately **disabled**; the finite
live pilot ran at efcad3f:4 known unresolved seeds,19 successful TMDb GETs,4 private
review results,zero retries/corrections/acquisitions. Final comparison refinement
replayed those responses offline, with no additional GETs. Worker credential
removed, pilot ledger closed, no scheduler.2 promising proposals (Fragmentos and
Steve Howe),Syd Barrett target unresolved,Rainbow edition still contradictory.
Three additional chronological examples were already verified and excluded;
no further genuinely unresolved cohort demonstrated. Manual manifest admission,
off/lossy outcome hook and incomplete upstream delivery remain limits.

481 tests pass on seedbox and CI3.12/3.13; local479 pass/2 Linux-only skips.
Dependency/scoring/config and actual installed Landlock/libseccomp denial gates
pass. movie-intel30adc20 and collector3a20907 remain clean/pinned, healthy and
unrestarted; observer OFF. At18:43UTC,8 live intake movies accepted,storage-warning
count remains1. Cause of the historical warning unknown; fixed reason diagnostics
are in the PR but not deployed to the collector. Runtime corrections, recurring
traffic and Stage3 review/digest require separate approval.
[Report](reports/2026-10-18-identity-research.md) ·
[Brief](reports/2026-10-18-identity-research-brief.md).

## Landlock Stage1 follow-up — 2026-10-18, shadow deployment complete

Issue49's focused feasibility and integration passes succeeded with a small stdlib
Landlock ABI6 boundary, inherited loopback listener and standard systemd syscall
filter. Actual provider child denies protected file/directory, symlink, fd, proc,
signal, metadata and new-socket access. It can commit SQLite WAL and answer HTTP;
restart/dedup/disable and forced kernel/path failure checks pass. No provider/root
change. Full local suite445 tests:444 pass,1 Linux-only skip; focused54 likewise.
CI Python3.12/3.13 and seedbox each pass445, including the kernel check; dependency,
frozen scoring and configuration checks pass. PR48 merged4740413; collector source
is pinned at tested3a2090703f9b4b85d5a3982b0e99ef452a625420 (identical merge tree).
The separately installed collector is active/healthy with actual child denial
proofs. Only an authenticated loopback RELEASE_NEW route was added; all existing
autobrr notifier/filter rows are unchanged. movie-intel checkout/process remains
clean at30adc20b7d46bbe89bb14728d778d9d1142c57c6, never restarted, observer off.
Local/public health200,1909 movies; both bindings and cache/config hashes unchanged.
Normal existing movie-intel activity later added1 action (58→59), no old action
changed and no acquisition started. No notification/approval/Radarr/download test.

Actual production observation:4 unresolved seeds;461 retained rows →450 accepted,
4 quarantined,7 excluded. Repeat454 duplicates, no new evidence/cases. Store450
releases/454 evidence versions/345 provisional unresolved cases before live events.
**3 real movie events accepted by18:06:17UTC**, max lag0.0833s; totals453 releases,
457 evidence versions/346 unresolved cases. Real publisher delivery is verified. Coverage remains
incomplete. One transient storage warning during import recovered; its counter is
retained and stable at1. Autobrr logging is disabled and no external alert worker was added.
[Report](reports/2026-10-18-landlock-shadow.md) and
[brief](reports/2026-10-18-landlock-shadow-brief.md) supersede the isolation blocker
below. Stage2 and further identity work require review; none has begun.

## Identity investigation Stage 1 — earlier 2026-10-18, deployment blocked

[Draft PR #48](https://github.com/kolorifer/radarr-festival-list/pull/48) implements
issue #47 on an isolated branch (runtime a64b948): private durable inbox,
strict release.new intake, versioned evidence/provisional cases, default-off outcome
observer, four unresolved private seeds and bounded retained reconciliation. No
Stage 2 work or additional identity repairs. [Report](reports/2026-10-18-identity-triage.md)
and [brief](reports/2026-10-18-identity-triage-brief.md) distinguish tests from live capture.

Provider isolation preflight failed: PrivateUsers denied; InaccessiblePaths alone
was silently ignored. No collector/route installed and no production changes. Live
intake is zero. Production remains clean, healthy at `30adc20` with both approved bindings.
Private retained validation:457 rows,446 accepted, 4 quarantined, 7 excluded TV;
repeat 450 duplicates without added evidence/cases; all 4 seeds unresolved. Deployment
requires a supported isolation boundary and review of the blocked safety gate.
Landlock ABI6 is available, but an alternative sandbox is not implemented/validated.
Final runtime a64b948 passes435 local tests and435 on each CI Python3.12/3.13;
44 focused Stage1 tests pass. No runtime changes follow that tested commit.

## Reviewed identity corrections — 2026-10-18, deployed and verified

[Issue #45](https://github.com/kolorifer/radarr-festival-list/issues/45) authorizes
only the reviewed Hamnet source-title/year repair and exact Not Not Jazz alias.
The implementation binds both to private exact release/IMDb/TMDb provenance,
passes corrected context through the existing external-ID checks and preserves
the original release and acquisition safeguards. No other mappings or persistent
investigation queue are included. Runtime validation/deployment results are tracked
in the [report](reports/2026-10-18-reviewed-identity.md) and
[brief](reports/2026-10-18-reviewed-identity-brief.md).

**PR #46 merged** as `cba8d79cd889311d3e27715774c2888f78641d0d`. Production is
pinned clean at tested **`30adc20b7d46bbe89bb14728d778d9d1142c57c6`**; its tree
matches the merge. Both private bindings are enabled, mode600, with existing
credentials/unrelated configuration preserved. Service active/running, NRestarts=0,
local/public health200, 1,909 movies. Private action/cache state was unchanged.

**Verified:** 391 tests pass locally and on seedbox; CI passes Python3.12/3.13;
dependency/scoring/configuration preflight passes. Live deployed GET-only cohort:
16/16 expected outcomes, 12 verified (including the two repairs and Snowman control),
four unchanged unmapped associations; four additional negative/revocation checks
pass. Only the two approved identities improved. No notification replay, test
messages/tokens, Radarr access, additions, searches or downloads. The unrelated
cleanup task remains untouched. Earlier deployment sections below are historical.

## Tracker metadata — 2026-10-18, deployed and enabled

The user's instruction to update implementation after the investigation is
implemented on `feature/tracker-metadata-identity`. Native IMDb/TMDb fields now
undergo ID-first movie/crosswalk/title/year validation; an optional, default-off
TorrentLeech adapter reads the exact listing using dedicated private cookies.
Explicit conflicts/unmapped IDs cannot fall back to title guesses or enable Grab.
New caches are bounded, expiring and isolated from legacy title lookup; existing
exact-release approval/attempt/replay guarantees remain intact.

**Merged/deployed/enabled:** PR #42 merged as `cdb8761`. Full listing verification
found a FREELEECH display badge causing five exact-heading mismatches; the narrow
markup correction merged in PR #43 (`65a695c`). Production is pinned clean at the
tested correction head **`a2049938b7c2cc77017de3920f1140c220108a5d`**. A fresh
dedicated session is stored privately with mode600 and lookup is enabled in the
running process; no runtime Prowlarr cookie dependency. Active/running,
NRestarts=0, local/public health200, 1,909 catalog movies, read-only Radarr status OK.

**Tested:** 375 tests pass locally and on seedbox; CI passes on Python3.12/3.13;
dependency/scoring/config checks pass. Full source-listing-to-TMDb comparison with
deployed code and dedicated credentials passes all 16 expected outcomes: 9/15
previous failures resolved, four unmapped IMDb associations, two review cases,
plus resolved Snowman control. Private stores were unchanged during the final
comparison. No deliberate notification replay, approval, search or download.

Private backups were taken and unrelated settings preserved. Session expiry,
unmapped/conflicting identities and HTML/rate/busy failures remain safe limits.
The unrelated CODEX_TASK.md cleanup assignment remains untouched.
[Deployment report](reports/2026-10-18-tracker-metadata-deployment.md) ·
[Deployment brief](reports/2026-10-18-tracker-metadata-deployment-brief.md) ·
[Implementation report](reports/2026-10-18-tracker-metadata-implementation.md) ·
[Completed brief](reports/2026-10-18-tracker-metadata-implementation-brief.md).

## Tracker metadata investigation — 2026-10-18, proposal only

Investigated current main a7c2e13 and deployed dcae919; no identity-resolution
implementation or deployment. Running autobrr matches the official v1.88.0 binary.
TorrentLeech listings supply IMDb IDs that the current IRC parser does not collect;
autobrr can forward populated meta_imdb/meta_tmdb, but movie-intel ignores them.
Across 15 currently unresolved sampled title/year pairs, all 15 listings carry
valid IMDb movie IDs and 11 map uniquely to TMDb with matching IMDb round trips.
Ten have corroborating title/year context; malformed Hamnet still requires review.
Four lack TMDb mappings, including Fragmentos: IMDb identifies Alejandro Rangel's
2025 film, while candidate TMDb 1356955 lacks the required IMDb cross-link.
Recommend ID validation plus a bounded exact-listing metadata adapter, subject to
product review. No new policy is adopted. The report distinguishes historical
payload inference from direct observation and documents the cleaned-up CLI probe
exception. Production remains clean at dcae919, active and healthy.
[Investigation report](reports/2026-10-18-tracker-metadata-investigation.md) ·
[Assigned brief](reports/2026-10-18-tracker-metadata-investigation-brief.md).
The unrelated CODEX_TASK.md assignment remains untouched.

## Notification reliability — 2026-10-18

Implemented, deployed and technically verified end to end at runtime commit
dcae919 (draft PR #41). Local/seedbox suites: 335 tests pass; CI passes on 3.12/3.13.
Local/public health 200; active/running, NRestarts=0. Approved duplicate Telegram
movie events removed; other notifications/settings preserved and temporary API
keys revoked. User-approved The Boxtrolls (2014) exact HULU 2160p PiRaTeS release
produced a Telegram photo/card/button, added with search disabled and downloaded/
imported successfully (9,064,876,594 bytes, WEBDL-2160p). Exact original reference
and grab/import identity matched; no search command observed; used-token GET/POST
return 410. Nocturne ambiguity remains safe in a read-only replay with sending
disabled. User presentation review is separate from technical completion.
See [engineering evidence](reports/2026-10-18-notification-reliability.md)
and [assigned brief](reports/2026-10-18-notification-reliability-brief.md).
The existing unrelated cleanup assignment remains untouched.

Subsystem verification above: 2026-10-18; other entries retain their own dates.
Read [decisions](DECISIONS.md),
[active task](CODEX_TASK.md) and [engineering instructions](../AGENTS.md).

## Local launcher quota compatibility — 2026-10-25

Direct local repair for the installed GitHub-to-Codex launcher, from clean
564a022 on main. The installed Codex quota probe succeeds, but the account now
reports a weekly primary window (10,080 minutes), no secondary window and 87%
remaining at diagnosis (86% at the installed verification). The old parser required primary=300 minutes and rejected that valid
telemetry, causing QUOTA_UNAVAILABLE. Authentication was not the cause.

The parser now validates the newest Codex quota snapshot and uses the lowest
remaining percentage across its reported primary/secondary windows. The <=15%
pause, five-hour observation freshness bound, expiry checks, cooldown, local
reservation, kernel locks and atomic create-only GitHub claims are retained.
Errors no longer attribute an unknown probe failure to authentication.

Scope is launcher-only. The unrelated legacy CODEX_TASK.md assignment and all
Radarr/scoring/Telegram/seedbox code and services remain unchanged. Existing issue
#86 task 1 is verified by read-only selection; no replacement task or claim reset
is part of this repair. See the [completed brief](reports/2026-10-25-launcher-quota-repair-brief.md)
and [verification report](reports/2026-10-25-launcher-quota-repair.md) for test and
local installation evidence. No remote push or production deployment is included.

## Explicit operations-only publication — 2026-10-17 (local review)

Issue #35 / supervisor task 2 corrects PR #36 locally from verified clean
580eb8e777a71f6a270950aa4e9cff76a891bb6b on automation/issue-35-worker. Exact
before/after fingerprint enforcement now applies only to explicit operations_only.
Default private tasks preserve the established exact immediately preceding
CONTINUE_FROM reconciliation contract: authorized retained-file cleanup may
change the fingerprint, but final checkout must be clean and HEAD unchanged
before artifact publication. Inputs remain immutable; private tasks never enter
code publication. Original partial-work tar/index backups remain preserved.
Prompts and protocol now distinguish these contracts. Default private failed-child
reporting is restored to CHILD_FAILED; operations-only changes still take refusal
priority with child failure separately recorded. Receipt schema remains v1.

TESTED: 138 focused / 316 full tests pass without skips in isolated Python 3.9.6;
pip check, final diff/scope and documentation link checks pass. Targeted synthetic
correction: 3 tests pass, including default private
artifact/receipt/readback success after retained-file reconciliation, operations
refusal of the same cleanup and the prior failure/backup continuation case.
OBSERVED LIVE: none. No merge/deployment,
launcher/service/schedule changes, seedbox/Radarr/media/private-inventory access,
credential access or child Git/GitHub publication. Supervisor acceptance is pending.
The unrelated legacy CODEX_TASK.md remains unchanged and was not executed; no next
task inferred. [Task-2 brief](reports/2026-10-17-private-continuation-correction-brief.md) ·
[Task-2 report](reports/2026-10-17-private-continuation-correction.md).

Task-1 evidence below is historical; its additional exact fingerprint enforcement
on default private tasks and changed private-failure precedence are superseded by
the task-2 correction above. Operations-only immutability remains unchanged.

Issue #35 / supervisor task 1 implements a strict latest-owner PUBLICATION_MODE
directive on automation/issue-35-worker from clean main 92afda3. Omission preserves
ordinary code publication. Explicit operations_only skips all parent add/commit/
push/PR handling, including earlier branch commits, without granting operational
authority. Exact before/after checkout checks run even on child failure; changed
work is refused/preserved and unchanged exact retained continuation is accepted.
Parent execution-N.json separates child exit/parsed result from delivery failure;
worker READY does not establish external deployment state. Private grants/CAS/
readback remain independent; terminal receipt schema stays v1. PR #31 claim and
retention boundaries are preserved.

TESTED: 136 focused / 314 full tests pass without skips in isolated Python 3.9.6;
pip check, final diff/scope and documentation checks pass. All operational/private
boundaries are synthetic. OBSERVED LIVE: none for this change. No merge, launcher/service/
schedule changes, live smoke, seedbox/Radarr/media/private-inventory access or
Git/GitHub publication by this child. Issue #33 deployment is complete according
to supervisor-supplied user context; it was not retried or inspected here.

EXPECTED BY DESIGN: later explicitly authorized operations-only tasks skip public
code publication. The harmless local assertion [acceptance plan](../automation/OPERATIONS_ACCEPTANCE.md)
is prepared; merge, launcher deployment and live acceptance remain supervisor
follow-up after review. Product acceptance is pending. The unrelated legacy
CODEX_TASK.md remains unchanged and was not executed; no next task inferred.
[Completed brief](reports/2026-10-17-operations-publication-brief.md) ·
[Engineering report](reports/2026-10-17-operations-publication.md) ·
[Protocol](../automation/SUPERVISOR_PROTOCOL.md).

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

## Issue 62 — staged edition annotations and alternative-download investigation

Read-only investigation found that current Radarr push/retry paths cannot guarantee preservation of an existing file. A restricted download-only helper requires the owner’s explicit credential-boundary decision. Display-only curated edition annotations and tests are staged separately, with no production changes. See [investigation and plan](reports/2026-10-19-issue62-investigation.md). PR63 rollout remains separate; integrate its fix before deploying this work.

Issue62 update: owner explicitly permits Radarr to replace the old file after confirmation of a specific alternative release. This supersedes keep-existing-file wording, but not per-release approval. Native manual grab requires a search-cache entry that autobrr pushes do not create; the remaining direct-helper credential decision is still pending. Exact annotation draft 6b3d6b8 passed all 588 seedbox tests, undeployed.
## Metadata retry budget fix (2026-10-19)

Owner-authorized Contagion investigation follow-up: zero-request budget/cooldown waits are deferred without consuming lookup attempts; temporary Telegram lookup failures are explicit. Validation/deployment tracked in [report](reports/2026-10-19-retry-budget-fix.md). No new identity correction or request budget.

PR63 completed: merge 4239e63; production actor cd4e25f96d1d5d0d6de5f953959bdb2ed10aa72a. Both CI versions passed, exact runtime passed 564 seedbox tests, public/local health200. Collector 23cacc8, research configuration and approval/delivery state preserved. Contagion remains pending with zero counted retries; no live notification/download/lookup replay. See the retry-budget report for schedule and expiry limits.

## Issue62 approved helper implementation — 2026-10-19

Owner explicitly approved restricted helper credential reuse and possible Radarr replacement after individual confirmation. PR64 now implements the helper, durable source receipts and confirmation page alongside edition annotations. PR63's `cd4e25f` runtime is the deployment baseline. Read-only qBittorrent login/category/hook checks passed; final regression, CI and isolated-runtime deployment validation are in progress. No live acquisition test is authorized. See [report](reports/2026-10-19-issue62-investigation.md) and [runbook](../deploy/ALTERNATIVE_GRAB.md).

## Issue62 deployed — 2026-10-19

PR64 merged `d0bbf10` after current-head CI passed. Production actor **`906a2cdc5c8fad2c62bb5e8ab46675ec290eb143`**, isolated on the prior `cd4e25f` runtime, enables individually confirmed exact-release Grab Anyway with explicit possible-replacement consent. The helper uses approved private existing qBittorrent credentials and fixed `radarr` category. Local suite 609 (two Linux-only skips); exact runtime seedbox 592 passed. Local/public health200, unchanged 1,909-movie catalog, collector `23cacc8` unchanged, research installation/schedule preserved, approval state unchanged, digest still two sent. No source fetch, notification replay or live download was tested. All 21 retained cutoff-bearing references passed structural validation; 13 are pure cutoff reasons. Historical messages are not backfilled. Full report: [issue62 implementation/deployment](reports/2026-10-19-issue62-investigation.md).

## Custom Format Grab Anyway gap fixed — 2026-10-19

PR65 merged `6c55c3c`; production **`5e2758405962ea23a46df079f2ca34d503b5a276`** adds the exact equal/higher existing Custom Format score reason. All original eligibility, explicit replacement and replay protections remain. CI passed; local611 (two skips), seedbox594 passed. Actual retained Masters of the Universe rejection passes the deployed rule; local/public health200, existing configuration/approval/receipt/research state preserved. No live notification or download test. [Report](reports/2026-10-19-custom-format-grab.md).

## Daily retry recovery deployed — 2026-10-20

PR66 merged `27d9814`; production **`09c3ab44767c2182fbf23b1214da74c336949fbc`** replaces weekly extra-metadata retry caps with rolling daily60 total /20 listing /40 TMDb, preserving cooldowns/auth holds, attempt history, per-case limits and review-only corrections. Five budget waits migrated once; **Toby, Contagion, Rooster Cogburn, Legend of the White Dragon and Making the Shining all naturally recovered with verified external IDs** in the next five minutes, using15 extra GETs. CI passed; local616 (two skips), exact runtime599 passed. Digest copy is clearer with unchanged delivery keys (65-case proof); sent count stayed9. Health200, configuration/research/approval/downloader state preserved. No live download or correction performed. [Report](reports/2026-10-20-daily-identity-retries.md).


## Evidence and choices replace persistent approvals — 2026-10-20

D033 supersedes D032. PR74 merged `a8d5d9a`; production actor
**`3a6c2cc9e2613a60719ba7030e5968895d14d7f2`**. The persistent Madame Bovary
approval is revoked with history preserved; persistent lookup/creation is retired.
New supported conflicting notifications offer a private evidence-and-choice page;
selection applies only to that expiring occurrence, with separate download
confirmation and source/target revalidation. Same-torrent later encounters require
fresh review. Existing generic automatic rules remain; choices never train an
exception or mark future cases resolved.

Local647 tests(two skips), seedbox runtime630/main647, both CI versions passed.
Live Madame Bovary remains `needs_review/year_conflict`, with description/NFO,
three image references and three research candidates available;1949 crosswalk
verified read-only without recording a choice. Health200; action/receipt state,
collector PID, configuration and research installation/schedule unchanged. No
notification replay or download. Historical messages are not edited/backfilled.
See [implementation/deployment report](reports/2026-10-20-occurrence-evidence-choice.md).

Owner disposition,2026-10-20: **Aberfan: The Village That Fought Back(2026) skipped**
as unwanted. Exact case now `routine/skipped_routine` in collector and report;
excluded from open review/research export, with evidence/history retained. Silent
receipt prevents a maintenance notification. No download, identity correction or
autobrr change. Health200, runtime unchanged. See the status-reconciliation report.
