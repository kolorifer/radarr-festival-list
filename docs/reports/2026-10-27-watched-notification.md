# Engineering report: Watched notification presentation

**Specification:** [Owner's requested behavior](2026-10-27-watched-notification-brief.md).
**Result:** Implemented and locally verified; deployment blocked by missing host access.
**Repository revision:** fix/watched-notification, based on recorded actor
`d598296e4ba3b3223e9014c993b116ada9ed723e`.
**Verification date:** 2026-10-27, isolated cloud checkout, Python 3.12.

## What changed

Enriched rejection cards no longer show “POTENTIAL FALSE NEGATIVE”. A matched
Radarr movie with the current watched tag displays **Watched** in place of its
model assessment. Other movies retain their qualification information without
the warning. Posters, ratings, recognition and actual rejection details remain.

Watch state comes from the matched movie's numeric tag IDs and a fresh GET /tag;
there is no hardcoded tag ID, monitoring inference or private-manifest dependency.
An unresolved/contradictory identity cannot supply a watch label. Unavailable
Radarr movie/tag reads leave the normal notification usable without a watch claim.

## Files and components changed

| Component | Purpose |
| --- | --- |
| movie_intel_service.py | Read watch state after identity resolution and render the label |
| radarr_client.py | Resolve assigned tag IDs to the exact current label |
| test_watched_notifications.py | Eight synthetic regression tests |
| test_movie_intel_service.py | Assert warning removal and retained qualification text |
| .github/workflows/movie-intel-test.yml | Run existing CI against the isolated runtime PR base |
| docs | Preserve brief, result and agreed presentation decision |

## Acceptance criteria and evidence

| Criterion | Result | Evidence |
| --- | --- | --- |
| Watched tag replaces model assessment | Passed | Mock Radarr movie + tag GETs through build_movie_context |
| Unmonitored alone never means watched | Passed | Untagged/unrelated-tag/missing-movie cases |
| No misleading warning on other movies | Passed | Updated original formatter regression |
| Unknown/contradictory identity never claims watched | Passed | IMDb/TMDb mismatch and unresolved-state cases |
| Lookup failure preserves notification | Passed | Movie/tag errors and malformed tag response |
| No acquisition or movie changes | Passed synthetically | Only GET paths used by new integration; full existing action suite passes |
| Live tag and Telegram behavior | Not verified | No host/API access in this session |

## Tests run and results

- `.venv/bin/python -m unittest -v test_watched_notifications test_movie_intel_service test_film_editions test_notification_reliability`: 39 passed.
- `.venv/bin/python -m unittest -v`: 745 tests in 42.782s, OK with one skip
  (kernel Landlock unavailable). Run with network permission for local mock servers.
- `.venv/bin/python production_scoring.py --check`: passed; 1,909 candidates,
  224 grandfathered, 163 new and 387 qualified.
- `.venv/bin/python -m pip check`: passed. No dependency changes.
- `git diff --check`: passed.

An earlier main-based trial ran 695 tests: the first sandboxed attempt had
42 local-socket permission errors; the network-enabled rerun passed with one
skip. Inspection then found deployed open runtime PRs, so the final change was
ported to their recorded actor baseline and the full 745-test suite rerun.
The main-based trial is not the deployment artifact.

## Deployment result

Not deployed. Environment inspection found no configured credentials/VPN or
SSH connection for the seedbox. The owner was asked which existing deployment
connection to use. Live checkout, health and Radarr state have not been inspected.
The baseline is based on PR89's deployment report, not a fresh host readback.
Do not deploy main or replace the current actor without checking its actual HEAD.
Preserve its current open runtime work and follow deploy/README.md preflight,
backup, service-only activation, health and read-only integration checks.

No real notification, card edit, search, grab, Radarr write, or service restart
was performed. Existing Telegram messages are not rewritten by this code change.

## Limits and review

Existing routine rejections that intentionally skip identity enrichment still
skip it; no guessed watched label is added to those cards. Enriched cards add at
most one movie GET and one tag GET, using existing 20-second request timeouts and
no automatic retries; unavailable reads can therefore delay the card. Tag IDs
are resolved fresh, so renames/removals do not leave a cached watched assertion.

Production access and current-baseline verification remain necessary. Product
acceptance and live integration verification are pending.

## Commit and PR reference

This report's containing fix/watched-notification commit and pull request supply
the revision reference. The PR targets runtime/watched-notification-baseline.

## Project context updates

PROJECT_STATE.md records implementation separately from deployment. D036 records
the owner's requested presentation. The completed implementation brief and this
report are archived together. CODEX_TASK.md's unrelated cleanup assignment is
preserved; no cleanup action was taken or marked complete.
