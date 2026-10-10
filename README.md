# Radarr Festival List

A free bridge from IMDb Editors' annual **Festival Films You Need to Know** list to Radarr.

The repository checks IMDb twice a day and generates `festival.json` in the StevenLu Custom format understood by Radarr. It uses IMDb's website GraphQL query rather than scraping HTML, and retrieves every page before publishing.

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
