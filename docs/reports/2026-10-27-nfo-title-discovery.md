# NFO-title discovery and unresolved-case review

**Specification:** [approved brief](2026-10-27-nfo-title-discovery-brief.md).
**Result:** implementation complete; verification/deployment in progress.

## Findings from the complete four-case review

| Case | Retained evidence | Remaining limitation |
| --- | --- | --- |
| Dead Mountainers Hotel | NFO original title HUKKUNUD ALPINISTI HOTELL,1979,83min,German and Estonian audio. Estonian Film Institute catalog supports Dead Mountaineer’s Hotel(1979). | Empty misspelled-English searches; fresh tracker heading mismatch; final Estonian track previously absorbed subtitle field. No automatic match yet. |
| Carrue | Tracker description Carrie,1976,98min,Sissy Spacek/Piper Laurie; asserted IMDbtt0074285. NFO98min9sec,three English tracks. | Exact whitespace reference fix verified offline; fresh candidate comparison pending. Retained incomplete65 is not a new score. |
| Le Syndrome du Titanic | Same title/year2009,IMDbtt1503718,TMDb52374; NFO97min/six French tracks versus catalog93min. | Historical identity conflict remains review; no sourced runtime explanation. Retained83.55 lacks corrected audio points; not a fresh rescored result. |
| The Wolverine | IMDbtt1430132,TMDb76170; explicit Extended Cut,138min,English film audio and separate commentary versus126min catalog. |85.71review; live public edition corroboration deferred. Earlier100edition comparison is offline only. |

Public corroboration for the first candidate:
[Estonian Film Institute](https://classics.filmi.ee/movie/dead-mountaineers-hotel/).
Public identifiers IMDbtt0204526/TMDb46908 remain proposed until checked through
the normal bounded provider flow. No hardcoded movie identity is introduced.

## Implementation

- Parse container Title/Movie name separately from track titles. Permit at most
  one original-title/year fallback after an empty ordinary query set, bound to a
  single exact NFO filename and a successfully checked tracker heading. Ambiguous,
  conflicting-year, oversized or unsafe hints are ignored. At most three search
  queries total; existing candidate/detail caps and shared request limits remain.
- Unnumbered Text Language/Format sections end audio tracks; subtitles cannot
  contaminate or manufacture an audio language. No language-scoring policy change.
- On heading mismatch, retain expected and up to four observed headings with
  bounded redacted text, timestamp and page digest. Diagnostics never accept a
  mismatching page or retain full HTML/private URLs. Expose them in shadow reports.
- Evidence revision3 re-assesses incomplete/review cases; checkpoint format2 is
  retained so compatible completed GETs are not discarded. Successful prior
  proposals remain dated evidence; no budget or pilot reset.
- AGENTS.md records the owner's full-set review preference. Identity review,
  source binding, approval and download safeguards are unchanged.

## Verification and deployment

Pending exact-runtime full suites, CI/preflight and shadow-only deployment.
Daily shadow budget was already40/40; no extra provider requests are authorized
by this rollout. Normal scheduling resumes under the existing ledger/deadline.

## Limitations

A tracker heading mismatch still blocks all fresh NFO acceptance and discovery.
The new diagnostic will be collected on the next permitted listing fetch; the
old failed response was not retained and cannot be reconstructed. A fallback
search is discovery evidence, not an override or identity approval. No actor or
recurring research worker changes are included. The unrelated cleanup task in
CODEX_TASK.md remains assigned and unchanged.
