# Passive evidence-scoring shadow pilot — 2026-10-20

## Authorized scope

The owner approved running the proposed scorer in shadow mode on real examples
before deciding about production identification. Keep the existing weights,
threshold70 and margin15. No automatic identities, queue reconciliation,
notifications, download actions or extra provider requests are authorized here.

## Implementation

A separate `research.identity_scoring.shadow` process reads existing research
proposal databases using SQLite read-only/query-only connections. It never loads
actor/provider clients or configuration. A Python audit hook rejects socket use.
It writes only a private atomic comparison report. Hourly observations last seven
days; a fixed-date timer and an explicit processing deadline bound the pilot.
The actor, collector and research schedules and request budgets are unchanged.

Up to1000 retained proposal rows are inspected, newest first per database.
Duplicate source/version/result snapshots collapse into one row; the same case
with changed evidence remains a separate observation. Reports distinguish results
created before the pilot from new results during it. Repeated runs are idempotent
for unchanged inputs. Invalid/oversized records are reported as unscorable.

The adapter retains all retrieved movie rivals, including undetailed search
results, so missing rival fields cannot create a falsely large winning margin.
A crosswalk is verified only by a successful unique IMDb find response matching
the detail ID with no TV result. Research labels and human choices earn no points.

## Coverage and interpretation

This is a **passive research-evidence diagnostic**, not complete parallel matching
of every autobrr release. Successful actor identifications, failures never admitted
to research, and queued cases without a completed research result are not scored.
The existing daily research worker controls when new evidence becomes available.

Stored projections lack exact listing/NFO filename binding, original source audio
language, and complete candidate pagination. These missing integrity checks remain
blocked. `arithmetic_pass` means only that the available score and conservative
margin pass the numerical proposal; it is NOT a proposed authorized identity.
The guarded decision remains review when proof is absent. Source runtime retained
in original facts can contribute arithmetic, but is explicitly unbound.
A future complete shadow adapter will need retained provenance and candidate
coverage before this can support a decision to enable automatic scoring.

Reviewed fixture replay remains available separately; those nine development
examples must not be counted as newly observed traffic or production accuracy.
This pilot cannot establish a false-positive rate without human-reviewed labels.

## Verification and deployment

Deployed isolated shadow commit `f4e8409` after verification. Production actor
remains `658d8f838aed7a03db7d01244254362fba99369a`; no actor restart or code switch.
No change to production matching is part of this installation. Rollback is disabling/removing only the new shadow
timer; retained private reports can remain for review.


- Full local suite: **700 tests passed**, two Linux-only skips,159.126s.
  The first sandboxed run failed41 local socket-binding tests with EPERM;
  the authorized local-network rerun passed in full.
- Final isolated package: **21 tests passed on seedbox Python3.13**.
- GitHub CI Python3.12 and3.13 passed on `f4e8409` (run39472449037).
- Installed scorer/observer SHA256 hashes match the local tested files.
- Shadow service exited0/success; shadow timer, actor, collector and existing
  investigation timer all active. Local health200. Protected actor source,
  private environment, actions file and existing investigation timer hashes
  unchanged during installation. No provider request, notification or download.
- Existing research ledgers were opened read-only; no queue status was changed.
- Initial scan: **8 historical snapshots,7 distinct titles,0 new results**,
  no arithmetic passes and no guarded would-identify decisions. Two Madame Bovary
  snapshots represent different research evidence, not duplicate processing.
  Repeated identical input deduplication/read-only behavior is covered by tests.

The historical top scores are Madame Bovary35 (two snapshots), Nunakal−50,
Aberfan50, Steve Howe−8, Rainbow−35, Syd Barrett−20 and Fragmentos60.83.
These are scores of **old incomplete candidate snapshots**, not current matcher
results. In particular, Nunakal's old search lacks the later documented alias,
release date and crosswalk used in its successful reviewed identification. This
must not be presented as a regression or contradiction of its offline75 score.
No case was reopened; even the skipped Aberfan appears only as historical data.

The pilot processes new research results until **2026-10-27 19:12 Europe/Warsaw**
(the end crosses the daylight-saving change). The fixed-date timer has no dates
pastOctober27; after the exact deadline the program preserves its last report and
does no processing. Report: private
`~/.local/state/identity-scoring-shadow/report.json`. Disable early with
`systemctl --user disable --now identity-scoring-shadow.timer`.

## Recommendation

Review genuinely new snapshots separately from this baseline. This passive phase
can expose numerical behavior and missing evidence; it is **not sufficient for
approving production activation**. A complete comparison needs additional retained
actor provenance/candidate coverage and reviewed labels. No automatic promotion,
threshold adjustment or extra research request budget is enabled. Draft PR78
remains open for review. The unrelated current CODEX_TASK was preserved.
