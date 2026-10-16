# Engineering report: issue #20 / supervisor task 3

**Specification:** Latest trusted SUPERVISOR_TASK 3: investigate the single
safeguard-blocked removal using private evidence and read-only live state.
**Result:** READY_FOR_REVIEW; same-movie equivalence established, new user
authorization required before any removal.
**Repository revision:** automation/issue-20-worker, base 0534549.
**Verification date:** 2026-10-16, existing unattended SSH/private-state path.

## Findings and acceptance evidence

The sole mismatched field is the Radarr database ID. IMDb, TMDb, title and year
match exactly. The originally authorized database ID is unoccupied, and the
current external-identity match is unique. This establishes the same intended
movie under a different database ID. The evidence does not establish the cause
of that change.

The original private operation, Task 1 before/execution evidence, Task 2 final
report and independent verification were read before live Radarr queries.
The operation blob matches the version recorded by Task 2.

Current safeguards: hasFile=false, monitored=true, no movie file or disk size,
no tags, no canonical watched membership, no qualified-catalog protection and
no explicit protection fields. Monitoring alone is not a protection in the
original operation. The entry remains untouched.

New authorization must name the current exact five-field identity tuple for
this single removal. Permit only entry removal with deleteFiles=false and
addImportExclusion=false, subject to fresh identity/uniqueness and all original
safeguard checks. No safeguard relaxation, media deletion, re-addition or
unrelated action is needed or authorized. The exact tuple is private.

## Files and components changed

Only this sanitized aggregate report changes in the repository. The private
blocker-resolution report, exact evidence, read-only acquisition source and
minimal re-authorization scope are saved locally in a mode700 directory with
mode600 files:

`/private/tmp/issue20-task3-rgwrxbuh/blocker-resolution.md`

Adjacent `evidence.json` and `investigation-source.py` retain the detailed
evidence and acquisition code. These are local private handoff artifacts;
supervisor/runner retention is required. They were not published to the private
GitHub repository or written to the seedbox, preserving read-only seedbox access
and runner ownership of Git publication.

## Checks run and results

- Live GET-only collection, tags, target detail and repeated collection/tags
  reads passed. Target and tags remained stable between readbacks.
- Exact original/current identity comparison, external-ID uniqueness, original
  ID absence and original Task 1 identity assertions passed.
- Detail/collection comparison passed for every field except images, whose
  endpoint serialization difference was already documented by Task 2.
- Canonical watched and deployed qualification protection checks passed.
- Private report JSON, exact re-authorization tuple, safeguard assertions and
  directory/file permissions verified locally.
- Repository diff/whitespace and private-identity disclosure checks passed.

Runtime tests and dependency checks were not run; no runtime/dependency change.
No public metadata lookup was needed because both exact external identifiers
and title/year agree.

## Deployment, risks and handoff

No deployment, Radarr writes, media operations, seedbox filesystem writes,
service/configuration changes, daemon startup, Git publication or issue comments.
No changes to unrelated briefs, project state or product decisions.

Current safeguards may change; a later authorized removal must recheck them.
The historical cause of database ID reassignment remains unresolved. User and
supervisor review the private exact identity before deciding whether to grant
new authorization. Automation owns commit/push/PR/issue reporting.
