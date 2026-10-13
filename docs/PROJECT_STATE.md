# Movie List project state

Last verified: 2026-10-13. Read [decisions](DECISIONS.md),
[active task](CODEX_TASK.md) and [engineering instructions](../AGENTS.md).
The user/ChatGPT decide product behavior; Codex executes agreed engineering work.

## Production and qualification baseline correction

Production remains clean at c7a458241b4a8a2acbd4d4f5a957d71e5198adc1;
movie-intel.service is active/running with zero restarts; local/public health 200.
No research score or qualification change is deployed or merged into main.

The deployed lookup and qualifier snapshot contain 224 qualified films.
The cleaned research comparator requested for calibration contains 255.
All 224 belong to 255 with identical routes; 31 additional research entries are
absent from deployment. Earlier references calling 255 production-qualified were
inaccurate. The production loader and read-only build_index() verify 224.
[Verification](../simulations/qualification-calibration/verification.json)
records exact differences. All primary calibration New/Lost/Retained labels use
the explicitly requested 255 research comparator.

Stable architecture and earlier operational/privacy findings:
[stable snapshot](https://github.com/kolorifer/radarr-festival-list/blob/7e9c32f7ac5d8c9a310e69a706731a272f23c003/docs/PROJECT_STATE.md).

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

## Fixed research model

D012: Audience=150, proportional 0.75 × existing calibrated IMDb + Letterboxd
components; effective fully eligible ceiling 1000.
TSPDT 100, Sight & Sound 100, BBC 100, NYT 100, US Institutional 100,
European Recognition 200, Independent Cinema 100, existing Critics Groups 100.
Existing canon correlation unchanged; Trakt/TMDb do not contribute.
No final qualification threshold/policy chosen.

D014: anthology/combined-work awards are not allocated to individual components
without explicit awarding-body attribution. Small Axe and combined Nymphomaniac
remain unallocated. D013 preserves routine engineering authorization.

## Completed qualification calibration

Branch: research/qualification-calibration; seedbox checkout:
~/radarr-festival-list-qualification-calibration.
Cleaned baseline: 762d6af242c84e26e2007d2a175b08c7e9c3b2a8, PR #3.
Generated calibration data: f93c21dc006686b2209ca3e3c5acbb6406376b9b.
[Draft PR #4](https://github.com/kolorifer/radarr-festival-list/pull/4) targets research/data-identity-integrity.

[Brief](reports/2026-10-13-qualification-calibration-brief.md) ·
[Engineering report](reports/2026-10-13-qualification-calibration.md) ·
[Artifact index](../simulations/qualification-calibration/README.md) ·
[Detailed summary](../simulations/qualification-calibration/summary.md).

Frozen 1,909 scores/IDs and 255 comparison qualification routes preserved.
Ten thresholds (100,125,150,175,200,225,250,300,350,400) × six policies=60 combinations:
score-only, A(existing OR score),B(>=2 families),C(>=1 family),D(Audience<=50%),
E(>=1 family and <=50% share when only one family contributes).
TSPDT/Sight&Sound count together as independent canon; raw counts remain available.
Only positive point contributions count.

Review options: A250=374 total/119 new/0 lost; A300=309/54/0;
E125=787/536/4; D200=381/199/73.
B/C/E add no filtering at >=200 in this universe; at >=300 D also matches score-only.
D200 loses 48 baseline films below threshold plus 25 additional share-guard losses,
while filtering nine new admissions. A250 has one audience-dominant new case,
Dune: Part Two; A300 has none. No final option selected.

All 13 existing positive taste signals and 33 watched annotations are already
baseline-qualified; they are diagnostic only, with no negative labels/training.
The four review options retain 13 positives. D200 loses three watched annotations.

Nine incomplete Audience rows score 0–45.74; none can reach 125 at the missing
Letterboxd ceiling. Those gaps cannot affect the shortlist under that bound.
Missing award/critic evidence is not bounded. Historical-poll eligibility varies
by year; absolute score thresholds are not renormalized.

105 full research tests pass, including 19 new policy/input regressions; pip check
passes. 19 generated artifacts and the pinned 224-record diagnostic input reproduce
byte for byte. Per-film CSV/JSON agree across 60 policies. 15 frozen input hashes
verify; configured-secret scans pass. Production remains unchanged.
Actual verification and hashes are linked above.

## Earlier completed research and remaining gaps

[Identity cleanup](reports/2026-10-13-identity-integrity.md):
951 cached TSPDT rows audited; 227 flagged; 5 corrected, 222 suspicious confirmed,
zero unresolved TSPDT identities. Final generated cleaned score data:
1451d54d67a5cb82b1a814d640866fe30a5a088d.
[PR #3](https://github.com/kolorifer/radarr-festival-list/pull/3), unmerged.

IMDb 1909/1909; Letterboxd 1900/1909. Nine Letterboxd gaps, ReelDB HTTP 403,
new corrected-film critic gaps and 32 unresolved award-source records remain.
No enrichment in the qualification task. Scores/data from PR #3 are unchanged.
[Historical150/200 comparison](reports/2026-10-13-audience-caps.md) remains historical;
legacy evidence-scores.json is not replaced with the finalized research model.

The user/ChatGPT review candidate lists, losses, dominance and recent-film coverage,
resolve the 255/224 adoption distinction and choose a future policy/threshold.
No next implementation task is selected; the active task is idle.
