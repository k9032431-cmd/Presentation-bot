"""Stil üçin görkeziş suraty (Pillow bilen, LibreOffice gerek däl)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import PREVIEW_DIR

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF"]


def _font(size, bold=False, serif=False):
    name = ("DejaVuSerif" if serif else "DejaVuSans") + ("-Bold" if bold else "") + ".ttf"
    for d in FONT_DIRS:
        p = Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _rgb(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def _lum(h):
    r, g, b, _ = _rgb(h)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def _grad(w, h, c1, c2):
    a, b = _rgb(c1), _rgb(c2)
    im = Image.new("RGBA", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            t = (x / w + y / h) / 2
            px[x, y] = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)) + (255,)
    return im


def _slide_title(s, W=1280, H=720):
    im = Image.new("RGBA", (W, H), _rgb(s["bg"]))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    serif = s.get("font") in ("Georgia", "Times New Roman")
    # sag blok
    im.paste(_grad(int(W * 0.48), H, s["primary"], s["secondary"]), (int(W * 0.52), 0))
    d.ellipse([W - 360, -120, W + 80, 320], fill=_rgb(s["accent"], 90))
    d.ellipse([W * 0.62, H - 300, W * 0.62 + 260, H - 40], fill=(255, 255, 255, 40))
    d.ellipse([W * 0.47, -60, W * 0.62, H + 60], fill=_rgb(s["bg"]))
    m = s.get("motif")
    if m == "frame":
        d.rectangle([24, 24, W - 24, H - 24], outline=_rgb(s["primary"]), width=3)
    elif m == "blocks":
        d.rectangle([0, 0, 22, H], fill=_rgb(s["primary"]))
        d.rectangle([22, 0, 30, H], fill=_rgb(s["accent"]))
    elif m == "diagonal":
        d.polygon([(W * 0.52, H), (W * 0.52 + 200, H), (W * 0.52, H - 200)], fill=_rgb(s["accent"], 200))
    im = Image.alpha_composite(im, ov)
    d = ImageDraw.Draw(im)
    d.rectangle([70, 160, 80, 470], fill=_rgb(s["accent"]))
    tc = s["primary"] if _lum(s["bg"]) > 0.4 else s["text"]
    d.text((110, 150), "PRESENTATION", font=_font(22, True), fill=_rgb(s["secondary"] if _lum(s["bg"]) > 0.4 else s["accent"]))
    d.text((106, 200), "Biznes\nprezentasiýa", font=_font(64, True, serif), fill=_rgb(tc), spacing=8)
    d.text((110, 380), "Stil: " + s["name"], font=_font(26), fill=_rgb(s["muted"]))
    d.rounded_rectangle([110, 470, 300, 515], radius=22, fill=_rgb(s["primary"]))
    on = (255, 255, 255, 255) if _lum(s["primary"]) < 0.6 else (17, 17, 17, 255)
    d.text((170, 478), "2026", font=_font(24, True), fill=on)
    return im


def _slide_cards(s, W=1280, H=720):
    im = Image.new("RGBA", (W, H), _rgb(s["bg"]))
    d = ImageDraw.Draw(im)
    serif = s.get("font") in ("Georgia", "Times New Roman")
    tc = s["primary"] if _lum(s["bg"]) > 0.4 else s["text"]
    d.text((70, 60), "Esasy ugurlar", font=_font(56, True, serif), fill=_rgb(tc))
    d.rectangle([72, 140, 160, 147], fill=_rgb(s["accent"]))
    cols = [s["primary"], s["secondary"], s["accent"]]
    for i in range(3):
        x = 70 + i * 390
        d.rounded_rectangle([x, 200, x + 360, 650], radius=24, fill=_rgb(s["surface"]))
        d.rectangle([x, 200, x + 360, 212], fill=_rgb(cols[i]))
        d.ellipse([x + 30, 245, x + 110, 325], fill=_rgb(s["primary"]))
        on = (255, 255, 255, 255) if _lum(s["primary"]) < 0.6 else (17, 17, 17, 255)
        d.text((x + 58, 260), str(i + 1), font=_font(40, True), fill=on)
        d.text((x + 30, 360), ["Strategiýa", "Analitika", "Ösüş"][i], font=_font(34, True), fill=_rgb(tc))
        for j in range(3):
            d.rounded_rectangle([x + 30, 430 + j * 45, x + 330 - j * 50, 448 + j * 45], radius=9,
                                fill=_rgb(s["muted"], 120))
    return im


def render_preview(style: dict) -> Path:
    key = hashlib.md5(json.dumps({k: v for k, v in style.items() if k != "id"},
                                 sort_keys=True).encode()).hexdigest()[:12]
    path = PREVIEW_DIR / f"style_{key}.png"
    if path.exists():
        return path
    a = _slide_title(style)
    b = _slide_cards(style)
    W = 1280
    canvas = Image.new("RGBA", (W + 80, 720 + 40 + 360 + 60), (24, 24, 28, 255))
    canvas.paste(a, (40, 40))
    sb = b.resize((620, 349))
    canvas.paste(sb, (40, 720 + 70))
    d = ImageDraw.Draw(canvas)
    # reňk palitrasy
    x = 700
    for k in ("primary", "secondary", "accent", "bg", "surface", "text"):
        d.rounded_rectangle([x, 800, x + 90, 890], radius=14, fill=_rgb(style[k]), outline=(80, 80, 80, 255))
        x += 105
    d.text((700, 910), style["name"], font=_font(44, True), fill=(255, 255, 255, 255))
    d.text((700, 975), f"{style.get('font', '')} · {style.get('motif', '')}", font=_font(26),
           fill=(170, 170, 180, 255))
    canvas.convert("RGB").save(path, quality=90)
    return path
