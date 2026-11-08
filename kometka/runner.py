"""One pass over the library, and restoring the original posters.

For every movie and series:
  1. If the poster tag changed (new item, or Jellyfin replaced the poster), download it.
     Unless it carries Kometka's marker, keep it as the original.
  2. Refresh the ratings from MDBList at most every RATINGS_MAX_AGE_DAYS.
  3. If the original or the badges changed, draw the badges on the ORIGINAL and upload it.
     The badges are worked out from the stored ratings on every pass, so changes to SOURCES
     or LETTERBOXD_SCALE show up on the next pass without asking MDBList again.
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
# Jellyfin item type -> MDBList media type
MEDIA_TYPES = {"Movie": "movie", "Series": "show"}


class State:
    """Per-item bookkeeping, kept as JSON in the data directory."""

    def __init__(self, path):
        self.path = path
        try:
            with open(path, encoding="utf-8") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {}
        # Kometka 1.0.x only did movies: it kept them under "movies", with a single Certified Fresh list.
        self.data.setdefault("items", self.data.pop("movies", {}))
        if "tmdb" in self.data.get("certified_fresh", {}):
            del self.data["certified_fresh"]

    @property
    def items(self):
        return self.data["items"]

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


def _certified_fresh(mdb, state, media_type, now):
    # Fetched even when SOURCES leaves Rotten Tomatoes out, so the stored ratings stay complete.
    lists = state.data.setdefault("certified_fresh", {})
    cached = lists.get(media_type)
    if not cached or now - cached["fetched"] > CERTIFIED_MAX_AGE_DAYS * DAY:
        try:
            cached = {"fetched": now, "tmdb": sorted(mdb.certified_fresh(media_type))}
            lists[media_type] = cached
        except Exception as e:
            log.warning("Could not fetch the Certified Fresh %ss list: %s", media_type, e)
            cached = cached or {"tmdb": []}
    return frozenset(cached["tmdb"])


def run_pass(cfg, jf, mdb, state, now=None):
    now = now or time.time()
    originals = _originals(cfg)
    certified = {}  # MDBList media type -> Certified Fresh TMDb ids, fetched when first needed
    rate_limited = False
    stats = dict(updated=0, unchanged=0, no_ratings=0, skipped=0, errors=0)

    for item in jf.items(cfg.libraries):
        item_id, name = item["Id"], item.get("Name", "?")
        media_type = MEDIA_TYPES.get(item.get("Type"))
        tmdb = (item.get("ProviderIds") or {}).get("Tmdb")
        tag = (item.get("ImageTags") or {}).get("Primary")
        if not media_type or not tmdb or not tag:
            stats["skipped"] += 1
            continue
        entry = state.items.setdefault(item_id, {})
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

            # Entries from Kometka 1.0.x kept the badges instead of the ratings, so they are refreshed too.
            stale = "ratings" not in entry or now - entry.get("rated", 0) > cfg.ratings_max_age_days * DAY
            if not rate_limited and stale:
                try:
                    if media_type not in certified:
                        certified[media_type] = _certified_fresh(mdb, state, media_type, now)
                    data = mdb.item(media_type, tmdb)
                    entry["ratings"] = overlay.ratings_from_mdblist(data, certified[media_type]) if data else {}
                    entry["rated"] = now
                    entry.pop("badges", None)
                except RateLimited as e:
                    rate_limited = True
                    log.warning("%s, the rest will be refreshed on the next pass", e)

            badges = overlay.badges(entry.get("ratings") or {}, cfg.sources, cfg.letterboxd_scale)
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
    """Uploads the original posters back and forgets about those items."""
    originals = _originals(cfg)
    restored = 0
    for item_id in list(state.items):
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
        del state.items[item_id]
    state.save()
    log.info("Restored %d original posters", restored)
    return restored
