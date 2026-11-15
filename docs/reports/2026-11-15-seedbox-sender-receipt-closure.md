# Frozen sender receipt closure and finite diagnostics

Main delegated a bounded installed-package correction after one original-card
edit became uncertain. The original attempt and reservation stay consumed; no
resend, reconstructed acknowledgement, paid review or reassessment is permitted.

The frozen actor's Telegram function imports retry_telegram only after validating
an HTTP JSON success. Because this function is extracted dynamically, static
package closure omitted that module. Main independently reproduced the missing
import with an invented HTTP success and verified that the installed module is
absent. This demonstrates a defect, not the historical send outcome or cause.

The wrapper now extracts the exact receipt function from the already hash-verified
actor file into a private namespace with its own thread-local state. Only the
exact receipt import is intercepted; other imports retain normal behavior and
process-wide modules remain untouched. The exact hook runs for edit methods,
where its existing behavior is a no-op. It does not manufacture an acknowledgement.
No actor startup, whole-module execution or broader runtime dependency is added.

A new append-only diagnostic binds the sender start and records finite callback,
transport, response and receipt phases plus a finite failure category. It contains
no exception text, token, URL, response body or message. These observations cannot
prove human ingestion or repair an uncertain attempt. Existing DB reservation,
acknowledgement transaction and no-resend behavior remain unchanged.

## Validation and deployment boundary

An isolated Python -I -S installed-only test exercises the real frozen edit and
HTTP callback with invented credentials/response, verifies missing ambient module,
receipt success, rejected response, missing frozen function and post-response
receipt failure. Connected queue/actor tests verify uncertain/null receipt,
reserved original, sanitized diagnostic and no replay after injected failure.
Exact-head independent review and full supported CI remain merge gates; final
results are retained in the PR and work checkpoint. No live operation, credential,
source read, provider request or deployment is part of this writer task.
