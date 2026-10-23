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

Pending final checks. Added tests cover language bonuses/dubs/commentary, Chinese
varieties, contradictory labels, four-detail bounds, visible incomplete rivals,
pagination and ambiguous alias intersections. Historical offline fixtures keep
their old input semantics; the new rule applies to fresh structured audio facts.
