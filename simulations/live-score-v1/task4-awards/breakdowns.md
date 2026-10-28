# Task 4 Recognition comparison

Observed subtotals only, as of 2026-10-28. Cohort order is retained; no leaderboard.

| Film | Europe /20 | Independent /10 | US /10 | Critics /10 | Task 2 base | New base /50 | Evidence Δ | TIFF (Δ) | Screenplay (Δ) | Both (Δ) | Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Hamnet | 5 | 1 | 9 | 0.8 | 15.8 | 15.8 | 0 | 19.8 (+4) | 15.8 (+0) | 19.8 (+4) | Partial |
| Anora | 19 | 6 | 10 | 6 | 41 | 41 | 0 | 41 (+0) | 41 (+0) | 41 (+0) | Partial |
| The Brutalist | 13 | 0 | 9 | 4.3 | 26.3 | 26.3 | 0 | 26.3 (+0) | 26.3 (+0) | 26.3 (+0) | Partial |
| The Substance | 4.4 | 2 | 7.5 | 0.8 | 14.7 | 14.7 | 0 | 14.7 (+0) | 20.7 (+6) | 20.7 (+6) | Partial |
| Sentimental Value | 20 | 0 | 10 | 0.8 | 30.8 | 30.8 | 0 | 30.8 (+0) | 30.8 (+0) | 30.8 (+0) | Partial |
| It Was Just an Accident | 19.4 | 0 | 5 | 0 | 24.4 | 24.4 | 0 | 24.4 (+0) | 24.4 (+0) | 24.4 (+0) | Partial |
| Nina Roza | 2 | 0 | 0 | 0 | 2 | 2 | 0 | 2 (+0) | 8 (+6) | 8 (+6) | Partial |
| I See Buildings Fall Like Lightning | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 (+0) | 0 (+0) | 0 (+0) | Partial |

All eight complete Recognition scores remain null. Family zeros mean no observed scored component, not verified whole-family absence. See [report](report.md), [results](results.json), and [all coverage cells](coverage.csv).

## Component attribution

Strongest value once per component; different components may add. Raw family sums cap at 100, then scale to 20/10/10/10. Candidate points apply inside those caps.

### Hamnet

`tt14905854` / TMDb 858024; retained year 2025.

| Component | Strongest normalized points /100 | Family | Evidence |
| --- | ---: | --- | --- |
| academy_best_picture | 65 | us_institutional | [R0001, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0002, nominee, 2026-10-25](https://www.oscars.org/oscars/ceremonies/2026); [R0003, nominee, 2026-10-26](https://www.oscars.org/oscars/ceremonies/2026) |
| globe_best_picture | 25 | us_institutional | [R0004, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0005, winner, 2026-10-25](https://goldenglobes.com/nominations/2026/) |
| bafta_best_film | 25 | european_recognition | [R0006, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0007, nominee, 2026-10-25](https://www.bafta.org/awards/film/?award-year=2026) |
| gotham_best_feature | 10 | independent_cinema | [R0008, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0009, nominee, 2026-10-25](https://letterboxd.com/thegotham/list/2025-gotham-film-awards-best-feature-nominees/detail/); [R0010, nominee, 2026-10-26](https://thegotham.org/press/nominations-announced-for-35th-annual-gotham-film-awards/) |
| critics_choice_best_picture | 8 | critics_groups_consensus | [R0011, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0012, nominee, 2026-10-25](https://www.criticschoice.com/31st-annual-critics-choice-awards-list-of-nominees-and-winners-2026/) |

Coverage: `{"not_yet_announced": 2, "source_not_checked": 132, "unavailable": 1, "verified_no_award": 12, "verified_positive": 6}`. Exact unresolved category/edition/stage cells are in [unresolved.csv](unresolved.csv).

### Anora

`tt28607951` / TMDb 1064213; retained year 2024.

| Component | Strongest normalized points /100 | Family | Evidence |
| --- | ---: | --- | --- |
| academy_best_picture | 100 | us_institutional | [R0013, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0014, winner, 2026-10-25](https://www.oscars.org/oscars/ceremonies/2025) |
| globe_best_picture | 10 | us_institutional | [R0015, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0016, nominee, 2026-10-25](https://goldenglobes.com/nominations/2025/) |
| bafta_best_film | 25 | european_recognition | [R0017, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0018, nominee, 2026-10-25](https://www.bafta.org/awards/film/?award-year=2025) |
| cannes_main | 70 | european_recognition | [R0019, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0020, winner, 2026-10-25](https://www.festival-cannes.com/en/press/press-releases/the-77th-festival-de-cannes-winners-list/) |
| spirit_best_feature | 50 | independent_cinema | [R0021, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0022, winner, 2026-10-25](https://www.filmindependent.org/press-releases/film-independent-celebrates-2025-spirit-awards-winners-organizations-history-at-40th-annual-ceremony/) |
| gotham_best_feature | 10 | independent_cinema | [R0023, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0024, nominee, 2026-10-26](https://thegotham.org/press/the-gothams-announce-award-nominees-for-34th-edition/) |
| lafca_best_film | 35 | critics_groups_consensus | [R0025, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0026, winner, 2026-10-26](https://www.lafca.net/Years/2024.php) |
| critics_choice_best_picture | 25 | critics_groups_consensus | [R0027, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0028, winner, 2026-10-25](https://www.criticschoice.com/30th-annual-critics-choice-awards-list-of-nominees-and-winners-2025/) |

Coverage: `{"not_yet_announced": 2, "source_not_checked": 132, "verified_no_award": 7, "verified_positive": 12}`. Exact unresolved category/edition/stage cells are in [unresolved.csv](unresolved.csv).

### The Brutalist

`tt8999762` / TMDb 549509; retained year 2024.

| Component | Strongest normalized points /100 | Family | Evidence |
| --- | ---: | --- | --- |
| academy_best_picture | 65 | us_institutional | [R0029, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0030, nominee, 2026-10-25](https://www.oscars.org/oscars/ceremonies/2025) |
| globe_best_picture | 25 | us_institutional | [R0031, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0032, winner, 2026-10-25](https://goldenglobes.com/nominations/2025/) |
| bafta_best_film | 25 | european_recognition | [R0033, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0034, nominee, 2026-10-25](https://www.bafta.org/awards/film/?award-year=2025) |
| venice_main | 10 | european_recognition | [R0035, competition, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0036, competition, 2026-10-26](https://www.labiennale.org/en/cinema/2024/venezia-81-competition) |
| venice_director | 30 | european_recognition | [R0037, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0038, winner, 2026-10-25](https://www.labiennale.org/en/news/official-awards-81st-venice-international-film-festival) |
| nyfcc_best_film | 35 | critics_groups_consensus | [R0039, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0040, winner, 2026-10-25](https://www.nyfcc.com/awards/); [R0041, winner, 2026-10-26](https://www.nyfcc.com/awards/) |
| critics_choice_best_picture | 8 | critics_groups_consensus | [R0042, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0043, nominee, 2026-10-25](https://www.criticschoice.com/30th-annual-critics-choice-awards-list-of-nominees-and-winners-2025/) |

Coverage: `{"not_yet_announced": 2, "source_not_checked": 133, "unavailable": 1, "verified_no_award": 9, "verified_positive": 8}`. Exact unresolved category/edition/stage cells are in [unresolved.csv](unresolved.csv).

### The Substance

`tt17526714` / TMDb 933260; retained year 2024.

| Component | Strongest normalized points /100 | Family | Evidence |
| --- | ---: | --- | --- |
| academy_best_picture | 65 | us_institutional | [R0044, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0045, nominee, 2026-10-25](https://www.oscars.org/oscars/ceremonies/2025) |
| globe_best_picture | 10 | us_institutional | [R0046, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0047, nominee, 2026-10-25](https://goldenglobes.com/nominations/2025/) |
| cannes_main | 10 | european_recognition | [R0048, competition, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0049, competition, 2026-10-26](https://www.festival-cannes.com/en/f/the-substance/) |
| efa_best_film | 12 | european_recognition | [R0050, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0051, nominee, 2026-10-25](https://www.europeanfilmawards.eu/efa-movie/the-substance/) |
| spirit_best_feature | 20 | independent_cinema | [R0052, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0053, nominee, 2026-10-26](https://www.filmindependent.org/press-releases/film-independent-announces-nominees-for-the-40th-anniversary-2025-spirit-awards/) |
| critics_choice_best_picture | 8 | critics_groups_consensus | [R0054, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0055, nominee, 2026-10-25](https://www.criticschoice.com/30th-annual-critics-choice-awards-list-of-nominees-and-winners-2025/) |

Coverage: `{"not_yet_announced": 2, "source_not_checked": 137, "unavailable": 1, "verified_no_award": 7, "verified_positive": 6}`. Exact unresolved category/edition/stage cells are in [unresolved.csv](unresolved.csv).

### Sentimental Value

`tt27714581` / TMDb 1124566; retained year 2025.

| Component | Strongest normalized points /100 | Family | Evidence |
| --- | ---: | --- | --- |
| efa_best_film | 40 | european_recognition | [R0056, winner, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0057, winner, 2026-10-25](https://www.europeanfilmawards.eu/efa-movie/sentimental-value/) |
| critics_choice_best_picture | 8 | critics_groups_consensus | [R0058, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0059, nominee, 2026-10-25](https://www.criticschoice.com/31st-annual-critics-choice-awards-list-of-nominees-and-winners-2026/) |
| academy_best_picture | 65 | us_institutional | [R0060, nominee, 2026-10-25](https://www.oscars.org/oscars/ceremonies/2026); [R0061, nominee, 2026-10-26](https://www.oscars.org/oscars/ceremonies/2026) |
| academy_international | 70 | us_institutional | [R0062, winner, 2026-10-25](https://www.oscars.org/oscars/ceremonies/2026); [R0063, winner, 2026-10-26](https://www.oscars.org/oscars/ceremonies/2026) |
| globe_best_picture | 10 | us_institutional | [R0064, nominee, 2026-10-25](https://goldenglobes.com/nominations/2026/) |
| globe_non_english | 5 | us_institutional | [R0065, nominee, 2026-10-25](https://goldenglobes.com/nominations/2026/) |
| bafta_best_film | 25 | european_recognition | [R0066, nominee, 2026-10-25](https://www.bafta.org/awards/film/?award-year=2026) |
| bafta_non_english | 35 | european_recognition | [R0067, winner, 2026-10-25](https://www.bafta.org/awards/film/?award-year=2026) |
| cannes_main | 10 | european_recognition | [R0068, competition, 2026-10-25](https://www.festival-cannes.com/en/retrospective/2025/awards/) |
| cannes_grand_prix | 55 | european_recognition | [R0069, winner, 2026-10-25](https://www.festival-cannes.com/en/retrospective/2025/awards/) |

Coverage: `{"not_yet_announced": 2, "source_not_checked": 128, "unavailable": 1, "verified_no_award": 9, "verified_positive": 13}`. Exact unresolved category/edition/stage cells are in [unresolved.csv](unresolved.csv).

### It Was Just an Accident

`tt36491653` / TMDb 1456349; retained year 2025.

| Component | Strongest normalized points /100 | Family | Evidence |
| --- | ---: | --- | --- |
| efa_best_film | 12 | european_recognition | [R0070, nominee, archived date unknown](https://github.com/kolorifer/radarr-festival-list/blob/9c5a0f06e1c39e48653338fd0865ddabdc525a61/sources/evidence-families.json); [R0071, nominee, 2026-10-25](https://www.europeanfilmawards.eu/efa-movie/it-was-just-an-accident/) |
| academy_international | 35 | us_institutional | [R0072, nominee, 2026-10-25](https://www.oscars.org/oscars/ceremonies/2026); [R0073, nominee, 2026-10-26](https://www.oscars.org/oscars/ceremonies/2026) |
| globe_best_picture | 10 | us_institutional | [R0074, nominee, 2026-10-25](https://goldenglobes.com/nominations/2026/) |
| globe_non_english | 5 | us_institutional | [R0075, nominee, 2026-10-25](https://goldenglobes.com/nominations/2026/) |
| bafta_non_english | 15 | european_recognition | [R0076, nominee, 2026-10-25](https://www.bafta.org/awards/film/?award-year=2026) |
| cannes_main | 70 | european_recognition | [R0077, winner, 2026-10-25](https://www.festival-cannes.com/en/retrospective/2025/awards/) |

Coverage: `{"not_yet_announced": 2, "source_not_checked": 129, "unavailable": 1, "verified_no_award": 14, "verified_positive": 7}`. Exact unresolved category/edition/stage cells are in [unresolved.csv](unresolved.csv).

### Nina Roza

`tt29271639` / TMDb 1527449; retained year 2026.

| Component | Strongest normalized points /100 | Family | Evidence |
| --- | ---: | --- | --- |
| berlin_main | 10 | european_recognition | [R0078, competition, 2026-10-25](https://www.berlinale-talents.de/bt/page/c/festival-returnees-2026) |

Coverage: `{"not_yet_announced": 12, "source_not_checked": 126, "unavailable": 8, "verified_no_award": 6, "verified_positive": 1}`. Exact unresolved category/edition/stage cells are in [unresolved.csv](unresolved.csv).

### I See Buildings Fall Like Lightning

`tt38991615` / TMDb 1455247; retained year 2026.

| Component | Strongest normalized points /100 | Family | Evidence |
| --- | ---: | --- | --- |

Coverage: `{"not_yet_announced": 12, "source_not_checked": 131, "unavailable": 4, "verified_no_award": 6}`. Exact unresolved category/edition/stage cells are in [unresolved.csv](unresolved.csv).
