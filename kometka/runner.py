"""One pass over the library, and restoring the original posters.

For every movie:
  1. If the poster tag changed (new movie, or Jellyfin replaced the poster), download it.
     Unless it carries Kometka's marker, keep it as the original.
  2. Refresh the ratings from MDBList at most every RATINGS_MAX_AGE_DAYS.
  3. If the original or the ratings changed, draw the badges on the ORIGINAL and upload it.
Generated posters carry a JPEG comment marker, so they are never mistaken for originals.
"""
import io
import json
import logging
import os
import time

from PIL import Image

from . import overlay
from .mdblist import RateLimited

log = logging.getLogger("kometka")

MARKER = b"kometka"
CERTIFIED_MAX_AGE_DAYS = 7
DAY = 86400


class State:
    """Per-movie bookkeeping, kept as JSON in the data directory."""

    def __init__(self, path):
        self.path = path
        try:
            with open(path, encoding="utf-8") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {}
        self.data.setdefault("movies", {})

    @property
    def movies(self):
        return self.data["movies"]

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)


def is_generated(image):
    return MARKER in image[:65536]


def render(original_path, badges):
    buf = io.BytesIO()
    overlay.draw(Image.open(original_path), badges).save(
        buf, "JPEG", quality=90, optimize=True, comment=MARKER)
    return buf.getvalue()


def _originals(cfg):
    path = os.path.join(cfg.data_dir, "originals")
    os.makedirs(path, exist_ok=True)
    return path


def _certified_fresh(cfg, mdb, state, now):
    if "rottentomatoes" not in cfg.sources:
        return frozenset()
    cached = state.data.get("certified_fresh")
    if not cached or now - cached["fetched"] > CERTIFIED_MAX_AGE_DAYS * DAY:
        try:
            cached = {"fetched": now, "tmdb": sorted(mdb.certified_fresh())}
            state.data["certified_fresh"] = cached
        except Exception as e:
            log.warning("Could not fetch the Certified Fresh list: %s", e)
            cached = cached or {"tmdb": []}
    return frozenset(cached["tmdb"])


def run_pass(cfg, jf, mdb, state, now=None):
    now = now or time.time()
    originals = _originals(cfg)
    certified = _certified_fresh(cfg, mdb, state, now)
    rate_limited = False
    stats = dict(updated=0, unchanged=0, no_ratings=0, skipped=0, errors=0)

    for movie in jf.movies(cfg.libraries):
        item_id, name = movie["Id"], movie.get("Name", "?")
        tmdb = (movie.get("ProviderIds") or {}).get("Tmdb")
        tag = (movie.get("ImageTags") or {}).get("Primary")
        if not tmdb or not tag:
            stats["skipped"] += 1
            continue
        entry = state.movies.setdefault(item_id, {})
        original = os.path.join(originals, item_id + ".img")
        try:
            new_original = False
            if tag != entry.get("tag"):
                image = jf.get_poster(item_id)
                if not is_generated(image):
                    with open(original, "wb") as f:
                        f.write(image)
                    new_original = True
                entry["tag"] = tag

            if not rate_limited and now - entry.get("rated", 0) > cfg.ratings_max_age_days * DAY:
                try:
                    data = mdb.movie(tmdb)
                    entry["badges"] = overlay.badges_from_mdblist(data, cfg.sources, certified) if data else []
                    entry["rated"] = now
                except RateLimited as e:
                    rate_limited = True
                    log.warning("%s, the rest will be refreshed on the next pass", e)

            badges = [tuple(b) for b in entry.get("badges") or []]
            if not badges:
                stats["no_ratings"] += 1
                continue
            drawn = [tuple(b) for b in entry.get("drawn") or []]
            if (new_original or badges != drawn) and os.path.exists(original):
                jf.set_poster(item_id, render(original, badges))
                entry["tag"] = jf.poster_tag(item_id)
                entry["drawn"] = badges
                stats["updated"] += 1
                log.info("%s: %s", name, "  ".join(text for _, text in badges))
            else:
                stats["unchanged"] += 1
        except Exception as e:
            stats["errors"] += 1
            log.error("%s: %s", name, e)
        state.save()

    state.save()
    log.info("Pass finished: %s", ", ".join("%s %d" % (k.replace("_", " "), v) for k, v in stats.items()))
    return stats


def restore(cfg, jf, state):
    """Uploads the original posters back and forgets about those movies."""
    originals = _originals(cfg)
    restored = 0
    for item_id in list(state.movies):
        path = os.path.join(originals, item_id + ".img")
        if os.path.exists(path):
            try:
                buf = io.BytesIO()
                Image.open(path).convert("RGB").save(buf, "JPEG", quality=95)
                jf.set_poster(item_id, buf.getvalue())
                os.remove(path)
                restored += 1
            except Exception as e:
                log.error("%s: %s", item_id, e)
                continue
        del state.movies[item_id]
    state.save()
    log.info("Restored %d original posters", restored)
    return restored
