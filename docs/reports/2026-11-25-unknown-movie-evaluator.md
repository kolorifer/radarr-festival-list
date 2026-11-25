# Evidence and proposed identities on Unknown Movie cards

**Specification**. Send the exact original release name and available torrent
evidence to the loopback evaluator. Evaluate unresolved releases and use the
result to propose an identity. Preserve explicit confirmation and the existing
acquisition and feedback behavior.

## Behavior

The actor projects the live /evaluate schema from the authenticated release
and its already checked listing. It omits absent fields and conflicting IMDb
hints. Sizes use decimal GB. Observed NFO audio takes precedence over concrete
announced language hints. Freeleech preserves an explicit false. Requests
carrying torrent information bypass cache keys that omit that evidence. The
evaluator receives no release capabilities, tracker links or credentials.

The evaluator replies to the acknowledged Telegram card and topic. It includes
the complete redacted result or error. An unidentified movie gets a distinct
proposal. High-confidence IDs may produce a corrected reply with the normal
action links after the existing title, year, crosswalk, source and local
catalogue checks and the original release reference check succeed. Existing
catalogue and source revalidation still applies at confirmation. A usable
proposal can also appear on an existing per-occurrence evidence-review page.
Remembered identities and conflicts keep their existing explicit review.
The evaluator never edits the original card. A newer correction supersedes
pending evaluation replies for the prior display.

The evaluator HTTP request has a separate 80-second deadline. Independent TMDb
checks use the actor's existing per-socket timeout. A slowly responding TMDb
request can extend the evaluation and confirmation paths.

## Verification and deployment

The evaluator client, Telegram presentation, retry transport, tracker metadata
and per-occurrence review tests use invented fixtures. They cover privacy, cache
selection, actionable and unresolved cards, proof of the proposed identity,
crosswalk or source conflicts, and prior Grab and watched behavior. The PR
records the supported Python checks and independent review. The actor package
is separate from repository integration. This engineering change does not
perform a production deployment or send live Telegram, feedback or Radarr
actions.
