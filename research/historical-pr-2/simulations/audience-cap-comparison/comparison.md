# Audience=150 vs Audience=200 calibration

Research only. No cap is selected and no qualification or production behavior changes.

## Reproduction and scoring

Frozen universe: 1909 IMDb IDs. Universe SHA-256: bcb725ca4577ea8a7cca8043e33e29090aaab0963b5fad45a108b24556d3518d.
Shared evidence SHA-256: 4d4a1a26e8ba2788fa9fab6d02d1c0f47869e9ee2dedad7303572957a8a80b2d.
Baseline: 8363f9393b9bc6961dc829b8ce01c9cd02fec641. Exact inputs and implementation hashes are in [manifest.json](manifest.json).

Audience=150 uses 0.75 × (IMDb + Letterboxd); Audience=200 uses 1.0 × the same raw sum.
IMDb calibration remains 6.5–8.5 and Letterboxd 3.0–4.3, with the existing logarithmic vote-confidence discount (1,000–100,000 votes).
European Recognition uses 2 × its normalized 100-point family score. Other family weights are fixed.
The existing 50% Sight & Sound corroboration alongside TSPDT remains in both runs. Critics Groups Consensus retains the existing NSFC/NYFCC/LAFCA wins, implemented Critics Choice Best Picture evidence, and capped 40-point broad-critic component.
Nominal family ceilings are 1,050/1,100 before the inherited canon overlap reduction; fully eligible ceilings after that reduction are 1,000/1,050.
Trakt/TMDb do not contribute. Missing audience components score zero without renormalization.

## Data completeness

| Measure | Count |
| --- | --- |
| candidate_count | 1909 |
| ReelDB_cached_in_universe | 1904 |
| IMDb_available_after_fallback | 1908 |
| Letterboxd_available | 1896 |
| complete_IMDb_Letterboxd_pairs | 1896 |
| incomplete_audience_pairs | 13 |
| IMDb_official_fallback_used | 4 |
| IMDb_seed_fallback_used | 0 |
| Metacritic_usable | 1614 |
| Rotten_Tomatoes_critics_usable | 1679 |
| positive_critics_family | 1328 |
| qualified_unchanged | 255 |

Per-film missing-data reasons are in [coverage.json](coverage.json). Valid low ratings and small vote counts are distinct from unavailable data.
Cached ReelDB values have no historical collection timestamps. Official IMDb fallback provenance is retained separately.
The same missingness applies to both variants; incomplete rows can underestimate audience contribution and movements.

## Comparison summary

| Measure | Count |
| --- | --- |
| score_changed | 1865 |
| rank_changed | 1858 |
| rank_up | 972 |
| rank_down | 886 |
| any_band_crossing | 736 |
| complete_audience_pairs | 1896 |
| incomplete_audience_pairs | 13 |

## Top-ranked films

### Audience=150

| Rank | Film | Year | Score | Audience | Non-audience | Complete pair |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Brokeback Mountain | 2005 | 803.78 | 114.23 | 689.55 | True |
| 2 | Boyhood | 2014 | 748.89 | 98.66 | 650.23 | True |
| 3 | Parasite | 2019 | 734.21 | 150.0 | 584.21 | True |
| 4 | There Will Be Blood | 2007 | 731.95 | 138.75 | 593.2 | True |
| 5 | Amour | 2012 | 679.91 | 121.73 | 558.18 | True |
| 6 | The Lives of Others | 2006 | 665.79 | 146.25 | 519.54 | True |
| 7 | Crouching Tiger, Hidden Dragon | 2000 | 665.52 | 112.22 | 553.3 | True |
| 8 | No Country for Old Men | 2007 | 660.66 | 138.75 | 521.91 | True |
| 9 | Moonlight | 2016 | 659.18 | 102.98 | 556.2 | True |
| 10 | Roma | 2018 | 652.58 | 104.72 | 547.86 | True |
| 11 | Mulholland Drive | 2001 | 649.43 | 127.5 | 521.93 | True |
| 12 | The Grand Budapest Hotel | 2014 | 648.95 | 129.23 | 519.72 | True |
| 13 | 12 Years a Slave | 2013 | 629.69 | 129.23 | 500.46 | True |
| 14 | Nomadland | 2020 | 618.9 | 76.16 | 542.74 | True |
| 15 | Spirited Away | 2001 | 601.29 | 150.0 | 451.29 | True |
| 16 | The Social Network | 2010 | 599.23 | 100.67 | 498.56 | True |
| 17 | The Zone of Interest | 2023 | 591.21 | 81.92 | 509.29 | True |
| 18 | The Hurt Locker | 2008 | 575.75 | 83.66 | 492.09 | True |
| 19 | The Pianist | 2002 | 573.98 | 150.0 | 423.98 | True |
| 20 | Anatomy of a Fall | 2023 | 571.43 | 104.72 | 466.71 | True |
| 21 | A Prophet | 2009 | 562.43 | 117.98 | 444.45 | True |
| 22 | In the Mood for Love | 2000 | 556.65 | 131.25 | 425.4 | True |
| 23 | The White Ribbon | 2009 | 553.38 | 114.66 | 438.72 | True |
| 24 | Spotlight | 2015 | 550.97 | 123.47 | 427.5 | True |
| 25 | Son of Saul | 2015 | 545.79 | 87.0 | 458.79 | True |

### Audience=200

| Rank | Film | Year | Score | Audience | Non-audience | Complete pair |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Brokeback Mountain | 2005 | 841.86 | 152.31 | 689.55 | True |
| 2 | Parasite | 2019 | 784.21 | 200.0 | 584.21 | True |
| 3 | Boyhood | 2014 | 781.77 | 131.54 | 650.23 | True |
| 4 | There Will Be Blood | 2007 | 778.2 | 185.0 | 593.2 | True |
| 5 | Amour | 2012 | 720.49 | 162.31 | 558.18 | True |
| 6 | The Lives of Others | 2006 | 714.54 | 195.0 | 519.54 | True |
| 7 | No Country for Old Men | 2007 | 706.91 | 185.0 | 521.91 | True |
| 8 | Crouching Tiger, Hidden Dragon | 2000 | 702.92 | 149.62 | 553.3 | True |
| 9 | Moonlight | 2016 | 693.51 | 137.31 | 556.2 | True |
| 10 | The Grand Budapest Hotel | 2014 | 692.03 | 172.31 | 519.72 | True |
| 11 | Mulholland Drive | 2001 | 691.93 | 170.0 | 521.93 | True |
| 12 | Roma | 2018 | 687.48 | 139.62 | 547.86 | True |
| 13 | 12 Years a Slave | 2013 | 672.77 | 172.31 | 500.46 | True |
| 14 | Spirited Away | 2001 | 651.29 | 200.0 | 451.29 | True |
| 15 | Nomadland | 2020 | 644.28 | 101.54 | 542.74 | True |
| 16 | The Social Network | 2010 | 632.79 | 134.23 | 498.56 | True |
| 17 | The Pianist | 2002 | 623.98 | 200.0 | 423.98 | True |
| 18 | The Zone of Interest | 2023 | 618.52 | 109.23 | 509.29 | True |
| 19 | Anatomy of a Fall | 2023 | 606.33 | 139.62 | 466.71 | True |
| 20 | The Hurt Locker | 2008 | 603.63 | 111.54 | 492.09 | True |
| 21 | A Prophet | 2009 | 601.76 | 157.31 | 444.45 | True |
| 22 | In the Mood for Love | 2000 | 600.4 | 175.0 | 425.4 | True |
| 23 | Spotlight | 2015 | 592.12 | 164.62 | 427.5 | True |
| 24 | The White Ribbon | 2009 | 591.6 | 152.88 | 438.72 | True |
| 25 | Pan's Labyrinth | 2006 | 586.85 | 177.31 | 409.54 | True |

## Biggest ranking gains

| Film | Year | Rank 150 | Rank 200 | Rank gain | Score 150 | Score 200 | Delta | Complete |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Zindagi Na Milegi Dobara | 2011 | 909 | 771 | 138 | 117.39 | 156.52 | 39.13 | True |
| A Dog's Will | 2000 | 879 | 744 | 135 | 119.74 | 159.65 | 39.91 | True |
| Demon Slayer: Kimetsu no Yaiba - The Movie: Mugen Train | 2020 | 862 | 728 | 134 | 121.44 | 161.92 | 40.48 | True |
| My Father and My Son | 2005 | 911 | 779 | 132 | 117.14 | 156.19 | 39.05 | True |
| Meiyazhagan | 2024 | 949 | 817 | 132 | 113.52 | 151.36 | 37.84 | True |
| Maharaja | 2024 | 916 | 787 | 129 | 116.41 | 155.21 | 38.8 | True |
| Wolf Children | 2012 | 923 | 794 | 129 | 115.9 | 154.53 | 38.63 | True |
| Baahubali 2: The Conclusion | 2017 | 1002 | 874 | 128 | 109.21 | 145.61 | 36.4 | True |
| Shutter Island | 2010 | 771 | 644 | 127 | 132.98 | 177.31 | 44.33 | True |
| A Silent Voice: The Movie | 2016 | 770 | 643 | 127 | 132.98 | 177.31 | 44.33 | True |
| Dangal | 2016 | 834 | 707 | 127 | 125.19 | 166.92 | 41.73 | True |
| The Fall | 2006 | 845 | 718 | 127 | 123.75 | 165.0 | 41.25 | True |
| Lost Ladies | 2023 | 926 | 799 | 127 | 115.67 | 154.22 | 38.55 | True |
| The Pursuit of Happyness | 2006 | 941 | 814 | 127 | 113.94 | 151.92 | 37.98 | True |
| Elite Squad | 2007 | 938 | 811 | 127 | 113.94 | 151.92 | 37.98 | True |
| Ip Man | 2008 | 939 | 812 | 127 | 113.94 | 151.92 | 37.98 | True |
| The Invisible Guest | 2016 | 940 | 813 | 127 | 113.94 | 151.92 | 37.98 | True |
| Silenced | 2011 | 998 | 871 | 127 | 109.52 | 146.03 | 36.51 | True |
| Swades | 2004 | 999 | 872 | 127 | 109.47 | 145.96 | 36.49 | True |
| Attack on Titan: Chronicle | 2020 | 986 | 860 | 126 | 110.09 | 146.79 | 36.7 | True |

## Biggest ranking losses

| Film | Year | Rank 150 | Rank 200 | Rank gain | Score 150 | Score 200 | Delta | Complete |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Emilia Pérez | 2024 | 1207 | 1453 | -246 | 89.46 | 89.46 | 0.0 | True |
| Spring Breakers | 2012 | 1280 | 1514 | -234 | 83.99 | 83.99 | 0.0 | True |
| Battle in Heaven | 2005 | 1237 | 1468 | -231 | 87.39 | 88.12 | 0.73 | True |
| Dry Season | 2006 | 863 | 1089 | -226 | 121.28 | 121.82 | 0.54 | True |
| The Brown Bunny | 2003 | 1219 | 1443 | -224 | 88.63 | 90.16 | 1.53 | True |
| Southland Tales | 2006 | 1272 | 1487 | -215 | 84.79 | 86.4 | 1.61 | True |
| Maestro | 2023 | 894 | 1100 | -206 | 118.77 | 120.69 | 1.92 | True |
| Trouble the Water | 2008 | 1167 | 1372 | -205 | 93.04 | 95.74 | 2.7 | True |
| Beaufort | 2007 | 971 | 1175 | -204 | 111.1 | 112.62 | 1.52 | True |
| Last Days | 2005 | 1127 | 1329 | -202 | 96.13 | 99.15 | 3.02 | True |
| A Screaming Man | 2010 | 745 | 947 | -202 | 135.19 | 137.5 | 2.31 | True |
| Film socialisme | 2010 | 1294 | 1490 | -196 | 83.2 | 86.25 | 3.05 | True |
| Lovers Rock | 2020 | 1074 | 1264 | -190 | 100.78 | 105.0 | 4.22 | False |
| Waiting for Happiness | 2002 | 1416 | 1605 | -189 | 74.66 | 75.66 | 1.0 | True |
| Happy Feet | 2006 | 1374 | 1562 | -188 | 77.79 | 79.71 | 1.92 | True |
| Hell and Back Again | 2011 | 1461 | 1649 | -188 | 72.21 | 72.21 | 0.0 | True |
| High Life | 2018 | 1182 | 1370 | -188 | 91.97 | 95.81 | 3.84 | True |
| Wild Grass | 2009 | 1357 | 1542 | -185 | 78.88 | 81.46 | 2.58 | True |
| The Image Book | 2018 | 899 | 1084 | -185 | 118.13 | 122.3 | 4.17 | True |
| In the Cut | 2003 | 1279 | 1462 | -183 | 84.1 | 88.65 | 4.55 | True |

## Biggest score increases

| Film | Year | Rank 150 | Rank 200 | Rank gain | Score 150 | Score 200 | Delta | Complete |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Parasite | 2019 | 3 | 2 | 1 | 734.21 | 784.21 | 50.0 | True |
| Spirited Away | 2001 | 15 | 14 | 1 | 601.29 | 651.29 | 50.0 | True |
| The Pianist | 2002 | 19 | 17 | 2 | 573.98 | 623.98 | 50.0 | True |
| The Departed | 2006 | 40 | 37 | 3 | 501.7 | 551.7 | 50.0 | True |
| The Lord of the Rings: The Return of the King | 2003 | 44 | 42 | 2 | 480.27 | 530.27 | 50.0 | True |
| Whiplash | 2014 | 52 | 46 | 6 | 466.55 | 516.55 | 50.0 | True |
| The Lord of the Rings: The Fellowship of the Ring | 2001 | 54 | 52 | 2 | 457.84 | 507.84 | 50.0 | True |
| City of God | 2002 | 60 | 55 | 5 | 451.58 | 501.58 | 50.0 | True |
| The Dark Knight | 2008 | 79 | 71 | 8 | 419.01 | 469.01 | 50.0 | True |
| The Lord of the Rings: The Two Towers | 2002 | 90 | 84 | 6 | 393.17 | 443.17 | 50.0 | True |
| Django Unchained | 2012 | 168 | 154 | 14 | 312.84 | 362.84 | 50.0 | True |
| Interstellar | 2014 | 274 | 227 | 47 | 255.52 | 305.52 | 50.0 | True |
| Spider-Man: Across the Spider-Verse | 2023 | 342 | 302 | 40 | 221.8 | 271.8 | 50.0 | True |
| The Prestige | 2006 | 371 | 324 | 47 | 212.82 | 262.82 | 50.0 | True |
| The Lives of Others | 2006 | 6 | 6 | 0 | 665.79 | 714.54 | 48.75 | True |
| Inglourious Basterds | 2009 | 46 | 43 | 3 | 478.26 | 527.01 | 48.75 | True |
| Spider-Man: Into the Spider-Verse | 2018 | 146 | 125 | 21 | 336.13 | 384.88 | 48.75 | True |
| Dune: Part Two | 2024 | 284 | 232 | 52 | 252.05 | 300.8 | 48.75 | True |
| The Odyssey | 2026 | 484 | 406 | 78 | 183.85 | 232.6 | 48.75 | True |
| Inception | 2010 | 50 | 45 | 5 | 471.72 | 519.8 | 48.08 | True |

## Diagnostic band crossings

Boundaries reuse the existing analysis bands; crossing one does not qualify a film.
| Boundary | Films crossing upward |
| --- | --- |
| 600 | 7 |
| 500 | 16 |
| 450 | 20 |
| 400 | 20 |
| 350 | 34 |
| 300 | 50 |
| 250 | 64 |
| 200 | 110 |
| 150 | 179 |
| 100 | 236 |

| Film | Year | Band 150 | Band 200 | Score 150 | Score 200 | Complete |
| --- | --- | --- | --- | --- | --- | --- |
| The Social Network | 2010 | 500-<600 | 600+ | 599.23 | 632.79 | True |
| The Pianist | 2002 | 500-<600 | 600+ | 573.98 | 623.98 | True |
| The Zone of Interest | 2023 | 500-<600 | 600+ | 591.21 | 618.52 | True |
| Anatomy of a Fall | 2023 | 500-<600 | 600+ | 571.43 | 606.33 | True |
| The Hurt Locker | 2008 | 500-<600 | 600+ | 575.75 | 603.63 | True |
| A Prophet | 2009 | 500-<600 | 600+ | 562.43 | 601.76 | True |
| In the Mood for Love | 2000 | 500-<600 | 600+ | 556.65 | 600.4 | True |
| WALL·E | 2008 | 450-<500 | 500-<600 | 486.21 | 533.04 | True |
| The Lord of the Rings: The Return of the King | 2003 | 450-<500 | 500-<600 | 480.27 | 530.27 | True |
| Inglourious Basterds | 2009 | 450-<500 | 500-<600 | 478.26 | 527.01 | True |
| Anora | 2024 | 450-<500 | 500-<600 | 499.51 | 526.14 | True |
| Inception | 2010 | 450-<500 | 500-<600 | 471.72 | 519.8 | True |
| Whiplash | 2014 | 450-<500 | 500-<600 | 466.55 | 516.55 | True |
| Call Me by Your Name | 2017 | 450-<500 | 500-<600 | 481.63 | 515.19 | True |
| La La Land | 2016 | 450-<500 | 500-<600 | 473.5 | 513.4 | True |
| Gladiator | 2000 | 450-<500 | 500-<600 | 463.06 | 511.14 | True |
| The Favourite | 2018 | 450-<500 | 500-<600 | 479.03 | 510.76 | True |
| Drive My Car | 2021 | 450-<500 | 500-<600 | 474.73 | 509.64 | True |
| The Lord of the Rings: The Fellowship of the Ring | 2001 | 450-<500 | 500-<600 | 457.84 | 507.84 | True |
| Ida | 2013 | 450-<500 | 500-<600 | 474.93 | 504.3 | True |
| Oldboy | 2003 | 450-<500 | 500-<600 | 455.98 | 503.48 | True |
| City of God | 2002 | 450-<500 | 500-<600 | 451.58 | 501.58 | True |
| Oppenheimer | 2023 | 450-<500 | 500-<600 | 457.04 | 501.37 | True |
| Slumdog Millionaire | 2008 | 400-<450 | 450-<500 | 447.2 | 485.18 | True |
| Memento | 2000 | 400-<450 | 450-<500 | 437.28 | 484.11 | True |

## Score distributions

| Statistic | Audience=150 | Audience=200 |
| --- | --- | --- |
| count | 1909 | 1909 |
| min | 0.0 | 0.0 |
| max | 803.78 | 841.86 |
| mean | 148.32 | 170.39 |
| median | 112.75 | 136.46 |
| stddev_population | 113.95 | 121.12 |
| p10 | 53.08 | 61.67 |
| p25 | 74.05 | 91.15 |
| p50 | 112.75 | 136.46 |
| p75 | 184.48 | 210.18 |
| p90 | 295.06 | 324.4 |
| p95 | 385.58 | 413.58 |
| p99 | 570.71 | 603.48 |

| Band | Audience=150 | Audience=200 |
| --- | --- | --- |
| 0-<100 | 828 | 592 |
| 100-<150 | 428 | 485 |
| 150-<200 | 238 | 307 |
| 200-<250 | 127 | 173 |
| 250-<300 | 105 | 119 |
| 300-<350 | 55 | 71 |
| 350-<400 | 42 | 56 |
| 400-<450 | 26 | 26 |
| 450-<500 | 20 | 24 |
| 500-<600 | 25 | 34 |
| 600+ | 15 | 22 |

Complete-pair-only distributions are also provided in comparison.json for missing-data sensitivity.

## Audience strength materially improves position

| Film | Year | Rank without audience | Rank 150 | Rank 200 | Lift | Audience 200 | Non-audience |
| --- | --- | --- | --- | --- | --- | --- | --- |
| I Swear | 2025 | 1563 | 698 | 584 | 979 | 182.72 | 4.68 |
| Prisoners | 2013 | 1465 | 645 | 535 | 930 | 185.0 | 12.64 |
| Avengers: Infinity War | 2018 | 1436 | 660 | 553 | 883 | 179.62 | 14.33 |
| Dear Zachary: A Letter to a Son About His Father | 2008 | 1398 | 623 | 521 | 877 | 183.57 | 17.42 |
| Warrior | 2011 | 1433 | 731 | 633 | 800 | 164.62 | 14.5 |
| Your Name. | 2016 | 1271 | 551 | 472 | 799 | 187.31 | 26.19 |
| Pirates of the Caribbean: The Curse of the Black Pearl | 2003 | 1501 | 809 | 704 | 797 | 156.92 | 10.41 |
| Samsara | 2011 | 1568 | 908 | 788 | 780 | 150.88 | 4.24 |
| Elite Squad 2: The Enemy Within | 2010 | 1562 | 903 | 785 | 777 | 150.81 | 4.7 |
| Training Day | 2001 | 1539 | 888 | 770 | 769 | 149.62 | 6.98 |
| V for Vendetta | 2005 | 1572 | 927 | 807 | 765 | 149.23 | 3.6 |
| Demon Slayer: Kimetsu No Yaiba Infinity Castle | 2025 | 1300 | 633 | 539 | 761 | 171.99 | 24.72 |
| Project Hail Mary | 2026 | 1222 | 544 | 467 | 755 | 185.0 | 29.6 |
| Batman Begins | 2005 | 1418 | 779 | 689 | 729 | 154.23 | 15.56 |
| Tokyo Godfathers | 2003 | 1389 | 741 | 662 | 727 | 156.83 | 18.43 |

These complete-data examples quantify audience lift; they are not endorsements or preferred-cap choices.

## Potential audience dominance over other evidence

The first diagnostic shows rising complete-data films whose audience share is at least 50%.
| Film | Rank 150 | Rank 200 | Audience share % | Audience 200 | Non-audience |
| --- | --- | --- | --- | --- | --- |
| Samsara | 908 | 788 | 97.27 | 150.88 | 4.24 |
| V for Vendetta | 927 | 807 | 97.64 | 149.23 | 3.6 |
| Elite Squad 2: The Enemy Within | 903 | 785 | 96.98 | 150.81 | 4.7 |
| Training Day | 888 | 770 | 95.54 | 149.62 | 6.98 |
| I Swear | 698 | 584 | 97.5 | 182.72 | 4.68 |
| Prisoners | 645 | 535 | 93.6 | 185.0 | 12.64 |
| Avengers: Infinity War | 660 | 553 | 92.61 | 179.62 | 14.33 |
| Pirates of the Caribbean: The Curse of the Black Pearl | 809 | 704 | 93.78 | 156.92 | 10.41 |
| Guardians of the Galaxy Vol. 3 | 839 | 734 | 91.07 | 146.92 | 14.4 |
| Cinderella Man | 872 | 769 | 92.04 | 144.23 | 12.47 |
| Dear Zachary: A Letter to a Son About His Father | 623 | 521 | 91.33 | 183.57 | 17.42 |
| Blood Diamond | 983 | 882 | 94.47 | 136.54 | 8.0 |
| The Batman | 844 | 745 | 88.97 | 141.92 | 17.6 |
| Warrior | 731 | 633 | 91.9 | 164.62 | 14.5 |
| Spider-Man: Brand New Day | 822 | 724 | 89.75 | 146.92 | 16.78 |

The following pairs invert order solely when the audience weight changes; the overtaken film has more non-audience evidence.
| Audience-favoured film | Higher-evidence film | Non-audience gap | Ranks at 150 | Ranks at 200 |
| --- | --- | --- | --- | --- |
| Interstellar | The Assassin | 160.89 | 274 / 204 | 227 / 247 |
| Dune: Part Two | The Assassin | 160.61 | 284 / 204 | 232 / 247 |
| Interstellar | Titane | 160.17 | 274 / 193 | 227 / 228 |
| Interstellar | Goodbye to Language | 151.26 | 274 / 231 | 227 / 292 |
| Dune: Part Two | Goodbye to Language | 150.98 | 284 / 231 | 232 / 292 |
| Coco | Goodbye to Language | 149.8 | 303 / 231 | 274 / 292 |
| Memories of Murder | The Assassin | 148.45 | 281 / 204 | 236 / 247 |
| Interstellar | Atlantics | 143.73 | 274 / 209 | 227 / 234 |
| Requiem for a Dream | The Assassin | 143.52 | 279 / 204 | 238 / 247 |
| Dune: Part Two | Atlantics | 143.45 | 284 / 209 | 232 / 234 |
| Howl's Moving Castle | The Assassin | 142.2 | 252 / 204 | 218 / 247 |
| Howl's Moving Castle | Titane | 141.48 | 252 / 193 | 218 / 228 |
| Memories of Murder | Goodbye to Language | 138.82 | 281 / 231 | 236 / 292 |
| Nobody Knows | Goodbye to Language | 138.29 | 316 / 231 | 290 / 292 |
| Kill Bill: Vol. 1 | The Assassin | 136.64 | 255 / 204 | 222 / 247 |

Point breakdowns for both films are retained in comparison.json. Dominance/inversion is a diagnostic for review, not proof that either film is better or that a cap is wrong.
Critics-group award identity gaps and missing broad-critic cache are reported in coverage.json; absent critical evidence is not proof of absence of acclaim.

## Artifacts and limits

- [Audience=150 JSON](audience_cap_150.json) / [CSV](audience_cap_150.csv)
- [Audience=200 JSON](audience_cap_200.json) / [CSV](audience_cap_200.csv)
- [Full comparison JSON](comparison.json) / [per-film CSV](comparison.csv)
- [Coverage and unresolved data](coverage.json) / [reproduction manifest](manifest.json)
- [Official IMDb fallback input](inputs/imdb-fallback.json)
- [ReelDB collection status](enrichment-status.json)

This is evidence for the user and ChatGPT. No cap is chosen, no production threshold is changed, and no runtime scoring deployment is performed.
