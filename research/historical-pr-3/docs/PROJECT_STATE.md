# Movie List project state

Last verified: 2026-10-13. Read [decisions](DECISIONS.md), [active task](CODEX_TASK.md)
and [engineering instructions](../AGENTS.md) before new work.
The user/ChatGPT own product decisions; Codex executes agreed engineering tasks.

## Stable architecture and production

Architecture/discovery/deployment context:
[stable snapshot](https://github.com/kolorifer/radarr-festival-list/blob/7e9c32f7ac5d8c9a310e69a706731a272f23c003/docs/PROJECT_STATE.md).

Fresh read-only SSH verification: production remains clean at
c7a458241b4a8a2acbd4d4f5a957d71e5198adc1. movie-intel.service is enabled,
active/running, zero restarts; local and public HTTPS health 200.
No research scoring change deployed or merged into main. Production feeds and
qualification remain fixed. This check does not retest live notification/download
integrations or resolve earlier downstream/provider privacy findings.

## Agreed research model

D012: Audience=150, proportional 0.75 × the existing calibrated IMDb + Letterboxd
sum. Effective fully eligible Evidence Score ceiling 1000. Other family weights
remain fixed: TSPDT 100, Sight & Sound 100, BBC 100, NYT 100, US Institutional 100,
European Recognition 200, Independent Cinema 100, existing Critics Groups 100.
Existing TSPDT/Sight&Sound correlation adjustment remains unchanged; Trakt/TMDb
do not contribute. No Evidence Score threshold has been agreed in this task.

Historical150/200 comparison:
[report](reports/2026-10-13-audience-caps.md),
[artifacts](../simulations/audience-cap-comparison/README.md).
Those outputs remain the historical baseline; final corrected Audience150
outputs are in the identity-integrity directory below. Legacy evidence-scores.json
is not replaced with this final research model.

## Completed integrity cleanup

Branch: research/data-identity-integrity.
Seedbox checkout: ~/radarr-festival-list-identity-integrity.
Baseline: 4d7943b6f4a2cff3b4ddc38fb8ff096747efc3bf.
Final generated data: 1451d54d67a5cb82b1a814d640866fe30a5a088d.
[Draft PR#3](https://github.com/kolorifer/radarr-festival-list/pull/3) targets research/audience-cap-calibration;
neither PR nor production changes are merged/deployed.

[Completed brief](reports/2026-10-13-identity-integrity-brief.md) ·
[Engineering report](reports/2026-10-13-identity-integrity.md) ·
[Artifact index](../simulations/data-identity-integrity/README.md) ·
[Comparison](../simulations/data-identity-integrity/comparison.md).

951 cached2000–2023 TSPDT/backcatalog rows audited out of 994 source rows;
227 flagged:222 confirmed correct, 5 corrected, 0 unresolved. False identities:
Time,Birdman,La Morte rouge,Spider,The Inheritance. Original source evidence
and ranks retained. Explicit verified mappings and metadata checks replace
fuzzy-only acceptance. Existing award evidence restored for corrected Time/Spider;
Birdman's wrongly attached Gotham award moved to its existing correct ID.

The universe still has 1,909 unique films:four false IDs removed/four correct
IDs added, correct Birdman already present, Spider-Man retained by audience
discovery. IMDb 1908 → 1909; Letterboxd/complete pairs 1896 → 1900; nine gaps remain.
All valid existing provider values preserved.15 award aliases fixed:
NSFC 4 → 0,LAFCA 2 → 1,CC 29 → 22,EFA 11 → 8,Gotham 1 → 1,NYFCC 0 → 0;32 source gaps remain.

18 retained scores and1,208 ordinal ranks change. Top 50 membership unchanged,
12 rank moves up to4 places. Top 100 has two replacements:Caché and Birdman enter;
Manchester by the Sea and Phantom Thread leave.52 common ranks move up to4.
Mean 148.32 → 148.52; median 112.75 → 112.70. All 255 qualifier IDs/routes unchanged.

86 full research-checkout tests and pip check pass through SSH and Actions.
Ten audit/scoring artifacts reproduce byte for byte; hashes and actual commands
are in [validation](../simulations/data-identity-integrity/validation.json).
Fixed scoring modules, source feeds and qualification inputs match baseline.

## Remaining limits and review

ReelDB metadata and ratings both return403 with the existing private Actions
credential. Nine Letterboxd aggregate/count gaps remain; no ratings invented.
Corrected-film ReelDB critic ratings cannot be recovered while access is denied.
Public page absence of an aggregate is not proof of global Letterboxd absence.

32 award source records remain explicit. Small Axe anthology allocation and the
combined Nymphomaniac director's cut need product/manual review. Other unresolved
titles are not safely identified within or absent from the frozen universe;
no unrelated films were added. The user/ChatGPT decide whether these limits
affect threshold calibration and assign the next brief. The active task is idle.
D013 preserves authorization for routine engineering without repeated approvals.
