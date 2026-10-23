# Multilingual scoring and bounded rival discovery

## Approved scope

Enable the approved multilingual language rule in shadow and remove ChinaII's
three-search-result stop, preserving bounded requests and visible rivals. Test
and deploy without downloads, notifications or production identity changes.

## Implementation

Fresh NFO audio earns the existing10 language points once if a supported film
audio language matches the candidate original language. Additional dubs and
commentary never stack points or incur a penalty. Missing/uncertain evidence
earns0. Audio sections not labelled commentary/auxiliary audio are treated as
film audio; this is an evidence-based assumption, not content inspection. Explicit
commentary, audio description and isolated-score labels are excluded. Catalog
language names map to codes; Chinese alone stays ambiguous, but an explicit
Cantonese/Mandarin qualifier or title label can disambiguate. Contradictory labels
are not used. Individual raw track labels/roles and scoring codes remain visible.

Each of at most2 alias queries retains up to20 first-page movie results. Unique
IDs are merged with tracker-ID candidates (maximum41). At most4 receive detail
lookups, prioritizing the tracker ID then existing title/year weights; only the
provisional leader receives a new reverse-ID lookup if needed. Thus normally at
most9 metadata requests, still enforced by unchanged10/run40/day reservations.
No popularity-based discarding. Search-only rivals remain in the scored output
with an optimistic100-point upper bound, forcing review until adequately checked.
Pagination/inconsistent query summaries also force review. The same sole movie
in the intersection of complete alias result sets can corroborate an undocumented
alias only alongside the existing catalog-title/year/checked-ID requirements;
other rivals still constrain the margin. Source conflicts remain blocked.

## Validation/deployment

Added tests cover language bonuses/dubs/commentary, Chinese
varieties, contradictory labels, four-detail bounds, visible incomplete rivals,
pagination and ambiguous alias intersections. Historical offline fixtures keep
their old input semantics; the new rule applies to fresh structured audio facts.


## Tests and deployment results

Runtime commit **29b9ace**, on draft PR #78, was deployed only to the isolated
shadow service. All 732 tests passed locally (two Linux-only skips, 134.344s)
and on the seedbox (46.578s); both Python 3.12/3.13 CI checks passed in run
39907081774. The targeted 51 shadow/offline/fresh tests also passed. Historical
offline fixture output remains unchanged.

The shadow unit now uses the tested archive under
`~/.local/share/identity-scoring-shadow/29b9ace`. Backup:
`identity-scoring-shadow-backup-4vzi7s0n`. Actor remains
**658d8f838aed7a03db7d01244254362fba99369a**. Protected source/configuration/action
hashes were unchanged, local health returned HTTP 200, and movie-intel,
identity-triage, research scan timer and shadow timer were all active afterward.
No downloads, notifications, actor restarts or production identity corrections
were triggered. Research history, request ledgers and pilot end time were preserved.

## Fresh observed results

| Case | Leading candidate | Score | Margin | Outcome | GETs |
| --- | --- | ---: | ---: | --- | ---: |
| China II | Once Upon a Time in China II, TMDb 10618 | 99.446903 | 111.344224 | Review | 8 |
| China III | Once Upon a Time in China III, TMDb 10619 | 98.660714 | 98.660714 | Would identify in shadow | 5 |
| The Beast | La bête / The Beast, TMDb 914206 | 100 | 0 | Review | 7 |

China II's searches returned four and three results, merging into four unique
candidates. All four received details: China II (99.45), China III (-11.90),
The Master (-20), and China IV (-68.44). No candidate-capacity failure remains.
Its 113m25s NFO runtime and five tracks are parsed; two Cantonese tracks,
Mandarin and an English dub are retained, while English commentary is excluded
from language scoring. Cantonese earns 10 points once. Review remains because
three films occur in both alias search result sets, so the undocumented alias
is not uniquely corroborated, and the existing identity-conflict review guard
also remains in force. The high numeric margin does not bypass either guard.

China III rises from 88.660714 to 98.660714 with the approved 10-point language
bonus. Its 111-minute NFO and four tracks remain visible. Explicit Cantonese
and Mandarin labels are recognized; commentary is excluded. The English dub
is retained as raw evidence but has no scoring code because English is absent
from this candidate set's catalog language map. This does not affect the
Cantonese original-language match. Both alias searches return only TMDb 10619.

The normal shadow service run also refreshed The Beast: French audio, 146-minute
runtime, year evidence and IMDb tt14407336 support TMDb 914206 at 100 points.
The broad search has additional pages; all 20 first-page candidates are retained,
four detailed, with the other 16 explicitly search-only. Their conservative
100-point upper bounds prevent a confident margin. Incomplete discovery and the
existing conflict review guard keep this a review proposal, not an approval.

The validation and normal shadow run used 20 GETs total (8+5+7), bringing the
existing daily ledger from 18 to **38/40**. Per-refresh counts stayed below the
unchanged 10-request limit. No budget increase or ledger reset occurred.
Genealogies of a Crime retains its previously refreshed 100-point proposal;
it was not re-fetched for this validation. Coverage remains eight historical
snapshots and four genuinely new pilot cases.

## Remaining limitations and handoff

Scores are evidence scores, not probabilities or production approvals. The
existing alias and conflict safeguards can still require review despite a high
score. Search-only rivals deliberately keep broad searches inconclusive; this
change makes them visible instead of failing the whole search. No extra pages
or unbounded detail expansion are fetched. Language recognition uses explicit
NFO labels and available catalog names, not audio inspection; ambiguous labels
remain unscored. The raw legacy `audio_language_missing_or_mixed` gap may still
appear alongside the new, valid per-track language codes.

The pilot still ends 2026-10-27 at 19:12 Europe/Warsaw. PR #78 remains draft;
production scorer activation and further policy changes require review.
