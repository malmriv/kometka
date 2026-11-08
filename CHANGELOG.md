# Changelog

All notable changes to Kometka are documented here.

## [1.1.0]
- Series get the same badges as movies. Their ratings come from MDBList by TMDb id. Certified Fresh info comes from the k0meta/certifiedfreshshows list on MDBList.
- `LETTERBOXD_SCALE` setting: `10` shows Letterboxd ratings out of 10 instead of 5.
- Kometka now keeps each item's ratings instead of its badges, so changes to `SOURCES` or `LETTERBOXD_SCALE` show up on the next pass. The first pass after upgrading fetches every item's ratings from MDBList again.

## [1.0.1] - November 2nd, 2026
- Bug: movies in a collection were not processed. Fix provided by friend: require collection items not to be collapsed in Jellyfin API calls.

## [1.0.0] - November 1st, 2026

- Letterboxd, Rotten Tomatoes (Fresh, Rotten and Certified Fresh) and IMDb badges on Jellyfin movie posters, styled after Kometa's ratings overlay.
- Ratings from MDBList, matched by TMDb id and refreshed every `RATINGS_MAX_AGE_DAYS` (7 by default).
- Original posters kept in `/data/originals`. Badges are always drawn on the original and uploaded through the Jellyfin API.
- Generated posters carry a JPEG comment marker so they are never mistaken for originals.
- A daily run at `SCHEDULE`, an optional run on start (`RUN_ON_START`), and the `--once` and `--restore` commands.
- `SOURCES` and `LIBRARIES` settings. API keys can come from environment variables or `*_FILE` secrets.
- Docker image on GitHub Container Registry.
