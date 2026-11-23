# Movie evaluation for actionable Telegram cards

When a new or corrected Unknown Movie card offers Add & Grab and the watched
action, the actor sends the card normally and then evaluates its exact full
release name. The request uses the seedbox's `movie-triage-api.service` on
`127.0.0.1:40716`, with a single `raw_text` property. The card and webhook
response do not wait for that API. An in-process queue limits concurrent work
and shows an unavailable message on the card if it cannot admit the release.
Admitted work waits for a slot and each started evaluation has an 80-second
limit. Slow evaluations can delay the replies behind them.

The result is a reply to the actual card. It uses the topic acknowledged by
Telegram. A legacy edit that does not confirm its reply target and topic is
left without an evaluation reply, with a fixed journal marker. The current
topic setting is not substituted. The reply leaves newer edits and both buttons intact. It
presents all parsed fields or the complete received error
within the 128 KiB response budget, with private values redacted. Redaction
covers known secrets, URLs and recognizable credential labels. Unlabelled
secret strings cannot be reliably identified. Short results
are HTML-escaped text. Long results are a text file sent to the same configured
Telegram destination through
Telegram's [document upload](https://core.telegram.org/bots/api#senddocument).
Transport errors, timeouts and rejected or oversized responses are visible as
errors. A Telegram delivery failure emits a fixed diagnostic. There is no
automatic resend. Work still in memory at an actor restart may be lost.
An initial acknowledgement without a verifiable message ID cannot receive a
safe reply. The actor preserves the original notification outcome.

The evaluator's identity is advisory. Following a confirmed Add & Grab,
Radarr's accepted push is followed by one best-effort feedback call using the
approved movie's IMDb and TMDb IDs and title, decision `watch`, and note
`Grabbed via Telegram`. Feedback gets four seconds and never retries an
uncertain response. The existing approval's durable executing marker prevents
another submission from the same approval if a process stops before cleanup.
Watched actions, failed grabs, link opens and alternative grabs send no feedback.

## Verification and actor release

The offline suite exercises the raw request shape, successful and failed
evaluations, full error details, credential redaction, exact reply binding,
photo fallback, attachment bytes, saturation, retry edits and the Radarr
approved feedback boundary. No real evaluation, feedback, download or
Telegram send is needed to verify the release.

Prepare an isolated actor release directly from
`6dc6ee7c4216fa69d2a31035657b3c7de98690f1`. The runtime delta contains
`movie_intel_service.py` and `telegram_evaluator.py`. Verify against the existing
actor runbook and the independently checked live OpenAPI contract. In deployment
validation, use read-only actor health and evaluator service or schema checks.
Run invented HTTP/Telegram tests in the isolated off-host checkout, away from the
live loopback evaluator. Keep Radarr, the collector, the archive, the reporting
worker and their settings intact. Roll back only the actor code to the pinned
parent while preserving private state and the runbook's acquisition safeguards.
