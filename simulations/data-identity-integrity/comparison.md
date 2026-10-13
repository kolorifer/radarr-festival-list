# Research data integrity: before and after

Audience=150 (0.75 × IMDb + Letterboxd), effective ceiling1000. Other family weights, canon correlation and qualification are unchanged. Research only; no production rollout.

## Identity audit
Audited 951 TSPDT/backcatalog records; 227 flagged for closer inspection. Counts: {'confirmed_correct': 946, 'corrected': 5, 'unresolved': 0}.

### Corrected identities
| TSPDT rank | Source film | Wrong ID | Correct ID |
| --- | --- | --- | --- |
| 290 | Time | tt13138834 | tt11416746 |
| 338 | Birdman | tt5130912 | tt2562232 |
| 509 | La Morte rouge | tt4698742 | tt0806125 |
| 603 | Spider | tt0145487 | tt0278731 |
| 897 | The Inheritance | tt7923220 | tt12913444 |

### All suspicious matches
| Rank | Source title | IMDb ID after | Classification | Flags |
| --- | --- | --- | --- | --- |
| 2 | Mulholland Dr. | tt0166924 | confirmed_correct | source_resolved_title_difference |
| 3 | Yi Yi | tt0244316 | confirmed_correct | short_common_title |
| 13 | Caché | tt0387898 | confirmed_correct | short_common_title |
| 15 | La Ciénaga | tt0240419 | confirmed_correct | source_resolved_title_difference |
| 18 | City of God | tt0317248 | confirmed_correct | director_conflict, partial_codirector_credit |
| 22 | Get Out | tt5052448 | confirmed_correct | short_common_title |
| 23 | Tie Xi Qu: West of the Tracks | tt0389448 | confirmed_correct | year_conflict |
| 34 | The Act of Killing | tt2375605 | confirmed_correct | runtime_conflict |
| 38 | Zama | tt3409848 | confirmed_correct | short_common_title |
| 39 | Boyhood | tt1065073 | confirmed_correct | short_common_title |
| 46 | Platform | tt0258885 | confirmed_correct | country_conflict |
| 48 | Oldboy | tt0364569 | confirmed_correct | short_common_title |
| 57 | Zodiac | tt0443706 | confirmed_correct | short_common_title |
| 58 | WALL-E | tt0910970 | confirmed_correct | short_common_title |
| 60 | Amour | tt1602620 | confirmed_correct | short_common_title |
| 63 | Amélie | tt0211915 | confirmed_correct | short_common_title |
| 73 | Roma | tt6155172 | confirmed_correct | country_conflict, short_common_title |
| 74 | Carol | tt2402927 | confirmed_correct | short_common_title |
| 81 | Millennium Mambo | tt0283283 | confirmed_correct | runtime_conflict |
| 82 | Memento | tt0209144 | confirmed_correct | short_common_title |
| 85 | Hunger | tt0986233 | confirmed_correct | short_common_title |
| 88 | Distant | tt0346094 | confirmed_correct | short_common_title |
| 90 | The New World | tt0402399 | confirmed_correct | runtime_conflict |
| 106 | The Son | tt0291172 | confirmed_correct | short_common_title |
| 108 | Tabu | tt2153963 | confirmed_correct | short_common_title |
| 118 | La Commune (Paris, 1871) | tt0257497 | confirmed_correct | year_conflict |
| 119 | Goodbye to Language | tt2400275 | confirmed_correct | country_conflict |
| 124 | Avatar | tt0499549 | confirmed_correct | short_common_title |
| 129 | Cemetery of Splendour | tt2818654 | confirmed_correct | source_resolved_title_difference |
| 130 | 2046 | tt0212712 | confirmed_correct | short_common_title |
| 133 | Spring, Summer, Autumn, Winter… and Spring | tt0374546 | confirmed_correct | source_resolved_title_difference |
| 135 | La Flor | tt9047474 | confirmed_correct | short_common_title |
| 137 | Head-On | tt0347048 | confirmed_correct | short_common_title |
| 141 | Arrival | tt2543164 | confirmed_correct | short_common_title |
| 142 | The Host | tt0468492 | confirmed_correct | short_common_title |
| 143 | Ida | tt2718492 | confirmed_correct | short_common_title |
| 147 | Gravity | tt1454468 | confirmed_correct | short_common_title |
| 151 | Volver | tt0441909 | confirmed_correct | short_common_title |
| 159 | Burning | tt7282468 | confirmed_correct | short_common_title |
| 165 | Oasis | tt0320193 | confirmed_correct | short_common_title |
| 184 | Le Havre | tt1508675 | confirmed_correct | short_common_title |
| 185 | Hero | tt0299977 | confirmed_correct | short_common_title |
| 187 | Old Joy | tt0468526 | confirmed_correct | short_common_title |
| 192 | Monsoon Wedding | tt0265343 | confirmed_correct | country_conflict |
| 195 | Poetry | tt1287878 | confirmed_correct | short_common_title |
| 205 | Drive | tt0780504 | confirmed_correct | short_common_title |
| 206 | Bamako | tt0814666 | confirmed_correct | short_common_title |
| 207 | Up | tt1049413 | confirmed_correct | short_common_title |
| 209 | Ten | tt0301978 | confirmed_correct | short_common_title |
| 211 | L' Enfant | tt0456396 | confirmed_correct | short_common_title, source_resolved_title_difference |
| 216 | Evolution of a Filipino Family | tt0424062 | confirmed_correct | runtime_conflict |
| 217 | Borat: Cultural Learnings of America for Make Benefit Glorious Nation of Kazakhstan | tt0443453 | confirmed_correct | source_resolved_title_difference |
| 220 | Titane | tt10944760 | confirmed_correct | short_common_title |
| 226 | Weekend | tt1714210 | confirmed_correct | short_common_title |
| 230 | Her | tt1798709 | confirmed_correct | short_common_title |
| 238 | Mother | tt1216496 | confirmed_correct | short_common_title |
| 241 | Shara | tt0363060 | confirmed_correct | short_common_title, source_resolved_title_difference |
| 249 | Cold War | tt6543652 | confirmed_correct | short_common_title |
| 250 | Finding Nemo | tt0266543 | confirmed_correct | director_conflict, partial_codirector_credit |
| 251 | Timbuktu | tt3409392 | confirmed_correct | country_conflict |
| 252 | Moolaadé | tt0416991 | confirmed_correct | source_resolved_year_difference |
| 261 | Pulse | tt0286751 | confirmed_correct | short_common_title |
| 269 | 21 Grams | tt0315733 | confirmed_correct | country_conflict, short_common_title |
| 273 | Hugo | tt0970179 | confirmed_correct | short_common_title |
| 274 | Fat Girl | tt0243255 | confirmed_correct | short_common_title |
| 276 | Elle | tt3716530 | confirmed_correct | short_common_title |
| 277 | Saraband | tt0299478 | confirmed_correct | runtime_conflict |
| 283 | Le Quattro Volte | tt1646975 | confirmed_correct | source_resolved_title_difference |
| 290 | Time | tt11416746 | corrected | non_film_imdb_type, short_common_title, source_resolved_year_difference |
| 291 | O Brother, Where Art Thou? | tt0190590 | confirmed_correct | director_conflict, partial_codirector_credit |
| 297 | Gerry | tt0302674 | confirmed_correct | short_common_title |
| 299 | In the Cut | tt0199626 | confirmed_correct | country_conflict |
| 301 | Western | tt5157326 | confirmed_correct | short_common_title |
| 314 | Us | tt6857112 | confirmed_correct | short_common_title |
| 320 | Birth | tt0337876 | confirmed_correct | short_common_title |
| 325 | Tomboy | tt1847731 | confirmed_correct | short_common_title |
| 327 | The Hunt | tt2106476 | confirmed_correct | short_common_title |
| 329 | Memoria | tt8399288 | confirmed_correct | short_common_title |
| 331 | Red Road | tt0471030 | confirmed_correct | short_common_title |
| 332 | Paprika | tt0851578 | confirmed_correct | short_common_title |
| 338 | Birdman | tt2562232 | corrected | country_conflict, director_conflict, runtime_conflict, short_common_title |
| 341 | Kings & Queen | tt0344273 | confirmed_correct | source_resolved_title_difference |
| 345 | Raw | tt4954522 | confirmed_correct | short_common_title |
| 346 | Fantasma, O | tt0239381 | confirmed_correct | source_resolved_title_difference, title_alias_requires_corroboration |
| 382 | Neighbouring Sounds | tt2190367 | confirmed_correct | source_resolved_title_difference |
| 383 | 13 Lakes | tt0445158 | confirmed_correct | short_common_title |
| 384 | Phoenix | tt2764784 | confirmed_correct | short_common_title |
| 388 | Time Out | tt0279065 | confirmed_correct | short_common_title |
| 395 | TÁR | tt14444726 | confirmed_correct | short_common_title |
| 404 | Nope | tt10954984 | confirmed_correct | short_common_title |
| 410 | Carlos | tt1321865 | confirmed_correct | non_film_imdb_type, short_common_title |
| 411 | Days | tt11697820 | confirmed_correct | short_common_title |
| 416 | Vai-E-Vem | tt0367195 | confirmed_correct | short_common_title |
| 417 | Gangs of Wasseypur | tt1954470 | confirmed_correct | runtime_conflict |
| 418 | 3-Iron | tt0423866 | confirmed_correct | short_common_title |
| 425 | Dunkirk | tt5013056 | confirmed_correct | short_common_title |
| 427 | Eureka | tt0243889 | confirmed_correct | short_common_title |
| 430 | Notre musique | tt0360845 | confirmed_correct | source_resolved_title_difference |
| 439 | Playing | tt1165293 | confirmed_correct | short_common_title, source_resolved_title_difference |
| 440 | Big Fish | tt0319061 | confirmed_correct | short_common_title |
| 441 | Samson and Delilah | tt1340123 | confirmed_correct | source_resolved_title_difference |
| 442 | Babel | tt0449467 | confirmed_correct | short_common_title |
| 446 | Faust | tt1437357 | confirmed_correct | short_common_title |
| 447 | Oh! Man | tt0431958 | confirmed_correct | short_common_title |
| 465 | Pariah | tt1233334 | confirmed_correct | short_common_title |
| 466 | La Captive | tt0216605 | confirmed_correct | source_resolved_title_difference |
| 468 | Gosford Park | tt0280707 | confirmed_correct | country_conflict |
| 470 | 45 Years | tt3544082 | confirmed_correct | short_common_title |
| 476 | Martyrs | tt1029234 | confirmed_correct | short_common_title |
| 477 | BPM (Beats Per Minute) | tt6135348 | confirmed_correct | source_resolved_title_difference |
| 479 | The Sun | tt0439817 | confirmed_correct | short_common_title |
| 487 | Traffic | tt0181865 | confirmed_correct | short_common_title |
| 495 | Decasia | tt0303325 | confirmed_correct | short_common_title |
| 504 | Lumumba | tt0246765 | confirmed_correct | short_common_title |
| 507 | Munich | tt0408306 | confirmed_correct | short_common_title |
| 509 | La Morte rouge | tt0806125 | corrected | source_resolved_title_difference, source_resolved_year_difference |
| 514 | Silence | tt0490215 | confirmed_correct | short_common_title |
| 515 | Napoleon Dynamite | tt0374900 | confirmed_correct | runtime_conflict |
| 516 | Primer | tt0390384 | confirmed_correct | short_common_title |
| 521 | Rocks | tt9067182 | confirmed_correct | short_common_title |
| 527 | Eden | tt3090634 | confirmed_correct | short_common_title |
| 535 | Hot Fuzz | tt0425112 | confirmed_correct | short_common_title |
| 538 | Shame | tt1723811 | confirmed_correct | short_common_title |
| 539 | At Sea | tt1829648 | confirmed_correct | short_common_title |
| 540 | Dune: Part One | tt1160419 | confirmed_correct | source_resolved_title_difference |
| 551 | Mommy | tt3612616 | confirmed_correct | short_common_title |
| 552 | The Human Surge | tt6041312 | confirmed_correct | source_resolved_title_difference |
| 553 | Once | tt0907657 | confirmed_correct | short_common_title, source_resolved_year_difference |
| 556 | Selma | tt1020072 | confirmed_correct | short_common_title |
| 562 | Bus 174 | tt0340468 | confirmed_correct | director_conflict, partial_codirector_credit, short_common_title |
| 570 | Bacurau | tt2762506 | confirmed_correct | short_common_title |
| 577 | Turtles Can Fly | tt0424227 | confirmed_correct | year_conflict |
| 586 | Marriage Story | tt7653254 | confirmed_correct | country_conflict |
| 588 | The Mouth of the Wolf | tt1603480 | confirmed_correct | runtime_conflict |
| 591 | Offside | tt0499537 | confirmed_correct | short_common_title |
| 596 | Heremias | tt0843515 | confirmed_correct | source_resolved_title_difference, title_alias_requires_corroboration |
| 601 | Hat Wolff von Amerongen Konkursdelikte begangen? | tt0499138 | confirmed_correct | source_resolved_title_difference |
| 603 | Spider | tt0278731 | corrected | country_conflict, director_conflict, runtime_conflict, short_common_title, source_resolved_title_difference |
| 605 | Shrek | tt0126029 | confirmed_correct | short_common_title |
| 609 | RR | tt1261422 | confirmed_correct | short_common_title |
| 610 | Daratt | tt0825241 | confirmed_correct | short_common_title, source_resolved_title_difference |
| 612 | Juno | tt0467406 | confirmed_correct | short_common_title |
| 620 | RRR | tt8178634 | confirmed_correct | short_common_title |
| 625 | Mary and Max | tt0978762 | confirmed_correct | runtime_conflict, source_resolved_year_difference |
| 628 | Wadjda | tt2258858 | confirmed_correct | short_common_title |
| 629 | The Lighthouse | tt7984734 | confirmed_correct | country_conflict |
| 633 | Pina | tt1440266 | confirmed_correct | short_common_title |
| 640 | Sin City | tt0401792 | confirmed_correct | short_common_title |
| 641 | I Am Love | tt1226236 | confirmed_correct | short_common_title |
| 654 | Une Visite au Louvre | tt0405418 | confirmed_correct | source_resolved_title_difference |
| 657 | Shirin | tt1284587 | confirmed_correct | short_common_title |
| 661 | Quo vadis, Aida? | tt8633462 | confirmed_correct | country_conflict |
| 663 | This is Not a Burial, it's a Resurrection | tt10849514 | confirmed_correct | country_conflict |
| 664 | Solaris | tt0307479 | confirmed_correct | short_common_title |
| 668 | Elf | tt0319343 | confirmed_correct | short_common_title |
| 670 | Chunhyang | tt0245837 | confirmed_correct | runtime_conflict |
| 672 | Mustang | tt3966404 | confirmed_correct | short_common_title |
| 676 | Minari | tt10633456 | confirmed_correct | short_common_title |
| 690 | Milk | tt1013753 | confirmed_correct | short_common_title |
| 692 | EO | tt19652910 | confirmed_correct | short_common_title |
| 701 | Lincoln | tt0443272 | confirmed_correct | short_common_title |
| 704 | Barbie | tt1517268 | confirmed_correct | short_common_title |
| 707 | Monster | tt0340855 | confirmed_correct | short_common_title |
| 709 | Looper | tt1276104 | confirmed_correct | short_common_title |
| 723 | Compartment No. 6 | tt10262648 | confirmed_correct | source_resolved_title_difference |
| 727 | Barbara | tt2178941 | confirmed_correct | short_common_title |
| 729 | Mia madre | tt3013610 | confirmed_correct | source_resolved_title_difference |
| 730 | Sicario | tt3397884 | confirmed_correct | short_common_title |
| 731 | Aurora | tt1403047 | confirmed_correct | short_common_title |
| 733 | Elena | tt1925421 | confirmed_correct | short_common_title |
| 734 | 13th | tt5895028 | confirmed_correct | short_common_title |
| 735 | Moon | tt1182345 | confirmed_correct | short_common_title |
| 745 | For Sama | tt9617456 | confirmed_correct | short_common_title |
| 758 | Maqbool | tt0379370 | confirmed_correct | short_common_title |
| 759 | Transit | tt6675244 | confirmed_correct | short_common_title |
| 765 | Bastards | tt2821088 | confirmed_correct | runtime_conflict |
| 770 | Amy | tt2870648 | confirmed_correct | short_common_title |
| 774 | Vincere | tt1156173 | confirmed_correct | short_common_title |
| 787 | Chopper | tt0221073 | confirmed_correct | short_common_title |
| 789 | Jauja | tt2514338 | confirmed_correct | short_common_title |
| 790 | Annette | tt6217926 | confirmed_correct | short_common_title |
| 798 | Joker | tt7286456 | confirmed_correct | short_common_title |
| 802 | Trilogy: The Weeping Meadow | tt0366721 | confirmed_correct | source_resolved_title_difference |
| 805 | Snatch | tt0208092 | confirmed_correct | country_conflict, short_common_title |
| 807 | Capote | tt0379725 | confirmed_correct | runtime_conflict, short_common_title |
| 814 | Signs | tt0286106 | confirmed_correct | short_common_title |
| 825 | Room | tt3170832 | confirmed_correct | short_common_title |
| 833 | Creed | tt3076658 | confirmed_correct | short_common_title |
| 836 | Operai, contadini | tt0305923 | confirmed_correct | source_resolved_title_difference |
| 840 | Woman on the Beach | tt0835787 | confirmed_correct | runtime_conflict |
| 846 | Devdas | tt0238936 | confirmed_correct | short_common_title |
| 849 | Crash | tt0375679 | confirmed_correct | short_common_title |
| 854 | Quei loro incontri | tt0815227 | confirmed_correct | source_resolved_title_difference |
| 857 | DiG! | tt0388888 | confirmed_correct | short_common_title |
| 865 | America | tt6217698 | confirmed_correct | short_common_title |
| 869 | Senna | tt1424432 | confirmed_correct | short_common_title |
| 870 | Ex Libris: The New York Public Library | tt6209282 | confirmed_correct | source_resolved_title_difference |
| 877 | The Mist | tt0884328 | confirmed_correct | short_common_title |
| 878 | Frozen | tt2294629 | confirmed_correct | short_common_title |
| 892 | Oxhide | tt0453795 | confirmed_correct | short_common_title |
| 895 | 24 City | tt1103963 | confirmed_correct | short_common_title |
| 896 | La Vie nouvelle | tt0310313 | confirmed_correct | source_resolved_title_difference |
| 897 | The Inheritance | tt12913444 | corrected | director_conflict, source_resolved_title_difference |
| 898 | Brick | tt0393109 | confirmed_correct | short_common_title |
| 905 | Japón | tt0322824 | confirmed_correct | short_common_title |
| 906 | No | tt2059255 | confirmed_correct | short_common_title |
| 907 | Belfast | tt12789558 | confirmed_correct | short_common_title |
| 908 | Drug War | tt2165735 | confirmed_correct | short_common_title |
| 909 | Stevie | tt0334416 | confirmed_correct | short_common_title |
| 910 | Afire | tt26440619 | confirmed_correct | short_common_title |
| 921 | Monos | tt6062774 | confirmed_correct | short_common_title |
| 926 | Tristram Shandy: A Cock and Bull Story | tt0423409 | confirmed_correct | source_resolved_title_difference |
| 930 | [Rec] | tt1038988 | confirmed_correct | short_common_title |
| 932 | Pig | tt11003218 | confirmed_correct | short_common_title |
| 936 | Enemy | tt2316411 | confirmed_correct | short_common_title |
| 942 | Whisky | tt0331370 | confirmed_correct | short_common_title |
| 950 | Elvis | tt3704428 | confirmed_correct | short_common_title |
| 955 | The Isle | tt0255589 | confirmed_correct | short_common_title |
| 957 | 3 Faces | tt8269552 | confirmed_correct | short_common_title |
| 959 | Where Does Your Hidden Smile Lie? | tt0342866 | confirmed_correct | year_conflict |
| 965 | The Ring | tt0298130 | confirmed_correct | short_common_title |
| 971 | Shirley | tt8430598 | confirmed_correct | short_common_title |
| 972 | Il Divo | tt1023490 | confirmed_correct | short_common_title |
| 983 | Control | tt0421082 | confirmed_correct | short_common_title |
| 984 | Cow | tt11548822 | confirmed_correct | short_common_title |
| 988 | Lantana | tt0259393 | confirmed_correct | short_common_title |
| 1000 | Jackie | tt1619029 | confirmed_correct | short_common_title |

### Unresolved identities
| Rank | Title | Reason |
| --- | --- | --- |

Metadata warnings remain visible for cuts, release dates, co-director omissions, and country definitions; identity confirmation does not rewrite those source fields.

## Audience coverage
| Measure | Before | After |
| --- | --- | --- |
| candidates | 1909 | 1909 |
| IMDb | 1908 | 1909 |
| Letterboxd | 1896 | 1900 |
| complete_pairs | 1896 | 1900 |

Missing components remain zero without renormalization. Missing data is not a claim that no Letterboxd page exists.

| IMDb ID | Film | Missing |
| --- | --- | --- |
| tt4573394 | Endless Corridor | letterboxd |
| tt16747572 | The Silence of Swastika | letterboxd |
| tt15176374 | Unpaarvayil | letterboxd |
| tt38063392 | Mission Muh Dikhayi | letterboxd |
| tt1380807 | Material | letterboxd |
| tt0274622 | LaLee's Kin: The Legacy of Cotton | letterboxd |
| tt31113046 | Making Memories of Murder | letterboxd |
| tt0970184 | Operation Homecoming: Writing the Wartime Experience | letterboxd |
| tt0316013 | Prisoner of Paradise | letterboxd |

## Award-source identities
| Source | Unresolved before | After |
| --- | --- | --- |
| efa_best_film | 11 | 8 |
| gotham_best_feature | 1 | 1 |
| nsfc_best_picture | 4 | 0 |
| nyfcc_best_film | 0 | 0 |
| lafca_best_film | 2 | 1 |
| critics_choice_best_picture | 29 | 22 |

| Source | Title | Status | IMDb ID / reason |
| --- | --- | --- | --- |
| efa_best_film | Harry, He's Here to Help | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| efa_best_film | Hidden | corrected | tt0387898 |
| efa_best_film | Brothers | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| efa_best_film | Grbavica: Esma's Secret | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| efa_best_film | La Vie En Rose | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| efa_best_film | Honey | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| efa_best_film | Blancanieves | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| efa_best_film | Nymphomaniac – Director's Cut | unresolved | Award covers both volumes/director cut; a single-film allocation is not inferred |
| efa_best_film | BPM (Beats per Minute) | corrected | tt6135348 |
| efa_best_film | Girl | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| efa_best_film | Compartment No. 6 | corrected | tt10262648 |
| gotham_best_feature | Test Pattern | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| nsfc_best_picture | Pan's Labyrinth (El laberinto del fauno) | corrected | tt0457430 |
| nsfc_best_picture | Waltz with Bashir (Vals im Bashir) | corrected | tt1185616 |
| nsfc_best_picture | Goodbye to Language (Adieu au Langage) | corrected | tt2400275 |
| nsfc_best_picture | Parasite (Gisaengchung) | corrected | tt6751668 |
| lafca_best_film | Crouching Tiger, Hidden Dragon (Wo hu cang long) | corrected | tt0190332 |
| lafca_best_film | Small Axe | unresolved | Anthology award; allocation to individual Small Axe films requires a product decision |
| critics_choice_best_picture | Quills | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Thirteen Days | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Ali | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Lord of the Rings: The Fellowship of the Ring | corrected | tt0120737 |
| critics_choice_best_picture | The Shipping News | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Lord of the Rings: The Two Towers | corrected | tt0167261 |
| critics_choice_best_picture | In America | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Lord of the Rings: The Return of the King | corrected | tt0167260 |
| critics_choice_best_picture | Master and Commander | corrected | tt0311113 |
| critics_choice_best_picture | Kinsey | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Dreamgirls | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Notes on a Scandal | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Sweeney Todd | corrected | tt0408236 |
| critics_choice_best_picture | The Kite Runner | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Nine | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Birdman | corrected | tt2562232 |
| critics_choice_best_picture | Star Wars: The Force Awakens | corrected | tt2488496 |
| critics_choice_best_picture | Loving | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Mary Poppins Returns | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Ma Rainey’s Black Bottom | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | News of the World | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | One Night in Miami | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Babylon | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Glass Onion: A Knives Out Mystery | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Saltburn | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | The Color Purple | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Sing Sing | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Jay Kelly | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |
| critics_choice_best_picture | Wicked: For Good | unresolved | Not an obvious alias for an existing candidate; retained outside-universe/identity review |

## Score and rank changes
18 retained films change score; 903 change ordinal rank. Substituted identities are shown separately because their before/after scores refer to different works.

| Film | Score before | After | Delta | Rank before | After |
| --- | --- | --- | --- | --- | --- |
| Birdman or (The Unexpected Virtue of Ignorance) | 336.92 | 440.52 | 103.6 | 145 | 65 |
| Caché | 372.0 | 452.0 | 80.0 | 104 | 59 |
| Mangrove | 37.04 | 84.65 | 47.61 | 1821 | 1273 |
| Lovers Rock | 100.78 | 147.77 | 46.99 | 1074 | 665 |
| Spider-Man | 147.57 | 107.23 | -40.34 | 665 | 1013 |
| Parasite | 734.21 | 769.21 | 35.0 | 3 | 2 |
| The Lord of the Rings: The Return of the King | 480.27 | 505.27 | 25.0 | 44 | 40 |
| Compartment Number 6 | 134.96 | 158.96 | 24.0 | 748 | 597 |
| 120 BPM (Beats Per Minute) | 284.89 | 308.89 | 24.0 | 212 | 173 |
| Goodbye to Language | 271.43 | 294.08 | 22.65 | 231 | 197 |
| Crouching Tiger, Hidden Dragon | 665.52 | 679.78 | 14.26 | 7 | 6 |
| Waltz with Bashir | 325.64 | 335.08 | 9.44 | 155 | 147 |
| Pan's Labyrinth | 542.52 | 551.27 | 8.75 | 26 | 24 |
| The Lord of the Rings: The Fellowship of the Ring | 457.84 | 459.84 | 2.0 | 54 | 54 |
| The Lord of the Rings: The Two Towers | 393.17 | 395.17 | 2.0 | 90 | 91 |
| Master and Commander: The Far Side of the World | 308.89 | 310.89 | 2.0 | 172 | 170 |
| Sweeney Todd: The Demon Barber of Fleet Street | 112.75 | 114.75 | 2.0 | 955 | 930 |
| Star Wars: Episode VII - The Force Awakens | 74.08 | 76.08 | 2.0 | 1431 | 1406 |

### Largest ranking movements
| Film | Rank before | After | Movement | Score delta |
| --- | --- | --- | --- | --- |
| Mangrove | 1821 | 1273 | 548 | 47.61 |
| Lovers Rock | 1074 | 665 | 409 | 46.99 |
| Spider-Man | 665 | 1013 | -348 | -40.34 |
| Compartment Number 6 | 748 | 597 | 151 | 24.0 |
| Birdman or (The Unexpected Virtue of Ignorance) | 145 | 65 | 80 | 103.6 |
| Caché | 104 | 59 | 45 | 80.0 |
| 120 BPM (Beats Per Minute) | 212 | 173 | 39 | 24.0 |
| Goodbye to Language | 231 | 197 | 34 | 22.65 |
| Sweeney Todd: The Demon Barber of Fleet Street | 955 | 930 | 25 | 2.0 |
| Star Wars: Episode VII - The Force Awakens | 1431 | 1406 | 25 | 2.0 |
| Waltz with Bashir | 155 | 147 | 8 | 9.44 |
| The Lord of the Rings: The Return of the King | 44 | 40 | 4 | 25.0 |
| The Act of Killing | 89 | 92 | -3 | 0.0 |
| The Other Side of the Wind | 1000 | 998 | 2 | 0.0 |
| High Fidelity | 980 | 978 | 2 | 0.0 |
| Nowhere in Africa | 994 | 992 | 2 | 0.0 |
| Spirit: Stallion of the Cimarron | 1009 | 1007 | 2 | 0.0 |
| Dancer in the Dark | 82 | 84 | -2 | 0.0 |
| Erin Brockovich | 206 | 208 | -2 | 0.0 |
| Trouble Every Day | 996 | 994 | 2 | 0.0 |
| Children of Men | 72 | 74 | -2 | 0.0 |
| Memento | 66 | 68 | -2 | 0.0 |
| The Piano Teacher | 97 | 99 | -2 | 0.0 |
| Road to Perdition | 928 | 926 | 2 | 0.0 |
| Ice Age | 1007 | 1005 | 2 | 0.0 |
| Dogville | 200 | 202 | -2 | 0.0 |
| Bloody Sunday | 964 | 962 | 2 | 0.0 |
| Zelary | 1737 | 1739 | -2 | 0.0 |
| American Splendor | 207 | 209 | -2 | 0.0 |
| Sympathy for Mr. Vengeance | 957 | 955 | 2 | 0.0 |

### Top50 / top100
| Set | Membership changes | Common ranks changed | Largest rank change |
| --- | --- | --- | --- |
| 50 | 0 | 12 | 4 |
| 100 | 2 | 52 | 4 |

The report gives numerical membership/order effects; materiality remains a product-review judgment.

### Distribution
| Metric | Before | After |
| --- | --- | --- |
| min | 0.0 | 0.0 |
| max | 803.78 | 803.78 |
| mean | 148.32 | 148.48 |
| median | 112.75 | 112.61 |
| stddev_population | 113.95 | 114.38 |

Score percentiles and diagnostic-band counts are in comparison.json.

## Provenance and reproduction
See identity-audit.json for every source/metadata field and evidence URL; award-identity-audit.json for every source gap; rating-enrichment.json for attempted provider selectors; manifest.json for all inputs/code hashes.

Offline regeneration: python integrity_research_score.py. Existing audience-cap comparison artifacts remain historical baseline results. No scoring threshold has been selected.
