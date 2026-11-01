# Changelog

All notable changes to Kometka are documented here.

## [1.0.0] - November 1st, 2026

- Letterboxd, Rotten Tomatoes (Fresh, Rotten and Certified Fresh) and IMDb badges on Jellyfin movie posters, styled after Kometa's ratings overlay.
- Ratings from MDBList, matched by TMDb id and refreshed every `RATINGS_MAX_AGE_DAYS` (7 by default).
- Original posters kept in `/data/originals`. Badges are always drawn on the original and uploaded through the Jellyfin API.
- Generated posters carry a JPEG comment marker so they are never mistaken for originals.
- A daily run at `SCHEDULE`, an optional run on start (`RUN_ON_START`), and the `--once` and `--restore` commands.
- `SOURCES` and `LIBRARIES` settings. API keys can come from environment variables or `*_FILE` secrets.
- Docker image on GitHub Container Registry.

## To be released
- Do something similar for series. The ratings would come from different sources, though.
