# Shadow evidence extraction and budget recovery

**Specification:** [approved brief](2026-10-27-shadow-recovery-brief.md).
**Result:** implementation complete; validation and shadow deployment in progress.

## Changes

- Decorated MediaInfo sections now expose separate audio tracks, including commentary,
  and File Name bindings. Compact General/Length/Audio layouts expose runtime,
  filename and ISO language codes. Subtitle/video tracks cannot supply audio evidence.
- Exact tracker-reference recovery tolerates whitespace only. Source-ID digest,
  year, current occurrence provenance and fresh tracker heading remain mandatory.
- AKA alias remainders, 4K/remaster/restoration format markers and Format version
  fields do not trigger cut research. Genuine unfamiliar named cuts remain leads.
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

Pending full suite, exact-runtime seedbox/CI checks and shadow-only rollout.
No downloads or notifications authorized or performed by this implementation.
