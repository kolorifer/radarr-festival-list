# Astra Investigation Task: Use Tracker Metadata to Improve Movie Identification

**Project:** `kolorifer/radarr-festival-list`
**Subsystem:** autobrr → movie-intel → Telegram → Radarr
**Priority:** High
**Scope:** Read-only investigation and implementation proposal. No production changes yet.

## 1. Objective

Our long-term goal is to **identify virtually every movie announced through autobrr**, with rare, explicitly justified exceptions.

Currently, movie-intel occasionally cannot resolve a film from its title and year. This prevents enriched Telegram notifications and the **Add to Radarr & grab this release** action.

We suspect torrent-indexing websites may already provide reliable IMDb or TMDb identifiers that our pipeline is not using.

**Investigate whether these identifiers can substantially improve resolution without compromising identity accuracy.**

The aim is not to hide unidentified notifications. Every unresolved case should ultimately be investigated and lead to a proposed solution or an explicit explanation of the remaining ambiguity.

## 2. First investigation: Fragmentos (2025)

A real Telegram notification was received:

- **Movie:** Fragmentos (2025)
- **Release:** `Fragmentos 2025 BluRay 1080p x264 DTS-HD MA 5 1-MTeam`
- **Radarr rejection:** Unknown Movie
- **Movie-intel result:** Unresolved; no enrichment or Grab button.

Astra's previous engineering report identified this movie as having ambiguous exact TMDb matches.

Investigate the original release through our actual production pipeline.

Establish:

1. Which indexer/tracker supplied the announcement?
2. Does its movie listing contain an IMDb ID, TMDb ID, or other reliable film identifier?
3. What movie identity does the tracker associate with the release?
4. Does autobrr extract the identifier?
5. Does autobrr include it in the webhook payload?
6. Does movie-intel receive it?
7. If received, why isn't it used?
8. Would this information safely distinguish the competing *Fragmentos (2025)* identities?

Do not choose a film merely from filename similarity or popularity.

Distinguish the torrent-indexing website's movie metadata from the BitTorrent tracker's peer-management functionality.

## 3. Current implementation

Inspect the deployed revision and current repository before drawing conclusions.

Relevant code:

- `movie_intel_service.py`
- `tmdb_resolver.py`
- autobrr webhook configuration and actual payload schema
- existing movie-intel tests

Our previous code inspection found that `build_movie_context()` resolves using title/year and an optional IMDb ID derived from our local Movie List catalog.

It does not explicitly extract tracker-provided IMDb/TMDb identifiers.

The existing resolver already supports IMDb-based TMDb lookup, making it a potentially useful integration point.

Check whether the installed autobrr version provides fields such as:

- `meta_imdb`
- `meta_tmdb`
- `info_url` / `infoUrl`
- `indexer`
- release-specific metadata and external IDs

**Do not assume these fields exist in our actual webhook payload just because autobrr supports them elsewhere. Verify the installed version and real production events.**

## 4. Generalize the investigation

Do not stop at Fragmentos.

Analyze a representative sample of recent unresolved events, including:

- ambiguous exact title/year matches
- localized titles
- alternative/original titles
- incorrect or inconsistent release years
- films missing from our local Movie List catalog
- events where TMDb returns no exact match

For each case, determine whether reliable identifying evidence was available upstream but lost or ignored downstream.

Classify failures into:

**A.** Tracker supplies an identifier; autobrr receives and forwards it; movie-intel ignores it.

**B.** Tracker supplies an identifier; autobrr does not expose or forward it.

**C.** Tracker listing has an identifier, but the current notification/payload lacks it.

**D.** Tracker supplies no reliable identifier; external metadata research is required.

**E.** Conflicting or incorrect external identifiers make automatic resolution unsafe.

Report how many sampled failures belong to each category.

## 5. Evaluate possible solutions

Compare the following approaches:

### Option A — Direct external-ID resolution

Extract trustworthy IMDb/TMDb identifiers from autobrr events and use them before title/year search.

Verify against authoritative metadata and detect conflicting identifiers.

### Option B — Improve autobrr metadata propagation

If the tracker has an external ID but the webhook omits it, determine whether supported autobrr settings, templates, filters or API capabilities can preserve it.

### Option C — Read-only tracker metadata lookup

Where the listing has an external ID but the webhook doesn't, investigate whether its supported API or authenticated listing can provide that ID using an already-known release reference.

Avoid unnecessary tracker requests and never bypass access controls.

### Option D — Carefully bounded fallback research

Where no authoritative ID exists, investigate alternative-title, localization, director, country and release-year evidence.

Keep these signals distinct from verified external identifiers. Do not silently turn a plausible match into an automatic Grab action.

For every option, assess reliability, coverage, maintenance cost, privacy, API limits and false-positive risk.

## 6. Preserve existing product decisions

- Conservative identity matching remains mandatory.
- Never choose an arbitrary candidate just to achieve higher identification coverage.
- An authoritative external ID may improve confidence, but conflicting metadata must be investigated.
- Movie identification does not authorize acquisition.
- The Grab action must still require user approval and target the **exact original release**, with Radarr search disabled.
- Do not expose private tracker URLs, passkeys, API credentials, torrent download references or action tokens in GitHub, chat or logs.
- Preserve the successful PR #41 notification/reliability fixes.
- Distinguish repository main from the actually deployed production revision.
- Do not modify production services, settings, releases, Radarr records or acquisition state during this investigation.

Use `REASONING: high` for any delegated Codex tasks.

## 7. Required deliverable

Return an evidence-based engineering report containing:

1. **Fragmentos root-cause analysis:** Exact source of the ambiguity and whether the tracker had sufficient identifying information.
2. **Actual payload analysis:** What identifier fields are available at each stage, with sanitized supporting evidence.
3. **Failure classification:** Results for representative unresolved notifications.
4. **Recommended solution:** Preferred architecture, identity precedence rules, consistency checks and safe fallback behavior.
5. **Expected improvement:** Which historical failures the proposed solution would resolve, with measured sample counts rather than speculative percentages.
6. **Implementation plan:** Specific files/components, test cases, migration or deployment requirements and rollback strategy.
7. **Remaining ambiguities:** Cases requiring human identification and how they should be presented to the user.

Include regression tests in the proposed plan for conflicting IDs, incorrect tracker assignments, missing metadata, duplicate title/year matches and the existing successful exact-release Grab flow.

## 8. Completion criteria

This investigation is complete when we can answer:

**“Why could the upstream tracker/indexer identify this movie while our system could not, and how can we reliably preserve that identifying information for future releases?”**

If the tracker did not actually know the movie's identity, demonstrate that rather than assuming otherwise.

**Do not implement or deploy the proposed identity-resolution changes yet.** Present the findings and recommended solution for product review first.

Astra owns the technical investigation. The main ChatGPT conversation retains responsibility for selecting new product rules and approving changes to identity-matching behavior.
