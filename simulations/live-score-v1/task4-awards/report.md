# Task 4 — eight-film awards and Recognition review

**Ready for bounded research review; evidence remains incomplete.** Research cutoff:
**2026-10-28**, day precision. No base Recognition subtotal changes versus Task 2.
The meaningful delta is narrower uncertainty: **49 category/edition/stage gaps
closed**, with other coverage explicitly unresolved. Passing tests establish
reproducibility, not evidence completeness or product acceptance.

This packet is the new Task 4 delta against
`824ed090e93c69e7ee5af6fe7df398725d8a6056`. Task 2 arithmetic/evidence baseline is
`489ce4e3e005dbb15fadebf8ac27e6c181cf3a98`; Task 1 reference is
`b62f00de56b2f1aa488e9f41742b86617efcec72`. Those inherited, unmerged research
artifacts are **prior work**, not Task 4 deliverables. [PR #88](https://github.com/kolorifer/radarr-festival-list/pull/88)
remains closed/unmerged under the supervisor's publication contract; this worker
made no GitHub write or independent claim about its live state. Parent publication
must use a **new research PR**, linked to [#86](https://github.com/kolorifer/radarr-festival-list/issues/86)
and #88, and identify this baseline/delta. No merge or deployment is authorized.

## Inventory and research method

[Pre-research inventory](inputs/gap-inventory.json) derives **112 film/institution
entries** from Tasks 1/2 before new checks: retained scored components, original
records, categories, edition envelope, existing coverage checks, priorities and
reasons for further work. The eight identities and release-event context are the
exact Task 3 manifest. No IMDb/TMDb substitution or fresh audience observation.
Nina Roza remains `tt29271639` / 1527449, **not** `tt29893755`. The festival
attribution uses title, director and film context; an institution need not print
an IMDb ID. Nina's [CIFF dossier](https://www.ciffcalgary.ca/films/2026/nina-roza)
corroborates that context, not a new ID correction. The retained 2026-04-24 TMDb
event is not a worldwide release claim. Buildings retains 2026-12-04 as one
future release event; its [Fortnight dossier](https://www.quinzaine-cineastes.fr/en/film/i-see-buildings-fall-like-lightning)
already documents a 2026 world premiere, with Clio Barnard directing.

The audit envelope is deliberately explicit: festival/Sundance/annual critics/
Gotham editions **2024, 2025, 2026**; Academy/Globes/BAFTA/Spirit/Critics Choice
ceremonies **2025, 2026, 2027**; EFA **2024 (37th), 2026 (38th), 2027 (39th)**.
There is no invented 2025 EFA ceremony. Each component has a winner stage and,
where the retained model awards nonzero selection/nomination points, a separate
selection/nomination stage. This is 1,224 auditable cells, not 1,224 new fetches.
The initial release-season candidate subset has 408 cells: retained-year festivals/
annual awards, following-year ceremonies, and the stated EFA transition. These
are candidate scopes, **not inferred film eligibility**. Additional window cells
make potentially different release seasons visible rather than silently certifying
them absent. No claim covers every award a film may ever receive.

New reads target missing category or final-result stages; already adequate
positive nominations are reused with their original 2026-10-25/26 dates. Each of
the 19 source records in [evidence.json](inputs/evidence.json) states why it was
needed, URL, actual observation day, original scope, edition/date where established,
access method and limitations. Ten primary-origin pages were readable through the
web reader (cache possible), one mirrored primary PDF was read, one other festival
dossier provides secondary Berlin corroboration, one syndicated primary release
was indexed only, and six origin URLs failed. The indexed release also returned
403 on open. These are source records, not a count of unique successful origin
network requests; searches and sectional reads of the same page are not extra
verifications. No origin-live freshness guarantee or invented request timestamps.
Only normalized facts/lists/citations are retained, not page bodies or articles.

## What genuinely closed, and what did not

| New check | Evidence effect and limit | Newly closed cells |
| --- | --- | ---: |
| [Spirit 2025 nominations](https://www.filmindependent.org/press-releases/film-independent-announces-nominees-for-the-40th-anniversary-2025-spirit-awards/), [2026 nominations](https://www.filmindependent.org/press-releases/film-independent-announces-nominees-for-the-2026-spirit-awards/) | Scoped Best Feature/First Feature negatives for relevant retained seasons; existing Anora/Substance positives reused. Nomination absence also excludes a win in that same category/edition. | 20 |
| [EFA 2024 final record](https://www.europeanfilmawards.eu/award-edition/awards-2024/), [2026 final record](https://www.europeanfilmawards.eu/award-edition/awards-2026/) | Scoped European Film negatives and final winner stages; retained Substance/Accident nominations and Sentimental Value win unchanged. | 12 |
| [Sundance 2026 final awards](https://www.sundance.org/blogs/2026-sundance-film-festival-announces-award-winners) | Nina/Buildings do not appear among Grand Jury, Audience, Directing or Special Jury winners in the four defined feature Competition sections. **Competition credit remains unchecked.** NEXT, shorts, Waldo Salt and other types are not added to the model. | 8 |
| [BAFTA 2026 results](https://www.bafta.org/awards/film/?award-year=2026) | Closes Hamnet non-English and Accident Best Film scopes, and non-winning stages; no change to positive Best Film/non-English components. British Film and acting recognition are unscored here. | 7 |
| [Gotham 2024 winners](https://thegotham.org/press/34th-gothams-winners/), [2025 winners](https://thegotham.org/press/winners-2025-gotham-film-awards/) | Final Best Feature winner stage for Anora/Hamnet closes; neither wins. Other negative nomination scopes were already closed in Task 2 and are not counted again. Accident's International Feature win is a distinct unmodeled category. | 2 |

There are **70 new explicit checks**: 36 scoped negative assertions, 16 pending
calendar assertions, 18 unavailable assertions. Expanded into distinct stages and
compared with retained coverage, these close 49 previously unchecked/unavailable
cells. An assertion and an expanded stage cell are different units. No new scored
component, corrected component, or base-score change was found. No misattribution
was demonstrated in retained scored facts; no correction has been invented.

[The 39th EFA calendar](https://www.europeanfilmawards.eu/campaign-rules/) separates
the October shortlist from November 14 nominations and January 16, 2027 awards.
This classifies 16 previously unchecked cells as pending, **not closed positive/
negative evidence**. Retained Academy and Critics Choice calendars remain pending
for the two 2026 controls. Other future-season cells whose announcement timing
was not checked remain `source_not_checked`; they are unresolved, not negatives.

[Nina's screenplay attribution](https://infomedia.sh/wp-content/uploads/2026/02/berlinale-preise-2026.pdf)
is corroborated by page 4 of the mirrored official-jury document dated 2026-02-21:
Geneviève Dulude-de Celles is explicitly credited for Nina Roza. This strengthens
attribution but is **not direct Berlinale-origin retrieval** and adds no new points.
The direct festival overview was inaccessible. This packet conservatively leaves
its unverified negative winner stages unavailable rather than certifying absence
from the mirror. Original [Talents evidence](https://www.berlinale-talents.de/bt/page/c/festival-returnees-2026)
remains the retained scored Competition and candidate-screenplay source.

Hamnet's [retained producer evidence](https://amblin.com/movie/hamnet/) is supported
by an [indexed TIFF-origin syndicated announcement](https://ebs.publicnow.com/view/66AC456BAB1E8414DECF54463E5ACC650BF8355D).
That corroboration distinguishes the main People's Choice winner from Sentimental
Value's **International** runner-up placement, which earns no candidate points.
The syndicated page returned 403 on direct open; a candidate TIFF-origin URL also
failed. Neither indexed text nor failed URLs establishes absence for other films.

LAFCA's [2024 archive](https://www.lafca.net/Years/2024.php),
[2025 archive](https://www.lafca.net/Years/2025.php) and
[2025 press release](https://www.lafca.net/pressReleases/7Dec25.php) again failed
(timeout, timeout, 502). Indexed primary results surfaced, but **no new absence
is certified from them**. Anora's retained positive remains intact; repeat access
failure does not erase it. No alternate proxy, authentication, account or barrier
bypass was attempted. The Cannes 2026 selection URL was inaccessible; Buildings'
Fortnight selection is positive side-section context, not main-Competition award
proof or a complete main-Competition negative. The failed attempted URLs are
recorded as attempts, not asserted canonical/citable award records.

## Recognition comparison

Observed points only; **cohort order is retained, not ranked**. All eight complete
Recognition fields are null. A displayed zero is no observed scored component,
not a complete zero-awards claim. See [detailed components and individual links](breakdowns.md),
[film JSON](results.json) and [eight-row CSV](comparison.csv).

| Film | Europe /20 | Independent /10 | US /10 | Critics /10 | Task 2 base | New base /50 | Evidence Δ | TIFF only | Screenplay only | Both  Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Hamnet | 5 | 1 | 9 | 0.8 | 15.8 | 15.8 | 0 | 19.8 | 15.8 | 19.8  Partial |
| Anora | 19 | 6 | 10 | 6 | 41 | 41 | 0 | 41 | 41 | 41  Partial |
| The Brutalist | 13 | 0 | 9 | 4.3 | 26.3 | 26.3 | 0 | 26.3 | 26.3 | 26.3  Partial |
| The Substance | 4.4 | 2 | 7.5 | 0.8 | 14.7 | 14.7 | 0 | 14.7 | 20.7 | 20.7  Partial |
| Sentimental Value | 20 | 0 | 10 | 0.8 | 30.8 | 30.8 | 0 | 30.8 | 30.8 | 30.8  Partial |
| It Was Just an Accident | 19.4 | 0 | 5 | 0 | 24.4 | 24.4 | 0 | 24.4 | 24.4 | 24.4  Partial |
| Nina Roza | 2 | 0 | 0 | 0 | 2 | 2 | 0 | 2 | 8 | 8  Partial |
| I See Buildings Fall Like Lightning | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0  Partial |

All four same-variant evidence deltas versus Task 2 are zero. Optional **within
packet** deltas remain TIFF +4 for Hamnet, screenplay +6 for The Substance/Nina;
all others zero observed bonus. Uncertified candidate absence is explicitly
`source_not_checked`, not a verified ineligibility assertion. TIFF is main winner
only, capped inside Independent /10; screenplay is a uniquely attributed main-
Competition Cannes/Berlin/Venice win, once across festivals, capped inside Europe
/20. Both are **off in base and unapproved as permanent policy**.

The retained research Recognition function reconstructs historical components at
`9c5a0f06e1c39e48653338fd0865ddabdc525a61`: normalized family sum caps at 100,
then Europe ×0.2 and the other families ×0.1. Sources corroborate the same
component without stacking; win replaces nomination for that component. Legitimate
distinct components add, including competition and a different festival prize.
Sundance Grand Jury+Audience convergence remains exactly unchanged. No production
scoring module is imported or edited.

For example, Anora's Academy win plus Globe nomination is normalized 110, capped
to 100 = US10; another citation adds zero. Sentimental Value's Academy Picture
nomination + International win + Globe components exceed US100; its BAFTA + EFA
+ Cannes components exceed Europe100. Both families remain capped. Corroboration
therefore cannot raise its subtotal. Gotham International Feature and EFA
screenwriter wins do not map to the existing Best Feature/European Film components.
The retained EFA category expanded to include documentary/animation nominees;
the legacy single `efa_best_film` mapping is preserved and flagged for review,
not redesigned. The historical Globe Drama/Comedy shared component also remains
strongest-once; no hierarchy, section eligibility or weights have changed.

Hamnet's old curated **1** remains the existing IMDb list-membership counter,
unrelated to this Recognition subtotal. Its scoped Spirit/EFA/BAFTA/Gotham gaps
narrow, while base stays **5+1+9+0.8=15.8** and the retained experimental TIFF
variant stays **19.8**. This is no new score gain since Task 2, no feed repair,
and no audience/overall calibration. Audience 50 / Recognition 50 and experimental
Approach A remain the agreed context; this task neither recalculates Audience nor
finalizes constants, overall scores or overall ranks.

## Coverage as of cutoff

| State | Full three-edition audit window | Initial release-season candidate subset |
| --- | ---: | ---: |
| verified_positive | 53 | 53 |
| scoped verified_no_award | 70 | 66 |
| source_not_checked | 1,048 | 248 |
| unavailable | 17 | 17 |
| not_yet_announced | 36 | 24 |
| Total | 1,224 | 408 |

These are phase cells, not percentages of all possible awards or source fetches.
The smaller subset is a reproducible starting audit scope, not proof of release
eligibility. A nomination being positive does not automatically close its final
winner stage. A complete nomination-list absence closes both nomination and win
for that same category/edition. A winners-only absence never closes nomination
or participation. Archived facts with unknown edition remain scored per baseline
but do not assert dated matrix coverage.

[coverage.json](coverage.json) and [coverage.csv](coverage.csv) enumerate every
film/institution/component/edition/stage with check/positive-record IDs and a
concrete reason. [unresolved.csv](unresolved.csv) enumerates **all 1,101 unresolved
cells**, including pending; no cells are omitted from the report's machine-readable
handoff. Core gaps include LAFCA negative coverage; Berlin direct final-record
access; Cannes 2026 main selection/award scopes; festival participation and other
unreviewed categories; exact prior final-winner stages not independently checked;
and forthcoming/unchecked release seasons. Successful source/tool reads are not
completeness. Source barriers did not block completion of this bounded packet.

## Offline reproduction and owner review

Standard-library Python 3.9+; available interpreter was 3.9.6, no project venv or
supported 3.12/3.13 interpreter found. No new dependencies. Run from repo root:

```sh
python3 simulations/live-score-v1/task4-awards/compare.py
python3 simulations/live-score-v1/task4-awards/compare.py --check
python3 -m unittest discover -s simulations/live-score-v1/task4-awards -p 'test_*.py' -v
```

Inputs pin 34 Task 1/2/3 packet/report files by SHA-256, the exact manifest, Task 2
numerical baseline, historical revision and source evidence. Regeneration has no
network/Git subprocess, audience calculation, background work or baseline writes;
provenance tests alone inspect local pinned Git objects. Focused behavior tests
are synthetic; the cited records support real-film claims. Actual focused and
preservation commands/results are in the [engineering report](../../../docs/reports/2026-10-28-live-score-v1-task4-awards.md).
No full runtime suite, service, live integration or production verification is
claimed. No later task is commissioned.

| Owner-facing review | Finding / remaining question |
| --- | --- |
| Meaningful delta | 49 exact gaps close; base evidence delta is zero for all eight. Is this narrower evidence status sufficient for the current review, with explicit unresolved scopes? |
| TIFF proposal | Hamnet +4 only. Keep main-winner-only and Independent cap? International runner-up is excluded. No approval is assumed. |
| Screenplay proposal | Substance and Nina +6 each; unique main-Competition film attribution, once per film. Approve/reject this scope independently of TIFF? |
| Legacy mappings | EFA expanded European Film nominations and historical shared Globe component are retained. Any policy reconsideration needs a separate agreed brief. |
| Coverage display | Review the examples below; they propose wording only, with no new completeness threshold or UI/runtime implementation. |

Plain-text display proposals:

- `Hamnet — Recognition observed 15.8/50. Partial coverage; complete score unavailable. Experimental TIFF variant 19.8 (+4).`
- `Nina Roza — Recognition observed 2/50. European Film 2027 nominations pending (scheduled 14 Nov 2026). Experimental screenplay variant 8 (+6).`
- `Hamnet — no nomination in Spirit Best Feature / Best First Feature, 2026 only, verified against final lists. Other institutions remain partial.`
- `I See Buildings Fall Like Lightning — Recognition observed 0/50; incomplete. Directors’ Fortnight selection is outside scored Cannes main Competition; main-Competition coverage unavailable.`

These examples do not equate missing with zero, certify overall completeness, or
approve the optional additions. Separate audience-provider enquiry remains
independent and untouched. Parent owns publication; user/ChatGPT owns acceptance.
