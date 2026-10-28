# Shadow evidence extraction and budget recovery

**Specification:** [approved brief](2026-10-27-shadow-recovery-brief.md).
**Result:** tested and deployed in shadow mode; second bounded pilot running.
**Runtime:** `028867a6ef08f53804e19b1b84f6d3a2d01f73c7`.
**Review:** [PR92](https://github.com/kolorifer/radarr-festival-list/pull/92), draft,
based on the existing shadow research branch. No production matching activation.

## Changes

- Decorated MediaInfo sections now expose separate audio tracks, including commentary,
  and File Name bindings. Compact General/Length/Audio layouts expose runtime,
  filename and ISO language codes. Subtitle/video tracks cannot supply audio evidence.
- Exact tracker-reference recovery tolerates whitespace only. Source-ID digest,
  year, current occurrence provenance and fresh tracker heading remain mandatory.
- AKA alias remainders, 4K/remaster/restoration format markers and Format version
  fields do not trigger cut research. A complete known movie title also prevents
  shorter catalog aliases from inventing an edition (for example, the article
  “The”). Genuine unfamiliar named cuts remain leads.
- Completed GET responses are checkpointed privately for at most24h, bound to the
  same current occurrence. A run can use the remaining daily allowance and resume
  next time without repeating successful requests. Limits remain10/run40/day.
- New/unresolved versions precede repeat checks. Completed current-version results
  and previously supported shadow proposals are retained without daily requests.
  They keep original evidence times and are explicitly labelled stale after24h;
  stale evidence is never presented as a fresh matcher result or production approval.
- Failed refreshes preserve earlier good evidence. Stable failures wait24h;
  temporary failures back off to24h. Provider holds and cumulative ledgers survive.
  Fixed diagnostic codes now distinguish listing mismatch/invalid ID/network failures.
- New pilot separates carried-over snapshots from historical baseline and genuinely
  new results. No actor, research queue, approval or acquisition behavior changes.

## Scope and remaining limits

Scoring weights, thresholds, rival bounds and actual conflicting-ID review guards
are unchanged. Cut runtime comparisons remain annotations, not identity approval.
No fresh fetch is made for an unchanged completed research version during this
pilot; later tracker edits require a new evidence version or an explicitly scoped
recheck. Partial checkpoints expire after24h, so a longer interruption requires
fresh requests. Reference lookup fails closed above10000 retained releases for
one year. Existing daily research intake timing and source retention limits remain.

The first pilot ended October27 with18 snapshots (8historical/10new),6supported
shadow proposals,2review cases and2incomplete cases. This second pilot preserves
that evidence and all reservations; it does not reset budgets to recover capacity.

## Verification and deployment

- Final runtime: full local suite **787 tests passed**, 2 expected Linux-only skips,
  113.902s; exact seedbox suite **787 passed**, 47.041s. Focused final recovery/cut
  suite22 tests passed. Initial restricted local execution could not open mock
  HTTP servers; the permitted full rerun passed, followed by the final rerun.
- Both Python3.12/3.13 CI jobs passed on exact commit028867a:
  [run40577142617](https://github.com/kolorifer/radarr-festival-list/actions/runs/40577142617).
- Dependency check,1909-row catalog and private configuration preflight passed.
- Read-only retained evidence proof: Titanic97min, **six French audio tracks and
  one filename**; Carrue exact tracker reference recovered despite stored leading
  whitespace. These are retained-evidence proofs, not fresh provider matches.
- Integration test starts with38/40 used, persists two GETs, simulates restart,
  and finishes with four GETs next day without repeating the listing or IMDb
  mapping. Actual ID conflicts remain review-only. Tests cover checkpoint expiry,
  no I/O after pilot deadline, cohort separation and preservation of dated evidence.
- The first live pilot invocation used **five GETs**, advancing the shared
  October27 ledger34→39/40. Wolverine retained its85.714286 review result and
  saved its checked listing plus four completed metadata responses. Its two-GET
  edition discovery was deferred with one daily request remaining. No budget
  reset/increase; resumed evidence remains bounded to24h.
- That first invocation exposed an article-only alias remainder. Final028867a
  removes it. Zero-request replay of the same checkpoint now retains only the
  two sourced “Extended Cut” claims. The final public edition lookup has **not**
  run; this replay is not fresh edition corroboration or identity approval.

### Deployment and pilot

Initial pilot rollout34b2f9d and final refinement028867a each verified all254
archived files against the isolated tested checkout. Private backups precede
both unit changes; all actor configuration/action hashes, collector/actor PIDs,
research timer, shadow scores/caches and request ledger were preserved across
those rollouts. The only provider traffic was the explicitly initiated first
pilot invocation above. Final installation preserves that checkpoint and39/40
ledger. Local/public health200; actor/collector/research timer healthy.

Production actor is unchanged at **ae1e6be9f245fa4b04296ce881817ed2a4dc5fca**,
which includes separately authorized watched-tag presentation work. No actor
restart, queue update, identity correction, notification or download was triggered.
Existing unrelated production operations continue normally.

Pilot2 runs **October27 21:18:37–November3 21:18:37 Europe/Warsaw**
(20:18:37UTC), hourly at minute35UTC, with the existing10/run40/UTC-day caps.
The manifest enforces a seven-day maximum and keeps the previous pilot's report
and manifest in a private backup. Deadline guard prevents processing afterward.
This rollout adds no permanent research schedule or production identity correction.

Coverage at startup: **8 historical snapshots,10 carried-over snapshots,0 new**.
Six prior supported results are reused with explicit age; Wolverine, Titanic,
Carrue and Dead Mountainers Hotel remain the four carryovers requiring work.
New proposals arriving during this pilot are tracked separately. Ordinary daily
research intake remains unchanged, so arrivals not yet admitted have no score.

Rollback switches only the shadow service to its preceding tested directory,
retaining current ledgers/checkpoints and the new pilot's original deadline.
Never restore an old action store, request ledger or earlier pilot manifest over
current state. Stop the shadow timer if the new pilot must be ended early.

### Handoff

PROJECT_STATE and DECISIONS record this approved scope and verified deployment.
The unrelated cleanup assignment in CODEX_TASK is preserved. Review later pilot
results before changing production scoring; stale retained scores are historical
proposals and do not authorize a movie or download.
