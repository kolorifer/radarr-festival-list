# Legacy library audit — 2026-10-16

**Specification:** trusted supervisor task 6 for control issue #11; research only.
**Result:** verified private publication. This public brief contains aggregates and methodology only.
**Public scope:** this file only. The runner owns commit/push/PR and issue reporting
on `automation/issue-11-worker`; this worker performed no Git publication.

## Universe and provenance

Two fresh live library reads contained **969** entries. The reproducible exact
identity exclusion used the deployed qualified Movie List catalogue together with
current main-branch festival, curated and backcatalog outputs, fetched at one
pinned main revision. The resulting audit universe contains **475** entries.

| Exact current-output exclusions, in join order | Additional entries |
| --- | ---: |
| Qualified Movie List output | 387 |
| Festival output | 72 |
| Curated output | 2 |
| Backcatalog output | 33 |
| Total excluded | 494 |

Live read-only import-list inspection confirmed the festival feed is enabled for
automatic import. Curated/backcatalog exact matches were conservatively excluded
as current project output even without a corresponding enabled import. These
counts establish current-output membership; they do not prove the historical
importer of each entry. No release-year cutoff or reconstruction of previously
removed entries was used.

All candidates passed the current TMDb/IMDb identity cross-check. Current-output
provenance uncertainty is **0**; **3** conflicting external Wikidata crosswalks
are separately flagged and their enrichment excluded. These external conflicts
do not change the exact current-output anti-join.

The universe includes **50** downloaded entries and **136** canonical-watched
entries. One additional entry has an explicit standing preservation decision.
Watched and protection evidence stays visible in the private records.

## Advisory recommendations

| Recommendation | Entries |
| --- | ---: |
| `KEEP` | 137 |
| `PROBABLY_KEEP` | 233 |
| `REVIEW` | 105 |
| `PROBABLY_REMOVE` | 0 |
| `REMOVE_CANDIDATE` | 0 |

Canonical watched and explicit protection force `KEEP`. Existing downloads receive
`KEEP` or `PROBABLY_KEEP`. International/festival/major-award and canonical evidence
support preservation. Audience ratings alone, missing awards, language, release
age, franchise status or genre do not establish a removal case. Mixed or
incomplete evidence remains `REVIEW`. No adequately corroborated removal-oriented
case was established. Confidence describes the advisory preservation/review
judgment, not objective quality or permission to delete.

## Evidence coverage

Coverage below distinguishes fresh evidence, historical cache and lookup
completion. A completed lookup is not exhaustive verification or proof of no
recognition. Counts use all 475 candidates as denominator.

| Evidence | Available / checked | Coverage |
| --- | ---: | ---: |
| Current official IMDb rating and votes | 460 / 475 | 96.84% |
| Historical Letterboxd rating | 75 / 475 | 15.79% |
| Verified Letterboxd rating/watch count | 0 / 475 | 0.0% |
| Current TMDb supplemental metadata | 475 / 475 | 100.0% |
| Current RT critics score and count | 397 / 475 | 83.58% |
| Current Metacritic critics score and count | 352 / 475 | 74.11% |
| Metacritic current or historical score/count | 356 / 475 | 74.95% |
| Primary qualitative critics view | 360 / 475 | 75.79% |
| Exact structured recognition lookup completed | 458 / 475 | 96.42% |
| Primary BFI canon lookup completed | 475 / 475 | 100.0% |
| European recognition found | 92 / 475 | 19.37% |
| Independent/festival recognition found | 9 / 475 | 1.89% |
| Major/national award recognition found | 167 / 475 | 35.16% |
| Canonical evidence found | 63 / 475 | 13.26% |

The pipeline joins the [official IMDb daily dataset](https://data.imdb.com/non-commercial-datasets/)
once, reuses validated project evidence, fetches exact TMDb identities, batches
Wikidata entities, and caches direct RT/Metacritic source results. Every private
record contains source information, availability status, dates where known,
confidence, rationale, positive/negative evidence and a personal-fit note.

Wins, nominations, selections/participation, negative awards and canon evidence
are distinguished. Secondary claims retain category/context and references;
participation is never reported as a prize. Domestic popularity recognition alone
is not a decisive preservation signal. Source and recommendation facts are
separate. No production scoring model, numerical rating gate or automatic action
was introduced.

## Source limitations

- Direct Letterboxd access returned HTTP 403. Historical provider vote counts are
  retained privately but cannot reliably be labelled ratings versus watches.
  Original retrieval dates for historical rating/award caches are unavailable.
- Wikidata is an incomplete secondary index. Five sampled official award reference
  pages were unavailable; their claims are not presented as freshly corroborated
  official-source facts. Individual award/festival programmes and cast/crew
  nominations were not exhaustively researched. Seven claims lack a usable
  English label and are explicitly marked unavailable.
- The [BFI critics' list](https://www.bfi.org.uk/sight-and-sound/greatest-films-all-time)
  was checked across all 264 entries, including ties. The Criterion primary
  extraction contains 344 entries and is partial. Unique title/year/known-alias
  matches are tied to independently verified library identities; ambiguous
  matches are not accepted. Registry access returned HTTP 403. Ebert and
  restoration catalogues were not exhaustively verified.
- **45** critic-page year discrepancies are flagged; the affected fresh aggregates
  are excluded. A discrepancy may reflect release-date conventions or a wrong
  crosswalk and requires review. Historical fallback evidence, where present,
  remains separately labelled. Legacy Radarr critic values with zero review
  counts/user-type labels are unverified context and do not inflate coverage.
- Qualitative views paraphrase the primary consensus verdict and mentioned themes
  automatically; they are not independent critical essays. Private excerpts are
  capped at 20 words per primary source. Unknown context biases toward review.

## Private deliverables and verification

Only these two audit artifacts are published in the designated private state
repository; no detailed inventory is included in this public repository:

- `legacy-library-audit-2026-10-16.json` — every candidate, evidence, recommendation,
  exact derivation inputs, cached enrichment and reproducible pipeline sources.
- `legacy-library-audit-2026-10-16.md` — methodology, coverage, limitations and
  ordered advisory review groups, including explicit empty removal groups.

The worker-local validation script passed **34 consistency and safeguard checks**
across all 475 records: exact universe, identity uniqueness, current-output
exclusion, downloaded/watched/protection rules, explicit missing evidence,
confidence/category validity, source types, count/percentage reconciliation,
negative-award separation and quote limits. Ten representative groups were sampled: 13 primary critic score/count pairs
matched fresh reads, and six direct Metacritic IMDb identities matched. Detailed
spot-check results and independent live comparison are retained privately.

Fresh before/after reads returned identical allowlisted library records,
canonical watched manifest, production catalogue and deployment revision.
This worker issued only read requests to Radarr and made no media, service,
configuration or credential changes. Publication is restricted to the two named
private artifacts using the existing publisher credentials and verified private
repository metadata; both uploaded files are read back and compared byte-for-byte.
Public privacy scanning, `git diff --check`, new-file whitespace checking and
final single-file scope verification passed. Runtime unit tests were not run:
no application/runtime code was modified or deployed.

## Handoff

No deployment or daemon activation. Existing repository work, active task briefs,
project state, decisions and seedbox research helper remain untouched. The private
recommendations require supervisor/user review; they authorize no deletion.
The runner supplies the resulting public commit and PR references.
