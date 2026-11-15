# Complete retained explanations and explicit same-facts delivery revalidation

Specification: main's bounded follow-on to accepted PR209, preserving all old
assessments, review requests/cards/receipts and charges. Main holds live calls.
The three selected original messages are text and their complete retained
explanations fit in 1121–1609 UTF-16 units before added dated-provenance labeling.
Their original source evidence expired; the original clocks must not be renewed.

## Complete, versioned cards

The old sentence clipping could replace a long material year/runtime uncertainty
with an unrelated physical-edition fallback. New card revision2 preserves the
entire retained rationale, uncertainty and every blocker support/conflict field,
including existing explicit withheld labels. Collector claims, listing context,
IDs, source link and original dated listing/catalogue observations remain visible.
No invented explanation, truncation, replacement message or caption conversion.

Primary bound verification: Telegram's official Bot API documents 4096 characters
for editMessageText and1024 for editMessageCaption, after entity parsing:
https://core.telegram.org/bots/api#editmessagetext
https://core.telegram.org/bots/api#editmessagecaption
The implementation conservatively counts UTF-16 units, uses the selected exact
original ref kind, and checks that bound both at proposal and the real sender.
Old plan revision1 retains900 units. New plan revision2 is separately named.
Oversize refuses before review; complete text is never silently shortened.

Default old card/request reconstruction remains byte-compatible. New records pin
card revision2; the explicit review-only successor verifies the old failed request
against its old card, then binds the new complete card to the same old assessment,
receipt, source URL and exact target hash. No reassessment or old review replay.

## Explicit fresh-source proof, not a renewed old assessment

After a genuinely approved separate review, main computes the offline exact proof:
`automation.seedbox_delivery_evidence.proposal(queue, preparation)`.
Main verifies that private proof and invokes:

```
python -I -B BOOTSTRAP MANIFEST MANIFEST_SHA delivery-revalidate CONFIG CONFIG_SHA PREPARATION PROPOSAL_SHA
```

Existing actor/collector lifetimes, confinement, singleton and config pins apply.
One durable reservation precedes the selected current snapshot and one bounded
listing/crosswalk/catalogue acquisition. There is no model credential or request.
The source URL and original target are checked before reading source credentials.
All material typed listing/catalogue/collector fields, exact local release/NFO
context and target must match. Source/catalogue clocks must advance; the current
occurrence/version must remain selected. Changed facts refuse without automatic
reassessment. An interrupted or failed acquisition is consumed and never retried.

Fresh raw originals, normalized facts, clocks, crosswalk, manifest and binding
are retained separately under delivery-evidence-PREPARATION. All original bytes,
assessment clocks, report HTML, reviews and prior ledger prefix remain unchanged.
The retained proof is independently rederived and checked before use. Missing,
failed, interrupted, altered or expired revalidation cannot fall back to old data.
Historical full-card correction requires this proof even if the original source
happens still to be fresh. Ordinary newly captured cases retain their normal path.

The existing source pause applies atomically: auth/config failure itself becomes
a recoverable shared circuit;429 keeps the full server-directed delay, including
more than one day. Successful proof resolves only the blocked unsent local stage.
No eighth slot, new worker, scheduler or generalized retry framework is added.

At delivery, existing original-row/spool locking, actor lifetime/topology, current
collector occurrence and no-resend guards remain. The locked callback also checks
source/snapshot expiry with the existing15-second send budget immediately before
edit. Observations cannot freeze later remote changes; freshness is a dated bounded
check, not a claim that sources can never change.

## Verification and operational limits

Invented connected tests cover long material uncertainty, every blocker field,
text/caption limits, explicit source-only comparison, old-prefix/HTML preservation,
unchanged-source original edit/no replay, changed target before credential access,
changed facts, interrupted reads, altered/expired proof, callback expiry and shared
auth/rate-limit behavior. An intermediate38-test run found one obsolete old-card
wording assertion; an intermediate23-test run retained one explicit packet_changed
guard refusal and one sanitized revalidation refusal (cause not established).
A separately instrumented isolated successful path passed7.491s with no guard
changes. The later54-test combined run retained two packet_changed refusals in
fixture setup (109.320s); no assertion failure or guard weakening is hidden. Final exact tests/review/CI/package results belong to the PR/checkpoint.

Main owns private proof, deployment and any source/review/delivery invocation.
This repository task has made no live provider, source, host or Telegram calls.
Unrelated CODEX_TASK instructions remain unchanged.
