# Fresh evidence for shadow identity scoring — 2026-10-21

## Request and scope

The owner requested fresh tracker metadata and full NFO evidence for shadow
scoring, including multiple audio tracks in the same language. Deploy only the
shadow process; preserve actor matching, review requirements, download confirmation
and existing collector/research services. No notifications or downloads.

This supersedes the passive-only restriction for the shadow collector, not for
production identification. Scoring weights/thresholds and the October27 pilot
end remain unchanged. The unrelated CODEX_TASK is preserved.

## Implementation

`research/identity_scoring/fresh.py` extracts runtime from the container section
before video/audio/subtitles and collects every audio track's explicit language.
It supports multiple tracks with the same language; mixed/missing declarations
receive no language points. Catalog language names map source declarations to ISO
codes; candidate original language is never substituted for missing source data.
Subtitles do not contribute audio-language evidence or container runtime.

`refresh.py` is a separate shadow-only runner. It reads current collector and
research state plus autobrr references read-only. A refresh must bind the research
version to the current unresolved occurrence, the hashed torrent ID to autobrr's
exact torrent ID, and the canonical listing URL to that same ID. The existing
tracker parser then verifies the exact release heading before any NFO is used.
Closed/reviewed/skipped/changed occurrences must not be promoted by this runner.

The full NFO is extracted before the actor's3,000-character projection. A64KiB
hard cap rejects over-limit NFOs rather than parsing an incomplete prefix.
Private shadow state retains sanitized full text, source digest, description and
existing screenshot references. It never stores tracker capabilities or cookies.
No screenshots are fetched or analyzed automatically.

NFO provenance is recorded as **the NFO element of the exact checked listing**.
A missing embedded filename is explicitly recorded, rather than claiming it was
verified. A contradictory filename or readable movie-name/year blocks acceptance.
Damaged movie-name character encoding is marked as a gap, not repaired with a
film-specific exception. This shadow-only source-binding approach does not change
production's stricter filename requirement.

Candidate search, detail records and unique reverse IMDb mappings are refreshed.
All search results up to3 candidates, plus a tracker-linked rival if omitted by
search, are retained. More than3 candidates, incomplete pagination/details,
conflicting IDs and non-unique/TV mappings cannot pass the scoring guards. Existing
needs-review identity conflicts remain review-only. Arithmetic passes remain
separate from guarded decisions; neither authorizes acquisition.

## Bounds and state

Only cases first researched during this pilot are refreshed. At most one case is
processed per hourly run,10 requests per run and40 per UTC day, with reservations
persisted before I/O. Provider authentication failures suspend that provider;
rate limits persist cooldown. Requests are spaced at least1.05seconds. These are
shadow-specific limits; existing research/actor budgets and state are unchanged.
Successful evidence is reused for at most24hours; failures can retry next hour.
Network uses existing dedicated tracker/TMDb credentials, bounded responses,
fixed metadata routes, no redirects and no proxy inheritance. No Radarr,
qBittorrent or Telegram client is imported.

Private `refresh-state.json` stores refreshed evidence separately from the
original research snapshots. `report.json` shows fresh scores alongside the old
retained snapshot. A failed refresh is explicit and cannot silently reuse an old
successful fresh decision. The previous passive runner remains available for
rollback. Deployment backs up shadow configuration/state only, never restores
actor actions, and restarts only the shadow oneshot service.

## Verification and deployment

Deployed shadow implementation **cf70212**. Actor remains
**658d8f838aed7a03db7d01244254362fba99369a**, with no restart or code switch.

- Final local suite: **714 tests passed**, two Linux-only skips,148.528s.
- Final seedbox suite: **714 tests passed**,45.772s, including Linux isolation checks.
- GitHub CI Python3.12/3.13 passed on the implementation revision.
-14 new tests cover full NFO parsing, multi-audio, mixed/missing languages,
  subtitle isolation, conflicts, provenance versions, budgets and end-to-end
  mocked page capture. Existing shadow/offline tests also pass.
- Read-only preflight caught an initial research-envelope/collector-version
  comparison mistake. It was fixed by following the collector provenance digest,
  regression-tested, and rechecked against the live case before activation.
- Installed fresh.py/refresh.py hashes match the tested local sources. Existing
  tracker/parser/request-guard helpers also match production bytes.
- Shadow-only unit switched after backing up its previous unit and state under
  `~/.local/state/identity-scoring-shadow-backup-vdi8fkwj`. Rollback restores the
  previous shadow unit and reloads/restarts that timer; no actor state restore.
- Local production health200. Actor, collector, original investigation timer and
  shadow timer active. Actor source, private environment, action file, original
  investigation timer and pilot deadline hashes unchanged during deployment.
- No Radarr/download client/Telegram calls, queue updates or notification replays.

## Live result

**Genealogies of a Crime (1997): retained50 → fresh100 points.**
The shadow decision is `would_identify`, TMDb125039 / IMDbtt0119242.
Title30 + year20 + NFO runtime15 + audio language10 + tracker IMDb25.
Full sanitized NFO length8,024 characters;113min; two French audio tracks.
The original description's114min is retained for review; scoring uses the NFO's
container runtime113min, which matches TMDb. Movie-name encoding damage is
explicitly flagged; the NFO has no embedded filename. Binding is to its element
on the exactly checked torrent page, not a claimed file-content inspection.

A complete one-page title search returned one candidate; unique IMDb mapping
agreed. Reported margin100 compares with the zero baseline for a sole retrieved
candidate; it is not proof that no unseen catalog competitor exists.

The run used **4 metadata GETs**. A second invocation added **0 requests** and
preserved the original50-point snapshot beside the fresh100-point result. The
collector case remains `eligible`; no production identity or approval changed.
One fresh pilot case is available; eight historical snapshots remain unchanged.
Pilot deadline stays **2026-10-27 19:12 Europe/Warsaw**.

## Remaining limitations

This still covers completed research cases arriving during the pilot, not every
incoming release. Evidence is up to24h old between successful refreshes; request
caps can defer further cases. Unknown NFO layouts, over64KiB text and mixed/unknown
language declarations lose the corresponding evidence rather than being guessed.
Conflicts and incomplete candidate discovery remain guarded. Screenshot references
are collected for human review, without automatic visual interpretation.
Scoring remains experimental, not a probability and not enabled for live identity
decisions. PR78 remains draft; no merge or production scoring activation.
