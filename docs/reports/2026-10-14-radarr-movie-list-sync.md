# Radarr Movie List synchronization engineering report

Status: Implementation and dry-run complete; live apply/deployment pending.

Branch production/radarr-movie-list-sync; based on main a4c9066.
D017 adds membership/score-band synchronization without changing D012/D014/D016.
107 full tests pass (25 new); pip check, production artifact check and preflight pass.

Live dry-run:387 qualified;152 existing to tag;235 missing to add;
0 already correct,0 unresolved identities,0 managed removals.
All755 existing films use /home/kolorifer/movies and Ultra-HD-Remux (profile7).
These are the single unambiguous existing conventions; no new choice is invented.
All235 lookups matched exact IMDb and separately confirmed TMDb identity.

Only managed tags and missing monitored movie records may be written.
searchForMovie=false; no acquisition/refresh/delete/move command is available.
Existing settings and unrelated tags are preserved by tag-only editor calls.
Private before/after snapshots and operation journals support recovery.

Initial apply, second dry-run, scheduler proof and final deployment verification
will be recorded before completing the task.
