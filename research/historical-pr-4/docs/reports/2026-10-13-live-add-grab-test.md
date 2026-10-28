# Live integration verification: Telegram add-and-grab

Date: 2026-10-13

Status: **Passed end-to-end live test.**

## Scenario

A real autobrr/Radarr `Unknown Movie` rejection for **Marty Supreme (2025)** produced the enriched Telegram notification and the live action button:

`➕ Add to Radarr & grab this release`

The announced release was:

`Marty Supreme 2025 2160p UHD BluRay Hybrid REMUX DV HDR10+ HEVC Atmos-TRiToN`

The notification resolved the film metadata correctly and exposed no private tracker URL in the Telegram message or public action URL.

## Live action

Opening the Telegram action loaded the movie-intel confirmation page with the resolved movie/poster, exact announced release, Radarr root-folder selector, and quality-profile selector.

Selections used for the live test:

- Root folder: `/home/kolorifer/movies`
- Quality profile: `Ultra-HD-Remux`

The user then submitted **Add movie & grab this release**.

## Result

The live result page returned:

> Added and sent to downloader
>
> Movie is available in Radarr and the exact announced release was re-pushed. No indexer search was run.

The user then independently confirmed that everything completed correctly in the real Radarr/downloader flow.

Therefore the following production integration path is now live-verified:

`real autobrr rejection -> movie-intel webhook -> enriched Telegram notification -> approval page -> Radarr movie add -> exact release re-push -> downloader`

This replaces earlier project-state wording that treated the notification/download integration as not yet live-tested.

## Scope / caveats

- This was a real production-path test, not a synthetic fixture.
- The test verifies the add-and-grab path for an unknown movie and exact autobrr release.
- No generic Radarr indexer search was requested by the action.
- The user observed successful downstream completion.
- The single-use action-token replay/HTTP 410 behavior was not separately re-demonstrated during this live test; it remains covered by the service test suite.
- No raw tracker URL, API key, webhook secret, or action token is recorded here.
