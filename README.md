# Radarr Festival List

A free bridge from IMDb Editors' annual **Festival Films You Need to Know** list to Radarr.

The repository checks the public IMDb list twice a day and generates `festival.json` in the simple StevenLu Custom format understood by Radarr.

## Current source

- 2026 — https://www.imdb.com/list/ls4179043772/

Future annual lists can be added to the `LISTS` dictionary in `festival.py`.

## Radarr

Add a new **StevenLu Custom** Import List and use this URL:

https://raw.githubusercontent.com/kolorifer/radarr-festival-list/main/festival.json

Suggested settings:

- Enable Automatic Add: Yes
- Monitor: Movie Only
- Search on Add: No
- Minimum Availability: Announced
- Radarr Tag: `festival-auto`
- Quality Profile: a festival profile that accepts good 1080p releases and can upgrade to 2160p when available

## Updating

GitHub Actions runs twice per day. You can also open **Actions → Update festival list → Run workflow** to refresh it immediately.

The script refuses to overwrite the feed if it cannot find any movies, so a temporary IMDb markup/network failure will not replace a working list with an empty one.
