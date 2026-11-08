"""Draws rating badges on a poster, mimicking Kometa's default "ratings" overlay.

Sizes are defined for a 1000x1500 poster and scaled to the real one.
"""
import os

from PIL import Image, ImageDraw, ImageFont

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

BACKGROUND = (0, 0, 0, 153)  # Kometa's #00000099
RADIUS = 30
PADDING = 15
HEIGHT = 105
FONT_SIZE = 55
GAP = 20
BOTTOM_MARGIN = 30
LOGO_HEIGHT = 70
FRESH = 60  # Rotten Tomatoes: Fresh from 60%, like Kometa's fresh_rating 6.0


def _logo(name, height):
    im = Image.open(os.path.join(ASSETS, name + ".png")).convert("RGBA")
    return im.resize((round(im.width * height / im.height), height), Image.LANCZOS)


def draw(poster, badges):
    """Returns an RGB copy of poster with badges [(icon, text), ...] centred at the bottom."""
    im = poster.convert("RGBA")
    if not badges:
        return im.convert("RGB")
    k = im.width / 1000
    font = ImageFont.truetype(os.path.join(ASSETS, "Inter-Medium.ttf"), round(FONT_SIZE * k))
    height, padding, radius, gap = (round(v * k) for v in (HEIGHT, PADDING, RADIUS, GAP))

    parts = []
    for icon, text in badges:
        logo = _logo(icon, round(LOGO_HEIGHT * k))
        box = font.getbbox(text)
        width = padding + logo.width + padding + (box[2] - box[0]) + padding * 2
        parts.append((logo, text, box, width))

    x = (im.width - sum(p[3] for p in parts) - gap * (len(parts) - 1)) // 2
    y = im.height - round(BOTTOM_MARGIN * k) - height
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    pen = ImageDraw.Draw(layer)
    for logo, text, box, width in parts:
        pen.rounded_rectangle((x, y, x + width, y + height), radius, fill=BACKGROUND)
        layer.alpha_composite(logo, (x + padding, y + (height - logo.height) // 2))
        text_y = y + (height - (box[3] - box[1])) // 2 - box[1]
        pen.text((x + padding * 2 + logo.width, text_y), text, font=font, fill=(255, 255, 255, 255))
        x += width + gap
    return Image.alpha_composite(im, layer).convert("RGB")


def ratings_from_mdblist(item, certified_fresh=frozenset()):
    """The ratings Kometka can draw from an MDBList movie or show, e.g.
    {"letterboxd": 3.9, "tomatoes": 92, "certified_fresh": True, "imdb": 7.5}. Letterboxd is out of 5."""
    found = {r["source"]: r["value"] for r in item.get("ratings", []) if r.get("value") is not None}
    ratings = {source: found[source] for source in ("letterboxd", "tomatoes", "imdb") if source in found}
    if "tomatoes" in ratings:
        ratings["certified_fresh"] = (item.get("ids") or {}).get("tmdb") in certified_fresh
    return ratings


def badges(ratings, sources, letterboxd_scale=5):
    """Turns ratings into [(icon, text), ...] in the order of sources, Letterboxd out of letterboxd_scale."""
    badges = []
    for source in sources:
        if source == "letterboxd" and "letterboxd" in ratings:
            badges.append(("Letterboxd", "%.1f" % (ratings["letterboxd"] * letterboxd_scale / 5)))
        elif source == "rottentomatoes" and "tomatoes" in ratings:
            score = ratings["tomatoes"]
            icon = ("RT-Crit-Top" if ratings.get("certified_fresh")
                    else "RT-Crit-Fresh" if score >= FRESH else "RT-Crit-Rotten")
            badges.append((icon, "%d%%" % score))
        elif source == "imdb" and "imdb" in ratings:
            badges.append(("IMDb", "%.1f" % ratings["imdb"]))
    return badges
