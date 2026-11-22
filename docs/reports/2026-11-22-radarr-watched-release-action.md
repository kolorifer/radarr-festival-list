# Release-card watched action

The companion button shares the normal release card's private token and movie
identity revalidation. Its separate confirmation route prevents a watched form
from reaching acquisition. Both the initial card and ordinary retry edits use
the same keyboard builder. An alternative grab or unconfirmed identity review
does not offer the watched action.

`movie_intel_service.py` handles the confirmation and records success on the
existing private action. `radarr_client.py` performs exact reads, optional watched
tag creation, a search-disabled unmonitored movie add or an additive editor
update. An existing record keeps its other tags, files, root and profile.
Readback after an ambiguous reply reconciles the exact movie and both desired
settings. A partial update remains visible and a person can recommit through
the unchanged link, with no background retry. The original Grab operation
continues to handle its own attempt state and release submission.

## Verification and deployment

The invented Radarr integration exercises a new movie, an existing movie with
a file and tags, retries after partial and uncertain writes, a concurrent exact
add, invalid input, identity refusal and the ordinary Grab approval. The
notification tests cover text, photo and original-message retry edits.

The production actor is pinned separately from the repository main branch.
Prepare the actor release from `06d17aafefb5a5161364e4bf6f63667a649e1aa3`
with only the reviewed changes to `movie_intel_service.py` and `radarr_client.py`.
Verify that exact parent and those two runtime blobs before activation. Follow
the [actor update and rollback runbook](../../deploy/README.md). Keep the current
environment, unit, private actions and other services. Run offline configuration
and regression checks against the isolated release, then restart only movie-intel.
Verify the running revision, local and public health, and safe Radarr read access
without submitting a real movie form or sending a live Telegram test.

On rollback, return the actor to the prior pinned release. Preserve current
action state and continue to honor the runbook's uncertain acquisition guard.
The extra watched completion field is compatible with the previous action store.
An already delivered watched link needs the newer actor route. Code validation
does not prove a live Radarr write or Telegram delivery. The reporting worker and
its pinned actor hashes are separate and require their own review before any
future reactivation.
