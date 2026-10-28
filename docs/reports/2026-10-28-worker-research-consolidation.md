# Worker research consolidation — 2026-10-28

## Scope and provenance

The offline Live Movie Score research from PR #88 at
`824ed090e93c69e7ee5af6fe7df398725d8a6056` is preserved in
`simulations/live-score-v1/`, together with its three briefs and reports. It is
not an adopted score or an operational collector. Its source-validation packet
runs offline by default; provider access and rights remain unresolved as stated
in the packet. The public Task 6 legacy audit from PR #16 at
`bf130e26e60cb253da4db921713ae04478c6d3e4` is saved separately as
`2026-10-16-legacy-library-audit-task6.md`; the later second-pass report keeps
its existing path and findings. Detailed private evidence was not accessed.

## Verification and disposition

The 20 Task 1, 14 Task 2 and 18 source-validation offline tests passed, as did
both artifact byte checks. Full-suite and CI results are recorded in the PR.
No deployment, live provider request, production data change, or activation was
performed. This integration is one part of the wider repository consolidation;
other research and remote branches remain to be reviewed.
