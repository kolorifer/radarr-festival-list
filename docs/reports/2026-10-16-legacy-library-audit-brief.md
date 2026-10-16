# Legacy-library audit: second-pass aggregate report

Research only, completed 2026-10-16 for control issue #18, supervisor task 1.
Detailed inventory, evidence and recommendations remain in the private
`kolorifer/radarr-state` repository. This public report contains aggregates only.

## Results

| Recommendation | Task 6 | Second pass |
| --- | ---: | ---: |
| KEEP | 137 | 137 |
| PROBABLY_KEEP | 233 | 249 |
| REVIEW | 105 | 89 |
| PROBABLY_REMOVE | 0 | 0 |
| REMOVE_CANDIDATE | 0 | 0 |
| Total | 475 | 475 |

Deep research covered 133 records: all 105 previous REVIEW records and 28
additional records with source-identity, critic-page or aggregate-coverage gaps.
Sixteen preservation judgments gained affirmative corroboration. Each remaining
REVIEW has a film-specific post-research reason and reception profile. No
removal-oriented distribution was manufactured, and unavailable evidence never
became a removal argument.

## Evidence coverage

Counts below use the same 475-record denominator. Verified earlier evidence
retains its retrieval date when a fresh request is blocked; a failed request
does not count as newly verified evidence.

| Evidence | Task 6 | Second pass |
| --- | ---: | ---: |
| IMDb rating and rating count | 460 | 462 |
| Rotten Tomatoes score and critic count | 397 | 415 |
| Metacritic score and critic count | 352 | 380 |
| Metacritic including historical cache | 356 | 382 |
| Primary qualitative critic evidence | 360 | 376 |
| European recognition, primary or labeled secondary evidence | 92 | 100 |
| Independent/festival recognition, primary or labeled secondary evidence | 9 | 10 |
| Major-award evidence | 167 | 167 |
| Canonical reputation evidence | 63 | 64 |

The official IMDb daily dataset was joined against the entire universe. Exact
TMDb identity and supplementary audience evidence were refreshed for all 133
research targets. TMDb supplement coverage remains 475; unrated cohorts remain
explicit. Letterboxd remains 75 historical cached ratings and zero newly
verified rating/watch-count observations.

Additional release/status checks covered 35 records with sparse reception or
unavailable film-article context, distinguishing provisional release metadata
from an established reception record.

Revision-pinned film-article context was recovered for 108 targets. Following
archive, review and contextual links produced 513 distinct source URLs: 366
returned content and 147 were unavailable. Returned follow-up content covered
94 targets; 48 had returned content at individual-review URLs. These are access
counts, not counts of verified awards or favorable reviews. Casting and
distribution news, navigation text and empty scripted pages do not establish
critical consensus or recognition.

## Method and safeguards

Unattended SSH and the seedbox's existing private authentication supplied the
two original audit artifacts and canonical protection data. No local `gh` was
used. Live read-only Radarr collections were reconciled against the deployed
qualified catalog and current public feed union. The 969-record library still
contained exactly 475 audit candidates and 494 current-output exclusions.

Research combined current audience data, independently sourced critic
aggregates, individual reviews, official festival/program archives, award
context and canonical listings. Secondary film articles located source leads;
they were not treated as proof of absence. Wins, nominations, participation and
individual cast/craft awards remain distinct. Future scheduled honors were
excluded from completed-award claims.

Regional release-year discrepancies required additional identity evidence.
Metacritic's embedded movie identity was decoded explicitly. Rotten Tomatoes
discrepancies required the exact dual-identity crosswalk, film-title match and
complete director-set corroboration from current metadata; 25 source checks
were resolved through that route. A canonical lookup additionally corrected
an American/British spelling difference using an identical release year.
Unresolved identities remain explicit.

Downloaded, canonical-watched, explicitly protected and identity/provenance
ambiguous records retain their safeguards. Current-project output remains
excluded. No rating gates, scoring weights, genre/franchise cleanup rules or
automatic actions were introduced.

## Verification and delivery

All 475 records were checked for universe membership, exact identities,
recommendation completeness, protection rules, source distinctions and count
arithmetic. Twenty-five representative records were spot-checked across
preservation changes, protected/downloaded records, identity ambiguity and
mixed/sparse REVIEW patterns. Twenty-two fresh primary critic rechecks matched;
three samples had no applicable critic aggregate. With zero removal-oriented
recommendations, the conditional removal sample requirement does not apply.

Independent before/after reads confirmed identical allowlisted live library
records, canonical watched data and deployed catalog bytes. Radarr operations
were GET-only. No media, service, configuration or viewing/protection changes
were made.

Exactly these two private artifacts are replaced, with prior versions retained
in private Git history:

- `legacy-library-audit-2026-10-16.json`
- `legacy-library-audit-2026-10-16.md`

The JSON preserves per-record evidence, source tiers, retrieval dates, earlier
judgments, reproducible research scripts and validation results. The Markdown
provides the corresponding private review report. Private source caches remain
outside the public repository. Public publication and independent artifact
verification belong to the runner/supervisor.

Limitations remain material: 25 targets lacked identity-resolved film-article
context; some archive requests were blocked or returned unusable content;
Letterboxd could not be newly verified; some award claims remain explicitly
secondary; and small audience/critic cohorts limit confidence. This is not an
exhaustive cast/crew-award or canonical-catalog crawl. The 89 REVIEW judgments
remain for product review. Runtime tests were not run for this audit/document
change; audit validation, representative source checks, privacy checks and
diff/whitespace checks provide the relevant verification.
