# Live Movie Score v1 — Task 2, 2026-10-26

Issue #86, supervisor task 2. **Ready for research review with unresolved fresh
rating access.** This is a separate packet against Task 1 / [PR #88](https://github.com/kolorifer/radarr-festival-list/pull/88)
at `b62f00de56b2f1aa488e9f41742b86617efcec72`. The original packet remains
byte-for-byte at its original paths; fourteen baseline files are SHA-256 pinned
in [the manifest](inputs/baseline-manifest.json) and tested against that Git commit.
No production policy, dependencies, feeds, frozen catalog, service, unrelated task,
merge or deployment changed. The parent owns commit/push/PR/issue publication.

## Findings and coverage

The same 24 films remain: ten 2024 premieres, ten 2025 and four 2026 controls.
No title, IMDb ID, TMDb ID, year or stratum was replaced or corrected. Familiar
Touch retains its 2024 premiere / 2025 release distinction; A Different Man's
2023 production year is distinct from its 2024 film identity. Nina Roza remains
`tt29271639`, not the conflicting indexed ID excluded in Task 1. The pinned
identity evidence was retained, not presented as a new identity-source retrieval.

| Evidence | Task 1 | Task 2 result |
| --- | ---: | --- |
| Fresh IMDb rating/count observations | 0 | **0**; public-packet rights not established |
| Archived IMDb pairs | 22 | 22 unchanged; measurement time unknown |
| Indexed IMDb-only observations | 2 | 2 unchanged, stale/unknown origin date; not live |
| Fresh Letterboxd rating/count observations | 0 | **0**; permitted access not established |
| Archived Letterboxd pairs | 22 | 22 unchanged; measurement time unknown |
| Unavailable Letterboxd halves | 2 | 2 unchanged: Nina Roza; I See Buildings Fall Like Lightning |
| Independently reviewed award annotations | 93 | 26 additional corroborations: 25 primary-page reviews, one indexed primary |
| Components with new direct primary support | — | 11 components across ten films; no additional base points |
| New scoped coverage checks | — | 81: 19 positive, 52 scoped verified absences, eight pending, two unavailable |
| Complete current overall scores / ranks | 0 | **0 / 0**; all unsupported fields remain null |

Thus IMDb has **24 stale/unknown-date observations**, Letterboxd **22 stale and
two unavailable**. There are **zero fresh paired films**. “New review” means a
source was inspected on 2026-10-26, not that its origin response was live or its
underlying facts newly announced. Public web-reader responses may be cached.
The source-review window was 15:50:04–15:54:09 UTC; award reviews have day
precision, not fabricated request timestamps. There were no new rating
observations for which to report an exact retrieval or measurement time.

No newly obtained raw rating datasets, articles, reviews, account data or source
page bodies are published. This packet carries the expressly retained baseline
observations and derived arithmetic. Their presence in a public repository does
not establish upstream redistribution rights. Task 2 neither resolves nor
expands those rights. Integer archived counts are retained intact; upstream
rounding and platform weighting have not been independently established.

## Provider feasibility before acquisition

[Machine-readable access/rights audit](inputs/source-audit.json) records decisions,
failed URLs and distinctions between current checks and historical failures.

- **IMDb:** the [daily official export](https://developer.imdb.com/non-commercial-datasets/)
  technically contains same-row rating/count pairs. Its [reuse conditions](https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX)
  restrict use and republication; website extraction is prohibited. We did not
  acquire a new export, scrape film pages, or assume this public derived research
  packet has licensed publication rights. A licensed API was not demonstrated
  available under the no-subscription/no-account constraints.
- **Letterboxd:** [API access](https://letterboxd.com/api-beta/access/) remains
  request-only and excludes analysis/recommendation, LLM/GPT and personal uses.
  October 2026 [terms](https://letterboxd.com/legal/terms-of-use/), sections 6.8
  and 6.11, restrict export and automated acquisition absent authorization.
  [Robots rules](https://letterboxd.com/robots.txt) are separately restrictive and
  do not supply a license. The embedding-help URL failed at its support-domain
  redirect; no updated embedding permission was verified. No film-page or
  indexed-rating extraction, account access, RSS substitution or workaround.
- **ReelDB:** [current public docs](https://reeldb.io/) require an API key. They
  do not establish upstream acquisition provenance, downstream rating rights,
  numeric quotas or a usable rate contract. Task 1's unauthenticated HTTP 403
  remains a historical observation; **no new endpoint request** was made after
  this pre-acquisition check. No signup, key discovery or authenticated call.

This is a bounded feasibility review, not proof that every possible licensed
provider is unavailable. A third-party endpoint being reachable would not resolve
the missing provenance and rights. No acquisition was attempted after these
barriers. The accepted fallback is to preserve stale/unavailable observations;
freshness is not inferred from a recently crawled search result.

## Award evidence changes

All [new annotations and scoped checks](inputs/observations.json) include film
attribution, original category, winner/nominee/competition status, edition,
announcement/ceremony date where verified, source URL, review date and access
method. A null event day means only the edition year was established. Exact IDs
come from the retained identity mapping; we do not claim institution pages assert
IMDb IDs themselves. The [per-film breakdowns](breakdowns.md) show every change,
retained context, venue coverage and individual verification URL. All original
facts remain available in [Task 1 breakdowns](../breakdowns.md).

| Film(s) | Component receiving direct primary support beyond Task 1 | Source |
| --- | --- | --- |
| Anora; Babygirl | Gotham Best Feature nomination | [2024 official nominations](https://thegotham.org/press/the-gothams-announce-award-nominees-for-34th-edition/) |
| Familiar Touch; Hamnet; East of Wall; Sorry, Baby; Train Dreams | Gotham Best Feature nomination, previously archival/indexed | [2025 official nominations](https://thegotham.org/press/nominations-announced-for-35th-annual-gotham-film-awards/) |
| The Brutalist; I'm Still Here | Venice main Competition | [Venezia 81 selection](https://www.labiennale.org/en/cinema/2024/venezia-81-competition) |
| The Substance | Cannes main Competition; Spirit Best Feature nomination | [Cannes film dossier](https://www.festival-cannes.com/en/f/the-substance/), [Spirit official nominations](https://www.filmindependent.org/press-releases/film-independent-announces-nominees-for-the-40th-anniversary-2025-spirit-awards/) |

Additional primary reviews corroborate Sound of Falling's EFA film nomination,
eight film-category [Academy 2026](https://www.oscars.org/oscars/ceremonies/2026)
facts, the [NYFCC](https://www.nyfcc.com/awards/) film winners and
[NSFC 2025](https://nationalsocietyoffilmcritics.com/2026/01/03/one-battle-after-another-named-best-picture-of-2025/).
These span all four Recognition families. They are corroborations, not additive
award types: One Battle After Another's Gotham nomination cannot stack under its
already known win. All 288 Task 2 subtotals equal Task 1 for the same variant.

Anora's [LAFCA 2024](https://www.lafca.net/Years/2024.php) fact now has **indexed
primary** corroboration; direct retrieval timed out. The 2025 archive and homepage
also failed via the web reader. This does not become direct-origin verification,
and absence is not inferred from those failures. The obsolete guessed archive
paths are documented separately from the correctly discovered paths.

Published Gotham, NSFC and NYFCC category lists support only named-edition/category
checks, not whole-family completeness. Familiar Touch's later release season is
handled explicitly. NSFC runner-up Anora/Sinners, Gotham international nominees
It Was Just an Accident/Sound of Falling, Sundance's Waldo Salt screenplay award
for Sorry, Baby, and Venice Orizzonti/debut recognition for Familiar Touch stay
unscored under the preserved types. In particular, Waldo Salt is not silently
converted into a Special Jury Award or a European main-screenplay award.

The [Academy calendar](https://press.oscars.org/news/academy-and-abc-announce-show-dates-99th-and-100th-oscarsr)
and [Critics Choice event page](https://www.criticschoice.com/critics-choice-awards/)
keep the four 2026 controls' next-season checks `not_yet_announced`, without
assuming eligibility. Other untouched venues remain `source_not_checked` for
Task 2 even when Task 1 contains positive facts. Checks do not supply numerical
zeros for unknown families, missing audiences or unannounced awards.

## Fixed-snapshot arithmetic and ranking comparison

The unchanged scales are IMDb 6.0→0 / 8.5→25 and Letterboxd 3.0→0 / 4.3→25,
clamped. For each source, adjust **before** mapping/clamping:

`adjusted_rating = (n × rating + m × prior) / (n + m)`

Priors are exactly IMDb 7.25 and Letterboxd 3.65; m is exactly 0, 1,000 or 10,000
for each source. The priors are scale midpoints, not fitted population estimates.
A missing rating or actual count remains missing even if a prior exists. Platform
aggregates are weighted and voter populations differ; no posterior uncertainty
or equal effective sample quality is claimed.

Recognition is exactly European 20 + Independent 10 + US 10 + Critics 10.
The Task 1 historical component normalization, strongest-per-component
deduplication, Sundance convergence and family caps are reused without changes.
Audience 25 + 25 and Recognition 50 give maximum 100. These are research
constants, not new production policy.

[comparison.csv](comparison.csv) has 288 rows with raw ratings/counts, adjusted
ratings, source points and signed adjustments, all four Recognition contributions,
conditional subtotals, Task 1 evidence deltas and audience-rank changes.
[results.json](results.json) also contains original provenance, coverage,
component evidence and null overall scores/ranks. The
[readable comparison](breakdowns.md) gives all films side by side.

The only audience-rank subset is the same **22 paired observations from the
unchanged archival batch** used by Task 1. It is a comparison of that batch, not
a current leaderboard. It includes differing source sample sizes and cannot
establish release-time preference. Indexed IMDb-only controls cannot enter it.
No complete comparable current overall ranking is possible. Conditional observed
subtotals are not current-score lower bounds: old audience ratings can fall and
unverified recognition can rise within caps. Missing halves are never reweighted.

| Case | Audience m=0 | m=1,000 | m=10,000 | Audience ranks, same archival subset |
| --- | ---: | ---: | ---: | --- |
| Dune: Part Two | 49.000 | 48.986 | 48.858 | 1 / 1 / 1 |
| The Odyssey | 49.000 | 48.975 | 48.758 | 1 / 2 / 2 |
| Hamnet | 41.077 | 41.031 | 40.647 | 5 / 5 / 5 |
| Sinners | 36.154 | 36.147 | 36.090 | 9 / 9 / 9 |
| Train Dreams | 36.154 | 36.121 | 35.845 | 9 / 10 / 10 |
| Familiar Touch | 26.385 | 26.655 | 26.126 | 15 / 15 / 15 |
| East of Wall | 4.846 | 11.148 | 20.266 | 20 / 20 / 20 |
| Nina Roza, IMDb contribution only | 6.000 | 11.289 | 12.354 | no rank, LB missing |
| Buildings, IMDb contribution only | 9.000 | 12.226 | 12.471 | no rank, LB missing |

Concrete effects:

- Smoothing separates Dune/Odyssey and Sinners/Train Dreams raw ties because their
  rating/count pairs differ. Exactly two rank labels change under either positive
  strength; the other twenty remain stable. This is tie separation, not two
  observed overtakes. **All same-scenario ranks are unchanged from Task 1.**
- East of Wall's 1,218 IMDb and 6,745 Letterboxd votes give signed Audience changes
  **+6.302 / +15.419**. Both raw ratings are below the priors. This approach can
  raise scores substantially; it is not a universal confidence penalty. Despite
  that large change, it does not cross another film in this particular subset.
- Familiar Touch has only 1,635 IMDb / 8,637 LB votes. Opposing source adjustments
  give +0.270 at 1,000 and −0.259 at 10,000; the aggregate need not be monotone.
- The Substance gains a small +0.001 / +0.008 net Audience adjustment. Emilia
  Pérez and Babygirl remain tied at zero Audience: their adjusted ratings remain
  below the quality floors at these strengths. A raised rating can still yield
  no points because clamping occurs after adjustment.
- The paired-subset minimum / median / maximum is 0 / 32.692 / 49.000 at m=0,
  0 / 32.680 / 48.986 at 1,000, and 0 / 32.544 / 48.858 at 10,000. Its mean rises
  30.451→30.755→31.105, largely reflecting low-count upward shrinkage. Distribution
  arithmetic does not validate taste or the prior constants.

The Task 1→2 **evidence effect is zero numeric points** for all three strengths
and all four extension variants. This is distinct from the nonzero within-Task-2
**smoothing effect** above. An extra day of source review did not establish a new
rating measurement or a new scored award. It improved provenance and scoped
coverage; claiming new live rankings would conceal the access limitation.

## Hamnet and separate candidate awards

Hamnet remains `tt14905854` / TMDb 858024 with archived IMDb 7.8/138,621 and
Letterboxd 4.2/1,749,286. Its Gotham nomination now has a direct institution URL,
and its Academy Picture nomination is corroborated again. Base Recognition is
unchanged at **5 Europe + 1 Independent + 9 US + 0.8 Critics = 15.8**. Conditional
base subtotals are 56.877 / 56.831 / 56.447 across the three strengths. There is
no complete current score or overall rank. Task 1's curated score 1 remains an
IMDb list-membership counter; no feed repair or award inference is made.

TIFF main People's Choice +4 Independent and uniquely attributed Cannes/Berlin/
Venice main-Competition screenplay +6 Europe remain **off in base**. Four
sensitivity combinations are retained for each strength, inside the existing
family caps, at most one bonus of each kind per film. Their original Task 1
evidence/dates are retained, not relabeled as Task 2 verifications.

| Film | Optional effect on observed Recognition |
| --- | --- |
| Hamnet | TIFF only: 15.8→19.8; m=1,000 conditional subtotal 60.831 |
| The Substance | Screenplay only: 14.7→20.7 |
| I'm Still Here | Screenplay only: 15.0→21.0 |
| Nina Roza | Screenplay only: 2.0→8.0; LB and overall score remain missing |

Other cohort films receive no candidate bonus in this packet. Nominations, side
sections, TIFF runners-up/international/documentary/Midnight Madness awards and
mere festival-list inclusion do not enable an extension. No new stacking or
weight policy was chosen.

## Reproduction, verification and remaining decisions

From the repository root, Python 3.9+ and the standard library suffice:

```sh
python3 simulations/live-score-v1/task2/compare.py
python3 simulations/live-score-v1/task2/compare.py --check
python3 -m unittest discover -s simulations/live-score-v1/task2 -p 'test_*.py' -v
python3 -m unittest discover -s simulations/live-score-v1 -p 'test_*.py' -v
```

These utilities do not acquire data or invoke production code. Git is used only
by provenance tests to compare local pinned objects. All source evidence is fixed
in inputs; offline scoring does not need Git or network. The containing
[engineering report](../../../docs/reports/2026-10-26-live-score-v1-task2.md)
records actual checks and environmental limits. The original Task 1 packet is
verified, not regenerated or republished as a new measurement.

For review, retain the 1,000-vote scenario as the more restrained candidate:
it preserves the same high-count order while raising East of Wall much less than
10,000. **Task 2 adds no fresh audience evidence to validate that preference.**
No strength or prior is finalized. Keep both new award signals separate until
the owner/ChatGPT decides their scope.

Concrete remaining product decisions:

1. Given East of Wall's +6.302 versus +15.419, which strength should be the next
   review candidate? Is calibration selection deferred until a lawful fresh
   paired sample exists? The current comparison cannot fit source-specific priors.
2. Which rights-cleared source and publication permission can support future
   IMDb/LB paired counts? No credentials, signup or operational work is requested
   or authorized by this report.
3. Approve or reject TIFF main winner +4 and main-festival screenplay +6, and
   explicitly decide screenplay stacking/scope. The tested convention is once
   per kind/film under existing caps; no extension is approved here.
4. What should a future display say when a source is stale/unavailable or an
   award season pending? This packet withholds overall scores/ranks rather than
   inventing a coverage threshold or treating absence of evidence as zero.

Future event refresh, a 30-day success cache and Telegram enrichment remain
unauthorized context. No operational phase is inferred from this research.
