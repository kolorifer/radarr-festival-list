# Generic conflict investigation

## Approved scope

Owner requested generic conflict investigation starting with Madame Bovary, keeping
conflicting-ID overrides subject to review. Test/deploy safely without downloads
or notification replay. This introduces proposal discovery, not identity repair.

## Implementation

The collector admits strongly correlated title/year/identity conflicts to existing
research eligibility. Structural listing conflicts, invalid/nonmovie metadata,
authentication failures and weak/conflicting source correlation remain excluded.
Original asserted IDs are retained privately for research even when removed from
user-facing accepted metadata. Actor matching/approval still blocks the conflict.

The research worker searches title alternatives even when the source IMDb link
already maps to a movie. It retains the linked candidate, prioritizes matching-year
search candidates for detail inspection, and preserves all source/identifier/year
contradictions. Details include director, cast, runtime and original language.
Independent source corroboration is explicitly marked missing when unavailable;
a candidate is always review_required, never an applied runtime correction.
At most one title search and three details are used for conflict investigations,
plus the source IMDb lookup: within the existing five-GET per-version budget.
Recurring budgets (five cases/25 GETs weekly), isolation and timer unchanged.

## Components and tests

Changed actor context/observer, collector identity_selection, research provider/
worker, and regression tests. Tests cover a wrong linked adaptation plus the
matching-year alternative, retained contradictions, proposal-only status,
corroboration gaps, source assertion retention without display/action approval,
and the strong-source eligibility boundary. Existing safeguards remain covered.

Local suite616 tests passed (two Linux-only skips). Seedbox: full actor runtime599
and collector-compatible implementation616 tests passed. CI3.12/3.13 passed.
Implementation082a1ca; PR71 merged as0f27ec7b6283bf6c263e91bbc17b8469ff0f0075. Actor/worker runtime15e07b4 is based on pinned c2ae4e1.
Collector identity_selection is from082a1ca, preserving its newer selected-only
intake behavior; other collector modules remain at their verified installed versions.

## Deployment

Production clean at15e07b446637f21049f9a673b80c543e945fa0ac. Private backups taken,
dependency/catalog/config preflight passed, local/public health200 with1909movies.
Actor and collector restarted; research timer paused only during deployment and
restored. Selected-only intake verified. Actual collector startup Landlock ABI6
denial checks and installed-worker protected-file/symlink/inherited-FD/network
negative proofs passed; worker proof issued zero HTTP requests. Protected configs,
units, unchanged modules, approval state and downloader receipts preserved.
No research budget reset, source exception, history deletion or notification replay.

## Madame Bovary pilot

Fresh exact-source read-only context confirmed year_conflict and retained the
tracker IMDb assertion privately. Only its metadata observation was published to
the collector; no webhook handler, notification or acquisition method was invoked.
The strongly correlated case became research-eligible while approval stayed
unavailable. The confined scan exited0 and used exactly five GETs: find, movie
search and three candidate details. Weekly usage increased from2cases/4requests
to3cases/9requests, within unchanged caps. Result: identifier_conflict,
next_action human_review, runtime_correction false, current proposal retained.

| Candidate | Catalog evidence | Remaining conflict |
| --- | --- | --- |
| Tracker-linked TMDb253161 / IMDbtt2334733 | 2015; Sophie Barthes;118min; Mia Wasikowska, Rhys Ifans | Filename year1949 disagrees |
| Proposed alternative TMDb45184 / IMDbtt0041615 | 1949-08-25; Vincente Minnelli;106min; Jennifer Jones, James Mason;English | Different IMDb from tracker; independent source corroboration missing |
| Competing TMDb2528 / IMDbtt0102368 | 1991; Claude Chabrol;143min; Isabelle Huppert;French | Both IMDb and year disagree |

The1949 record is the relevant candidate for human review, not an approved torrent
identity. All three remain review_required; search/detail truncation is recorded.
Post-pilot collector still says needs_review/year_conflict; no Madame Bovary
approval was created or changed. Actor/collector active NRestarts0; daily timer
active. No downloads or deliberately replayed notifications. The existing
changed-case digest can surface this new proposal under its approved normal policy.

## Limits

Catalog candidate metadata is not independent proof of the torrent's content.
The worker has no tracker credentials and does not fetch NFOs or media files;
missing independent corroboration is surfaced for review. Title search examines
one bounded result page and at most three candidate details; it cannot prove
catalog completeness. Existing historical review-only projections are not bulk
replayed; new/materially refreshed outcomes use the generic flow. The existing
changed-case digest may report new evidence through its normal delivery policy;
no old notification is deliberately replayed. No override is applied automatically.
