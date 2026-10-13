# Evidence Score qualification calibration

Research-only. Frozen PR #3 dataset: 1,909 films; 255 existing qualified IDs/routes.
Audience 150, effective ceiling 1000, all other weights and canon correlation unchanged.
No policy/threshold is selected; no production change or Radarr action.

## Definitions and limits

Thresholds use the published absolute score and inclusive >=. Family contribution means positive points. TSPDT/Sight&Sound count together as canon for B/C/E; raw counts remain available. Critics Groups remains its existing merged award/broad-critic family; a small positive broad-critic contribution counts, so family count is not evidence strength.

Existing qualification is a comparison label, not ground truth for quality. Overlap%=existing-qualified selected / all selected; retention%=selected baseline /255. These are agreement metrics, not validated precision/recall of user taste.

Recent=2020 onward; borderline=within 10 points, diagnostics only. Known watched films retain their qualification; annotations describe existing monitoring context. Current Radarr library and live addability were not queried.

No taste value affects scores/decisions; unknown films are unlabelled, not negative examples. The thirteen existing positive signals are all baseline-qualified; the 33 watched annotations are also all baseline-qualified. This small positive-only sample cannot validate newly admitted films or estimate taste precision. No anthology/combined-work award is allocated to components.

Nine Letterboxd gaps and 32 unresolved award-source records remain from PR#3. ReelDB HTTP 403 is unchanged; no live enrichment in this task. Scores with missing data remain observed lower evidence; upper bounds never fabricate ratings. Recent films have fewer historical-poll eligibility opportunities; thresholds are not renormalized.

| Code | Research predicate |
| --- | --- |
| score_only | Evidence Score >= threshold |
| A_keep_existing | Existing qualification OR Evidence Score >= threshold |
| B_two_families | Score >= threshold AND at least 2 independent non-audience families |
| C_one_family | Score >= threshold AND at least 1 independent non-audience family |
| D_audience_half | Score >= threshold AND Audience <= 50% of total |
| E_low_evidence_guard | Score >= threshold AND >=1 non-audience family; with only 1 family, Audience <=50% |

## Distribution

| Statistic | All | Current qualified | Unqualified | Audience complete | Incomplete |
| --- | --- | --- | --- | --- | --- |
| count | 1909 | 255 | 1654 | 1900 | 9 |
| min | 0.0 | 108.67 | 0.0 | 0.0 | 0.0 |
| max | 803.78 | 803.78 | 571.43 | 803.78 | 45.74 |
| mean | 148.52 | 338.46 | 119.24 | 149.13 | 19.66 |
| median | 112.7 | 301.78 | 99.71 | 113.5 | 8.04 |
| stddev_population | 114.37 | 145.09 | 73.71 | 114.29 | 18.31 |

### all

| Score band | Count |
| --- | --- |
| 0-<25 | 45 |
| 25-<50 | 124 |
| 50-<75 | 326 |
| 75-<100 | 334 |
| 100-<125 | 244 |
| 125-<150 | 182 |
| 150-<175 | 144 |
| 175-<200 | 95 |
| 200-<225 | 79 |
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

| Percentile | Score |
| --- | --- |
| 10 | 53.08 |
| 25 | 74.09 |
| 50 | 112.7 |
| 75 | 184.48 |
| 90 | 296.8 |
| 95 | 388.85 |
| 99 | 570.71 |

| Independent non-audience families | Count |
| --- | --- |
| 0 | 314 |
| 1 | 458 |
| 2 | 529 |
| 3 | 361 |
| 4 | 152 |
| 5 | 57 |
| 6 | 27 |
| 7 | 11 |

### currently qualified

| Score band | Count |
| --- | --- |
| 0-<25 | 0 |
| 25-<50 | 0 |
| 50-<75 | 0 |
| 75-<100 | 0 |
| 100-<125 | 2 |
| 125-<150 | 7 |
| 150-<175 | 15 |
| 175-<200 | 24 |
| 200-<225 | 23 |
| 225-<250 | 15 |
| 250-<275 | 24 |
| 275-<300 | 15 |
| 300-<325 | 9 |
| 325-<350 | 19 |
| 350-<375 | 10 |
| 375-<400 | 12 |
| 400-<450 | 23 |
| 450-<500 | 17 |
| 500-<600 | 25 |
| 600-<700 | 11 |
| 700-<800 | 3 |
| 800-<900 | 1 |
| 900-<1000 | 0 |
| 1000 | 0 |

| Percentile | Score |
| --- | --- |
| 10 | 183.03 |
| 25 | 218.69 |
| 50 | 301.78 |
| 75 | 432.43 |
| 90 | 537.43 |
| 95 | 622.14 |
| 99 | 739.74 |

| Independent non-audience families | Count |
| --- | --- |
| 1 | 8 |
| 2 | 46 |
| 3 | 68 |
| 4 | 54 |
| 5 | 44 |
| 6 | 24 |
| 7 | 11 |

### currently unqualified

| Score band | Count |
| --- | --- |
| 0-<25 | 45 |
| 25-<50 | 124 |
| 50-<75 | 326 |
| 75-<100 | 334 |
| 100-<125 | 242 |
| 125-<150 | 175 |
| 150-<175 | 129 |
| 175-<200 | 71 |
| 200-<225 | 56 |
| 225-<250 | 33 |
| 250-<275 | 40 |
| 275-<300 | 25 |
| 300-<325 | 19 |
| 325-<350 | 8 |
| 350-<375 | 16 |
| 375-<400 | 3 |
| 400-<450 | 4 |
| 450-<500 | 3 |
| 500-<600 | 1 |
| 600-<700 | 0 |
| 700-<800 | 0 |
| 800-<900 | 0 |
| 900-<1000 | 0 |
| 1000 | 0 |

| Percentile | Score |
| --- | --- |
| 10 | 48.94 |
| 25 | 70.38 |
| 50 | 99.71 |
| 75 | 148.9 |
| 90 | 215.66 |
| 95 | 271.72 |
| 99 | 360.83 |

| Independent non-audience families | Count |
| --- | --- |
| 0 | 314 |
| 1 | 450 |
| 2 | 483 |
| 3 | 293 |
| 4 | 98 |
| 5 | 13 |
| 6 | 3 |

### audience complete

| Score band | Count |
| --- | --- |
| 0-<25 | 40 |
| 25-<50 | 120 |
| 50-<75 | 326 |
| 75-<100 | 334 |
| 100-<125 | 244 |
| 125-<150 | 182 |
| 150-<175 | 144 |
| 175-<200 | 95 |
| 200-<225 | 79 |
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

| Percentile | Score |
| --- | --- |
| 10 | 54.25 |
| 25 | 74.37 |
| 50 | 113.5 |
| 75 | 185.21 |
| 90 | 297.36 |
| 95 | 389.17 |
| 99 | 571.46 |

| Independent non-audience families | Count |
| --- | --- |
| 0 | 308 |
| 1 | 455 |
| 2 | 529 |
| 3 | 361 |
| 4 | 152 |
| 5 | 57 |
| 6 | 27 |
| 7 | 11 |

### audience incomplete

| Score band | Count |
| --- | --- |
| 0-<25 | 5 |
| 25-<50 | 4 |
| 50-<75 | 0 |
| 75-<100 | 0 |
| 100-<125 | 0 |
| 125-<150 | 0 |
| 150-<175 | 0 |
| 175-<200 | 0 |
| 200-<225 | 0 |
| 225-<250 | 0 |
| 250-<275 | 0 |
| 275-<300 | 0 |
| 300-<325 | 0 |
| 325-<350 | 0 |
| 350-<375 | 0 |
| 375-<400 | 0 |
| 400-<450 | 0 |
| 450-<500 | 0 |
| 500-<600 | 0 |
| 600-<700 | 0 |
| 700-<800 | 0 |
| 800-<900 | 0 |
| 900-<1000 | 0 |
| 1000 | 0 |

| Percentile | Score |
| --- | --- |
| 10 | 0.0 |
| 25 | 2.0 |
| 50 | 8.04 |
| 75 | 37.58 |
| 90 | 40.04 |
| 95 | 42.89 |
| 99 | 45.17 |

| Independent non-audience families | Count |
| --- | --- |
| 0 | 6 |
| 1 | 3 |

## Score-only threshold summary

| Policy | Threshold | Total | New | Retained | Lost | Overlap % | New Audience>50% | Recent new |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| score_only | 100 | 1080 | 825 | 255 | 0 | 23.61 | 339 | 159 |
| score_only | 125 | 836 | 583 | 253 | 2 | 30.26 | 180 | 116 |
| score_only | 150 | 654 | 408 | 246 | 9 | 37.61 | 82 | 86 |
| score_only | 175 | 510 | 279 | 231 | 24 | 45.29 | 25 | 63 |
| score_only | 200 | 415 | 208 | 207 | 48 | 49.88 | 9 | 50 |
| score_only | 225 | 336 | 152 | 184 | 71 | 54.76 | 2 | 42 |
| score_only | 250 | 288 | 119 | 169 | 86 | 58.68 | 1 | 35 |
| score_only | 300 | 184 | 54 | 130 | 125 | 70.65 | 0 | 17 |
| score_only | 350 | 129 | 27 | 102 | 153 | 79.07 | 0 | 11 |
| score_only | 400 | 88 | 8 | 80 | 175 | 90.91 | 0 | 5 |

Full loss lists: [score-only-losses.csv](score-only-losses.csv). Every policy includes distributions by year/family composition and incomplete-data sensitivity in calibration.json.

## All policy comparisons

| Policy | Threshold | Total | New | Retained | Lost | Overlap % | New Audience>50% | Recent new |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| score_only | 100 | 1080 | 825 | 255 | 0 | 23.61 | 339 | 159 |
| A_keep_existing | 100 | 1080 | 825 | 255 | 0 | 23.61 | 339 | 159 |
| B_two_families | 100 | 887 | 640 | 247 | 8 | 27.85 | 173 | 122 |
| C_one_family | 100 | 1032 | 777 | 255 | 0 | 24.71 | 291 | 145 |
| D_audience_half | 100 | 692 | 486 | 206 | 49 | 29.77 | 0 | 94 |
| E_low_evidence_guard | 100 | 912 | 659 | 253 | 2 | 27.74 | 173 | 123 |
| score_only | 125 | 836 | 583 | 253 | 2 | 30.26 | 180 | 116 |
| A_keep_existing | 125 | 838 | 583 | 255 | 0 | 30.43 | 180 | 116 |
| B_two_families | 125 | 779 | 532 | 247 | 8 | 31.71 | 133 | 103 |
| C_one_family | 125 | 827 | 574 | 253 | 2 | 30.59 | 171 | 113 |
| D_audience_half | 125 | 607 | 403 | 204 | 51 | 33.61 | 0 | 81 |
| E_low_evidence_guard | 125 | 787 | 536 | 251 | 4 | 31.89 | 133 | 104 |
| score_only | 150 | 654 | 408 | 246 | 9 | 37.61 | 82 | 86 |
| A_keep_existing | 150 | 663 | 408 | 255 | 0 | 38.46 | 82 | 86 |
| B_two_families | 150 | 638 | 394 | 244 | 11 | 38.24 | 69 | 84 |
| C_one_family | 150 | 654 | 408 | 246 | 9 | 37.61 | 82 | 86 |
| D_audience_half | 150 | 525 | 326 | 199 | 56 | 37.9 | 0 | 71 |
| E_low_evidence_guard | 150 | 640 | 395 | 245 | 10 | 38.28 | 69 | 84 |
| score_only | 175 | 510 | 279 | 231 | 24 | 45.29 | 25 | 63 |
| A_keep_existing | 175 | 534 | 279 | 255 | 0 | 47.75 | 25 | 63 |
| B_two_families | 175 | 509 | 278 | 231 | 24 | 45.38 | 24 | 62 |
| C_one_family | 175 | 510 | 279 | 231 | 24 | 45.29 | 25 | 63 |
| D_audience_half | 175 | 444 | 254 | 190 | 65 | 42.79 | 0 | 57 |
| E_low_evidence_guard | 175 | 509 | 278 | 231 | 24 | 45.38 | 24 | 62 |
| score_only | 200 | 415 | 208 | 207 | 48 | 49.88 | 9 | 50 |
| A_keep_existing | 200 | 463 | 208 | 255 | 0 | 55.08 | 9 | 50 |
| B_two_families | 200 | 415 | 208 | 207 | 48 | 49.88 | 9 | 50 |
| C_one_family | 200 | 415 | 208 | 207 | 48 | 49.88 | 9 | 50 |
| D_audience_half | 200 | 381 | 199 | 182 | 73 | 47.77 | 0 | 47 |
| E_low_evidence_guard | 200 | 415 | 208 | 207 | 48 | 49.88 | 9 | 50 |
| score_only | 225 | 336 | 152 | 184 | 71 | 54.76 | 2 | 42 |
| A_keep_existing | 225 | 407 | 152 | 255 | 0 | 62.65 | 2 | 42 |
| B_two_families | 225 | 336 | 152 | 184 | 71 | 54.76 | 2 | 42 |
| C_one_family | 225 | 336 | 152 | 184 | 71 | 54.76 | 2 | 42 |
| D_audience_half | 225 | 326 | 150 | 176 | 79 | 53.99 | 0 | 41 |
| E_low_evidence_guard | 225 | 336 | 152 | 184 | 71 | 54.76 | 2 | 42 |
| score_only | 250 | 288 | 119 | 169 | 86 | 58.68 | 1 | 35 |
| A_keep_existing | 250 | 374 | 119 | 255 | 0 | 68.18 | 1 | 35 |
| B_two_families | 250 | 288 | 119 | 169 | 86 | 58.68 | 1 | 35 |
| C_one_family | 250 | 288 | 119 | 169 | 86 | 58.68 | 1 | 35 |
| D_audience_half | 250 | 282 | 118 | 164 | 91 | 58.16 | 0 | 34 |
| E_low_evidence_guard | 250 | 288 | 119 | 169 | 86 | 58.68 | 1 | 35 |
| score_only | 300 | 184 | 54 | 130 | 125 | 70.65 | 0 | 17 |
| A_keep_existing | 300 | 309 | 54 | 255 | 0 | 82.52 | 0 | 17 |
| B_two_families | 300 | 184 | 54 | 130 | 125 | 70.65 | 0 | 17 |
| C_one_family | 300 | 184 | 54 | 130 | 125 | 70.65 | 0 | 17 |
| D_audience_half | 300 | 184 | 54 | 130 | 125 | 70.65 | 0 | 17 |
| E_low_evidence_guard | 300 | 184 | 54 | 130 | 125 | 70.65 | 0 | 17 |
| score_only | 350 | 129 | 27 | 102 | 153 | 79.07 | 0 | 11 |
| A_keep_existing | 350 | 282 | 27 | 255 | 0 | 90.43 | 0 | 11 |
| B_two_families | 350 | 129 | 27 | 102 | 153 | 79.07 | 0 | 11 |
| C_one_family | 350 | 129 | 27 | 102 | 153 | 79.07 | 0 | 11 |
| D_audience_half | 350 | 129 | 27 | 102 | 153 | 79.07 | 0 | 11 |
| E_low_evidence_guard | 350 | 129 | 27 | 102 | 153 | 79.07 | 0 | 11 |
| score_only | 400 | 88 | 8 | 80 | 175 | 90.91 | 0 | 5 |
| A_keep_existing | 400 | 263 | 8 | 255 | 0 | 96.96 | 0 | 5 |
| B_two_families | 400 | 88 | 8 | 80 | 175 | 90.91 | 0 | 5 |
| C_one_family | 400 | 88 | 8 | 80 | 175 | 90.91 | 0 | 5 |
| D_audience_half | 400 | 88 | 8 | 80 | 175 | 90.91 | 0 | 5 |
| E_low_evidence_guard | 400 | 88 | 8 | 80 | 175 | 90.91 | 0 | 5 |

## Numerical shortlist for product review

These four operating points span retention-first, broad guarded discovery and evidence-led replacement. They are review candidates, not a quality ranking or a selected production policy.

| Policy | Threshold | Total | New | Retained | Lost | Overlap % | New Audience>50% | Recent new |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_keep_existing | 250 | 374 | 119 | 255 | 0 | 68.18 | 1 | 35 |
| A_keep_existing | 300 | 309 | 54 | 255 | 0 | 82.52 | 0 | 17 |
| E_low_evidence_guard | 125 | 787 | 536 | 251 | 4 | 31.89 | 133 | 104 |
| D_audience_half | 200 | 381 | 199 | 182 | 73 | 47.77 | 0 | 47 |

### A_keep_existing_250

Preserves all existing films and adds 119; a moderate expansion with one audience-dominant new case.

Trade-off: 119 new; 0 current losses; 1 audience-dominant new; 35 recent new. Known positive taste losses: 0.
Full lists: [new](candidates/A_keep_existing_250-new.csv), [lost](candidates/A_keep_existing_250-lost.csv), [borderline](candidates/A_keep_existing_250-borderline.csv).

#### top newly admitted

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 | 5 | False | True | False | unknown |
| Anora | 2024 | 499.51 | 79.91 | 419.6 | 4 | False | True | False | unknown |
| The Favourite | 2018 | 479.03 | 95.19 | 383.84 | 6 | False | True | False | unknown |
| Tár | 2022 | 455.62 | 85.67 | 369.95 | 6 | False | True | False | unknown |
| One Battle After Another | 2025 | 439.72 | 104.72 | 335.0 | 4 | False | True | False | unknown |
| Poor Things | 2023 | 437.2 | 96.92 | 340.28 | 4 | False | True | False | unknown |
| BlacKkKlansman | 2018 | 430.21 | 95.19 | 335.02 | 4 | False | True | False | unknown |
| Joker | 2019 | 413.44 | 119.42 | 294.02 | 4 | False | True | False | unknown |
| Atonement | 2007 | 388.42 | 106.44 | 281.98 | 4 | False | True | False | unknown |
| Triangle of Sadness | 2022 | 380.42 | 66.64 | 313.78 | 4 | False | True | False | unknown |

#### borderline above score

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I'm Not There | 2007 | 250.44 | 46.34 | 204.1 | 4 | False | True | False | unknown |
| The Wonders | 2014 | 251.34 | 32.23 | 219.11 | 3 | False | True | False | unknown |
| Honeyland | 2019 | 251.56 | 82.57 | 168.99 | 3 | False | True | False | unknown |
| Hell or High Water | 2016 | 251.58 | 93.17 | 158.41 | 3 | False | True | False | unknown |
| Dune: Part Two | 2024 | 252.05 | 146.25 | 105.8 | 2 | False | True | False | unknown |
| The Help | 2011 | 252.16 | 117.69 | 134.47 | 3 | True | True | False | unknown |
| You Can Count on Me | 2000 | 252.4 | 68.03 | 184.37 | 3 | False | True | False | unknown |
| Memories of Murder | 2003 | 252.96 | 135.0 | 117.96 | 2 | True | True | False | unknown |
| Captain Phillips | 2013 | 253.03 | 94.91 | 158.12 | 3 | False | True | False | unknown |
| Requiem for a Dream | 2000 | 253.86 | 130.97 | 122.89 | 4 | True | True | False | unknown |

#### borderline below score

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Crash | 2004 | 249.73 | 45.0 | 204.73 | 5 | True | True | False | unknown |
| Hedwig and the Angry Inch | 2001 | 248.83 | 95.89 | 152.94 | 3 | False | False | False | unknown |
| District 9 | 2009 | 248.65 | 98.66 | 149.99 | 3 | False | False | False | unknown |
| Hugo | 2011 | 247.27 | 66.34 | 180.93 | 3 | False | False | False | unknown |
| Fahrenheit 9/11 | 2004 | 247.19 | 69.62 | 177.57 | 3 | False | False | False | unknown |
| The Rider | 2017 | 246.86 | 71.71 | 175.15 | 3 | False | False | False | unknown |
| An Education | 2009 | 246.6 | 60.09 | 186.51 | 4 | False | False | False | unknown |
| The Big Short | 2015 | 246.6 | 100.67 | 145.93 | 4 | False | False | False | unknown |
| I Am Not Your Negro | 2016 | 246.43 | 100.16 | 146.27 | 3 | True | True | False | unknown |
| Bacurau | 2019 | 245.87 | 75.18 | 170.69 | 3 | False | False | False | unknown |

#### surprising inclusions review

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dune: Part Two | 2024 | 252.05 | 146.25 | 105.8 | 2 | False | True | False | unknown |
| Isle of Dogs | 2018 | 256.48 | 112.22 | 144.26 | 3 | False | True | False | unknown |
| I'm Still Here | 2024 | 318.48 | 135.0 | 183.48 | 3 | False | True | False | unknown |
| The Imitation Game | 2014 | 255.69 | 108.17 | 147.52 | 3 | False | True | False | unknown |
| Sinners | 2025 | 262.79 | 100.97 | 161.82 | 3 | False | True | False | unknown |
| Train Dreams | 2025 | 262.91 | 100.97 | 161.94 | 3 | False | True | False | unknown |
| Captain Phillips | 2013 | 253.03 | 94.91 | 158.12 | 3 | False | True | False | unknown |
| Like Father, Like Son | 2013 | 268.39 | 100.42 | 167.97 | 3 | False | True | False | unknown |
| Hell or High Water | 2016 | 251.58 | 93.17 | 158.41 | 3 | False | True | False | unknown |
| The Fabelmans | 2022 | 259.55 | 95.19 | 164.36 | 3 | False | True | False | unknown |

#### surprising exclusions review

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### highest score guard exclusions

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### high audience weak evidence selected

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Howl's Moving Castle | 2004 | 262.96 | 138.75 | 124.21 | 3 | True | True | False | unknown |
| Kill Bill: Vol. 1 | 2003 | 262.75 | 132.98 | 129.77 | 3 | True | True | False | unknown |
| Interstellar | 2014 | 255.52 | 150.0 | 105.52 | 3 | True | True | False | unknown |
| Requiem for a Dream | 2000 | 253.86 | 130.97 | 122.89 | 4 | True | True | False | unknown |
| Memories of Murder | 2003 | 252.96 | 135.0 | 117.96 | 2 | True | True | False | unknown |
| Dune: Part Two | 2024 | 252.05 | 146.25 | 105.8 | 2 | False | True | False | unknown |
| Coco | 2017 | 241.7 | 134.72 | 106.98 | 2 | True | True | False | unknown |
| Downfall | 2004 | 233.3 | 127.22 | 106.08 | 3 | True | True | False | unknown |
| Top Gun: Maverick | 2022 | 233.01 | 121.44 | 111.57 | 3 | True | True | False | unknown |
| Paddington 2 | 2017 | 224.22 | 112.22 | 112.0 | 2 | True | True | False | unknown |

#### high audience weak evidence excluded

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nobody Knows | 2004 | 237.31 | 118.82 | 118.49 | 3 | False | False | False | unknown |
| No Other Land | 2024 | 221.31 | 130.91 | 90.4 | 2 | False | False | False | unknown |
| The Wind Rises | 2013 | 217.86 | 112.22 | 105.64 | 3 | False | False | False | unknown |
| 13th | 2016 | 209.11 | 125.95 | 83.16 | 3 | False | False | False | unknown |
| Wolfwalkers | 2020 | 207.53 | 116.1 | 91.43 | 3 | False | False | False | unknown |
| Dallas Buyers Club | 2013 | 203.71 | 110.19 | 93.52 | 2 | False | False | False | unknown |
| The Intouchables | 2011 | 203.22 | 144.23 | 58.99 | 2 | False | False | False | unknown |
| Jojo Rabbit | 2019 | 200.39 | 110.19 | 90.2 | 2 | False | False | False | unknown |
| The Wild Robot | 2024 | 199.01 | 129.23 | 69.78 | 2 | False | False | False | unknown |
| The Martian | 2015 | 197.29 | 102.41 | 94.88 | 2 | False | False | False | unknown |

#### strong non audience low audience share

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Goodbye to Language | 2014 | 294.08 | 14.65 | 279.43 | 4 | True | True | False | unknown |
| The Assassin | 2015 | 288.37 | 21.96 | 266.41 | 4 | True | True | False | unknown |
| Titane | 2021 | 294.53 | 28.84 | 265.69 | 3 | True | True | False | unknown |
| The Tree of Life | 2011 | 523.69 | 57.41 | 466.28 | 7 | True | True | True | watched |
| The Power of the Dog | 2021 | 449.25 | 51.64 | 397.61 | 4 | True | True | False | unknown |
| Nomadland | 2020 | 618.9 | 76.16 | 542.74 | 5 | True | True | False | unknown |
| Blue Is the Warmest Colour | 2013 | 426.65 | 52.78 | 373.87 | 4 | True | True | False | unknown |
| Elephant | 2003 | 347.82 | 45.58 | 302.24 | 3 | True | True | False | unknown |
| Boyhood | 2014 | 748.89 | 98.66 | 650.23 | 7 | True | True | True | watched |
| Uncle Boonmee Who Can Recall His Past Lives | 2010 | 391.67 | 53.03 | 338.64 | 4 | True | True | False | watched |

#### recent new

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 | 5 | False | True | False | unknown |
| Anora | 2024 | 499.51 | 79.91 | 419.6 | 4 | False | True | False | unknown |
| Tár | 2022 | 455.62 | 85.67 | 369.95 | 6 | False | True | False | unknown |
| One Battle After Another | 2025 | 439.72 | 104.72 | 335.0 | 4 | False | True | False | unknown |
| Poor Things | 2023 | 437.2 | 96.92 | 340.28 | 4 | False | True | False | unknown |
| Triangle of Sadness | 2022 | 380.42 | 66.64 | 313.78 | 4 | False | True | False | unknown |
| The Voice of Hind Rajab | 2025 | 367.42 | 117.79 | 249.63 | 3 | False | True | False | unknown |
| Minari | 2020 | 365.41 | 97.22 | 268.19 | 5 | False | True | False | unknown |
| Another Round | 2020 | 360.7 | 108.47 | 252.23 | 4 | False | True | False | unknown |
| The Banshees of Inisherin | 2022 | 355.66 | 104.72 | 250.94 | 4 | False | True | False | unknown |

#### older new

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Favourite | 2018 | 479.03 | 95.19 | 383.84 | 6 | False | True | False | unknown |
| BlacKkKlansman | 2018 | 430.21 | 95.19 | 335.02 | 4 | False | True | False | unknown |
| Joker | 2019 | 413.44 | 119.42 | 294.02 | 4 | False | True | False | unknown |
| Atonement | 2007 | 388.42 | 106.44 | 281.98 | 4 | False | True | False | unknown |
| The Diving Bell and the Butterfly | 2007 | 375.94 | 111.82 | 264.12 | 5 | False | True | False | unknown |
| Winter Sleep | 2014 | 369.24 | 110.92 | 258.32 | 3 | False | True | False | unknown |
| Zero Dark Thirty | 2012 | 363.73 | 74.14 | 289.59 | 5 | False | True | False | unknown |
| The Revenant | 2015 | 363.68 | 108.17 | 255.51 | 4 | False | True | False | unknown |
| Drive | 2011 | 360.97 | 100.67 | 260.3 | 4 | False | True | False | unknown |
| Babel | 2006 | 359.48 | 74.14 | 285.34 | 4 | False | True | False | unknown |

#### Existing positive taste sanity check

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Boyhood | 2014 | 748.89 | 98.66 | 650.23 | 7 | True | True | True | watched |
| The Lives of Others | 2006 | 665.79 | 146.25 | 519.54 | 6 | True | True | True | watched |
| Moonlight | 2016 | 659.18 | 102.98 | 556.2 | 6 | True | True | True | watched |
| A Prophet | 2009 | 562.43 | 117.98 | 444.45 | 6 | True | True | True | watched |
| The White Ribbon | 2009 | 553.38 | 114.66 | 438.72 | 5 | True | True | True | watched |
| Lost in Translation | 2003 | 537.71 | 85.39 | 452.32 | 7 | True | True | True | watched |
| The Tree of Life | 2011 | 523.69 | 57.41 | 466.28 | 7 | True | True | True | watched |
| Get Out | 2017 | 506.43 | 112.22 | 394.21 | 5 | True | True | True | watched |
| Call Me by Your Name | 2017 | 481.63 | 100.67 | 380.96 | 6 | True | True | True | watched |
| Melancholia | 2011 | 389.7 | 68.66 | 321.04 | 5 | True | True | True | watched |
| Amores Perros | 2000 | 347.19 | 125.48 | 221.71 | 4 | True | True | True | watched |
| Dogville | 2003 | 291.71 | 125.48 | 166.23 | 3 | True | True | True | watched |
| The Turin Horse | 2011 | 240.12 | 88.26 | 151.86 | 3 | True | True | True | watched |

### A_keep_existing_300

Preserves all existing films with a smaller 54-film expansion and no audience-dominant new cases.

Trade-off: 54 new; 0 current losses; 0 audience-dominant new; 17 recent new. Known positive taste losses: 0.
Full lists: [new](candidates/A_keep_existing_300-new.csv), [lost](candidates/A_keep_existing_300-lost.csv), [borderline](candidates/A_keep_existing_300-borderline.csv).

#### top newly admitted

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 | 5 | False | True | False | unknown |
| Anora | 2024 | 499.51 | 79.91 | 419.6 | 4 | False | True | False | unknown |
| The Favourite | 2018 | 479.03 | 95.19 | 383.84 | 6 | False | True | False | unknown |
| Tár | 2022 | 455.62 | 85.67 | 369.95 | 6 | False | True | False | unknown |
| One Battle After Another | 2025 | 439.72 | 104.72 | 335.0 | 4 | False | True | False | unknown |
| Poor Things | 2023 | 437.2 | 96.92 | 340.28 | 4 | False | True | False | unknown |
| BlacKkKlansman | 2018 | 430.21 | 95.19 | 335.02 | 4 | False | True | False | unknown |
| Joker | 2019 | 413.44 | 119.42 | 294.02 | 4 | False | True | False | unknown |
| Atonement | 2007 | 388.42 | 106.44 | 281.98 | 4 | False | True | False | unknown |
| Triangle of Sadness | 2022 | 380.42 | 66.64 | 313.78 | 4 | False | True | False | unknown |

#### borderline above score

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| On Body and Soul | 2017 | 301.01 | 64.54 | 236.47 | 4 | False | True | False | unknown |
| Finding Nemo | 2003 | 301.12 | 121.44 | 179.68 | 4 | True | True | False | unknown |
| Beasts of the Southern Wild | 2012 | 301.31 | 68.78 | 232.53 | 4 | False | True | False | unknown |
| The Worst Person in the World | 2021 | 301.47 | 108.47 | 193.0 | 5 | True | True | False | unknown |
| Distant | 2002 | 301.78 | 65.52 | 236.26 | 3 | True | True | False | unknown |
| Timbuktu | 2014 | 302.12 | 44.23 | 257.89 | 5 | False | True | False | unknown |
| All the Beauty and the Bloodshed | 2022 | 303.92 | 81.37 | 222.55 | 4 | False | True | False | unknown |
| The Kid with a Bike | 2011 | 306.53 | 60.65 | 245.88 | 3 | False | True | False | unknown |
| A Beautiful Mind | 2001 | 306.68 | 115.67 | 191.01 | 4 | True | True | False | unknown |
| Pain and Glory | 2019 | 307.84 | 97.81 | 210.03 | 4 | False | True | False | unknown |

#### borderline below score

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dune | 2021 | 299.36 | 108.17 | 191.19 | 4 | False | False | False | unknown |
| Holy Motors | 2012 | 299.17 | 67.99 | 231.18 | 4 | True | True | False | unknown |
| The Incredibles | 2004 | 298.85 | 119.72 | 179.13 | 3 | True | True | False | unknown |
| The Son's Room | 2001 | 298.17 | 56.5 | 241.67 | 3 | False | False | False | unknown |
| Good Night, and Good Luck. | 2005 | 298.07 | 68.65 | 229.42 | 5 | False | False | False | unknown |
| Hamnet | 2025 | 297.52 | 117.98 | 179.54 | 4 | False | False | False | unknown |
| Flee | 2021 | 297.34 | 101.95 | 195.39 | 3 | False | False | False | unknown |
| Incendies | 2010 | 296.66 | 142.5 | 154.16 | 4 | True | True | False | unknown |
| The Holdovers | 2023 | 294.66 | 127.5 | 167.16 | 4 | True | True | False | unknown |
| Titane | 2021 | 294.53 | 28.84 | 265.69 | 3 | True | True | False | unknown |

#### surprising inclusions review

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I'm Still Here | 2024 | 318.48 | 135.0 | 183.48 | 3 | False | True | False | unknown |
| Close | 2022 | 324.2 | 104.75 | 219.45 | 3 | False | True | False | unknown |
| The Voice of Hind Rajab | 2025 | 367.42 | 117.79 | 249.63 | 3 | False | True | False | unknown |
| Winter Sleep | 2014 | 369.24 | 110.92 | 258.32 | 3 | False | True | False | unknown |
| I, Daniel Blake | 2016 | 350.77 | 101.72 | 249.05 | 3 | False | True | False | unknown |
| The Wind That Shakes the Barley | 2006 | 310.16 | 89.83 | 220.33 | 3 | False | True | False | unknown |
| Lust, Caution | 2007 | 327.5 | 79.33 | 248.17 | 3 | False | True | False | unknown |
| 120 BPM (Beats Per Minute) | 2017 | 308.89 | 73.52 | 235.37 | 3 | False | True | False | unknown |
| The Hand of God | 2021 | 312.97 | 72.29 | 240.68 | 3 | False | True | False | unknown |
| The Brutalist | 2024 | 350.72 | 78.17 | 272.55 | 3 | False | True | False | unknown |

#### surprising exclusions review

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### highest score guard exclusions

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### high audience weak evidence selected

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Howl's Moving Castle | 2004 | 262.96 | 138.75 | 124.21 | 3 | True | True | False | unknown |
| Kill Bill: Vol. 1 | 2003 | 262.75 | 132.98 | 129.77 | 3 | True | True | False | unknown |
| Interstellar | 2014 | 255.52 | 150.0 | 105.52 | 3 | True | True | False | unknown |
| Requiem for a Dream | 2000 | 253.86 | 130.97 | 122.89 | 4 | True | True | False | unknown |
| Memories of Murder | 2003 | 252.96 | 135.0 | 117.96 | 2 | True | True | False | unknown |
| Coco | 2017 | 241.7 | 134.72 | 106.98 | 2 | True | True | False | unknown |
| Downfall | 2004 | 233.3 | 127.22 | 106.08 | 3 | True | True | False | unknown |
| Top Gun: Maverick | 2022 | 233.01 | 121.44 | 111.57 | 3 | True | True | False | unknown |
| Paddington 2 | 2017 | 224.22 | 112.22 | 112.0 | 2 | True | True | False | unknown |
| Perfect Days | 2023 | 222.16 | 127.5 | 94.66 | 4 | True | True | False | unknown |

#### high audience weak evidence excluded

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dune: Part Two | 2024 | 252.05 | 146.25 | 105.8 | 2 | False | False | False | unknown |
| Nobody Knows | 2004 | 237.31 | 118.82 | 118.49 | 3 | False | False | False | unknown |
| No Other Land | 2024 | 221.31 | 130.91 | 90.4 | 2 | False | False | False | unknown |
| The Wind Rises | 2013 | 217.86 | 112.22 | 105.64 | 3 | False | False | False | unknown |
| 13th | 2016 | 209.11 | 125.95 | 83.16 | 3 | False | False | False | unknown |
| Wolfwalkers | 2020 | 207.53 | 116.1 | 91.43 | 3 | False | False | False | unknown |
| Dallas Buyers Club | 2013 | 203.71 | 110.19 | 93.52 | 2 | False | False | False | unknown |
| The Intouchables | 2011 | 203.22 | 144.23 | 58.99 | 2 | False | False | False | unknown |
| Jojo Rabbit | 2019 | 200.39 | 110.19 | 90.2 | 2 | False | False | False | unknown |
| The Wild Robot | 2024 | 199.01 | 129.23 | 69.78 | 2 | False | False | False | unknown |

#### strong non audience low audience share

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Tree of Life | 2011 | 523.69 | 57.41 | 466.28 | 7 | True | True | True | watched |
| The Power of the Dog | 2021 | 449.25 | 51.64 | 397.61 | 4 | True | True | False | unknown |
| Nomadland | 2020 | 618.9 | 76.16 | 542.74 | 5 | True | True | False | unknown |
| Blue Is the Warmest Colour | 2013 | 426.65 | 52.78 | 373.87 | 4 | True | True | False | unknown |
| Elephant | 2003 | 347.82 | 45.58 | 302.24 | 3 | True | True | False | unknown |
| Boyhood | 2014 | 748.89 | 98.66 | 650.23 | 7 | True | True | True | watched |
| Uncle Boonmee Who Can Recall His Past Lives | 2010 | 391.67 | 53.03 | 338.64 | 4 | True | True | False | watched |
| The Zone of Interest | 2023 | 591.21 | 81.92 | 509.29 | 5 | True | True | False | unknown |
| Brokeback Mountain | 2005 | 803.78 | 114.23 | 689.55 | 7 | True | True | False | watched |
| The Hurt Locker | 2008 | 575.75 | 83.66 | 492.09 | 7 | True | True | False | unknown |

#### recent new

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 | 5 | False | True | False | unknown |
| Anora | 2024 | 499.51 | 79.91 | 419.6 | 4 | False | True | False | unknown |
| Tár | 2022 | 455.62 | 85.67 | 369.95 | 6 | False | True | False | unknown |
| One Battle After Another | 2025 | 439.72 | 104.72 | 335.0 | 4 | False | True | False | unknown |
| Poor Things | 2023 | 437.2 | 96.92 | 340.28 | 4 | False | True | False | unknown |
| Triangle of Sadness | 2022 | 380.42 | 66.64 | 313.78 | 4 | False | True | False | unknown |
| The Voice of Hind Rajab | 2025 | 367.42 | 117.79 | 249.63 | 3 | False | True | False | unknown |
| Minari | 2020 | 365.41 | 97.22 | 268.19 | 5 | False | True | False | unknown |
| Another Round | 2020 | 360.7 | 108.47 | 252.23 | 4 | False | True | False | unknown |
| The Banshees of Inisherin | 2022 | 355.66 | 104.72 | 250.94 | 4 | False | True | False | unknown |

#### older new

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Favourite | 2018 | 479.03 | 95.19 | 383.84 | 6 | False | True | False | unknown |
| BlacKkKlansman | 2018 | 430.21 | 95.19 | 335.02 | 4 | False | True | False | unknown |
| Joker | 2019 | 413.44 | 119.42 | 294.02 | 4 | False | True | False | unknown |
| Atonement | 2007 | 388.42 | 106.44 | 281.98 | 4 | False | True | False | unknown |
| The Diving Bell and the Butterfly | 2007 | 375.94 | 111.82 | 264.12 | 5 | False | True | False | unknown |
| Winter Sleep | 2014 | 369.24 | 110.92 | 258.32 | 3 | False | True | False | unknown |
| Zero Dark Thirty | 2012 | 363.73 | 74.14 | 289.59 | 5 | False | True | False | unknown |
| The Revenant | 2015 | 363.68 | 108.17 | 255.51 | 4 | False | True | False | unknown |
| Drive | 2011 | 360.97 | 100.67 | 260.3 | 4 | False | True | False | unknown |
| Babel | 2006 | 359.48 | 74.14 | 285.34 | 4 | False | True | False | unknown |

#### Existing positive taste sanity check

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Boyhood | 2014 | 748.89 | 98.66 | 650.23 | 7 | True | True | True | watched |
| The Lives of Others | 2006 | 665.79 | 146.25 | 519.54 | 6 | True | True | True | watched |
| Moonlight | 2016 | 659.18 | 102.98 | 556.2 | 6 | True | True | True | watched |
| A Prophet | 2009 | 562.43 | 117.98 | 444.45 | 6 | True | True | True | watched |
| The White Ribbon | 2009 | 553.38 | 114.66 | 438.72 | 5 | True | True | True | watched |
| Lost in Translation | 2003 | 537.71 | 85.39 | 452.32 | 7 | True | True | True | watched |
| The Tree of Life | 2011 | 523.69 | 57.41 | 466.28 | 7 | True | True | True | watched |
| Get Out | 2017 | 506.43 | 112.22 | 394.21 | 5 | True | True | True | watched |
| Call Me by Your Name | 2017 | 481.63 | 100.67 | 380.96 | 6 | True | True | True | watched |
| Melancholia | 2011 | 389.7 | 68.66 | 321.04 | 5 | True | True | True | watched |
| Amores Perros | 2000 | 347.19 | 125.48 | 221.71 | 4 | True | True | True | watched |
| Dogville | 2003 | 291.71 | 125.48 | 166.23 | 3 | True | True | True | watched |
| The Turin Horse | 2011 | 240.12 | 88.26 | 151.86 | 3 | True | True | True | watched |

### E_low_evidence_guard_125

Broad discovery option; removes audience-only and audience-dominant single-family admissions while preserving strong single-family evidence.

Trade-off: 536 new; 4 current losses; 133 audience-dominant new; 104 recent new. Known positive taste losses: 0.
Full lists: [new](candidates/E_low_evidence_guard_125-new.csv), [lost](candidates/E_low_evidence_guard_125-lost.csv), [borderline](candidates/E_low_evidence_guard_125-borderline.csv).

#### top newly admitted

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 | 5 | False | True | False | unknown |
| Anora | 2024 | 499.51 | 79.91 | 419.6 | 4 | False | True | False | unknown |
| The Favourite | 2018 | 479.03 | 95.19 | 383.84 | 6 | False | True | False | unknown |
| Tár | 2022 | 455.62 | 85.67 | 369.95 | 6 | False | True | False | unknown |
| One Battle After Another | 2025 | 439.72 | 104.72 | 335.0 | 4 | False | True | False | unknown |
| Poor Things | 2023 | 437.2 | 96.92 | 340.28 | 4 | False | True | False | unknown |
| BlacKkKlansman | 2018 | 430.21 | 95.19 | 335.02 | 4 | False | True | False | unknown |
| Joker | 2019 | 413.44 | 119.42 | 294.02 | 4 | False | True | False | unknown |
| Atonement | 2007 | 388.42 | 106.44 | 281.98 | 4 | False | True | False | unknown |
| Triangle of Sadness | 2022 | 380.42 | 66.64 | 313.78 | 4 | False | True | False | unknown |

#### borderline above score

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Descent | 2005 | 125.05 | 60.86 | 64.19 | 2 | False | True | False | unknown |
| Om Shanti Om | 2007 | 125.17 | 65.5 | 59.67 | 1 | False | False | False | unknown |
| Dangal | 2016 | 125.19 | 125.19 | 0.0 | 0 | False | False | False | unknown |
| Happy Hour | 2015 | 125.2 | 51.86 | 73.34 | 1 | False | True | False | unknown |
| Incredibles 2 | 2018 | 125.42 | 60.58 | 64.84 | 2 | False | True | False | unknown |
| Sorry, Baby | 2025 | 125.46 | 79.52 | 45.94 | 2 | False | True | False | unknown |
| The Rescue | 2021 | 125.57 | 99.73 | 25.84 | 1 | False | False | False | unknown |
| Victoria | 2015 | 125.84 | 86.3 | 39.54 | 2 | False | True | False | unknown |
| Mysteries of Lisbon | 2010 | 126.26 | 20.8 | 105.46 | 2 | False | True | False | unknown |
| Summer Hours | 2008 | 126.36 | 35.13 | 91.23 | 2 | False | True | False | unknown |

#### borderline below score

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Star Trek | 2009 | 124.65 | 92.89 | 31.76 | 1 | False | False | False | unknown |
| Deadpool | 2016 | 124.64 | 96.64 | 28.0 | 2 | False | False | False | unknown |
| Guardians of the Galaxy Vol. 3 | 2023 | 124.59 | 110.19 | 14.4 | 1 | False | False | False | unknown |
| Love Actually | 2003 | 124.52 | 66.34 | 58.18 | 1 | False | False | False | unknown |
| Inside Out 2 | 2024 | 124.51 | 66.34 | 58.17 | 2 | False | False | False | unknown |
| Days | 2020 | 124.44 | 27.07 | 97.37 | 3 | False | False | False | unknown |
| Leviathan | 2012 | 124.24 | 22.25 | 101.99 | 2 | False | False | False | unknown |
| The Batman | 2022 | 124.04 | 106.44 | 17.6 | 1 | False | False | False | unknown |
| The Fall | 2006 | 123.75 | 123.75 | 0.0 | 0 | False | False | False | unknown |
| Shirkers | 2018 | 123.45 | 58.64 | 64.81 | 3 | False | False | False | unknown |

#### surprising inclusions review

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Blind Side | 2009 | 129.33 | 64.33 | 65.0 | 1 | False | True | False | unknown |
| Bohemian Rhapsody | 2018 | 171.34 | 81.34 | 90.0 | 1 | False | True | False | unknown |
| Happy Hour | 2015 | 125.2 | 51.86 | 73.34 | 1 | False | True | False | unknown |
| Lovers Rock | 2020 | 147.77 | 59.66 | 88.11 | 1 | False | True | False | unknown |
| Demon Slayer: Kimetsu No Yaiba Infinity Castle | 2025 | 153.71 | 128.99 | 24.72 | 2 | False | True | False | unknown |
| I Saw the Devil | 2010 | 133.2 | 106.44 | 26.76 | 2 | False | True | False | unknown |
| The Hateful Eight | 2015 | 133.25 | 106.44 | 26.81 | 2 | False | True | False | unknown |
| Rush | 2013 | 142.59 | 111.92 | 30.67 | 2 | False | True | False | unknown |
| Star Wars: Episode III - Revenge of the Sith | 2005 | 140.59 | 108.47 | 32.12 | 2 | False | True | False | unknown |
| The Raid: Redemption | 2011 | 128.72 | 98.94 | 29.78 | 2 | False | True | False | unknown |

#### surprising exclusions review

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| My Octopus Teacher | 2020 | 167.8 | 107.8 | 60.0 | 1 | True | False | False | unknown |
| Inside Job | 2010 | 132.28 | 100.73 | 31.55 | 1 | True | False | False | unknown |
| In Vanda's Room | 2000 | 122.06 | 24.73 | 97.33 | 1 | True | False | False | unknown |
| The Intruder | 2004 | 108.67 | 15.2 | 93.47 | 1 | True | False | False | unknown |

#### highest score guard exclusions

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Odyssey | 2026 | 183.85 | 146.25 | 37.6 | 1 | False | False | False | unknown |
| It's Such a Beautiful Day | 2012 | 172.08 | 92.2 | 79.88 | 1 | False | False | False | unknown |
| Gangs of Wasseypur | 2012 | 169.65 | 110.88 | 58.77 | 1 | False | False | False | unknown |
| Project Hail Mary | 2026 | 168.35 | 138.75 | 29.6 | 1 | False | False | False | unknown |
| My Octopus Teacher | 2020 | 167.8 | 107.8 | 60.0 | 1 | True | False | False | unknown |
| Your Name. | 2016 | 166.67 | 140.48 | 26.19 | 1 | False | False | False | unknown |
| American Psycho | 2000 | 163.53 | 87.41 | 76.12 | 1 | False | False | False | unknown |
| Avengers: Endgame | 2019 | 158.38 | 128.94 | 29.44 | 1 | False | False | False | unknown |
| Dear Zachary: A Letter to a Son About His Father | 2008 | 155.1 | 137.68 | 17.42 | 1 | False | False | False | unknown |
| Harry Potter and the Deathly Hallows: Part 2 | 2011 | 151.93 | 117.69 | 34.24 | 1 | False | False | False | unknown |

#### high audience weak evidence selected

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Howl's Moving Castle | 2004 | 262.96 | 138.75 | 124.21 | 3 | True | True | False | unknown |
| Kill Bill: Vol. 1 | 2003 | 262.75 | 132.98 | 129.77 | 3 | True | True | False | unknown |
| Interstellar | 2014 | 255.52 | 150.0 | 105.52 | 3 | True | True | False | unknown |
| Requiem for a Dream | 2000 | 253.86 | 130.97 | 122.89 | 4 | True | True | False | unknown |
| Memories of Murder | 2003 | 252.96 | 135.0 | 117.96 | 2 | True | True | False | unknown |
| Dune: Part Two | 2024 | 252.05 | 146.25 | 105.8 | 2 | False | True | False | unknown |
| Coco | 2017 | 241.7 | 134.72 | 106.98 | 2 | True | True | False | unknown |
| Nobody Knows | 2004 | 237.31 | 118.82 | 118.49 | 3 | False | True | False | unknown |
| Downfall | 2004 | 233.3 | 127.22 | 106.08 | 3 | True | True | False | unknown |
| Top Gun: Maverick | 2022 | 233.01 | 121.44 | 111.57 | 3 | True | True | False | unknown |

#### high audience weak evidence excluded

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Odyssey | 2026 | 183.85 | 146.25 | 37.6 | 1 | False | False | False | unknown |
| It's Such a Beautiful Day | 2012 | 172.08 | 92.2 | 79.88 | 1 | False | False | False | unknown |
| Gangs of Wasseypur | 2012 | 169.65 | 110.88 | 58.77 | 1 | False | False | False | unknown |
| Project Hail Mary | 2026 | 168.35 | 138.75 | 29.6 | 1 | False | False | False | unknown |
| My Octopus Teacher | 2020 | 167.8 | 107.8 | 60.0 | 1 | True | False | False | unknown |
| Your Name. | 2016 | 166.67 | 140.48 | 26.19 | 1 | False | False | False | unknown |
| American Psycho | 2000 | 163.53 | 87.41 | 76.12 | 1 | False | False | False | unknown |
| Avengers: Endgame | 2019 | 158.38 | 128.94 | 29.44 | 1 | False | False | False | unknown |
| Dear Zachary: A Letter to a Son About His Father | 2008 | 155.1 | 137.68 | 17.42 | 1 | False | False | False | unknown |
| Harry Potter and the Deathly Hallows: Part 2 | 2011 | 151.93 | 117.69 | 34.24 | 1 | False | False | False | unknown |

#### strong non audience low audience share

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Goodbye to Language | 2014 | 294.08 | 14.65 | 279.43 | 4 | True | True | False | unknown |
| A Screaming Man | 2010 | 135.19 | 6.94 | 128.25 | 2 | False | True | False | unknown |
| Blackboards | 2000 | 146.42 | 7.96 | 138.46 | 2 | False | True | False | unknown |
| The Assassin | 2015 | 288.37 | 21.96 | 266.41 | 4 | True | True | False | unknown |
| Divine Intervention | 2002 | 210.81 | 17.57 | 193.24 | 3 | False | True | False | unknown |
| In This World | 2002 | 143.0 | 13.26 | 129.74 | 3 | False | True | False | unknown |
| The Woman Who Left | 2016 | 175.87 | 16.73 | 159.14 | 2 | False | True | False | unknown |
| Titane | 2021 | 294.53 | 28.84 | 265.69 | 3 | True | True | False | unknown |
| The Tree of Life | 2011 | 523.69 | 57.41 | 466.28 | 7 | True | True | True | watched |
| The Power of the Dog | 2021 | 449.25 | 51.64 | 397.61 | 4 | True | True | False | unknown |

#### recent new

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 | 5 | False | True | False | unknown |
| Anora | 2024 | 499.51 | 79.91 | 419.6 | 4 | False | True | False | unknown |
| Tár | 2022 | 455.62 | 85.67 | 369.95 | 6 | False | True | False | unknown |
| One Battle After Another | 2025 | 439.72 | 104.72 | 335.0 | 4 | False | True | False | unknown |
| Poor Things | 2023 | 437.2 | 96.92 | 340.28 | 4 | False | True | False | unknown |
| Triangle of Sadness | 2022 | 380.42 | 66.64 | 313.78 | 4 | False | True | False | unknown |
| The Voice of Hind Rajab | 2025 | 367.42 | 117.79 | 249.63 | 3 | False | True | False | unknown |
| Minari | 2020 | 365.41 | 97.22 | 268.19 | 5 | False | True | False | unknown |
| Another Round | 2020 | 360.7 | 108.47 | 252.23 | 4 | False | True | False | unknown |
| The Banshees of Inisherin | 2022 | 355.66 | 104.72 | 250.94 | 4 | False | True | False | unknown |

#### older new

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Favourite | 2018 | 479.03 | 95.19 | 383.84 | 6 | False | True | False | unknown |
| BlacKkKlansman | 2018 | 430.21 | 95.19 | 335.02 | 4 | False | True | False | unknown |
| Joker | 2019 | 413.44 | 119.42 | 294.02 | 4 | False | True | False | unknown |
| Atonement | 2007 | 388.42 | 106.44 | 281.98 | 4 | False | True | False | unknown |
| The Diving Bell and the Butterfly | 2007 | 375.94 | 111.82 | 264.12 | 5 | False | True | False | unknown |
| Winter Sleep | 2014 | 369.24 | 110.92 | 258.32 | 3 | False | True | False | unknown |
| Zero Dark Thirty | 2012 | 363.73 | 74.14 | 289.59 | 5 | False | True | False | unknown |
| The Revenant | 2015 | 363.68 | 108.17 | 255.51 | 4 | False | True | False | unknown |
| Drive | 2011 | 360.97 | 100.67 | 260.3 | 4 | False | True | False | unknown |
| Babel | 2006 | 359.48 | 74.14 | 285.34 | 4 | False | True | False | unknown |

#### Existing positive taste sanity check

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Boyhood | 2014 | 748.89 | 98.66 | 650.23 | 7 | True | True | True | watched |
| The Lives of Others | 2006 | 665.79 | 146.25 | 519.54 | 6 | True | True | True | watched |
| Moonlight | 2016 | 659.18 | 102.98 | 556.2 | 6 | True | True | True | watched |
| A Prophet | 2009 | 562.43 | 117.98 | 444.45 | 6 | True | True | True | watched |
| The White Ribbon | 2009 | 553.38 | 114.66 | 438.72 | 5 | True | True | True | watched |
| Lost in Translation | 2003 | 537.71 | 85.39 | 452.32 | 7 | True | True | True | watched |
| The Tree of Life | 2011 | 523.69 | 57.41 | 466.28 | 7 | True | True | True | watched |
| Get Out | 2017 | 506.43 | 112.22 | 394.21 | 5 | True | True | True | watched |
| Call Me by Your Name | 2017 | 481.63 | 100.67 | 380.96 | 6 | True | True | True | watched |
| Melancholia | 2011 | 389.7 | 68.66 | 321.04 | 5 | True | True | True | watched |
| Amores Perros | 2000 | 347.19 | 125.48 | 221.71 | 4 | True | True | True | watched |
| Dogville | 2003 | 291.71 | 125.48 | 166.23 | 3 | True | True | True | watched |
| The Turin Horse | 2011 | 240.12 | 88.26 | 151.86 | 3 | True | True | True | watched |

### D_audience_half_200

Evidence-led replacement comparator; removes audience dominance entirely but loses many currently qualified films.

Trade-off: 199 new; 73 current losses; 0 audience-dominant new; 47 recent new. Known positive taste losses: 0.
Full lists: [new](candidates/D_audience_half_200-new.csv), [lost](candidates/D_audience_half_200-lost.csv), [borderline](candidates/D_audience_half_200-borderline.csv).

#### top newly admitted

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 | 5 | False | True | False | unknown |
| Anora | 2024 | 499.51 | 79.91 | 419.6 | 4 | False | True | False | unknown |
| The Favourite | 2018 | 479.03 | 95.19 | 383.84 | 6 | False | True | False | unknown |
| Tár | 2022 | 455.62 | 85.67 | 369.95 | 6 | False | True | False | unknown |
| One Battle After Another | 2025 | 439.72 | 104.72 | 335.0 | 4 | False | True | False | unknown |
| Poor Things | 2023 | 437.2 | 96.92 | 340.28 | 4 | False | True | False | unknown |
| BlacKkKlansman | 2018 | 430.21 | 95.19 | 335.02 | 4 | False | True | False | unknown |
| Joker | 2019 | 413.44 | 119.42 | 294.02 | 4 | False | True | False | unknown |
| Atonement | 2007 | 388.42 | 106.44 | 281.98 | 4 | False | True | False | unknown |
| Triangle of Sadness | 2022 | 380.42 | 66.64 | 313.78 | 4 | False | True | False | unknown |

#### borderline above score

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Jojo Rabbit | 2019 | 200.39 | 110.19 | 90.2 | 2 | False | False | False | unknown |
| The Station Agent | 2003 | 200.53 | 82.47 | 118.06 | 3 | False | True | False | unknown |
| You Were Never Really Here | 2017 | 200.67 | 47.89 | 152.78 | 4 | False | True | False | unknown |
| Vera Drake | 2004 | 202.61 | 64.68 | 137.93 | 3 | False | True | False | unknown |
| The Witch | 2015 | 202.96 | 64.91 | 138.05 | 3 | False | True | False | unknown |
| The Intouchables | 2011 | 203.22 | 144.23 | 58.99 | 2 | False | False | False | unknown |
| The Souvenir | 2019 | 203.67 | 26.09 | 177.58 | 3 | False | True | False | unknown |
| Dallas Buyers Club | 2013 | 203.71 | 110.19 | 93.52 | 2 | False | False | False | unknown |
| Darkest Hour | 2017 | 204.14 | 68.36 | 135.78 | 3 | False | True | False | unknown |
| Soul | 2020 | 204.23 | 108.17 | 96.06 | 2 | True | False | False | unknown |

#### borderline below score

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Only Lovers Left Alive | 2013 | 199.63 | 72.41 | 127.22 | 4 | False | False | False | unknown |
| Infernal Affairs | 2002 | 199.6 | 119.72 | 79.88 | 2 | True | False | False | unknown |
| Waking Life | 2001 | 199.38 | 87.73 | 111.65 | 3 | False | False | False | unknown |
| Dogtooth | 2009 | 199.37 | 62.89 | 136.48 | 3 | True | False | False | unknown |
| Frankenstein | 2025 | 199.21 | 79.91 | 119.3 | 3 | False | False | False | unknown |
| The Wild Robot | 2024 | 199.01 | 129.23 | 69.78 | 2 | False | False | False | unknown |
| Coraline | 2009 | 198.58 | 117.98 | 80.6 | 3 | True | False | False | unknown |
| This Is England | 2006 | 198.48 | 108.47 | 90.01 | 2 | True | False | False | unknown |
| Tabu | 2012 | 198.05 | 42.69 | 155.36 | 4 | False | False | False | unknown |
| About Schmidt | 2002 | 197.46 | 56.85 | 140.61 | 4 | False | False | False | unknown |

#### surprising inclusions review

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Fighter | 2010 | 204.44 | 100.67 | 103.77 | 2 | False | True | False | unknown |
| Sentimental Value | 2025 | 230.77 | 113.36 | 117.41 | 2 | False | True | False | unknown |
| Still Walking | 2008 | 217.13 | 104.54 | 112.59 | 2 | False | True | False | unknown |
| Shaun of the Dead | 2004 | 212.12 | 100.67 | 111.45 | 2 | False | True | False | unknown |
| Flow | 2024 | 240.4 | 112.22 | 128.18 | 2 | False | True | False | unknown |
| Me and Earl and the Dying Girl | 2015 | 211.68 | 96.92 | 114.76 | 2 | False | True | False | unknown |
| Nocturnal Animals | 2016 | 208.81 | 74.14 | 134.67 | 2 | False | True | False | unknown |
| Oasis | 2002 | 215.39 | 71.64 | 143.75 | 2 | False | True | False | unknown |
| Devils on the Doorstep | 2000 | 240.3 | 61.44 | 178.86 | 2 | False | True | False | unknown |
| Lagaan: Once Upon a Time in India | 2001 | 207.81 | 102.01 | 105.8 | 3 | False | True | False | unknown |

#### surprising exclusions review

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Howl's Moving Castle | 2004 | 262.96 | 138.75 | 124.21 | 3 | True | False | False | unknown |
| Kill Bill: Vol. 1 | 2003 | 262.75 | 132.98 | 129.77 | 3 | True | False | False | unknown |
| Interstellar | 2014 | 255.52 | 150.0 | 105.52 | 3 | True | False | False | unknown |
| Requiem for a Dream | 2000 | 253.86 | 130.97 | 122.89 | 4 | True | False | False | unknown |
| Memories of Murder | 2003 | 252.96 | 135.0 | 117.96 | 2 | True | False | False | unknown |
| Coco | 2017 | 241.7 | 134.72 | 106.98 | 2 | True | False | False | unknown |
| Downfall | 2004 | 233.3 | 127.22 | 106.08 | 3 | True | False | False | unknown |
| Top Gun: Maverick | 2022 | 233.01 | 121.44 | 111.57 | 3 | True | False | False | unknown |
| Paddington 2 | 2017 | 224.22 | 112.22 | 112.0 | 2 | True | False | False | unknown |
| Perfect Days | 2023 | 222.16 | 127.5 | 94.66 | 4 | True | False | False | unknown |

#### highest score guard exclusions

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Howl's Moving Castle | 2004 | 262.96 | 138.75 | 124.21 | 3 | True | False | False | unknown |
| Kill Bill: Vol. 1 | 2003 | 262.75 | 132.98 | 129.77 | 3 | True | False | False | unknown |
| Interstellar | 2014 | 255.52 | 150.0 | 105.52 | 3 | True | False | False | unknown |
| Requiem for a Dream | 2000 | 253.86 | 130.97 | 122.89 | 4 | True | False | False | unknown |
| Memories of Murder | 2003 | 252.96 | 135.0 | 117.96 | 2 | True | False | False | unknown |
| Dune: Part Two | 2024 | 252.05 | 146.25 | 105.8 | 2 | False | False | False | unknown |
| Coco | 2017 | 241.7 | 134.72 | 106.98 | 2 | True | False | False | unknown |
| Nobody Knows | 2004 | 237.31 | 118.82 | 118.49 | 3 | False | False | False | unknown |
| Downfall | 2004 | 233.3 | 127.22 | 106.08 | 3 | True | False | False | unknown |
| Top Gun: Maverick | 2022 | 233.01 | 121.44 | 111.57 | 3 | True | False | False | unknown |

#### high audience weak evidence selected

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

#### high audience weak evidence excluded

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Howl's Moving Castle | 2004 | 262.96 | 138.75 | 124.21 | 3 | True | False | False | unknown |
| Kill Bill: Vol. 1 | 2003 | 262.75 | 132.98 | 129.77 | 3 | True | False | False | unknown |
| Interstellar | 2014 | 255.52 | 150.0 | 105.52 | 3 | True | False | False | unknown |
| Requiem for a Dream | 2000 | 253.86 | 130.97 | 122.89 | 4 | True | False | False | unknown |
| Memories of Murder | 2003 | 252.96 | 135.0 | 117.96 | 2 | True | False | False | unknown |
| Dune: Part Two | 2024 | 252.05 | 146.25 | 105.8 | 2 | False | False | False | unknown |
| Coco | 2017 | 241.7 | 134.72 | 106.98 | 2 | True | False | False | unknown |
| Nobody Knows | 2004 | 237.31 | 118.82 | 118.49 | 3 | False | False | False | unknown |
| Downfall | 2004 | 233.3 | 127.22 | 106.08 | 3 | True | False | False | unknown |
| Top Gun: Maverick | 2022 | 233.01 | 121.44 | 111.57 | 3 | True | False | False | unknown |

#### strong non audience low audience share

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Goodbye to Language | 2014 | 294.08 | 14.65 | 279.43 | 4 | True | True | False | unknown |
| The Assassin | 2015 | 288.37 | 21.96 | 266.41 | 4 | True | True | False | unknown |
| Titane | 2021 | 294.53 | 28.84 | 265.69 | 3 | True | True | False | unknown |
| The Tree of Life | 2011 | 523.69 | 57.41 | 466.28 | 7 | True | True | True | watched |
| The Power of the Dog | 2021 | 449.25 | 51.64 | 397.61 | 4 | True | True | False | unknown |
| Nomadland | 2020 | 618.9 | 76.16 | 542.74 | 5 | True | True | False | unknown |
| Blue Is the Warmest Colour | 2013 | 426.65 | 52.78 | 373.87 | 4 | True | True | False | unknown |
| The Wonders | 2014 | 251.34 | 32.23 | 219.11 | 3 | False | True | False | unknown |
| Elephant | 2003 | 347.82 | 45.58 | 302.24 | 3 | True | True | False | unknown |
| Boyhood | 2014 | 748.89 | 98.66 | 650.23 | 7 | True | True | True | watched |

#### recent new

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 | 5 | False | True | False | unknown |
| Anora | 2024 | 499.51 | 79.91 | 419.6 | 4 | False | True | False | unknown |
| Tár | 2022 | 455.62 | 85.67 | 369.95 | 6 | False | True | False | unknown |
| One Battle After Another | 2025 | 439.72 | 104.72 | 335.0 | 4 | False | True | False | unknown |
| Poor Things | 2023 | 437.2 | 96.92 | 340.28 | 4 | False | True | False | unknown |
| Triangle of Sadness | 2022 | 380.42 | 66.64 | 313.78 | 4 | False | True | False | unknown |
| The Voice of Hind Rajab | 2025 | 367.42 | 117.79 | 249.63 | 3 | False | True | False | unknown |
| Minari | 2020 | 365.41 | 97.22 | 268.19 | 5 | False | True | False | unknown |
| Another Round | 2020 | 360.7 | 108.47 | 252.23 | 4 | False | True | False | unknown |
| The Banshees of Inisherin | 2022 | 355.66 | 104.72 | 250.94 | 4 | False | True | False | unknown |

#### older new

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| The Favourite | 2018 | 479.03 | 95.19 | 383.84 | 6 | False | True | False | unknown |
| BlacKkKlansman | 2018 | 430.21 | 95.19 | 335.02 | 4 | False | True | False | unknown |
| Joker | 2019 | 413.44 | 119.42 | 294.02 | 4 | False | True | False | unknown |
| Atonement | 2007 | 388.42 | 106.44 | 281.98 | 4 | False | True | False | unknown |
| The Diving Bell and the Butterfly | 2007 | 375.94 | 111.82 | 264.12 | 5 | False | True | False | unknown |
| Winter Sleep | 2014 | 369.24 | 110.92 | 258.32 | 3 | False | True | False | unknown |
| Zero Dark Thirty | 2012 | 363.73 | 74.14 | 289.59 | 5 | False | True | False | unknown |
| The Revenant | 2015 | 363.68 | 108.17 | 255.51 | 4 | False | True | False | unknown |
| Drive | 2011 | 360.97 | 100.67 | 260.3 | 4 | False | True | False | unknown |
| Babel | 2006 | 359.48 | 74.14 | 285.34 | 4 | False | True | False | unknown |

#### Existing positive taste sanity check

| Film | Year | Score | Audience | Non-audience | Families | Current | Selected | Taste | Watched |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Boyhood | 2014 | 748.89 | 98.66 | 650.23 | 7 | True | True | True | watched |
| The Lives of Others | 2006 | 665.79 | 146.25 | 519.54 | 6 | True | True | True | watched |
| Moonlight | 2016 | 659.18 | 102.98 | 556.2 | 6 | True | True | True | watched |
| A Prophet | 2009 | 562.43 | 117.98 | 444.45 | 6 | True | True | True | watched |
| The White Ribbon | 2009 | 553.38 | 114.66 | 438.72 | 5 | True | True | True | watched |
| Lost in Translation | 2003 | 537.71 | 85.39 | 452.32 | 7 | True | True | True | watched |
| The Tree of Life | 2011 | 523.69 | 57.41 | 466.28 | 7 | True | True | True | watched |
| Get Out | 2017 | 506.43 | 112.22 | 394.21 | 5 | True | True | True | watched |
| Call Me by Your Name | 2017 | 481.63 | 100.67 | 380.96 | 6 | True | True | True | watched |
| Melancholia | 2011 | 389.7 | 68.66 | 321.04 | 5 | True | True | True | watched |
| Amores Perros | 2000 | 347.19 | 125.48 | 221.71 | 4 | True | True | True | watched |
| Dogville | 2003 | 291.71 | 125.48 | 166.23 | 3 | True | True | True | watched |
| The Turin Horse | 2011 | 240.12 | 88.26 | 151.86 | 3 | True | True | True | watched |

## Findings and sensitivity

At thresholds 200 and above, B/C/E select exactly the score-only set in this universe: family-count guards add no filtering. This is an observed dataset result, not a guarantee for future candidates.
Audience has a 150-point cap: above 300, it cannot exceed50% of total, so D is mathematically redundant. At 300, exact 50% ties pass; observed B/C/D/E also match score-only.
At 100, score-only admits 48 audience-only films; at 125, 9; at 150 and above, none observed. C becomes identical to score-only from 150 in this dataset.
E matters at the lower thresholds. It removes weak single-family/audience-dominant cases while retaining some strong single-family films that B would reject; many multi-family audience-dominant cases remain.
D can remove strong known/currently qualified films whose audience share exceeds 50%; low share is not proof of better recommendations. At 200 it loses 73 current films: 48 below threshold and 25 additional share-guard losses, while filtering only 9 new admissions. Examples include Howl's Moving Castle, Kill Bill: Vol. 1, Interstellar and Memories of Murder. Known watched losses include The Swamp, A.I. Artificial Intelligence and Platform. This is the explicit cost of the evidence-led comparator.
A preserves every baseline film and therefore also its 49 already audience-dominant cases. New-admission dominance is reported separately from retained baseline dominance.

### Incomplete Audience sensitivity

| Film | Observed | Upper possible | Missing | Thresholds potentially crossed |
| --- | --- | --- | --- | --- |
| Endless Corridor | 45.74 | 120.74 | letterboxd | 100 |
| The Silence of Swastika | 38.62 | 113.62 | letterboxd | 100 |
| Unpaarvayil | 37.58 | 112.58 | letterboxd | 100 |
| Mission Muh Dikhayi | 36.98 | 111.98 | letterboxd | 100 |
| Material | 8.04 | 83.04 | letterboxd |  |
| LaLee's Kin: The Legacy of Cotton | 8.0 | 83.0 | letterboxd |  |
| Making Memories of Murder | 2.0 | 77.0 | letterboxd |  |
| Operation Homecoming: Writing the Wartime Experience | 0.0 | 75.0 | letterboxd |  |
| Prisoner of Paradise | 0.0 | 75.0 | letterboxd |  |

All nine incomplete rows currently score below 100; none is within 10 points of the tested thresholds. Only four could theoretically cross 100 at the maximum missing Letterboxd contribution; none can reach 125. Therefore the four shortlisted options are unaffected by these nine Audience gaps under this upper bound. Other missing award/critic evidence has not been bounded here.
Potential upper-bound crossings do not assert recovered ratings or hybrid eligibility. More audience can cause D/E to reject a film even while increasing its total score.

## Artifacts and reproduction

[calibration.json](calibration.json) contains full film records/decisions, all policy ID lists, year/composition distributions and sensitivity. [Per-film CSV](per-film-policies.csv), [threshold table](threshold-summary.csv), [policy table](policy-comparison.csv), [manifest](manifest.json).
Run python qualification_calibration.py in this research worktree. Frozen input/code/config hashes are in manifest.json. No external API requests are required.
