# Production qualification data

D016 is exactly `grandfathered_deployed_224 OR Evidence Score >=225`, inclusive.
No other admission gate is active. A film may have both production routes.
Legacy convergence/corroboration/canon routes are retained only as audit metadata.

- `grandfathered-224.json`: immutable identities and historical routes from
  deployed c7a458241b4a8a2acbd4d4f5a957d71e5198adc1. The exact file digest is pinned
  in the scorer. Research255 is never a grandfathered input.
- `evidence-inputs.json`: validated per-film identities, ranks, normalized
  award-family evidence, rating/vote pairs and provenance promoted from PR #5.
  Includes selected IMDb fallbacks and the PR #3 cleanup. No source is fetched
  during regeneration.
- `movie-catalog.json`: compact generated production lookup for all 1,909 films;
  scores, audience/family points, active routes, grandfather flag, historical
  routes, rating/recognition context and existing-schema watch annotations.
- `data-status.json`: five corrected identities, nine missing Letterboxd rows,
  32 unresolved award-source records and watch correction notes.
- `provenance.json`: exact source revisions/hashes and frozen acceptance counts.
- `../tests/fixtures/d016-frozen-scores.json`: all 1,909 expected score/family/rank
  values projected from the validated PR #5 snapshot. Test input only.

`production_scoring.py` owns D012 calculation and D016 qualification.
IMDb and Letterboxd are individually calibrated with the validated rating/vote
formula; their rounded component sum is weighted0.75. Audience maximum150.
TSPDT100, Sight & Sound100 (half alongside TSPDT), BBC100, NYT100,
US Institutional100, European Recognition200, Independent Cinema100 and
Critics Groups100. Broad critics remain inside the critics family, max40,
merged as strongest plus25% of weaker. Existing cutoff eligibility/canon
ceiling adjustment is preserved; it is not an admission normalization.
Effective fully eligible ceiling1000. Trakt/TMDb do not score.
D014 forbids assigning combined-work awards to components without attribution.

Run offline from the repository:

```sh
python production_scoring.py
python production_scoring.py --check
python -m unittest -v
```

Regeneration must retain all 1,909 frozen scores/family points/ranks and exactly
224 grandfathered +163 new =387 selected. Any drift fails.
A later evidence refresh needs an explicit reviewed input/fixture update; no
network collector or scheduled refresh mutates this snapshot.

The runtime reads only the production catalog and frozen224 file. Missing,
duplicate or inconsistent qualification data fails startup/preflight; it never
falls back to simulation qualifiers. Main's older research/annotation artifacts
are retained for history and are not runtime scoring inputs.

This is not a StevenLu import list. No Radarr list consumes it. Loading it,
regenerating it or starting movie-intel cannot add/search/download movies.
Public festival.json/curated.json/backcatalog.json are separate artifacts and
their IDs/order are preserved by this promotion.

Evidence history:
[PR #3](https://github.com/kolorifer/radarr-festival-list/pull/3),
[PR #4](https://github.com/kolorifer/radarr-festival-list/pull/4),
[PR #5](https://github.com/kolorifer/radarr-festival-list/pull/5).

D017's separate [sync command/timer](../deploy/RADARR_SYNC.md) consumes the
catalog for authorized monitored record additions and managed tags. It does not
issue acquisition commands. Movie-intel startup/regeneration remain read-only
with respect to Radarr.
