# Live Movie Score v1 calibration — 2026-10-25

Issue #86 / supervisor task 1. Research for product review; no production policy,
collector, service, dependency, feed, catalog, qualification or deployment change.
Repository base: `cc11595` on `automation/issue-86-worker`. Publication belongs
to the runner. The unrelated Radarr cleanup assignment remains untouched.

## Result and limits

The experiment contains **24 exact-ID films: 10 from 2024, 10 from 2025 and four
from 2026**, with twelve variants per film. It preserves IMDb 25 + Letterboxd 25
and European 20 + Independent 10 + US 10 + Critics 10. It is a reproducible comparison
of pinned observations, **not a measurement of today's complete live scores**.

| Evidence | Films | Freshness / limitation |
| --- | ---: | --- |
| IMDb rating and count, existing archived ReelDB rows | 22 | Present by pinned 2026-10-14 commit; original measurement timestamps absent |
| IMDb rating and count, targeted public index observations | 2 | Reviewed 2026-10-25; underlying measurement timestamps unknown |
| Letterboxd rating and count, existing archived ReelDB rows | 22 | Same archive; no fresh Letterboxd retrieval |
| Letterboxd unavailable | 2 | Nina Roza; I See Buildings Fall Like Lightning |
| Independently reviewed award facts | 93 facts | Primary web evidence, with cached/indexed exceptions explicitly tagged |
| Scoped award checks | 68 checks | 37 positive, 23 verified absences in named categories/editions, eight pending-season checks |
| Complete, current overall scores | **0** | No film has a certified complete award history and fresh paired audience observations |

Awards are positive evidence, not proof that every other award is absent. The
machine output keeps `overall_score=null`, and never assigns overall ranks.
An observed 0 is a subtotal contribution, not a measured absence. Each family's
`recognition_family_scores` stays null unless its observed evidence already
reaches the cap (where additional positive evidence cannot change its points). A missing half
is `null`, never substituted by zero or filled by doubling IMDb. The two partial
audience rows cannot be ranked against the paired rows.

Even the numeric subtotals are **conditional on the pinned ratings**, rather
than lower bounds on current scores: an archived rating can fall. Unknown awards
can add recognition within its caps. These are separate uncertainties. Six
decimal places in JSON/CSV describe arithmetic reproducibility, not empirical
accuracy; readable tables round to one decimal.

## Reproduce and inspect

From the repository root, Python 3.9+ and the standard library suffice for this
experiment:

```sh
python3 simulations/live-score-v1/calibrate.py
python3 simulations/live-score-v1/calibrate.py --check
python3 -m unittest discover -s simulations/live-score-v1 -p 'test_*.py' -v
```

These commands make **no network requests**. Tests also read the locally present
pinned Git objects to verify the archive slices; scoring needs only the JSON
inputs. No production module is imported.

- [Film breakdowns](breakdowns.md): identities, dates, rating/count pairs, all
  source links, original award labels, component points, coverage and twelve
  variants per film.
- [Machine results](results.json): complete arithmetic, signed sample
  adjustments, provenance, per-institution coverage and input SHA-256 hashes.
- [Flat comparison](comparison.csv): 288 film/variant rows, with explicit
  incomplete status and blank overall-score column.
- [Historical awards](inputs/historical-awards.json) and
  [ratings](inputs/historical-ratings.json): inspectable selected original rows.
- [New observations](inputs/observations.json): dated facts, exclusions,
  pending/absence checks and candidate extensions.
- [Identities](inputs/identities.json) and [cohort](inputs/cohort-seed.json):
  fixed selection and public identity corroboration.
- [Historical manifest](inputs/historical-manifest.json): full-file hashes and
  exact repository URLs for the calibration inputs and original award policy.

## Cohort and identity protocol

Selection is purposive calibration, not a representative sample or an estimate
of population preferences. The fixed manifest is the reproducible selection:
ten mature 2024 films span festival winners, high-rated broad releases, animation,
low audience ratings and small independent audiences; ten 2025 films include all
required titles, missing-award cases, broad successes and smaller releases. Four
2026 controls contrast broad/high-count releases with two sparse festival
observations and an unfinished annual awards season. No score threshold was used
for admission. This design intentionally overrepresents useful edge cases.

All IMDb IDs and TMDb IDs were joined on the same public Wikidata entity
(`P345`/`P4947`, CC0), then the corresponding public TMDb title/year and release
events were inspected. Exact mapping query, observed metadata, URLs and page
digests are pinned. No authenticated TMDb API, title-only automatic match or
private identity state was used. This is public metadata corroboration, not a
fresh IMDb dataset audit of all identities.

The cohort table in [breakdowns.md](breakdowns.md) lists every pair. Notable
reconciliations:

- **Familiar Touch:** 2024 premiere; TMDb displays 2025 and a 2025-06-20 release
  event. It remains in the 2024 premiere stratum; its later release explains
  the 2025 Gotham / 2026 Spirit context. Its 2024 Venice Orizzonti prizes do not
  become main-Competition awards. [Venice archive](https://www.labiennale.org/en/news/official-awards-81st-venice-international-film-festival)
- **A Different Man:** the Berlinale dossier uses production year 2023, while
  the selected IMDb-keyed archive and TMDb use 2024. The director/cast/title and
  exact ID mapping agree; the production year is not a different film.
  [Official dossier](https://www.berlinale.de/media/download/presse/dossier/pressedossier-2024.pdf)
- **Nina Roza:** use `tt29271639` / TMDb1527449. Exclude the conflicting indexed
  `tt29893755` result despite similar title/cast text. Mapping is pinned from
  [Wikidata Q137832534](https://www.wikidata.org/entity/Q137832534) and the
  [matching TMDb page](https://www.themoviedb.org/movie/1527449?language=en-US).
  Local release dates vary; the 2026 film has already played festivals.
- **I See Buildings Fall Like Lightning:** `tt38991615` / TMDb1455247, a verified
  2026 Directors' Fortnight world premiere. TMDb's 2026-12-04 release event does
  not imply it was unreleased everywhere on the research date.
  [British Council](https://filmsandfestivals.britishcouncil.org/projects/i-see-buildings-fall-like-lightning)

The sparse IMDb observations are 6.6/229 for Nina Roza and 6.9/85 for Buildings.
The former index reported a crawl that day; the latter reported last month.
Different Nina Roza locales show different count/rating pairs. We retain one
intact, exact-ID observation rather than blending dates or treating rounded K/M
counts as exact. Neither is claimed as a fresh live count.
[Nina Roza ratings](https://www.imdb.com/title/tt29271639/ratings/),
[Buildings title](https://www.imdb.com/title/tt38991615/)

## Audience arithmetic and confidence sensitivity

For either source, quality points are
`25 × clamp((rating − floor)/(full − floor), 0, 1)`. IMDb uses 6.0→8.5;
Letterboxd uses 3.0→4.3. These are the agreed new floors, not D012's IMDb floor.

We smooth the **rating before clamping**:

`adjusted = (n × observed_rating + m × prior_mean) / (n + m)`.

| Experiment | IMDb prior mean / equivalent votes | Letterboxd prior mean / equivalent votes |
| --- | --- | --- |
| unsmoothed | 7.25 / 0 | 3.65 / 0 |
| modest | 7.25 / 1,000 | 3.65 / 1,000 |
| stronger | 7.25 / 10,000 | 3.65 / 10,000 |

The midpoint priors give 12.5/25 points each. They express a neutral midpoint of
the chosen quality scales, not a measured population mean or a fitted prior.
Equal equivalent counts across providers are an experimental convenience, not
evidence that their voter populations or weighting algorithms are equivalent.
These are pseudo-count shrinkage scenarios; weighted platform aggregates and
correlated voters do not support an exact Bayesian posterior or credible interval.
There is no final confidence constant and no production implementation.

| Case | Unsmoothed audience | Modest | Stronger | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Hamnet | 41.1 | 41.0 | 40.6 | Large counts, little change |
| East of Wall | 4.8 | 11.1 | 20.3 | Shrinkage **raises** a below-prior rating |
| Familiar Touch | 26.4 | 26.7 | 26.1 | Opposing per-source adjustments; effect need not be monotone |
| Nina Roza, IMDb half only | 6.0 | 11.3 | 12.4 | Missing LB remains unknown |
| Buildings, IMDb half only | 9.0 | 12.2 | 12.5 | Sparse indexed sample approaches neutral prior |

East of Wall's archived IMDb count is 1,218, versus 6,745 at Letterboxd; the
signed Audience changes are +6.3 / +15.4 points. A neutral prior is therefore
not a universal low-sample penalty. A product requirement that confidence must
only reduce points would require a different, explicitly agreed rule.

For the **22 paired rows in the same archived batch**, audience-only minimum /
median / maximum are 0.0 / 32.7 / 49.0 unsmoothed, 0.0 / 32.7 / 49.0 modest,
and 0.0 / 32.5 / 48.9 stronger. Most high-count audience ordering is stable:
Dune: Part Two and The Odyssey tie first unsmoothed; shrinkage breaks that tie
in Dune's favor. Sinners and Train Dreams also separate from an unsmoothed tie.
There is no claim of taste validation from that stability. Only these
audience-only ranks appear in machine diagnostics; counts/freshness still limit
interpretation. Overall rankings across heterogeneous award coverage are withheld.

## Recognition provenance and snapshot gaps

The exact calibration source is
[`sources/evidence-families.json` at 9c5a0f0](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json).
Original `family_scores`, `family_evidence`, `award_family_policy` and
`extra_award_sources` are preserved in the selected slice. Tests reproduce every
selected original normalized family score before considering any new evidence.
Awards inherited without independent rechecking are tagged `archived_secondary`.
They retain the frozen citation; they are not mislabeled as new verification.

The normalized 0–100 components come from the pinned
[`evidence_sources.py`](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/evidence_sources.py)
and [`evidence_sources_extra.py`](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/evidence_sources_extra.py),
then Europe is multiplied by 0.2 and the other families by 0.1. Each normalized
family caps at 100. JSON and code enumerate every underlying type and value.
Examples: Academy Picture 100/65; Academy International 70/35; Globes Picture 25/10;
BAFTA Film 50/25; EFA Film 40/12; Cannes Palme 70/10, Grand Prix 55, Jury 40,
Director 30; Spirit Feature 50/20; Gotham 35/10; NSFC/NYFCC/LAFCA Film 35;
Critics Choice Picture 25/8. Historical Sundance 60 jury / 30 audience / 10
convergence is preserved, including the category-insensitive audience type.

Winner and nomination of the **same component** take the strongest value once;
repeat sources corroborate rather than add points. Main festival competition is
labeled `competition`, not a win, and retains the historical 10 normalized points.
Distinct historical types remain additive: competition 10 + Cannes Grand Prix 55
is 65, not a new winner/nominee double count. No anthology attribution is invented.
Acting, technical, international Gotham/Spirit and secondary festival categories
outside the historical types remain unscored. Metacritic/Rotten Tomatoes and
historical canon/qualification logic are not introduced into this experiment.

| Film | Frozen recognition projected to /50 | With verified facts, no candidate bonuses | Main documented gap |
| --- | ---: | ---: | --- |
| Hamnet | 15.8 | 15.8 | Existing standard film-award facts already present |
| Sentimental Value | 8.8 | 30.8 | Cannes Grand Prix/competition, Academy and Globes, BAFTA |
| It Was Just an Accident | 2.4 | 24.4 | Palme, Academy/Globes, BAFTA |
| Sirāt | 2.4 | 19.4 | Cannes joint Jury/competition, Academy/Globes, BAFTA |
| Sound of Falling | 2.4 | 12.4 | Cannes joint Jury/competition |
| Emilia Pérez | 8.8 | 30.8 | Cannes, Academy/Globes and BAFTA |
| Flow | 10.0 | 12.4 | Explicit EFA European Film nomination |
| East of Wall | 1.0 | 5.0 | Sundance NEXT audience + Spirit first-feature nomination |
| Sorry, Baby | 1.0 | 3.0 | Spirit feature nomination |

These are **evidence additions**, not new weighting policy. They can alter the
relative positions of the observed subtotals far more than modest confidence
adjustments. For example, Sentimental Value's known recognition increases by 22
points. A low audience result still coexists with high Recognition for Emilia
Pérez, as the agreed 50/50 design permits. There is no admission threshold here.

Individual fresh award facts link to their verification pages in the generated
breakdowns. Important source groups:

- [Cannes 2024](https://www.festival-cannes.com/en/press/press-releases/the-77th-festival-de-cannes-winners-list/)
  and [2025 retrospective](https://www.festival-cannes.com/en/retrospective/2025/awards/)
  distinguish Palme, Grand Prix, joint Jury and screenplay. The first attempted
  2025 press URL returned 403; the public retrospective/index evidence was used
  without attempting press authentication.
- [Academy 2025](https://www.oscars.org/oscars/ceremonies/2025),
  [Academy 2026](https://www.oscars.org/oscars/ceremonies/2026),
  [Globes 2025](https://goldenglobes.com/nominations/2025/),
  [Globes 2026](https://goldenglobes.com/nominations/2026/),
  [BAFTA 2025](https://www.bafta.org/awards/film/?award-year=2025) and
  [BAFTA 2026](https://www.bafta.org/awards/film/?award-year=2026) support named
  film categories; an acting win is not a film-category win.
- [EFA Sentimental Value](https://www.europeanfilmawards.eu/efa-movie/sentimental-value/)
  identifies its European Film award as 2026, despite the film's 2025 premiere;
  [Flow](https://www.europeanfilmawards.eu/efa-movie/flow/) explicitly separates
  European Film nomination from Animated Feature win.
- [Gotham 2024](https://thegotham.org/press/34th-gothams-winners/),
  [Gotham 2025](https://thegotham.org/press/winners-2025-gotham-film-awards/),
  [institution-authored nominee list](https://letterboxd.com/thegotham/list/2025-gotham-film-awards-best-feature-nominees/detail/),
  [Spirit 2025](https://www.filmindependent.org/press-releases/film-independent-celebrates-2025-spirit-awards-winners-organizations-history-at-40th-annual-ceremony/),
  [Spirit 2026](https://www.filmindependent.org/blog/backstage-for-a-dream-night-in-hollywood-at-the-2026-film-independent-spirit-awards/)
  and [Sundance 2025](https://www.sundance.org/blogs/2025-sundance-film-festival-award-winners-announced/)
  support Independent types. Gotham's authored list is indexed evidence, not a
  Letterboxd ratings provider; no scraping integration was built.
- [NYFCC archive](https://www.nyfcc.com/awards/),
  [NSFC 2025](https://nationalsocietyoffilmcritics.com/2026/01/03/one-battle-after-another-named-best-picture-of-2025/),
  [LAFCA indexed homepage](https://www.lafca.net/) and
  [Critics Choice 2026](https://www.criticschoice.com/31st-annual-critics-choice-awards-list-of-nominees-and-winners-2026/)
  support the critics family. A direct LAFCA fetch failed; the 2025 homepage
  index corroborates its winner. Anora's LAFCA 2024 fact remains archival.

The verified-no-award checks mean only absence from **named scoring categories
at the specified ceremony**. They do not mean the film has no awards. Conversely,
the Academy's [2026-season calendar](https://press.oscars.org/news/academy-and-abc-announce-show-dates-99th-and-100th-oscarsr)
puts nominations on 2027-01-21 and the ceremony on 2027-03-14. The
[next Critics Choice ceremony](https://www.criticschoice.com/critics-choice-awards/)
is 2027-01-03. These 2026-release controls are pending, not numerical zero evidence;
eligibility or nominations for a particular film are not predicted.

## Candidate extensions, kept separate

| Signal | Base observed recognition | Candidate effect inside existing family | Attribution |
| --- | ---: | --- | --- |
| Hamnet TIFF main People's Choice | 15.8 | +4 Independent, 1→5; total 19.8 | [Producer confirmation](https://amblin.com/movie/hamnet/); [dated secondary ceremony report](https://www.rogerebert.com/festivals/chloe-zhaos-hamnet-wins-the-tiff-peoples-choice-award) |
| The Substance Cannes screenplay | 14.7 | +6 Europe, 4.4→10.4; total 20.7 | [Official Cannes 2024](https://www.festival-cannes.com/en/press/press-releases/the-77th-festival-de-cannes-winners-list/) |
| I'm Still Here Venice screenplay | 15.0 | +6 Europe, 5→11; total 21 | [Official Venice 2024](https://www.labiennale.org/en/news/official-awards-81st-venice-international-film-festival) |
| Nina Roza Berlin screenplay | 2.0 | +6 Europe, 2→8; total 8 | [Berlinale Talents 2026](https://www.berlinale-talents.de/bt/page/c/festival-returnees-2026) |

Each screenplay award explicitly identifies one film; a jointly authored script
still counts once. The experiment conservatively permits one +6 screenplay
bonus per film across Cannes/Berlin/Venice main competitions. It excludes BAFTA,
EFA, Critics Choice or Oscar screenplay awards, nominations, and side sections.
Product review must decide this scope and any multiple-festival stacking rule.
TIFF's main winner is the only TIFF type tested: international, documentary,
Midnight Madness and runners-up are not silently included. Europe still caps 20,
Independent 10, and total 100. Tests exercise cap saturation even though these
four observed candidate cases do not saturate their families.

## Hamnet audit

At the base revision, `curated-details.json` says **score 1 / IMDb Festival list**
for `tt14905854`; `curated.py` increments list membership by one. This is a
discovery-feed counter with different semantics, not evidence of an award or a
1/100 movie score. No curated file or semantic rule is changed.

The pinned pairs are IMDb 7.8/138,621 and Letterboxd 4.2/1,749,286, with unknown
original measurement times. Unsmoothed Audience is 41.1; modest is 41.0. Standard
Recognition is **5 Europe + 1 Independent + 9 US + 0.8 Critics = 15.8**:

- BAFTA Best Film nomination:25 normalized × 0.2=5.
- Gotham Best Feature nomination:10 × 0.1=1.
- Academy Best Picture nomination 65 + Golden Globe Drama win 25 = 90 × 0.1=9.
- Critics Choice Best Picture nomination 8 × 0.1=0.8.

Modest/base observed subtotal is **56.8**; TIFF-only is **60.8**. Screenplay adds
nothing for Hamnet because no verified eligible screenplay **win** is present.
Its acting wins and Outstanding British Film win are acknowledged but outside
the preserved historical film categories. Its old curated 1 therefore requires
no repair to explain the much larger separate experimental subtotal.
[Academy](https://www.oscars.org/oscars/ceremonies/2026),
[Globes](https://goldenglobes.com/film/hamnet/),
[BAFTA](https://www.bafta.org/awards/search/?award-year=2026&search=Hamnet),
[Critics Choice](https://www.criticschoice.com/31st-annual-critics-choice-awards-list-of-nominees-and-winners-2026/)

## Data-source feasibility and bounded access audit

| Source | Current check | Practical conclusion |
| --- | --- | --- |
| IMDb official export | Reviewed daily `title.ratings` schema (`tconst`, averageRating, numVotes); no new bulk download made | Appropriate technical pair source for permitted personal use; public/operational redistribution rights need resolution |
| IMDb licensed API | Official licensing path exists; no subscription, key request or paid call | Not demonstrated available under this task |
| IMDb public pages/index | Two targeted indexed observations for sparse controls | Useful research citations with unknown measurement date; not a proposed runtime scraper |
| Letterboxd official API | Reviewed current access and authentication documentation | Access by request; current guidelines exclude this analysis/recommendation/personal/GPT use; no credentials requested |
| Letterboxd public web | Reviewed terms, official embedding guidance and robots.txt; no direct film scraping | JSON-LD/embedding guidance does not establish general permission to harvest a recommendation database |
| ReelDB | Homepage HTTP 200; one no-auth GET `/v1/title/tt14905854/ratings` returned HTTP 403 | Authenticated availability, rating rights, quotas and rate limits remain unverified; no key/private configuration consulted |
| TMDb / Wikidata | Public exact-ID mapping and TMDb HTML metadata read | Sufficient for this pinned identity corroboration; not a runtime integration or proof of future availability |

IMDb's [official datasets](https://developer.imdb.com/non-commercial-datasets/)
are daily and include count/rating pairs; its [reuse conditions](https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX)
restrict use/republication and prohibit website scraping. The experiment reuses
selected **already-public repository archive rows**, not a newly redistributed
IMDb export. Archive presence does not establish a broader provider license.
No bulk export was fetched or committed under this task.

Letterboxd's [API access guidelines](https://letterboxd.com/api-beta/access/),
[API authentication documentation](https://api-docs.letterboxd.com/),
[terms](https://letterboxd.com/legal/terms-of-use/) and
[embedding guidance](https://letterboxd.zendesk.com/hc/en-us/articles/17815623056911-Can-I-display-or-embed-Letterboxd-ratings-on-my-site-or-app)
were reviewed. Account RSS/export does not supply film-wide rating counts.
There was no login, scraping, proxy workaround or attempt to evade restrictions.

[ReelDB's current public documentation](https://reeldb.io/) requires an API key
and advertises a free-key path. This worker made no signup or authenticated
request, so the observed 403 does not demonstrate what a valid account would do.
The inspected documentation did not establish a numeric quota/rate limit or
downstream rating redistribution rights. No rate limit was probed by load and
the archived `audience_ratings.py` was not executed. Archived data are expressly
not presented as a fresh successful provider check.

For future award updates, use a reviewed per-institution manifest: named category,
edition/announcement date, exact film ID mapping, source URL and observation date,
winner/nominee/competition status, plus explicit `source_not_checked`,
`unavailable`, `not_yet_announced` or scoped verified absence. Prefer official
final lists, corroborate cached/secondary evidence, retain corrections and reject
ambiguous identities/combined-work attribution. Inspect source terms and access
before considering any collector. This strategy is a proposal; no network
collector, cache, timer or background task was added.

## Proposed v1 calibration for product review

Keep the agreed 50/50 structure and linear scales. Retain the historical normalized
award types, deduplication and family caps; the detected source omissions should
be repaired in a future authorized evidence process before judging award weights.
Do not promote this mixed-age packet as a live leaderboard or alter D012/D016.

For the next review candidate, prefer the **modest 1,000-equivalent-vote scenario**
over 10,000: high-count film ordering barely changes, while the stronger prior
substantially moves small samples toward the midpoint. The 7.25/3.65 midpoint
priors make the tradeoff transparent. This is a **conditional recommendation,
not a finalized constant**: the sample cannot fit provider-specific priors or
validate cold-start behavior without lawful, fresh paired small-count data.

Keep both extensions off in the base experiment until expressly decided. TIFF
main People's Choice +4 in Independent is a clear film-level addition worth
reviewing, with the existing 10 cap. A main-competition screenplay win +6 in Europe
is comparable in size to the existing normalized 30 director win × 0.2, and the
three examples have unique film attribution. Neither observation establishes
whether those additions improve recommendation quality.

Specific decisions for the owner/ChatGPT:

1. Does “confidence adjustment” permit raising below-prior scores, as this
   Bayesian model does, or must confidence only reduce points? Review East of Wall.
2. Keep neutral midpoint priors 7.25/3.65 and test strengths 1,000/10,000 further,
   or obtain a lawful, fresh paired sample before selecting provider-specific
   means/strengths? No production constants have been selected.
3. Approve TIFF **main winner only** at +4 in Independent, subject to 10 cap? Decide
   other TIFF categories and any correlation concern with audience ratings.
4. Approve +6 for uniquely attributed Cannes/Berlin/Venice **main screenplay wins**,
   once per film, subject to 20 cap? Decide side sections and multiple-festival wins.
5. Accept historical competition points/additive distinct award types and the
   Sundance NEXT audience mapping as preserved here, or explicitly revise them?
6. Which lawful provider and usage/redistribution rights can supply both rating
   counts? Current evidence does not establish an available live Letterboxd path.
7. Should a future product display a clearly provisional subtotal when an annual
   season is pending, and what source coverage/freshness is needed for a complete
   score? No new completeness threshold or ranking gate was implemented.

Event-driven refresh, durable 30-day success cache and Telegram enrichment remain
future context only. This packet requests no operational action or access.
