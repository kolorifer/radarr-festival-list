# Tracker metadata implementation brief

**Authorization:** The user's current instruction, “update implementation
according to new findings,” follows review of the
[tracker metadata investigation](2026-10-18-tracker-metadata-investigation.md).
This implements its supported ID-first resolution and exact-listing fallback
within D005/D008/D009/D010. It does not assign the unrelated cleanup task.

## Scope and acceptance

- Consume autobrr movie `meta_imdb` and `meta_tmdb`; never interpret torrent
  `external_id` as a movie ID. Validate format, movie endpoint, mapping cardinality,
  round trip, local identity and title/year context. Conflicts do not use search.
- Accept authoritative TMDb alternative/translated titles and actual release-date
  years. Preserve existing no-ID exact-title/year and duplicate popularity rules.
- Implement optional TorrentLeech exact-listing metadata, disabled by default,
  with dedicated private authentication, strict URL/redirect/content boundaries,
  bounded requests and caches, release-heading validation and safe failure.
- Distinguish verified TMDb identity, unverified source IMDb association without
  a mapping, review-required conflicts and unresolved metadata. Only verified
  TMDb results from the new path can enable the existing explicit approval flow.
- Preserve exact original download references, search-disabled adds, durable
  attempt/replay safeguards and routine-rejection bypass. No scoring changes.
- Test provider errors, malformed/conflicting IDs, wrong assignments, translation
  and release-year evidence, cache isolation, hostile URLs, login/markup failures,
  response limits/rate controls and the complete HTTP approval workflow.
- Run focused/full local tests and read-only checks of supported investigation
  cases. Record actual results separately from synthetic or earlier live evidence.

## Conservative assumptions and exclusions

No manually inferred Fragmentos crosswalk, synopsis/title-prefix heuristics,
independent IMDb metadata provider or new ratings coverage. Session provisioning,
adapter activation, merge and deployment are outside this implementation turn.
Production stays at its verified revision. New live notification/download tests
would require approval for that specific release. Research-only observations do
not silently become acquisition permissions.
