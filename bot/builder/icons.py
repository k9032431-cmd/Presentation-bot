"""Ikonlar (Font Awesome Free, CC BY 4.0) — stiliň reňkinde PNG edip çyzylýar."""
from __future__ import annotations

import functools
import io
import json
import logging
import os

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

# AI şu sanawdan saýlaýar (gysga we düşnükli atlar → Font Awesome ady)
ICONS = {
    "idea": "lightbulb", "rocket": "rocket", "growth": "arrow-trend-up", "chart": "chart-line",
    "pie": "chart-pie", "bar": "chart-column", "target": "bullseye", "goal": "flag-checkered",
    "team": "users", "people": "people-group", "person": "user-tie", "handshake": "handshake",
    "settings": "gear", "tools": "screwdriver-wrench", "security": "shield-halved", "lock": "lock",
    "key": "key", "globe": "earth-americas", "location": "location-dot", "map": "map-location-dot",
    "eco": "leaf", "plant": "seedling", "tree": "tree", "recycle": "recycle", "sun": "sun",
    "water": "droplet", "energy": "bolt", "battery": "battery-full", "fire": "fire",
    "heart": "heart", "health": "heart-pulse", "medicine": "stethoscope", "hospital": "hospital",
    "dna": "dna", "science": "flask", "atom": "atom", "brain": "brain", "ai": "robot",
    "chip": "microchip", "computer": "laptop", "phone": "mobile-screen", "cloud": "cloud",
    "database": "database", "server": "server", "code": "code", "network": "network-wired",
    "wifi": "wifi", "satellite": "satellite", "money": "money-bill-trend-up", "dollar": "sack-dollar",
    "coins": "coins", "bank": "building-columns", "investment": "hand-holding-dollar",
    "cart": "cart-shopping", "shop": "store", "delivery": "truck", "plane": "plane", "ship": "ship",
    "car": "car", "building": "building", "factory": "industry", "home": "house", "city": "city",
    "education": "graduation-cap", "book": "book-open", "school": "school", "teacher": "person-chalkboard",
    "law": "scale-balanced", "justice": "gavel", "art": "palette", "camera": "camera", "music": "music",
    "video": "film", "sport": "futbol", "food": "utensils", "coffee": "mug-hot", "time": "clock",
    "calendar": "calendar-days", "deadline": "hourglass-half", "check": "circle-check",
    "warning": "triangle-exclamation", "question": "circle-question", "info": "circle-info",
    "star": "star", "award": "award", "trophy": "trophy", "medal": "medal", "puzzle": "puzzle-piece",
    "search": "magnifying-glass", "compass": "compass", "route": "route", "chat": "comments",
    "megaphone": "bullhorn", "mail": "envelope", "news": "newspaper", "briefcase": "briefcase",
    "layers": "layer-group", "cubes": "cubes", "list": "list-check", "speed": "gauge-high",
    "quality": "gem", "customer": "face-smile", "support": "headset", "mountain": "mountain",
    "wind": "wind", "snow": "snowflake", "history": "landmark", "religion": "place-of-worship",
    "family": "people-roof", "child": "child-reaching", "weight": "weight-scale", "dumbbell": "dumbbell",
}
DEFAULT_CYCLE = ["idea", "growth", "target", "team", "settings", "star", "check", "rocket"]

_FA_DIR = None
_CODES: dict[str, int] = {}


def _load():
    global _FA_DIR, _CODES
    if _FA_DIR is not None:
        return _FA_DIR
    try:
        import fontawesomefree
        base = os.path.join(os.path.dirname(fontawesomefree.__file__), "static", "fontawesomefree")
        meta = json.load(open(os.path.join(base, "metadata", "icons.json"), encoding="utf-8"))
        _CODES = {name: int(v["unicode"], 16) for name, v in meta.items() if "solid" in v.get("styles", [])}
        _FA_DIR = os.path.join(base, "webfonts")
    except Exception:  # noqa: BLE001 - paket ýok bolsa ikonlar çyzylmaýar
        log.warning("fontawesomefree not available — icons disabled")
        _FA_DIR = ""
    return _FA_DIR


def resolve(name: str, i: int = 0) -> str:
    """AI beren ady Font Awesome adyna öwürmek."""
    n = (name or "").strip().lower().replace(" ", "-").replace("_", "-")
    if n in ICONS:
        return ICONS[n]
    _load()
    if n in _CODES:
        return n
    return ICONS[DEFAULT_CYCLE[i % len(DEFAULT_CYCLE)]]


@functools.lru_cache(maxsize=512)
def _render(fa_name: str, color: str, px: int) -> bytes | None:
    d = _load()
    if not d or fa_name not in _CODES:
        return None
    font = ImageFont.truetype(os.path.join(d, "fa-solid-900.ttf"), int(px * 0.78))
    ch = chr(_CODES[fa_name])
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    l, t, r, b = dr.textbbox((0, 0), ch, font=font)
    h = color.lstrip("#")
    rgb = tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))
    dr.text(((px - (r - l)) / 2 - l, (px - (b - t)) / 2 - t), ch, font=font, fill=rgb + (255,))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def icon_png(name: str, color: str, i: int = 0, px: int = 256) -> io.BytesIO | None:
    data = _render(resolve(name, i), color.upper(), px)
    return io.BytesIO(data) if data else None


def available() -> bool:
    return bool(_load())
