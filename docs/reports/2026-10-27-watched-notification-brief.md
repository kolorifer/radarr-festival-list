# Watched notification presentation

Source: the owner's 2026-10-27 request and screenshot of an unmonitored movie
rejection. Remove the unclear “POTENTIAL FALSE NEGATIVE” warning and show
“Watched” when that movie has the watched tag in Radarr.

## Agreed scope and implementation interpretation

- Remove the warning from enriched movie cards. For watched movies, replace the
  model assessment with a simple Watched label. For other movies, retain the
  existing qualification information without the warning.
- Resolve the actual movie's Radarr tag IDs to the current watched label. Do not
  infer watch state from unmonitored status, qualification, title or a fixed ID.
- Retain posters, ratings, recognition, identity safeguards and rejection details.
  Leave routine notifications that skip identity enrichment on their existing path.
- Failed optional Radarr reads must not prevent sending the normal card or claim
  that a movie is watched. No changes to tags, monitoring, scoring or acquisition.
- Validate synthetic tagged/untagged, failed lookup and identity mismatch cases,
  then run the complete suite and production catalog check.

Use an isolated change on the last reported actor runtime d598296, preserving
the deployed retry, routing and identity work. Production access must be restored
and the actual current checkout inspected before activation. No historical card
edit, notification replay, live test message or acquisition is part of validation.
The unrelated active cleanup assignment remains unchanged.
