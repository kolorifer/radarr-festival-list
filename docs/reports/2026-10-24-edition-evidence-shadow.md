# Evidence-backed edition titles in shadow

## Approved brief

Implement and test generic separation of collection/edition labels from movie
titles, starting with Bond 50 Goldfinger. Shadow only; preserve ID conflicts,
sequel numbers, bounded requests, explicit download confirmation and the pilot
end date. No downloads or notifications. Preserve unrelated active CODEX_TASK.

## Implementation

`editions.py` consumes sourced edition/member facts from `edition-evidence.json`.
The initial fact is Bond 50 / Goldfinger (1964), supported by the user-supplied
[Blu-ray.com collection listing](https://www.blu-ray.com/movies/Bond-50-Blu-ray/36569/),
inspected October 24. This is manually sourced bibliographic data, not a release
approval or a conflicting-ID correction. There is no Bond-specific code branch.
New labels need supported metadata records; automatic web discovery is not added.

Matching requires an exact documented label + full movie title at either edge,
exact membership year, description beginning with that movie title, and exactly
one NFO filename bound to the release. Explicit pack/collection/multiple-film
wording in the description refuses the interpretation. The scorer additionally
requires agreeing checked IMDb mapping, year, positive runtime agreement and
matching film audio, with no existing identity/provenance/alias blocks. Numeric
and sequel comparisons remain unchanged for ordinary titles. Original source
title and raw similarity remain visible; a separate edition-resolution audit
records why the title contribution became +30. Incomplete rivals still block.

`fresh.py` attaches the edition evidence; `scorer.py` applies the gated title
contribution. No actor, retry, Telegram, Radarr, research budget or scheduling
code changed. No provider requests are added, and no retained scores are rewritten.

## Starting evidence and expected result

Read-only retained evidence for Bond 50 Goldfinger shows IMDb tt0058150,
TMDb 658, year 1964, runtime 110 minutes and English film audio, all agreeing.
The checked tracker description starts with Goldfinger; the sole NFO filename
matches the exact release. Its current score is 40 because the number 50 triggers
the sequel-number safeguard. The new fixture demonstrates 100 under documented
edition interpretation. This fixture is not a fresh live score; live application
awaits a normal budget/freshness-admitted scheduled refresh.

## Validation

Eight new tests cover supported metadata, an unrelated synthetic edition label,
unknown labels and members, movie packs, missing/mismatched/multiple filenames,
conflicting/missing IDs and other evidence, pagination/unknown rivals, and numeric
movie titles. Initial full-suite failure was a deterministic report schema change
from an empty audit field; fixed by emitting the audit only when applied. Existing
historical score snapshots then pass unchanged. Final code revision f67f60c.

Final local suite: 749 tests, 127.243s, two Linux-only skips. Isolated seedbox:
749 tests, 48.424s, all pass. Python 3.12/3.13 CI passed on exact f67f60c
(run 40092406734). Unchanged historical scorer snapshots pass.

## Limitations

This is deliberately evidence-driven rather than a general prefix stripper.
Only sourced edition/member records are supported (initially one member), and
unfamiliar or insufficiently documented labels remain for review. A singleton NFO
and matching description support a single-film interpretation but are not an
inspection of downloaded torrent contents; misleading source evidence remains
possible. No acquisition or torrent-content download is used for verification.
Review any actual conflicting IDs. Shadow scores do not authorize production
identification or downloading. No automatic browsing or new external budget.

## Deployment

Deployed exact tested **f67f60cdf2ece0f74263e836fc19d36998f7e6b6**. Source
manifest matched the isolated archive. Private backup edition-shadow-backup-pxeqfkl9.
Only the shadow unit directory changed; its existing timer is active. The service
was inactive before switching; no running refresh was interrupted. Eight edition
tests also pass from the installed checkout. Local health returned200; actor,
collector and research timer remain active. Actor remains
**23202815754ba2d97a86608003ca276251f1ae9c**.

Protected actor/config/actions, research timer, pilot deadline and both shadow
ledgers have unchanged hashes. Deployment made zero provider requests and did
not run the shadow refresh, send notifications or trigger downloads. Retained
Goldfinger score40 remains until a naturally admitted fresh run; the expected100
is a fixture result only. Current31/40 daily usage cannot admit a full refresh.
No budgets or freshness timestamps reset. Monitor now watches the first actual
edition result and knows the already-reported targeted Beast result. PR78 remains
draft; no production scoring activation. Rollback switches only the shadow unit
back to ab88fbd, preserving evidence, request and action history.
