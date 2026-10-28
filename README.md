# Radarr Festival List

A free bridge from IMDb Editors' annual **Festival Films You Need to Know** list to Radarr.

The repository checks IMDb twice a day and generates `festival.json` in the StevenLu Custom format understood by Radarr. It uses IMDb's website GraphQL query rather than scraping HTML, and retrieves every page before publishing.

## Project status

See the [repository status and review map](docs/REPOSITORY-STATUS.md) for the deployed revision, open work and the plan for reconciling `main` with production.

## Movie notifications

For a plain-language explanation of autobrr, Radarr, Telegram, identity checks and confirmation buttons, see the [movie notifications guide](docs/MOVIE-NOTIFICATIONS-GUIDE.md).

## Current source

- 2026 — https://www.imdb.com/list/ls4179043772/
- 2025 — https://www.imdb.com/list/ls592740542/
- 2024 — https://www.imdb.com/list/ls540386006/

Future annual lists can be added to `LISTS` in `festival.py`.

## Radarr

Add a **StevenLu Custom** Import List with this URL:

https://raw.githubusercontent.com/kolorifer/radarr-festival-list/main/festival.json

Suggested settings:

- Enable Automatic Add: Yes
- Monitor: Movie Only
- Search on Add: No
- Minimum Availability: Announced
- Radarr Tag: `festival-auto`
- Quality Profile: your festival profile

## Updating

GitHub Actions runs twice per day, and when the script or workflow changes. Use **Actions → Update festival list → Run workflow** for a manual refresh.

A failed request, empty list, invalid ID, duplicate entry, changing count, or incomplete pagination fails the build and preserves the previous feed. All configured lists must succeed before the file is replaced.

IMDb's website API is undocumented and may change. The verified persisted query hash is pinned in `LIST_QUERY_HASH`; if IMDb retires it, check https://github.com/Kometa-Team/IMDb-Hash/blob/master/LIST_HASH and verify the new response before updating it. No subscription, API key, or browser automation is required.

## Movie-intel qualification service

The production model qualifies a film when its IMDb ID belongs to the frozen
224 deployed legacy films or its final Evidence Score is at least 225.
See [production data](production/README.md), [project state](docs/PROJECT_STATE.md)
and [deployment runbook](deploy/README.md).

Qualification informs enriched Telegram notifications. The separate
[Movie List reconciliation](deploy/RADARR_SYNC.md) adds missing monitored records
with search disabled and keeps membership/score-band tags current.
The existing confirmation action adds without a general search and pushes only
the approved release. The public festival list remains
independent of the qualification catalog.
