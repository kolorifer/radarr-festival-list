# Historical research consolidation — 2026-10-28

## Scope

The historical handoff and qualification research in PRs #1–#5 are retained
as isolated snapshots indexed in `research/README.md`. The complete #5 tree
and the earlier changed-file snapshots are verified byte-for-byte against the
original Git blobs. This retains original generated outputs, inputs, research
code, tests and reports at their respective revisions without replacing current
production files. Old workflows are nested archival content, not active GitHub
Actions. No research qualification threshold is adopted.

The distinct read-only investigation branch `investigation/issues55-56-readonly`
(`6507ca6`) also supplied its brief, report and eight synthetic tests. One test
was adapted to the later conflict-investigation route: it verifies the identity
remains `needs_review` while the collector admits it for research, rather than
asserting the obsolete `review_only` projection. It does not authorize an
identity correction or download.

## Verification and limitations

All 120 tests in the preserved #5 tree passed with Python 3.12. The eight
adapted incident characterizations passed. Snapshot files matched their source
Git blobs before staging; historical statements, private-evidence references,
and deployment claims remain dated and were not rechecked. Full current-tree
suite and CI results are recorded in the integration PR. No deployment,
production data changes, live acquisition or provider request was performed.
