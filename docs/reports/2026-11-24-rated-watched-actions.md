# Good and Bad watched confirmations

New or updated Telegram release cards with Add & Grab offer **Add as watched -
Good** and **Add as watched - Bad**. The actor's common keyboard builder covers
text cards, photo cards and ordinary retry edits. The links share the existing
private capability and live identity checks. Opening the page only shows a
confirmation. The chosen rating appears in the form and the submission must
match the private link.

Both confirmations mark the approved movie watched and unmonitored. Existing
tags and files are preserved and no search or download is started. After Radarr
verifies the result, the actor durably completes the watched action before
attempting local evaluator feedback. Good uses `watch`, Bad uses `skip`, and both
send the selected movie's IDs and title with note `watched`. The unexpired old
unrated route remains available and sends no rating. All three routes share the
same completion on a release approval, even when the same approval appears
on multiple cards. No fallback guesses a missing ID.

The feedback endpoint may accept a request even if the response is lost. A
completed action never retries feedback or gives the alternative rating another
attempt. If the actor stops after persisting completion but before submitting
feedback, the rating may be missing. Grab has its own existing outcome and
feedback. Failed or unconfirmed watched updates send no feedback.
The page reports a saved rating only after the installed evaluator acknowledges
the same decision with HTTP 200, status `saved` and a positive feedback count.
An uncertain response leaves the confirmed Radarr result visible.

## Actor release

The actor-only release applies the three runtime files directly to live actor
`710634224edd60d6fff4318736a93624419a4736`. Test invented request and evaluator
fixtures off-host. Use the existing actor restart and health checks for rollout
and preserve the latest private action store on rollback. New rated links
require the new actor route. Rollback preserves already-confirmed Radarr and
feedback state. No live confirmation, feedback request or Telegram send is
required to validate the deployment.
