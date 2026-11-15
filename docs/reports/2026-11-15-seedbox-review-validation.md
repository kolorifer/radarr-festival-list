# Seedbox separate-review validation and explicit review-only correction

Specification: main's bounded post-PR208 fix; preserve completed assessments,
all consumed attempts, source/target protections and the existing sole worker.
Main reports three corrected assessments completed, three review responses reached
historical-result validation then unclassified refusal, no sends, 170 queue events
and twelve retained 15-cent reservations. The old review bodies were discarded;
their actual verdicts and historical failure causes remain unknown.

## Concrete defect and correction

An invented schema-valid approve response with material problems reproduces the
unclassified diagnostic. This is evidence of a code defect, not proof of the old
responses. The existing approval-conflict guard remains. Review predicates now
have static diagnostic codes; no exception text is echoed. Empty findings and
bare verdict labels cannot count as a review explanation. Semantic quality still
requires model review/main audit; a deterministic text filter cannot establish it.

Existing disclosure rules are unchanged. A refused semantic/text result retains
only validated safe fields, explicit nulls for withheld fields, original/retained
answer hashes, exact request/accounting receipt and finite failed predicates.
There is no raw answer retention, fabricated explanation or approval by fallback.
Normal rejection is a per-case completed result. An unclassified review exception
opens the existing provider circuit and stops backlog spending. Its existing
explicit recovery artifact requires material_change=review_validation_fixed;
access_restored continues to apply to access failures.

New review request revision2 explicitly requires zero material problems and
substantive findings for approval; otherwise rejection is valid. Default revision1
builder and all old assessment/card/HTML/receipt bindings remain unchanged. Records
pin the new request revision; reconstruction selects the stored revision.

## Executable review-only successor

With the worker stopped, main computes
`automation.seedbox_automated_review.correction_proposal(queue, preparation)`.
This verifies the exact old completed assessment, card, evidence, review attempt
and historical-validation failure. The proof distinguishes old discarded outcomes
from new safely retained validation refusals, and binds the latter record when
present. It claims no unknown original answer or verdict. No source refresh,
reassessment, credential read or provider request occurs in this preparation.

After inspecting that exact private proof, main may invoke the installed entry:

```
python -I -B BOOTSTRAP MANIFEST MANIFEST_SHA review-correct CONFIG CONFIG_SHA PREPARATION PROPOSAL_SHA
```

Under existing confinement and singleton, configuration/circuit/credit/credential
checks precede one-use authorization. One distinct purpose-bound review request
reserves the same ledger at stage review_correction; old attempts/debits remain.
Repeated authorization, repeated request, another successor, changed proof or
prior send refuses. Interruption after authorization is not automatically replayed.
No ordinary worker path creates this additional request.

The completed successor permits only the next existing delivery stage. It does
not grant new identity/download rights. approved_plan reconstructs its exact
assessment/card/request/receipt chain; ordinary retained-evidence freshness,
current collector occurrence, original target, topology, sender locks and duplicate
checks still apply. Stale historical review remains inspectable but cannot send.
The completed successor itself resolves the earlier review operation block, so a
crash cannot require another provider request to reconcile local delivery.

## Verification and limitations

Invented connected tests exercise the real framing/parser, realistic findings,
contradictory approvals, withheld prose, empty/trivial findings, rejection,
unclassified circuit, old discarded-response correction, old prefix/debit
preservation, stale delivery refusal and existing original-card sender/no-replay.
The initial 7-test run retained one existing packet_changed metadata guard refusal;
no guard was weakened. A later intermediate 7-test run exposed a test clock rollback
and was corrected. A subsequent 34-test connected/legacy/reporting run passed in
43.345s. Final exact-head independent review and supported CI are merge gates;
final results are recorded in the PR and private work checkpoint.

Repository work uses invented fixtures only. Main owns final private proof,
deployment, explicit correction invocations and live review. No old assessment
is rerun and no live provider/host operation is performed here. Unrelated active
CODEX_TASK instructions remain unchanged.
