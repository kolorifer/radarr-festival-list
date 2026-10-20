# Reviewed occurrence versus automatic identification

## Approved brief

Implement the owner's distinction between a completed human review of one
occurrence and an identity that can be resolved automatically in future. Mark the
current Madame Bovary case reviewed as the 1949 film, preserving the tracker's
conflicting evidence. Require fresh evidence and a choice next time, including
when the same torrent returns. Test and deploy without downloads or permanent
exceptions. Unrelated catalog/cleanup work is out of scope.

## Implementation

The collector has an append-only `selection_reviews` workflow receipt, bound to
an exact current case version, its latest outcome event and its accepted delivery
cursor. It stores the reviewed target IDs/year for audit only. No matcher, action
or acquisition module reads it. The operator-only `review-occurrence` admin
command requires an exact current version and explicit target IDs/year; it cannot
create an approval capability or change the source assertions.

The projection is `reviewed_occurrence`, distinct from `verified` and `routine`.
Reports exclude it from unresolved age/count interpretation and research export;
the digest recognizes it without sending a completion notification. The underlying
conflict and historical research remain. Display text says the review is for this
occurrence only and gives no download approval.

Any new accepted delivery for that source invalidates closure, including an
identical filename/outcome or a selected-filter event. Exact transport redelivery
is deduplicated and does not reopen. Subsequent case versions include the new
occurrence binding, preventing reuse of the prior research version. A delayed new
event or maintenance refresh may conservatively reopen the case; this favors
fresh review over accidentally persisting an exception. This is workflow state,
not a verified identity, a learned rule or an identity override.

## Verification and deployment

Pending final tests, deployment and the bounded live workflow update.

## Limits

Closure is an operator action after explicit owner review. This change does not
automatically close cases when a web choice is submitted. Existing web choices
remain expiring and require separate download confirmation. Source events without
stable transport identity may cause conservative extra review; genuinely lost
upstream events cannot be detected by the collector. No recurrence schedule,
research budget, tracker credential or network-isolation change is introduced.
