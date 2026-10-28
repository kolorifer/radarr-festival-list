# Final threshold comparison: P225 vs P250

Authoritative grandfathered baseline: 224 deployed films at c7a4582. Research 255 is diagnostic only; its 31 additions are not automatically retained.
Frozen 1,909 Evidence Scores; Audience 150, ceiling 1000, weights/canon correlation and anthology attribution unchanged. Only the threshold differs. No final threshold chosen; no deployment or Radarr behavior change.

## Policy totals

| Policy | Total | Production retained | New | Audience-dominant new | Recent selected | Recent new |
| --- | --- | --- | --- | --- | --- | --- |
| P225 | 387 | 224 | 163 | 3 | 61 | 46 |
| P250 | 351 | 224 | 127 | 1 | 53 | 38 |

Recent means 2020 onward, matching previous calibration. Very recent means 2024 onward for examples only. These are diagnostics, not guards.

## Exact baseline reconciliation

| Threshold | Old A total | Old new vs 255 | P total | P new vs 224 | Naturally qualifying research31 | Removed legacy-only |
| --- | --- | --- | --- | --- | --- | --- |
| 225 | 407 | 152 | 387 | 163 | 11 | 20 |
| 250 | 374 | 119 | 351 | 127 | 8 | 23 |

- P225: total 407 - 20 = 387; new admissions 152 + 11 = 163.
- P250: total 374 - 23 = 351; new admissions 119 + 8 = 127.

Lower total and higher newcomer count can coexist: research-only legacy inclusions below the threshold disappear, while research-only films meeting the score now count as newcomers to actual production.
The old A225/A250 difference was 33; the true P225/P250 difference is 36 because Sound of Metal, Coco, The Salesman were previously grandfathered at both thresholds.

## P225-only newcomers

36 films have score 225–<250 and are not in deployed 224. Sorted by score descending, using frozen overall rank for ties.
| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hedwig and the Angry Inch | 2001 | 248.83 | 290 | 95.89 | 152.94 | 38.54 | canon+critics_groups_consensus+independent_cinema | False | False |
| District 9 | 2009 | 248.65 | 291 | 98.66 | 149.99 | 39.68 | canon+critics_groups_consensus+us_institutional | False | False |
| Hugo | 2011 | 247.27 | 292 | 66.34 | 180.93 | 26.83 | canon+critics_groups_consensus+us_institutional | False | False |
| Fahrenheit 9/11 | 2004 | 247.19 | 293 | 69.62 | 177.57 | 28.16 | canon+critics_groups_consensus+european_recognition | False | False |
| The Rider | 2017 | 246.86 | 294 | 71.71 | 175.15 | 29.05 | canon+critics_groups_consensus+independent_cinema | False | False |
| An Education | 2009 | 246.6 | 295 | 60.09 | 186.51 | 24.37 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| The Big Short | 2015 | 246.6 | 296 | 100.67 | 145.93 | 40.82 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Bacurau | 2019 | 245.87 | 298 | 75.18 | 170.69 | 30.58 | canon+critics_groups_consensus+european_recognition | False | False |
| The Florida Project | 2017 | 244.45 | 299 | 104.72 | 139.73 | 42.84 | canon+critics_groups_consensus+independent_cinema+nyt_21c | False | False |
| Happy as Lazzaro | 2018 | 243.08 | 300 | 87.97 | 155.11 | 36.19 | canon+critics_groups_consensus+european_recognition | False | False |
| Sound of Metal | 2020 | 242.93 | 301 | 114.23 | 128.7 | 47.02 | critics_groups_consensus+independent_cinema+us_institutional | False | True |
| Io Capitano | 2023 | 242.87 | 302 | 74.49 | 168.38 | 30.67 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Coco | 2017 | 241.7 | 303 | 134.72 | 106.98 | 55.74 | critics_groups_consensus+us_institutional | False | True |
| The Trial of the Chicago 7 | 2020 | 241.65 | 304 | 91.16 | 150.49 | 37.72 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Elle | 2016 | 241.3 | 305 | 61.46 | 179.84 | 25.47 | canon+critics_groups_consensus+european_recognition | False | False |
| The Salesman | 2016 | 240.81 | 306 | 88.38 | 152.43 | 36.7 | critics_groups_consensus+european_recognition+us_institutional | False | True |
| Memoria | 2021 | 240.43 | 307 | 42.54 | 197.89 | 17.69 | canon+critics_groups_consensus+european_recognition | False | False |
| Flow | 2024 | 240.4 | 308 | 112.22 | 128.18 | 46.68 | critics_groups_consensus+us_institutional | False | False |
| Devils on the Doorstep | 2000 | 240.3 | 309 | 61.44 | 178.86 | 25.57 | canon+european_recognition | False | False |
| Frost/Nixon | 2008 | 237.99 | 313 | 82.17 | 155.82 | 34.53 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Curious Case of Benjamin Button | 2008 | 237.71 | 314 | 89.14 | 148.57 | 37.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Nobody Knows | 2004 | 237.31 | 316 | 118.82 | 118.49 | 50.07 | canon+critics_groups_consensus+european_recognition | False | False |
| A Star Is Born | 2018 | 237.26 | 317 | 75.86 | 161.4 | 31.97 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Skin I Live In | 2011 | 237.18 | 318 | 87.41 | 149.77 | 36.85 | canon+critics_groups_consensus+european_recognition | False | False |
| EO | 2022 | 236.05 | 319 | 38.95 | 197.1 | 16.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Force Majeure | 2014 | 234.21 | 320 | 76.43 | 157.78 | 32.63 | canon+critics_groups_consensus+european_recognition | False | False |
| About Elly | 2009 | 233.39 | 321 | 101.56 | 131.83 | 43.52 | canon+critics_groups_consensus+european_recognition | False | False |
| The Substance | 2024 | 233.08 | 323 | 66.64 | 166.44 | 28.59 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| Borat | 2006 | 232.87 | 325 | 74.14 | 158.73 | 31.84 | canon+critics_groups_consensus+nyt_21c | False | False |
| The Reader | 2008 | 232.86 | 326 | 75.86 | 157.0 | 32.58 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| If Beale Street Could Talk | 2018 | 232.85 | 327 | 71.55 | 161.3 | 30.73 | canon+critics_groups_consensus+independent_cinema+us_institutional | False | False |
| First Reformed | 2017 | 231.46 | 328 | 78.35 | 153.11 | 33.85 | canon+critics_groups_consensus+european_recognition+independent_cinema | False | False |
| Burning | 2018 | 231.13 | 329 | 90.49 | 140.64 | 39.15 | canon+critics_groups_consensus+european_recognition | False | False |
| Sentimental Value | 2025 | 230.77 | 331 | 113.36 | 117.41 | 49.12 | critics_groups_consensus+european_recognition | False | False |
| Bad Education | 2004 | 228.49 | 333 | 88.45 | 140.04 | 38.71 | canon+critics_groups_consensus+european_recognition | False | False |
| Philomena | 2013 | 226.85 | 335 | 77.39 | 149.46 | 34.12 | critics_groups_consensus+european_recognition+us_institutional | False | False |

Full family columns, source evidence, production/research routes and watched/taste annotations are in [P225-only-vs-P250.csv](P225-only-vs-P250.csv).

### strongest by score

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hedwig and the Angry Inch | 2001 | 248.83 | 290 | 95.89 | 152.94 | 38.54 | canon+critics_groups_consensus+independent_cinema | False | False |
| District 9 | 2009 | 248.65 | 291 | 98.66 | 149.99 | 39.68 | canon+critics_groups_consensus+us_institutional | False | False |
| Hugo | 2011 | 247.27 | 292 | 66.34 | 180.93 | 26.83 | canon+critics_groups_consensus+us_institutional | False | False |
| Fahrenheit 9/11 | 2004 | 247.19 | 293 | 69.62 | 177.57 | 28.16 | canon+critics_groups_consensus+european_recognition | False | False |
| The Rider | 2017 | 246.86 | 294 | 71.71 | 175.15 | 29.05 | canon+critics_groups_consensus+independent_cinema | False | False |
| An Education | 2009 | 246.6 | 295 | 60.09 | 186.51 | 24.37 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| The Big Short | 2015 | 246.6 | 296 | 100.67 | 145.93 | 40.82 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Bacurau | 2019 | 245.87 | 298 | 75.18 | 170.69 | 30.58 | canon+critics_groups_consensus+european_recognition | False | False |

### most questionable for review high share

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Coco | 2017 | 241.7 | 303 | 134.72 | 106.98 | 55.74 | critics_groups_consensus+us_institutional | False | True |
| Nobody Knows | 2004 | 237.31 | 316 | 118.82 | 118.49 | 50.07 | canon+critics_groups_consensus+european_recognition | False | False |
| Sentimental Value | 2025 | 230.77 | 331 | 113.36 | 117.41 | 49.12 | critics_groups_consensus+european_recognition | False | False |
| Sound of Metal | 2020 | 242.93 | 301 | 114.23 | 128.7 | 47.02 | critics_groups_consensus+independent_cinema+us_institutional | False | True |
| Flow | 2024 | 240.4 | 308 | 112.22 | 128.18 | 46.68 | critics_groups_consensus+us_institutional | False | False |

### most questionable for review low modeled critic points

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Devils on the Doorstep | 2000 | 240.3 | 309 | 61.44 | 178.86 | 25.57 | canon+european_recognition | False | False |
| The Reader | 2008 | 232.86 | 326 | 75.86 | 157.0 | 32.58 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Curious Case of Benjamin Button | 2008 | 237.71 | 314 | 89.14 | 148.57 | 37.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Fahrenheit 9/11 | 2004 | 247.19 | 293 | 69.62 | 177.57 | 28.16 | canon+critics_groups_consensus+european_recognition | False | False |
| The Skin I Live In | 2011 | 237.18 | 318 | 87.41 | 149.77 | 36.85 | canon+critics_groups_consensus+european_recognition | False | False |

### festival cinephile evidence

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Memoria | 2021 | 240.43 | 307 | 42.54 | 197.89 | 17.69 | canon+critics_groups_consensus+european_recognition | False | False |
| EO | 2022 | 236.05 | 319 | 38.95 | 197.1 | 16.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| An Education | 2009 | 246.6 | 295 | 60.09 | 186.51 | 24.37 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| Elle | 2016 | 241.3 | 305 | 61.46 | 179.84 | 25.47 | canon+critics_groups_consensus+european_recognition | False | False |
| Devils on the Doorstep | 2000 | 240.3 | 309 | 61.44 | 178.86 | 25.57 | canon+european_recognition | False | False |
| Fahrenheit 9/11 | 2004 | 247.19 | 293 | 69.62 | 177.57 | 28.16 | canon+critics_groups_consensus+european_recognition | False | False |
| The Rider | 2017 | 246.86 | 294 | 71.71 | 175.15 | 29.05 | canon+critics_groups_consensus+independent_cinema | False | False |
| Bacurau | 2019 | 245.87 | 298 | 75.18 | 170.69 | 30.58 | canon+critics_groups_consensus+european_recognition | False | False |

### mainstream popular vote volume

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| District 9 | 2009 | 248.65 | 291 | 98.66 | 149.99 | 39.68 | canon+critics_groups_consensus+us_institutional | False | False |
| The Curious Case of Benjamin Button | 2008 | 237.71 | 314 | 89.14 | 148.57 | 37.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Coco | 2017 | 241.7 | 303 | 134.72 | 106.98 | 55.74 | critics_groups_consensus+us_institutional | False | True |
| The Big Short | 2015 | 246.6 | 296 | 100.67 | 145.93 | 40.82 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Borat | 2006 | 232.87 | 325 | 74.14 | 158.73 | 31.84 | canon+critics_groups_consensus+nyt_21c | False | False |
| The Substance | 2024 | 233.08 | 323 | 66.64 | 166.44 | 28.59 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| A Star Is Born | 2018 | 237.26 | 317 | 75.86 | 161.4 | 31.97 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Hugo | 2011 | 247.27 | 292 | 66.34 | 180.93 | 26.83 | canon+critics_groups_consensus+us_institutional | False | False |

### audience heavy

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Coco | 2017 | 241.7 | 303 | 134.72 | 106.98 | 55.74 | critics_groups_consensus+us_institutional | False | True |
| Nobody Knows | 2004 | 237.31 | 316 | 118.82 | 118.49 | 50.07 | canon+critics_groups_consensus+european_recognition | False | False |
| Sentimental Value | 2025 | 230.77 | 331 | 113.36 | 117.41 | 49.12 | critics_groups_consensus+european_recognition | False | False |
| Sound of Metal | 2020 | 242.93 | 301 | 114.23 | 128.7 | 47.02 | critics_groups_consensus+independent_cinema+us_institutional | False | True |
| Flow | 2024 | 240.4 | 308 | 112.22 | 128.18 | 46.68 | critics_groups_consensus+us_institutional | False | False |

### low audience strong other evidence

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Memoria | 2021 | 240.43 | 307 | 42.54 | 197.89 | 17.69 | canon+critics_groups_consensus+european_recognition | False | False |
| EO | 2022 | 236.05 | 319 | 38.95 | 197.1 | 16.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| An Education | 2009 | 246.6 | 295 | 60.09 | 186.51 | 24.37 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| Hugo | 2011 | 247.27 | 292 | 66.34 | 180.93 | 26.83 | canon+critics_groups_consensus+us_institutional | False | False |
| Elle | 2016 | 241.3 | 305 | 61.46 | 179.84 | 25.47 | canon+critics_groups_consensus+european_recognition | False | False |
| Devils on the Doorstep | 2000 | 240.3 | 309 | 61.44 | 178.86 | 25.57 | canon+european_recognition | False | False |
| Fahrenheit 9/11 | 2004 | 247.19 | 293 | 69.62 | 177.57 | 28.16 | canon+critics_groups_consensus+european_recognition | False | False |
| The Rider | 2017 | 246.86 | 294 | 71.71 | 175.15 | 29.05 | canon+critics_groups_consensus+independent_cinema | False | False |

Questionable means a discussion focus: high Audience share or low modeled Critics Groups points. It is not a negative quality label. Mainstream/popular examples use frozen IMDb vote volume, not inferred genre. Festival/cinephile examples use positive European/Independent evidence; categories overlap.

## Research-only 31: no implicit grandfathering

| Classification | Count |
| --- | --- |
| naturally_ge250 | 8 |
| naturally_ge225_lt250 | 3 |
| neither_threshold | 20 |

| Film | IMDb | Score | Rank | Original research routes | Natural225 | Natural250 | Shortfall225 | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| All Quiet on the Western Front | tt1016150 | 404.4 | 87 | corroboration | True | True | 0 | naturally_ge250 |
| Three Billboards outside Ebbing, Missouri | tt5027774 | 368.9 | 107 | convergence | True | True | 0 | naturally_ge250 |
| 1917 | tt8579674 | 343.86 | 136 | convergence | True | True | 0 | naturally_ge250 |
| Capernaum | tt8267604 | 326.06 | 155 | convergence | True | True | 0 | naturally_ge250 |
| The Father | tt10272386 | 325.29 | 156 | convergence | True | True | 0 | naturally_ge250 |
| 20 Days in Mariupol | tt24082438 | 281.63 | 218 | corroboration | True | True | 0 | naturally_ge250 |
| Wild Tales | tt3011894 | 273.33 | 227 | convergence | True | True | 0 | naturally_ge250 |
| The Help | tt1454029 | 252.16 | 283 | convergence | True | True | 0 | naturally_ge250 |
| Sound of Metal | tt5363618 | 242.93 | 301 | convergence | True | False | 0 | naturally_ge225_lt250 |
| Coco | tt2380307 | 241.7 | 303 | convergence | True | False | 0 | naturally_ge225_lt250 |
| The Salesman | tt5186714 | 240.81 | 306 | corroboration | True | False | 0 | naturally_ge225_lt250 |
| Spider-Man: Across the Spider-Verse | tt9362722 | 221.8 | 342 | convergence | False | False | 3.2 | neither_threshold |
| Ford v Ferrari | tt1950186 | 219.97 | 346 | convergence | False | False | 5.03 | neither_threshold |
| Hacksaw Ridge | tt2119532 | 216.13 | 358 | convergence | False | False | 8.87 | neither_threshold |
| Navalny | tt17041964 | 210.84 | 378 | corroboration | False | False | 14.16 | neither_threshold |
| Free Solo | tt7775622 | 210.45 | 382 | convergence | False | False | 14.55 | neither_threshold |
| Society of the Snow | tt16277242 | 206.82 | 397 | convergence | False | False | 18.18 | neither_threshold |
| Lion | tt3741834 | 205.08 | 403 | convergence | False | False | 19.92 | neither_threshold |
| Soul | tt2948372 | 204.23 | 406 | corroboration | False | False | 20.77 | neither_threshold |
| No Man's Land | tt0283509 | 192.75 | 445 | corroboration | False | False | 32.25 | neither_threshold |
| Zootopia | tt2948356 | 191.51 | 452 | corroboration | False | False | 33.49 | neither_threshold |
| Guillermo del Toro's Pinocchio | tt1488589 | 189.76 | 458 | corroboration | False | False | 35.24 | neither_threshold |
| Searching for Sugar Man | tt2125608 | 189.21 | 463 | convergence | False | False | 35.79 | neither_threshold |
| How to Train Your Dragon | tt0892769 | 185.25 | 475 | convergence | False | False | 39.75 | neither_threshold |
| Klaus | tt4729430 | 184.48 | 478 | convergence | False | False | 40.52 | neither_threshold |
| Song of the Sea | tt1865505 | 183.7 | 486 | convergence | False | False | 41.3 | neither_threshold |
| Big Hero 6 | tt2245084 | 182.59 | 488 | corroboration | False | False | 42.41 | neither_threshold |
| Icarus | tt6333060 | 170.73 | 531 | corroboration | False | False | 54.27 | neither_threshold |
| My Octopus Teacher | tt12888462 | 167.8 | 548 | corroboration | False | False | 57.2 | neither_threshold |
| The Cove | tt1313104 | 166.16 | 554 | corroboration | False | False | 58.84 | neither_threshold |
| Inside Job | tt1645089 | 132.28 | 775 | corroboration | False | False | 92.72 | neither_threshold |

The 20 below 225 are included only by the old research qualifier flag under both A policies; neither P policy admits them. Three in 225–<250 need score 225, not legacy protection. Eight >=250 qualify naturally under both.

### How each entered the research comparator

All 31 already existed as institutional seeds. The preceding generated Phase B records lacked IMDb and Letterboxd ratings and were unqualified. Cache enrichment then caused the unchanged outside-TSPDT rules to qualify them:
- Convergence: institutional strength>=1, both audience sources strong/broad, at least one exceptional.
- Corroboration: institutional strength>=2, at least one audience source strong/broad, when no other route qualified.
These are historical legacy rules, not new P225/P250 guards and not the final Evidence Score.
No Man's Land entered at 0e0c822 after cache 4aaacb7; the other 30 entered at 0c3b8f7 after cache 662de6d. Neither introduction is an ancestor of deployed c7a4582. The generator did not change in either introduction commit.

| Film | Introduction | First usable cache | Institutional seed | Strength | Historical reason |
| --- | --- | --- | --- | --- | --- |
| All Quiet on the Western Front | 0c3b8f7 | 662de6d | Academy Best Picture nominee + Academy International Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| Three Billboards outside Ebbing, Missouri | 0c3b8f7 | 662de6d | Academy Best Picture nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| 1917 | 0c3b8f7 | 662de6d | Academy Best Picture nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Capernaum | 0c3b8f7 | 662de6d | Academy International Feature Film nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| The Father | 0c3b8f7 | 662de6d | Academy Best Picture nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| 20 Days in Mariupol | 0c3b8f7 | 662de6d | Academy Documentary Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| Wild Tales | 0c3b8f7 | 662de6d | Academy International Feature Film nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| The Help | 0c3b8f7 | 662de6d | Academy Best Picture nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Sound of Metal | 0c3b8f7 | 662de6d | Academy Best Picture nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Coco | 0c3b8f7 | 662de6d | Academy Animated Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| The Salesman | 0c3b8f7 | 662de6d | Academy International Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| Spider-Man: Across the Spider-Verse | 0c3b8f7 | 662de6d | Academy Animated Feature Film nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Ford v Ferrari | 0c3b8f7 | 662de6d | Academy Best Picture nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Hacksaw Ridge | 0c3b8f7 | 662de6d | Academy Best Picture nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Navalny | 0c3b8f7 | 662de6d | Academy Documentary Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| Free Solo | 0c3b8f7 | 662de6d | Academy Documentary Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Society of the Snow | 0c3b8f7 | 662de6d | Academy International Feature Film nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Lion | 0c3b8f7 | 662de6d | Academy Best Picture nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Soul | 0c3b8f7 | 662de6d | Academy Animated Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| No Man's Land | 0e0c822 | 4aaacb7 | Academy International Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| Zootopia | 0c3b8f7 | 662de6d | Academy Animated Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| Guillermo del Toro's Pinocchio | 0c3b8f7 | 662de6d | Academy Animated Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| Searching for Sugar Man | 0c3b8f7 | 662de6d | Academy Documentary Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| How to Train Your Dragon | 0c3b8f7 | 662de6d | Academy Animated Feature Film nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Klaus | 0c3b8f7 | 662de6d | Academy Animated Feature Film nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Song of the Sea | 0c3b8f7 | 662de6d | Academy Animated Feature Film nominee | 1 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT convergence rule:institutional_strength>=1, both sources strong/broad, at least one exceptional. It was research regeneration, not Evidence Score qualification or deployment. |
| Big Hero 6 | 0c3b8f7 | 662de6d | Academy Animated Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| Icarus | 0c3b8f7 | 662de6d | Academy Documentary Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| My Octopus Teacher | 0c3b8f7 | 662de6d | Academy Documentary Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| The Cove | 0c3b8f7 | 662de6d | Academy Documentary Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |
| Inside Job | 0c3b8f7 | 662de6d | Academy Documentary Feature Film winner | 2 | Existing institutional seed; previous generated snapshot had no IMDb/Letterboxd ratings and did not qualify. Ratings enrichment then activated the unchanged Phase B outside-TSPDT corroboration rule:institutional_strength>=2 and at least one source strong/broad. It was research regeneration, not Evidence Score qualification or deployment. |

Exact first records, prior unqualified snapshots, rating/count observations, original thresholds, script/source hashes and commit provenance are frozen in [inputs/research31-history.json](inputs/research31-history.json). No values were inferred or refreshed.

## Selected and newcomer distributions

### P225

#### selected population

| Statistic | Score | Audience share% |
| --- | --- | --- |
| count | 387 | 387 |
| min | 108.67 | 4.98 |
| max | 803.78 | 83.25 |
| mean | 328.84 | 31.38 |
| p10 | 208.12 | 16.88 |
| p25 | 248.74 | 22.31 |
| p50 | 294.53 | 29.76 |
| p75 | 388.0 | 37.44 |
| p90 | 505.41 | 47.82 |
| p95 | 568.73 | 55.19 |
| p99 | 687.2 | 71.06 |

| Year | Films |
| --- | --- |
| 2000 | 23 |
| 2001 | 19 |
| 2002 | 21 |
| 2003 | 18 |
| 2004 | 20 |
| 2005 | 11 |
| 2006 | 19 |
| 2007 | 13 |
| 2008 | 18 |
| 2009 | 17 |
| 2010 | 14 |
| 2011 | 14 |
| 2012 | 13 |
| 2013 | 16 |
| 2014 | 17 |
| 2015 | 12 |
| 2016 | 12 |
| 2017 | 19 |
| 2018 | 14 |
| 2019 | 16 |
| 2020 | 9 |
| 2021 | 12 |
| 2022 | 14 |
| 2023 | 12 |
| 2024 | 7 |
| 2025 | 7 |

| Family contributing | Films | Total points |
| --- | --- | --- |
| tspdt_21c | 342 | 23905.22 |
| sight_sound | 29 | 579.84 |
| bbc_21c | 91 | 4829.0 |
| nyt_21c | 91 | 4812.0 |
| us_institutional | 224 | 15160.0 |
| european_recognition | 262 | 24544.0 |
| independent_cinema | 89 | 4210.0 |
| critics_groups_consensus | 374 | 12203.06 |
| audience | 387 | 37017.51 |

| Independent non-audience families | Films |
| --- | --- |
| 1 | 6 |
| 2 | 36 |
| 3 | 129 |
| 4 | 121 |
| 5 | 57 |
| 6 | 27 |
| 7 | 11 |

| Score band | Films |
| --- | --- |
| 0-<25 | 0 |
| 25-<50 | 0 |
| 50-<75 | 0 |
| 75-<100 | 0 |
| 100-<125 | 2 |
| 125-<150 | 6 |
| 150-<175 | 12 |
| 175-<200 | 16 |
| 200-<225 | 15 |
| 225-<250 | 48 |
| 250-<275 | 64 |
| 275-<300 | 40 |
| 300-<325 | 28 |
| 325-<350 | 27 |
| 350-<375 | 26 |
| 375-<400 | 15 |
| 400-<450 | 27 |
| 450-<500 | 20 |
| 500-<600 | 26 |
| 600-<700 | 11 |
| 700-<800 | 3 |
| 800-<900 | 1 |
| 900-<1000 | 0 |
| 1000 | 0 |

| Audience-share band | Films |
| --- | --- |
| 0-<10 | 3 |
| 10-<25 | 125 |
| 25-<50 | 226 |
| 50-<75 | 30 |
| 75-<100 | 3 |

Complete major-family composition counts and all distributions are in comparison.json. Canon is combined only for diagnostic family counts; points remain unchanged.

#### new population

| Statistic | Score | Audience share% |
| --- | --- | --- |
| count | 163 | 163 |
| min | 226.85 | 12.82 |
| max | 571.43 | 58.02 |
| mean | 295.0 | 30.13 |
| p10 | 238.45 | 18.56 |
| p25 | 252.11 | 23.18 |
| p50 | 281.1 | 29.96 |
| p75 | 322.73 | 36.22 |
| p90 | 363.72 | 41.49 |
| p95 | 402.8 | 45.03 |
| p99 | 486.81 | 52.22 |

| Year | Films |
| --- | --- |
| 2000 | 5 |
| 2001 | 4 |
| 2002 | 5 |
| 2003 | 3 |
| 2004 | 5 |
| 2005 | 5 |
| 2006 | 5 |
| 2007 | 6 |
| 2008 | 6 |
| 2009 | 4 |
| 2010 | 5 |
| 2011 | 7 |
| 2012 | 5 |
| 2013 | 5 |
| 2014 | 8 |
| 2015 | 5 |
| 2016 | 5 |
| 2017 | 10 |
| 2018 | 8 |
| 2019 | 11 |
| 2020 | 8 |
| 2021 | 6 |
| 2022 | 11 |
| 2023 | 7 |
| 2024 | 7 |
| 2025 | 7 |

| Family contributing | Films | Total points |
| --- | --- | --- |
| tspdt_21c | 122 | 6405.07 |
| sight_sound | 0 | 0.0 |
| bbc_21c | 9 | 427.0 |
| nyt_21c | 11 | 458.0 |
| us_institutional | 110 | 7250.0 |
| european_recognition | 129 | 12260.0 |
| independent_cinema | 44 | 2153.0 |
| critics_groups_consensus | 162 | 4991.19 |
| audience | 163 | 14141.47 |

| Independent non-audience families | Films |
| --- | --- |
| 2 | 5 |
| 3 | 74 |
| 4 | 68 |
| 5 | 13 |
| 6 | 3 |

| Score band | Films |
| --- | --- |
| 0-<25 | 0 |
| 25-<50 | 0 |
| 50-<75 | 0 |
| 75-<100 | 0 |
| 100-<125 | 0 |
| 125-<150 | 0 |
| 150-<175 | 0 |
| 175-<200 | 0 |
| 200-<225 | 0 |
| 225-<250 | 36 |
| 250-<275 | 42 |
| 275-<300 | 26 |
| 300-<325 | 19 |
| 325-<350 | 11 |
| 350-<375 | 17 |
| 375-<400 | 3 |
| 400-<450 | 5 |
| 450-<500 | 3 |
| 500-<600 | 1 |
| 600-<700 | 0 |
| 700-<800 | 0 |
| 800-<900 | 0 |
| 900-<1000 | 0 |
| 1000 | 0 |

| Audience-share band | Films |
| --- | --- |
| 0-<10 | 0 |
| 10-<25 | 50 |
| 25-<50 | 110 |
| 50-<75 | 3 |
| 75-<100 | 0 |

Complete major-family composition counts and all distributions are in comparison.json. Canon is combined only for diagnostic family counts; points remain unchanged.

### P250

#### selected population

| Statistic | Score | Audience share% |
| --- | --- | --- |
| count | 351 | 351 |
| min | 108.67 | 4.98 |
| max | 803.78 | 83.25 |
| mean | 338.04 | 31.0 |
| p10 | 199.6 | 16.66 |
| p25 | 259.58 | 22.03 |
| p50 | 306.68 | 29.35 |
| p75 | 401.62 | 36.89 |
| p90 | 518.45 | 47.95 |
| p95 | 574.87 | 56.19 |
| p99 | 705.93 | 72.55 |

| Year | Films |
| --- | --- |
| 2000 | 22 |
| 2001 | 18 |
| 2002 | 21 |
| 2003 | 18 |
| 2004 | 17 |
| 2005 | 11 |
| 2006 | 18 |
| 2007 | 13 |
| 2008 | 15 |
| 2009 | 14 |
| 2010 | 14 |
| 2011 | 12 |
| 2012 | 13 |
| 2013 | 15 |
| 2014 | 16 |
| 2015 | 11 |
| 2016 | 10 |
| 2017 | 15 |
| 2018 | 10 |
| 2019 | 15 |
| 2020 | 7 |
| 2021 | 11 |
| 2022 | 13 |
| 2023 | 11 |
| 2024 | 5 |
| 2025 | 6 |

| Family contributing | Films | Total points |
| --- | --- | --- |
| tspdt_21c | 319 | 22638.92 |
| sight_sound | 29 | 579.84 |
| bbc_21c | 91 | 4829.0 |
| nyt_21c | 89 | 4737.0 |
| us_institutional | 206 | 13970.0 |
| european_recognition | 236 | 22836.0 |
| independent_cinema | 81 | 3864.0 |
| critics_groups_consensus | 339 | 11197.17 |
| audience | 351 | 33999.45 |

| Independent non-audience families | Films |
| --- | --- |
| 1 | 6 |
| 2 | 32 |
| 3 | 105 |
| 4 | 113 |
| 5 | 57 |
| 6 | 27 |
| 7 | 11 |

| Score band | Films |
| --- | --- |
| 0-<25 | 0 |
| 25-<50 | 0 |
| 50-<75 | 0 |
| 75-<100 | 0 |
| 100-<125 | 2 |
| 125-<150 | 6 |
| 150-<175 | 12 |
| 175-<200 | 16 |
| 200-<225 | 15 |
| 225-<250 | 12 |
| 250-<275 | 64 |
| 275-<300 | 40 |
| 300-<325 | 28 |
| 325-<350 | 27 |
| 350-<375 | 26 |
| 375-<400 | 15 |
| 400-<450 | 27 |
| 450-<500 | 20 |
| 500-<600 | 26 |
| 600-<700 | 11 |
| 700-<800 | 3 |
| 800-<900 | 1 |
| 900-<1000 | 0 |
| 1000 | 0 |

| Audience-share band | Films |
| --- | --- |
| 0-<10 | 3 |
| 10-<25 | 122 |
| 25-<50 | 195 |
| 50-<75 | 28 |
| 75-<100 | 3 |

Complete major-family composition counts and all distributions are in comparison.json. Canon is combined only for diagnostic family counts; points remain unchanged.

#### new population

| Statistic | Score | Audience share% |
| --- | --- | --- |
| count | 127 | 127 |
| min | 250.44 | 12.82 |
| max | 571.43 | 58.02 |
| mean | 310.84 | 28.73 |
| p10 | 256.44 | 18.01 |
| p25 | 268.38 | 22.46 |
| p50 | 297.34 | 28.96 |
| p75 | 341.29 | 34.3 |
| p90 | 369.04 | 38.74 |
| p95 | 425.18 | 42.57 |
| p99 | 494.19 | 46.56 |

| Year | Films |
| --- | --- |
| 2000 | 4 |
| 2001 | 3 |
| 2002 | 5 |
| 2003 | 3 |
| 2004 | 2 |
| 2005 | 5 |
| 2006 | 4 |
| 2007 | 6 |
| 2008 | 3 |
| 2009 | 1 |
| 2010 | 5 |
| 2011 | 5 |
| 2012 | 5 |
| 2013 | 4 |
| 2014 | 7 |
| 2015 | 4 |
| 2016 | 3 |
| 2017 | 6 |
| 2018 | 4 |
| 2019 | 10 |
| 2020 | 6 |
| 2021 | 5 |
| 2022 | 10 |
| 2023 | 6 |
| 2024 | 5 |
| 2025 | 6 |

| Family contributing | Films | Total points |
| --- | --- | --- |
| tspdt_21c | 99 | 5138.77 |
| sight_sound | 0 | 0.0 |
| bbc_21c | 9 | 427.0 |
| nyt_21c | 9 | 383.0 |
| us_institutional | 92 | 6060.0 |
| european_recognition | 103 | 10552.0 |
| independent_cinema | 36 | 1807.0 |
| critics_groups_consensus | 127 | 3985.3 |
| audience | 127 | 11123.41 |

| Independent non-audience families | Films |
| --- | --- |
| 2 | 1 |
| 3 | 50 |
| 4 | 60 |
| 5 | 13 |
| 6 | 3 |

| Score band | Films |
| --- | --- |
| 0-<25 | 0 |
| 25-<50 | 0 |
| 50-<75 | 0 |
| 75-<100 | 0 |
| 100-<125 | 0 |
| 125-<150 | 0 |
| 150-<175 | 0 |
| 175-<200 | 0 |
| 200-<225 | 0 |
| 225-<250 | 0 |
| 250-<275 | 42 |
| 275-<300 | 26 |
| 300-<325 | 19 |
| 325-<350 | 11 |
| 350-<375 | 17 |
| 375-<400 | 3 |
| 400-<450 | 5 |
| 450-<500 | 3 |
| 500-<600 | 1 |
| 600-<700 | 0 |
| 700-<800 | 0 |
| 800-<900 | 0 |
| 900-<1000 | 0 |
| 1000 | 0 |

| Audience-share band | Films |
| --- | --- |
| 0-<10 | 0 |
| 10-<25 | 47 |
| 25-<50 | 79 |
| 50-<75 | 1 |
| 75-<100 | 0 |

Complete major-family composition counts and all distributions are in comparison.json. Canon is combined only for diagnostic family counts; points remain unchanged.

## Borderline analysis

Both inclusive ±15 windows are published: [225](borderline-P225.csv), [250](borderline-P250.csv). Band files use lower-inclusive/upper-exclusive boundaries:210–<225,225–<240,240–<250,250–<265.
Production films below threshold remain selected under both policies. A score band is not an exclusion list; inspect Prod224/P225/P250 flags.

### 210–<225

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wallace & Gromit: The Curse of the Were-Rabbit | 2005 | 224.91 | 337 | 89.42 | 135.49 | 39.76 | canon+critics_groups_consensus+us_institutional | False | False |
| Paddington 2 | 2017 | 224.22 | 338 | 112.22 | 112.0 | 50.05 | canon+critics_groups_consensus | True | True |
| Up in the Air | 2009 | 223.64 | 339 | 68.36 | 155.28 | 30.57 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Kids Are All Right | 2010 | 222.59 | 340 | 35.22 | 187.37 | 15.82 | canon+critics_groups_consensus+independent_cinema+us_institutional | False | False |
| Perfect Days | 2023 | 222.16 | 341 | 127.5 | 94.66 | 57.39 | canon+critics_groups_consensus+european_recognition+us_institutional | True | True |
| Spider-Man: Across the Spider-Verse | 2023 | 221.8 | 342 | 150.0 | 71.8 | 67.63 | critics_groups_consensus+us_institutional | False | True |
| Bridge of Spies | 2015 | 221.64 | 343 | 75.86 | 145.78 | 34.23 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| No Other Land | 2024 | 221.31 | 344 | 130.91 | 90.4 | 59.15 | critics_groups_consensus+us_institutional | False | False |
| The Squid and the Whale | 2005 | 221.19 | 345 | 70.06 | 151.13 | 31.67 | canon+critics_groups_consensus+independent_cinema | False | False |
| Ford v Ferrari | 2019 | 219.97 | 346 | 123.47 | 96.5 | 56.13 | critics_groups_consensus+us_institutional | False | True |
| Goodbye, Dragon Inn | 2003 | 219.95 | 347 | 59.35 | 160.6 | 26.98 | canon+critics_groups_consensus+european_recognition | True | True |
| Faces Places | 2017 | 219.69 | 348 | 82.28 | 137.41 | 37.45 | canon+critics_groups_consensus+us_institutional | True | True |
| Senna | 2010 | 219.65 | 349 | 143.63 | 76.02 | 65.39 | canon+critics_groups_consensus+independent_cinema | True | True |
| Paterson | 2016 | 218.72 | 350 | 81.7 | 137.02 | 37.35 | canon+critics_groups_consensus+european_recognition+independent_cinema | False | False |
| Once | 2006 | 218.33 | 351 | 100.67 | 117.66 | 46.11 | canon+critics_groups_consensus+independent_cinema | False | False |
| The Theory of Everything | 2014 | 217.87 | 352 | 79.61 | 138.26 | 36.54 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Wind Rises | 2013 | 217.86 | 353 | 112.22 | 105.64 | 51.51 | canon+critics_groups_consensus+us_institutional | False | False |
| Bowling for Columbine | 2002 | 217.73 | 354 | 110.19 | 107.54 | 50.61 | canon+critics_groups_consensus+european_recognition | True | True |
| Still Walking | 2008 | 217.13 | 355 | 104.54 | 112.59 | 48.15 | canon+critics_groups_consensus | False | False |
| American Hustle | 2013 | 216.38 | 356 | 49.33 | 167.05 | 22.8 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Man Who Wasn't There | 2001 | 216.25 | 357 | 89.42 | 126.83 | 41.35 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Hacksaw Ridge | 2016 | 216.13 | 358 | 123.47 | 92.66 | 57.13 | critics_groups_consensus+us_institutional | False | True |
| Frances Ha | 2012 | 215.78 | 359 | 91.44 | 124.34 | 42.38 | canon+critics_groups_consensus+independent_cinema+nyt_21c | False | False |
| Oasis | 2002 | 215.39 | 360 | 71.64 | 143.75 | 33.26 | canon+european_recognition | False | False |
| 2046 | 2004 | 215.31 | 361 | 88.3 | 127.01 | 41.01 | canon+critics_groups_consensus+european_recognition | False | False |
| Capturing the Friedmans | 2003 | 214.97 | 362 | 53.82 | 161.15 | 25.04 | canon+critics_groups_consensus+independent_cinema | False | False |
| Departures | 2008 | 214.68 | 363 | 98.83 | 115.85 | 46.04 | canon+critics_groups_consensus+us_institutional | False | False |
| Biutiful | 2010 | 214.28 | 364 | 81.8 | 132.48 | 38.17 | canon+european_recognition+us_institutional | False | False |
| Mother | 2009 | 214.27 | 365 | 112.3 | 101.97 | 52.41 | canon+critics_groups_consensus | True | True |
| Gosford Park | 2001 | 214.24 | 366 | 66.64 | 147.6 | 31.11 | canon+critics_groups_consensus+us_institutional | False | False |
| Lilya 4-Ever | 2002 | 213.88 | 367 | 111.97 | 101.91 | 52.35 | canon+critics_groups_consensus+european_recognition | True | True |
| Munich | 2005 | 213.71 | 368 | 83.66 | 130.05 | 39.15 | canon+critics_groups_consensus+us_institutional | False | False |
| The Sea Inside | 2004 | 213.7 | 369 | 93.53 | 120.17 | 43.77 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Belfast | 2021 | 212.91 | 370 | 55.09 | 157.82 | 25.87 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Prestige | 2006 | 212.82 | 371 | 150.0 | 62.82 | 70.48 | canon+critics_groups_consensus | True | True |
| Before Midnight | 2013 | 212.34 | 372 | 110.19 | 102.15 | 51.89 | canon+critics_groups_consensus+independent_cinema | True | True |
| For Sama | 2019 | 212.33 | 373 | 97.74 | 114.59 | 46.03 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Shaun of the Dead | 2004 | 212.12 | 374 | 100.67 | 111.45 | 47.46 | canon+critics_groups_consensus | False | False |
| The New World | 2005 | 211.98 | 375 | 50.46 | 161.52 | 23.8 | bbc_21c+canon+critics_groups_consensus | True | True |
| Poetry | 2010 | 211.78 | 376 | 84.32 | 127.46 | 39.81 | canon+critics_groups_consensus+european_recognition | False | False |
| Me and Earl and the Dying Girl | 2015 | 211.68 | 377 | 96.92 | 114.76 | 45.79 | critics_groups_consensus+independent_cinema | False | False |
| Navalny | 2022 | 210.84 | 378 | 87.63 | 123.21 | 41.56 | critics_groups_consensus+independent_cinema+us_institutional | False | True |
| Divine Intervention | 2002 | 210.81 | 379 | 17.57 | 193.24 | 8.33 | canon+critics_groups_consensus+european_recognition | False | False |
| Argentina, 1985 | 2022 | 210.58 | 380 | 90.07 | 120.51 | 42.77 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Le Havre | 2011 | 210.46 | 381 | 58.94 | 151.52 | 28.01 | canon+critics_groups_consensus+european_recognition | False | False |
| Free Solo | 2018 | 210.45 | 382 | 121.94 | 88.51 | 57.94 | critics_groups_consensus+us_institutional | False | True |
| Anomalisa | 2015 | 210.13 | 383 | 71.08 | 139.05 | 33.83 | canon+critics_groups_consensus+independent_cinema+us_institutional | False | False |

[Full family breakdown](borderline-band-210-225.csv)

### 225–<240

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3-Iron | 2004 | 239.78 | 311 | 106.48 | 133.3 | 44.41 | canon+critics_groups_consensus+european_recognition | True | True |
| Kung Fu Hustle | 2004 | 239.64 | 312 | 102.69 | 136.95 | 42.85 | canon+critics_groups_consensus+european_recognition | True | True |
| Frost/Nixon | 2008 | 237.99 | 313 | 82.17 | 155.82 | 34.53 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Curious Case of Benjamin Button | 2008 | 237.71 | 314 | 89.14 | 148.57 | 37.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Grizzly Man | 2005 | 237.41 | 315 | 104.79 | 132.62 | 44.14 | canon+critics_groups_consensus+independent_cinema+nyt_21c | True | True |
| Nobody Knows | 2004 | 237.31 | 316 | 118.82 | 118.49 | 50.07 | canon+critics_groups_consensus+european_recognition | False | False |
| A Star Is Born | 2018 | 237.26 | 317 | 75.86 | 161.4 | 31.97 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Skin I Live In | 2011 | 237.18 | 318 | 87.41 | 149.77 | 36.85 | canon+critics_groups_consensus+european_recognition | False | False |
| EO | 2022 | 236.05 | 319 | 38.95 | 197.1 | 16.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Force Majeure | 2014 | 234.21 | 320 | 76.43 | 157.78 | 32.63 | canon+critics_groups_consensus+european_recognition | False | False |
| About Elly | 2009 | 233.39 | 321 | 101.56 | 131.83 | 43.52 | canon+critics_groups_consensus+european_recognition | False | False |
| Downfall | 2004 | 233.3 | 322 | 127.22 | 106.08 | 54.53 | canon+critics_groups_consensus+us_institutional | True | True |
| The Substance | 2024 | 233.08 | 323 | 66.64 | 166.44 | 28.59 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| Top Gun: Maverick | 2022 | 233.01 | 324 | 121.44 | 111.57 | 52.12 | canon+critics_groups_consensus+us_institutional | True | True |
| Borat | 2006 | 232.87 | 325 | 74.14 | 158.73 | 31.84 | canon+critics_groups_consensus+nyt_21c | False | False |
| The Reader | 2008 | 232.86 | 326 | 75.86 | 157.0 | 32.58 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| If Beale Street Could Talk | 2018 | 232.85 | 327 | 71.55 | 161.3 | 30.73 | canon+critics_groups_consensus+independent_cinema+us_institutional | False | False |
| First Reformed | 2017 | 231.46 | 328 | 78.35 | 153.11 | 33.85 | canon+critics_groups_consensus+european_recognition+independent_cinema | False | False |
| Burning | 2018 | 231.13 | 329 | 90.49 | 140.64 | 39.15 | canon+critics_groups_consensus+european_recognition | False | False |
| Donnie Darko | 2001 | 230.85 | 330 | 113.94 | 116.91 | 49.36 | canon+critics_groups_consensus+independent_cinema | True | True |
| Sentimental Value | 2025 | 230.77 | 331 | 113.36 | 117.41 | 49.12 | critics_groups_consensus+european_recognition | False | False |
| Silent Light | 2007 | 229.11 | 332 | 36.44 | 192.67 | 15.91 | canon+european_recognition | True | True |
| Bad Education | 2004 | 228.49 | 333 | 88.45 | 140.04 | 38.71 | canon+critics_groups_consensus+european_recognition | False | False |
| O Brother, Where Art Thou? | 2000 | 227.16 | 334 | 102.69 | 124.47 | 45.21 | canon+critics_groups_consensus+european_recognition+nyt_21c | True | True |
| Philomena | 2013 | 226.85 | 335 | 77.39 | 149.46 | 34.12 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Big Fish | 2003 | 226.43 | 336 | 110.19 | 116.24 | 48.66 | canon+critics_groups_consensus+european_recognition | True | True |

[Full family breakdown](borderline-band-225-240.csv)

### 240–<250

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Crash | 2004 | 249.73 | 289 | 45.0 | 204.73 | 18.02 | canon+critics_groups_consensus+european_recognition+independent_cinema+us_institutional | True | True |
| Hedwig and the Angry Inch | 2001 | 248.83 | 290 | 95.89 | 152.94 | 38.54 | canon+critics_groups_consensus+independent_cinema | False | False |
| District 9 | 2009 | 248.65 | 291 | 98.66 | 149.99 | 39.68 | canon+critics_groups_consensus+us_institutional | False | False |
| Hugo | 2011 | 247.27 | 292 | 66.34 | 180.93 | 26.83 | canon+critics_groups_consensus+us_institutional | False | False |
| Fahrenheit 9/11 | 2004 | 247.19 | 293 | 69.62 | 177.57 | 28.16 | canon+critics_groups_consensus+european_recognition | False | False |
| The Rider | 2017 | 246.86 | 294 | 71.71 | 175.15 | 29.05 | canon+critics_groups_consensus+independent_cinema | False | False |
| An Education | 2009 | 246.6 | 295 | 60.09 | 186.51 | 24.37 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| The Big Short | 2015 | 246.6 | 296 | 100.67 | 145.93 | 40.82 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| I Am Not Your Negro | 2016 | 246.43 | 297 | 100.16 | 146.27 | 40.64 | canon+critics_groups_consensus+us_institutional | True | True |
| Bacurau | 2019 | 245.87 | 298 | 75.18 | 170.69 | 30.58 | canon+critics_groups_consensus+european_recognition | False | False |
| The Florida Project | 2017 | 244.45 | 299 | 104.72 | 139.73 | 42.84 | canon+critics_groups_consensus+independent_cinema+nyt_21c | False | False |
| Happy as Lazzaro | 2018 | 243.08 | 300 | 87.97 | 155.11 | 36.19 | canon+critics_groups_consensus+european_recognition | False | False |
| Sound of Metal | 2020 | 242.93 | 301 | 114.23 | 128.7 | 47.02 | critics_groups_consensus+independent_cinema+us_institutional | False | True |
| Io Capitano | 2023 | 242.87 | 302 | 74.49 | 168.38 | 30.67 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Coco | 2017 | 241.7 | 303 | 134.72 | 106.98 | 55.74 | critics_groups_consensus+us_institutional | False | True |
| The Trial of the Chicago 7 | 2020 | 241.65 | 304 | 91.16 | 150.49 | 37.72 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Elle | 2016 | 241.3 | 305 | 61.46 | 179.84 | 25.47 | canon+critics_groups_consensus+european_recognition | False | False |
| The Salesman | 2016 | 240.81 | 306 | 88.38 | 152.43 | 36.7 | critics_groups_consensus+european_recognition+us_institutional | False | True |
| Memoria | 2021 | 240.43 | 307 | 42.54 | 197.89 | 17.69 | canon+critics_groups_consensus+european_recognition | False | False |
| Flow | 2024 | 240.4 | 308 | 112.22 | 128.18 | 46.68 | critics_groups_consensus+us_institutional | False | False |
| Devils on the Doorstep | 2000 | 240.3 | 309 | 61.44 | 178.86 | 25.57 | canon+european_recognition | False | False |
| The Turin Horse | 2011 | 240.12 | 310 | 88.26 | 151.86 | 36.76 | bbc_21c+canon+critics_groups_consensus | True | True |

[Full family breakdown](borderline-band-240-250.csv)

### 250–<265

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gone Girl | 2014 | 264.42 | 247 | 123.47 | 140.95 | 46.69 | canon+critics_groups_consensus+nyt_21c | True | True |
| Uncut Gems | 2019 | 264.39 | 248 | 91.44 | 172.95 | 34.59 | canon+critics_groups_consensus+independent_cinema+nyt_21c | False | False |
| Certified Copy | 2010 | 264.09 | 249 | 78.74 | 185.35 | 29.82 | bbc_21c+canon+critics_groups_consensus+european_recognition | False | False |
| The Wrestler | 2008 | 263.32 | 250 | 115.97 | 147.35 | 44.04 | canon+critics_groups_consensus+independent_cinema | True | True |
| Licorice Pizza | 2021 | 263.2 | 251 | 51.34 | 211.86 | 19.51 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Howl's Moving Castle | 2004 | 262.96 | 252 | 138.75 | 124.21 | 52.76 | canon+critics_groups_consensus+us_institutional | True | True |
| Train Dreams | 2025 | 262.91 | 253 | 100.97 | 161.94 | 38.4 | critics_groups_consensus+independent_cinema+us_institutional | False | False |
| Sinners | 2025 | 262.79 | 254 | 100.97 | 161.82 | 38.42 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Kill Bill: Vol. 1 | 2003 | 262.75 | 255 | 132.98 | 129.77 | 50.61 | canon+critics_groups_consensus+nyt_21c | True | True |
| Nebraska | 2013 | 261.92 | 256 | 102.69 | 159.23 | 39.21 | canon+critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| The Farewell | 2019 | 261.07 | 257 | 98.75 | 162.32 | 37.83 | canon+critics_groups_consensus+european_recognition+independent_cinema | False | False |
| The Triplets of Belleville | 2003 | 260.9 | 258 | 94.79 | 166.11 | 36.33 | canon+critics_groups_consensus+european_recognition+us_institutional | True | True |
| Werckmeister Harmonies | 2000 | 260.83 | 259 | 96.59 | 164.24 | 37.03 | bbc_21c+canon+critics_groups_consensus | True | True |
| Never Rarely Sometimes Always | 2020 | 260.62 | 260 | 79.85 | 180.77 | 30.64 | canon+critics_groups_consensus+european_recognition+independent_cinema | False | False |
| Billy Elliot | 2000 | 260.35 | 261 | 108.47 | 151.88 | 41.66 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Hero | 2002 | 259.68 | 262 | 110.19 | 149.49 | 42.43 | canon+critics_groups_consensus+us_institutional | True | True |
| Marty Supreme | 2025 | 259.6 | 263 | 95.19 | 164.41 | 36.67 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Gleaners & I | 2000 | 259.55 | 264 | 91.25 | 168.3 | 35.16 | bbc_21c+canon+critics_groups_consensus+nyt_21c | True | True |
| The Fabelmans | 2022 | 259.55 | 265 | 95.19 | 164.36 | 36.68 | canon+critics_groups_consensus+us_institutional | False | False |
| Juno | 2007 | 259.35 | 266 | 74.14 | 185.21 | 28.59 | canon+critics_groups_consensus+independent_cinema+us_institutional | False | False |
| 25th Hour | 2002 | 257.05 | 267 | 93.17 | 163.88 | 36.25 | bbc_21c+canon+critics_groups_consensus | False | False |
| Little Women | 2019 | 256.61 | 268 | 114.23 | 142.38 | 44.52 | canon+critics_groups_consensus+us_institutional | True | True |
| Isle of Dogs | 2018 | 256.48 | 269 | 112.22 | 144.26 | 43.75 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Selma | 2014 | 256.38 | 270 | 83.64 | 172.74 | 32.62 | canon+critics_groups_consensus+independent_cinema+us_institutional | False | False |
| The Tale of The Princess Kaguya | 2013 | 255.72 | 271 | 125.68 | 130.04 | 49.15 | canon+critics_groups_consensus+us_institutional | True | True |
| Traffic | 2000 | 255.72 | 272 | 77.89 | 177.83 | 30.46 | canon+critics_groups_consensus+us_institutional | False | False |
| The Imitation Game | 2014 | 255.69 | 273 | 108.17 | 147.52 | 42.31 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Interstellar | 2014 | 255.52 | 274 | 150.0 | 105.52 | 58.7 | canon+critics_groups_consensus+nyt_21c | True | True |
| Under the Skin | 2013 | 254.69 | 275 | 34.61 | 220.08 | 13.59 | bbc_21c+canon+critics_groups_consensus+independent_cinema+nyt_21c | True | True |
| Mustang | 2015 | 254.59 | 276 | 103.02 | 151.57 | 40.47 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Lincoln | 2012 | 254.38 | 277 | 64.61 | 189.77 | 25.4 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| First Cow | 2019 | 254.29 | 278 | 67.64 | 186.65 | 26.6 | canon+critics_groups_consensus+european_recognition+independent_cinema | True | True |
| Requiem for a Dream | 2000 | 253.86 | 279 | 130.97 | 122.89 | 51.59 | bbc_21c+canon+critics_groups_consensus+independent_cinema | True | True |
| Captain Phillips | 2013 | 253.03 | 280 | 94.91 | 158.12 | 37.51 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Memories of Murder | 2003 | 252.96 | 281 | 135.0 | 117.96 | 53.37 | canon+critics_groups_consensus | True | True |
| You Can Count on Me | 2000 | 252.4 | 282 | 68.03 | 184.37 | 26.95 | canon+critics_groups_consensus+independent_cinema | False | False |
| The Help | 2011 | 252.16 | 283 | 117.69 | 134.47 | 46.67 | critics_groups_consensus+european_recognition+us_institutional | False | True |
| Dune: Part Two | 2024 | 252.05 | 284 | 146.25 | 105.8 | 58.02 | critics_groups_consensus+us_institutional | False | False |
| Hell or High Water | 2016 | 251.58 | 285 | 93.17 | 158.41 | 37.03 | canon+critics_groups_consensus+us_institutional | False | False |
| Honeyland | 2019 | 251.56 | 286 | 82.57 | 168.99 | 32.82 | critics_groups_consensus+independent_cinema+us_institutional | False | False |
| The Wonders | 2014 | 251.34 | 287 | 32.23 | 219.11 | 12.82 | canon+critics_groups_consensus+european_recognition | False | False |
| I'm Not There | 2007 | 250.44 | 288 | 46.34 | 204.1 | 18.5 | canon+critics_groups_consensus+european_recognition+independent_cinema | False | False |

[Full family breakdown](borderline-band-250-265.csv)

## Quality sanity checks

Neither policy creates Audience-only newcomers or newcomers with fewer than two positive independent non-audience families in this dataset. No one very weak non-audience source plus large Audience score passes. This is observed evidence, not an added guard or a guarantee for future data.
Audience dominance remains explicitly present; it is not silently excluded. Exact>50% uses points, not a rounded percent. A marginal 50.07% is different from pure Audience-only evidence.

### P225 audience-dominant newcomers

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dune: Part Two | 2024 | 252.05 | 284 | 146.25 | 105.8 | 58.02 | critics_groups_consensus+us_institutional | False | False |
| Coco | 2017 | 241.7 | 303 | 134.72 | 106.98 | 55.74 | critics_groups_consensus+us_institutional | False | True |
| Nobody Knows | 2004 | 237.31 | 316 | 118.82 | 118.49 | 50.07 | canon+critics_groups_consensus+european_recognition | False | False |

### P225 very recent with US institutional evidence

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anora | 2024 | 499.51 | 42 | 79.91 | 419.6 | 16.0 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| One Battle After Another | 2025 | 439.72 | 66 | 104.72 | 335.0 | 23.82 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| The Voice of Hind Rajab | 2025 | 367.42 | 108 | 117.79 | 249.63 | 32.06 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Brutalist | 2024 | 350.72 | 129 | 78.17 | 272.55 | 22.29 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| I'm Still Here | 2024 | 318.48 | 162 | 135.0 | 183.48 | 42.39 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Hamnet | 2025 | 297.52 | 190 | 117.98 | 179.54 | 39.65 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| Conclave | 2024 | 291.93 | 201 | 85.67 | 206.26 | 29.35 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Train Dreams | 2025 | 262.91 | 253 | 100.97 | 161.94 | 38.4 | critics_groups_consensus+independent_cinema+us_institutional | False | False |
| Sinners | 2025 | 262.79 | 254 | 100.97 | 161.82 | 38.42 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Marty Supreme | 2025 | 259.6 | 263 | 95.19 | 164.41 | 36.67 | critics_groups_consensus+european_recognition+us_institutional | False | False |

### P225 festival/canon non-production films just below threshold

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wallace & Gromit: The Curse of the Were-Rabbit | 2005 | 224.91 | 337 | 89.42 | 135.49 | 39.76 | canon+critics_groups_consensus+us_institutional | False | False |
| Up in the Air | 2009 | 223.64 | 339 | 68.36 | 155.28 | 30.57 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Kids Are All Right | 2010 | 222.59 | 340 | 35.22 | 187.37 | 15.82 | canon+critics_groups_consensus+independent_cinema+us_institutional | False | False |
| Bridge of Spies | 2015 | 221.64 | 343 | 75.86 | 145.78 | 34.23 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Squid and the Whale | 2005 | 221.19 | 345 | 70.06 | 151.13 | 31.67 | canon+critics_groups_consensus+independent_cinema | False | False |
| Paterson | 2016 | 218.72 | 350 | 81.7 | 137.02 | 37.35 | canon+critics_groups_consensus+european_recognition+independent_cinema | False | False |
| Once | 2006 | 218.33 | 351 | 100.67 | 117.66 | 46.11 | canon+critics_groups_consensus+independent_cinema | False | False |
| The Theory of Everything | 2014 | 217.87 | 352 | 79.61 | 138.26 | 36.54 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Wind Rises | 2013 | 217.86 | 353 | 112.22 | 105.64 | 51.51 | canon+critics_groups_consensus+us_institutional | False | False |
| Still Walking | 2008 | 217.13 | 355 | 104.54 | 112.59 | 48.15 | canon+critics_groups_consensus | False | False |
| American Hustle | 2013 | 216.38 | 356 | 49.33 | 167.05 | 22.8 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Man Who Wasn't There | 2001 | 216.25 | 357 | 89.42 | 126.83 | 41.35 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Frances Ha | 2012 | 215.78 | 359 | 91.44 | 124.34 | 42.38 | canon+critics_groups_consensus+independent_cinema+nyt_21c | False | False |
| Oasis | 2002 | 215.39 | 360 | 71.64 | 143.75 | 33.26 | canon+european_recognition | False | False |
| 2046 | 2004 | 215.31 | 361 | 88.3 | 127.01 | 41.01 | canon+critics_groups_consensus+european_recognition | False | False |

### P250 audience-dominant newcomers

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dune: Part Two | 2024 | 252.05 | 284 | 146.25 | 105.8 | 58.02 | critics_groups_consensus+us_institutional | False | False |

### P250 very recent with US institutional evidence

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anora | 2024 | 499.51 | 42 | 79.91 | 419.6 | 16.0 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| One Battle After Another | 2025 | 439.72 | 66 | 104.72 | 335.0 | 23.82 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| The Voice of Hind Rajab | 2025 | 367.42 | 108 | 117.79 | 249.63 | 32.06 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Brutalist | 2024 | 350.72 | 129 | 78.17 | 272.55 | 22.29 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| I'm Still Here | 2024 | 318.48 | 162 | 135.0 | 183.48 | 42.39 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Hamnet | 2025 | 297.52 | 190 | 117.98 | 179.54 | 39.65 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| Conclave | 2024 | 291.93 | 201 | 85.67 | 206.26 | 29.35 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Train Dreams | 2025 | 262.91 | 253 | 100.97 | 161.94 | 38.4 | critics_groups_consensus+independent_cinema+us_institutional | False | False |
| Sinners | 2025 | 262.79 | 254 | 100.97 | 161.82 | 38.42 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Marty Supreme | 2025 | 259.6 | 263 | 95.19 | 164.41 | 36.67 | critics_groups_consensus+european_recognition+us_institutional | False | False |

### P250 festival/canon non-production films just below threshold

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hedwig and the Angry Inch | 2001 | 248.83 | 290 | 95.89 | 152.94 | 38.54 | canon+critics_groups_consensus+independent_cinema | False | False |
| District 9 | 2009 | 248.65 | 291 | 98.66 | 149.99 | 39.68 | canon+critics_groups_consensus+us_institutional | False | False |
| Hugo | 2011 | 247.27 | 292 | 66.34 | 180.93 | 26.83 | canon+critics_groups_consensus+us_institutional | False | False |
| Fahrenheit 9/11 | 2004 | 247.19 | 293 | 69.62 | 177.57 | 28.16 | canon+critics_groups_consensus+european_recognition | False | False |
| The Rider | 2017 | 246.86 | 294 | 71.71 | 175.15 | 29.05 | canon+critics_groups_consensus+independent_cinema | False | False |
| An Education | 2009 | 246.6 | 295 | 60.09 | 186.51 | 24.37 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| The Big Short | 2015 | 246.6 | 296 | 100.67 | 145.93 | 40.82 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Bacurau | 2019 | 245.87 | 298 | 75.18 | 170.69 | 30.58 | canon+critics_groups_consensus+european_recognition | False | False |
| The Florida Project | 2017 | 244.45 | 299 | 104.72 | 139.73 | 42.84 | canon+critics_groups_consensus+independent_cinema+nyt_21c | False | False |
| Happy as Lazzaro | 2018 | 243.08 | 300 | 87.97 | 155.11 | 36.19 | canon+critics_groups_consensus+european_recognition | False | False |
| Io Capitano | 2023 | 242.87 | 302 | 74.49 | 168.38 | 30.67 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Trial of the Chicago 7 | 2020 | 241.65 | 304 | 91.16 | 150.49 | 37.72 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Elle | 2016 | 241.3 | 305 | 61.46 | 179.84 | 25.47 | canon+critics_groups_consensus+european_recognition | False | False |
| The Salesman | 2016 | 240.81 | 306 | 88.38 | 152.43 | 36.7 | critics_groups_consensus+european_recognition+us_institutional | False | True |
| Memoria | 2021 | 240.43 | 307 | 42.54 | 197.89 | 17.69 | canon+critics_groups_consensus+european_recognition | False | False |

Both preserve all known deployed watch/taste examples. Taste/watch annotations never affect scores or P flags. The previous 13 positive signals are a small positive-only sample, not preference ground truth for 36 newcomers.
Very recent films have less historical-poll eligibility; eligible_max_score is exposed, but no normalization or age correction is applied.
Nine missing Letterboxd components remain from PR #3; their prior bound cannot reach 125, so they cannot change P225/P250. Remaining award/critic gaps are not bounded. Small Axe and combined Nymphomaniac stay unallocated.

## Artifacts and reproduction

[comparison.json](comparison.json), [per-film.csv](per-film.csv), [P225-new.csv](P225-new.csv), [P250-new.csv](P250-new.csv), [research-31-review.csv](research-31-review.csv), [baseline-reconciliation.csv](baseline-reconciliation.csv), [manifest.json](manifest.json).
Run python production_threshold_calibration.py through SSH in this worktree. Inputs/code/config hashes are frozen; no enrichment or Radarr API calls. Full suite and byte-for-byte checks are recorded in the engineering handoff.

### Product review summary

**Strongest argument for 225:** it adds 36 additional non-production films with real canon/festival/institutional support, including Hedwig and the Angry Inch, The Rider, Bacurau,The Florida Project, Memoria, EO and Sound of Metal. The delta is not Audience-only.
**Strongest argument for 250:** a smaller 127-newcomer expansion rather than 163, excluding the entire 225–249.99 cohort and two additional audience-dominant newcomers. It is a clearer numerical margin, at the cost of omitting those supported discoveries. No measured taste precision establishes that 250 is better.
**Practical difference:** 36 films; P225=387 total/163 new; P250=351 total/127 new. All 224 production films retained. The 18 representatives below span that difference.

| Film | Year | Score | Rank | Audience | Other | Audience% | Families | Prod224 | Research 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hedwig and the Angry Inch | 2001 | 248.83 | 290 | 95.89 | 152.94 | 38.54 | canon+critics_groups_consensus+independent_cinema | False | False |
| District 9 | 2009 | 248.65 | 291 | 98.66 | 149.99 | 39.68 | canon+critics_groups_consensus+us_institutional | False | False |
| Hugo | 2011 | 247.27 | 292 | 66.34 | 180.93 | 26.83 | canon+critics_groups_consensus+us_institutional | False | False |
| The Rider | 2017 | 246.86 | 294 | 71.71 | 175.15 | 29.05 | canon+critics_groups_consensus+independent_cinema | False | False |
| An Education | 2009 | 246.6 | 295 | 60.09 | 186.51 | 24.37 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| Bacurau | 2019 | 245.87 | 298 | 75.18 | 170.69 | 30.58 | canon+critics_groups_consensus+european_recognition | False | False |
| The Florida Project | 2017 | 244.45 | 299 | 104.72 | 139.73 | 42.84 | canon+critics_groups_consensus+independent_cinema+nyt_21c | False | False |
| Sound of Metal | 2020 | 242.93 | 301 | 114.23 | 128.7 | 47.02 | critics_groups_consensus+independent_cinema+us_institutional | False | True |
| Coco | 2017 | 241.7 | 303 | 134.72 | 106.98 | 55.74 | critics_groups_consensus+us_institutional | False | True |
| Memoria | 2021 | 240.43 | 307 | 42.54 | 197.89 | 17.69 | canon+critics_groups_consensus+european_recognition | False | False |
| Flow | 2024 | 240.4 | 308 | 112.22 | 128.18 | 46.68 | critics_groups_consensus+us_institutional | False | False |
| The Curious Case of Benjamin Button | 2008 | 237.71 | 314 | 89.14 | 148.57 | 37.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| Nobody Knows | 2004 | 237.31 | 316 | 118.82 | 118.49 | 50.07 | canon+critics_groups_consensus+european_recognition | False | False |
| EO | 2022 | 236.05 | 319 | 38.95 | 197.1 | 16.5 | canon+critics_groups_consensus+european_recognition+us_institutional | False | False |
| The Substance | 2024 | 233.08 | 323 | 66.64 | 166.44 | 28.59 | critics_groups_consensus+european_recognition+independent_cinema+us_institutional | False | False |
| The Reader | 2008 | 232.86 | 326 | 75.86 | 157.0 | 32.58 | critics_groups_consensus+european_recognition+us_institutional | False | False |
| Burning | 2018 | 231.13 | 329 | 90.49 | 140.64 | 39.15 | canon+critics_groups_consensus+european_recognition | False | False |
| Sentimental Value | 2025 | 230.77 | 331 | 113.36 | 117.41 | 49.12 | critics_groups_consensus+european_recognition | False | False |

**Manual discussion:** Coco and Nobody Knows carry >50% Audience in the delta; The Reader and The Curious Case of Benjamin Button have low modeled critic-family points despite substantial institutional evidence. Flow, The Substance, Sentimental Value show recent-film eligibility limits. The 20 research-only films below 225 are not admitted and would need an explicit later grandfathering decision.
Selected/new means hypothetical qualification, not live library absence or downloadability. No final threshold is chosen; the user and ChatGPT make that product decision.
