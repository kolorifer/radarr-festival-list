# Generic edition claims and sourced runtimes — shadow deployment

## Outcome and authorization

Owner approved generic discovery of unfamiliar editions from release names,
tracker descriptions and NFOs, with sourced corroboration and review when evidence
is inconclusive. Implemented in the existing shadow pilot at
**8fd8283f33a9c1c8ce2642f0a66e01977b0bb857**; production actor remains
**d598296e4ba3b3223e9014c993b116ada9ed723e**. No production identity gate changed.
[Brief](2026-10-26-generic-cut-discovery-brief.md) and
[draft PR90](https://github.com/kolorifer/radarr-festival-list/pull/90), isolated
against the existing shadow branch. Unrelated CODEX_TASK is preserved.

## Behavior

`cut_discovery.py` collects bounded noun phrases ending in cut/edition/version,
unexplained title/suffix labels, and runtime disagreement without a label. Cut
names are not enumerated. Technical filename tokens, the known movie title and
bare numeric/Roman suffixes do not establish edition claims. Claim origin and
negation are retained; conflicting claims remain review. Unknown wording can be
inconclusive rather than guessed. No model/service or credential was added.

Research requires an exact single bound NFO, checked unique IMDb/TMDb mapping,
agreeing year, supported film audio and a matching whole movie title. It searches
the existing public Blu-ray.com catalog by movie title and inspects one exact
movie/year product. Canonical URL, product title, year and IMDb must agree. Only
the structured product-header edition label and runtime qualify; reviews,
recommendations, unrelated links, multi-movie packs, ambiguous edition headers
and wrong IDs cannot establish the fact. The first product is deliberately a
bounded lead, not exhaustive edition discovery; other products remain counted.

At most two extra public GETs share the existing10/run and40/day ceiling and
provider holds. Existing four movie-detail/rival handling is unchanged. No room
for both GETs produces a deferral, not an increased allowance. Known packaging
membership without a runtime discrepancy avoids redundant cut research.

Private cut-cache.json is keyed by movie title/year/IMDb, stores sourced facts
rather than approvals, retains source URL/hash/time, and expires positive evidence
after seven days or inconclusive/error results after one day. At most100 entries
and a2MiB read bound; writes are atomic. Every occurrence compares its own claims
and runtime with cached facts. No raw public HTML or torrent capabilities are
stored there. Cache hits add zero edition requests.

`refresh.py` adds edition_investigation to the normal shadow report. It shows the
claims, source evidence, gaps and original-versus-edition runtime contributions.
The existing score, candidate set, margin and identity decision remain visible
and unchanged. would_explain_runtime is an edition-evidence proposal, not an
identity approval. Actual ID conflicts and existing review gates remain blocked;
no Radarr, download, notification or action code is imported by the new module.

## Wolverine and unfamiliar names

The generic public title search returned16 exact movie/year product links. Its
first result was independently inspected:
[The Wolverine — Unleashed Extended Edition](https://www.blu-ray.com/movies/The-Wolverine-3D-Blu-ray/91011/).
The structured header supplies2013, IMDbtt1430132 and138minutes. The parser
recognized the release/NFO's Extended Cut as a compatible claim. There is no
Wolverine or edition-name branch in runtime code.

Offline replay used the actual retained release/NFO/description and the existing
verified movie identity/catalog runtime126, with captured public search/product
responses. It reports138minutes, would_explain_runtime, and an edition-aware
comparison100 versus the original85.714286. This is a development replay of
retained evidence plus captured public evidence, not a fresh scheduled shadow
result, not a new provider mapping lookup and not production approval.

Unknown labels such as Reborn Cut, Phoenix Edition and Stardust Version pass
syntactic extraction tests without registration. A synthetic Reborn fixture
requires matching sourced edition/runtime; it is not a live Frankenstein match.
The parser does not promise to interpret every language, colloquial label or
arbitrary prose construction. Unexplained leftovers and runtime mismatch still
create leads when explicit edition syntax is absent.

## Verification

- Eleven new tests cover extraction from each source, unknown labels/negation,
  provenance and unique-ID exclusions, product-header binding, conflicting claims,
  wrong movie/year/runtime, cache expiry/budget deferral and full refresh caching.
- End-to-end mocked refresh uses six GET reservations initially and four on repeat
  with two edition GETs eliminated by cache; original review/score are preserved.
- Exact final local suite:776 tests,153.684s, two Linux-only skips. Seedbox isolated
  suite:776 tests,46.746s, all passed. Initial local775-test run passed before the
  final additional integration test. Early focused invocation used two nonexistent
  test module names; corrected focused suite and final full runs passed.
- GitHub CI Python3.12/3.13 passed on exact8fd8283:
  [run40346073334](https://github.com/kolorifer/radarr-festival-list/actions/runs/40346073334).
- Dependency check,1909-row catalog and private configuration preflight passed.
  Installed archive's eleven focused tests also passed.

## Deployment and remaining limits

Only the idle shadow service's working directory changed fromd04608b to8fd8283.
Every archived source matched the isolated tested checkout. Private backup
cut-shadow-backup-7yvfs_mx retains the prior unit and shadow state. Its existing
fixed-date timer resumed; no manual service refresh was started. The actor stayed
on d598296, health200; collector PID and research timer remained unchanged.
Actor configuration/actions, shadow pilot, report/cache/request ledgers and timer
hashes were unchanged. No downloads, notifications, replay or queue mutation.

The new report field will populate through normal budget/freshness admission.
No past live score has been relabeled as fresh. The pilot still ends on
2026-10-27 at19:12 Europe/Warsaw; no extension, new schedule or budget increase.
Production Wolverine remains review-required until a separately approved change
allows corroborated edition evidence to affect identity decisions. Download
confirmation remains separate in all cases.

Source coverage is deliberately one public catalog and one product per lookup.
A different product, missing IMDb link, unrecognized page layout or ambiguous
header may leave valid editions unresolved. A multi-cut product's main header is
supporting edition evidence, not disc-content inspection. Named editions not
covered by this source may require another adapter later; no manual registry is
introduced as a workaround. Scores remain evidence points, not probabilities.
Rollback switches only the shadow working directory tod04608b, preserves current
private ledgers/caches and resumes the unchanged timer.
