# Implement and deploy D016 production qualification

Status: In progress. Authorized user brief, 2026-10-14.

Objective: make Movie List/movie-intel qualification authoritative under
`grandfathered_deployed_224 OR Evidence Score >=225`, inclusive.

Start from current main/deployed lineage. Promote only production requirements
from cleaned PR #3 and validated PR #5; keep research PRs/artifacts as audit history.
D016 is recorded at research/p225-vs-p250 906ff64; validated frozen handoff is 9c5a0f0.
Grandfather exact IMDb IDs and historical routes from deployed c7a4582 only.
The research255/31 additions are diagnostic and confer no admission.

D012 remains fixed: IMDb+Letterboxd Audience max150, fully eligible ceiling1000;
TSPDT100, Sight & Sound100 with existing canon correlation, BBC100, NYT100,
US Institutional100, European Recognition200, Independent Cinema100,
Critics Groups100. Trakt/TMDb do not score. D014 anthology attribution unchanged.
No share/family/age guards, normalization, new exceptions or 250 logic.

Active routes: grandfathered_production and evidence_score_225, both when applicable.
Legacy convergence/corroboration/canon are historical metadata only.
Replace movie_intel's simulation dependency with a production artifact/API exposing
identities, scores, family contributions, qualification, routes and grandfather status.
Keep enriched Telegram and tested approval->Radarr exact release flow working.

Correct selected-to-watch annotations for La Cienaga, Uncle Boonmee and Elephant:
not watched; use existing unknown state. No scoring or qualification effect.

Acceptance/validation:
- Frozen 1,909 identities/scores/family points/ranks unchanged from PR #5.
- Exactly224 grandfathered,163 new,387 selected; all224 retained once, no duplicates.
- Explicit below225 grandfather, score-only newcomer, both-routes, unqualified,
  retired research-only route, Sound of Metal/Coco/Salesman and >=250 regressions.
- Five cleaned TSPDT identities intact;9 missing Letterboxd and32 award gaps explicit.
- Complete unit/local HTTP integration suite, pip check, deterministic regeneration,
  exact baseline comparison, privacy scan and config preflight.
- Existing live Telegram/add-grab report preserved; no real test download.
- Read-only Radarr list inspection before activation; stop if new qualification
  would automatically add the163 films.

Production authorization: implementation, PR, merge after green CI if allowed,
backup/record old revision, deploy to existing seedbox checkout, restart only
movie-intel, verify service/local+public health200 and no restart loop; read-only
representative lookups and integration/config verification.
No bulk adds/searches/downloads/import-list refresh. Preserve StevenLu/IMDb feeds.

Handoff: decisions implemented status, current project/deployment state, idle task,
archived brief and engineering report with branch/PR/commits/tests/387 counts,
watch corrections, examples, service health, unchanged acquisition and rollback.
