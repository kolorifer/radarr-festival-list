# Engineering report: supervised historical manual completion

**Specification:** [completed brief](2026-11-04-supervised-manual-brief.md).
**Result:** Explicit prepare/complete operations connect an externally supplied
assessment to the existing expanded request and a durable private review result.

## Implementation

manual_offline exposes --prepare and --complete alongside its unchanged default
fixture rehearsal. manual_supervised uses the existing private-chain reader,
exclusive 0600 outputs and locked hash-linked History. Prepare retains exact
input, request, model-visible input and selection. Completion reconstructs and
verifies them, reserves its sole attempt, preserves exact reply/provenance bytes,
and validates before writing review-report.json. Interrupted or rejected attempts
remain consumed; subsequent completion or preparation cannot replace originals.

The narrow schema allows historical_candidate_proposal, unresolved or blocked,
never production supported_candidate. Candidate IDs, title and year must match
successful retained find/details, with explicit cited values. Every support value
must equal its referenced input value. Source contradictions and missing facts
must remain complete. Reasons are bounded text: their semantic truth still needs
independent human/model review, not merely syntax validation. Expired catalogue
evidence can support a historical proposal, not current physical-file identity.

The importer marks authorship, simulation and context status unknown. It records
only its own lack of generation and requires external chat-provenance verification.
Self-hashes and source hashes establish local correspondence, not authenticity.
Null provider receipts/bills mean not recorded. No receipt, bill or AI attestation
is fabricated. Real supervised reasoning is supplied by the existing coordinator
chat; the local operation is validation and storage, not an autonomous agent run.

## Validation and retained run

Focused tests cover preparation, complete historical result, exact original
retention, every selection hash, unsupported candidate, invented evidence, hidden
conflicts, malformed replies, current-status refusal, modified inputs/requests,
and changed-reply/replay rejection. Storage-sensitive tests use explicitly labeled
fixture path adapters; the actual retained-case run used the unchanged real private
path and ACL checks. Full Python 3.12/3.13 exact-head CI is required before merge.

One actual supervised coordinator assessment was supplied for the exact retained
case after inspecting its prepared full input. The result proposes a historical
catalogue candidate while preserving expired evidence, year conflict, unverified
physical identity and no approval. Exact request/answer/report/source hashes,
commands and separate independent review remain in private task evidence, not this
public report. Earlier simulated reports are preserved and never relabeled.

## Scope

Optional manual workflow only; no installed production closure, live transport,
PR135 admission guard, task claim, schedule or service changes. No source refresh,
API/client generation, credentials, spending or deployment. The containing PR and
commit supply exact code/CI references. Historical project state and unrelated
assigned task remain untouched; this report records the completed scoped brief.

Next operational gap: the human-review handoff still needs an explicit owner
identity disposition for this occurrence, with physical-source verification as
needed. A stored historical proposal is not permission to correct or acquire it.
