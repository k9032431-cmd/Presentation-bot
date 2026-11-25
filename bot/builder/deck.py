"""Prezentasiýany gurmak: 3 dereje (simple / medium / full)."""
from __future__ import annotations

import io
import logging

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Inches, Pt

from ..ai import Deck, Slide
from .anim import add_animations, add_transition
from .helpers import (MSO_SHAPE, bullets, fit, gradient, hex2rgb, mix, notes, on_color,
                      picture_fill, rect, round_corners, shadow, text)
from .icons import icon_png

log = logging.getLogger(__name__)

W, H = 13.333, 7.5

MEDIUM_TRANSITIONS = ["fade", "push"]
FULL_TRANSITIONS = ["morph", "push", "morph", "wipe", "morph", "cover", "split"]


FAMILIES = ["rise", "zoom", "fly_left", "rise", "wipe_left", "fade"]


def _effect_for(shape, idx: int, layout: str, family: str = "rise") -> str:
    """Doly derejede her element üçin animasiýa saýlamak."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    st = shape.shape_type
    if getattr(shape, "has_chart", False) and shape.has_chart:
        return "wipe_up"
    if st == MSO_SHAPE_TYPE.PICTURE:
        return "fade"
    if idx == 0:
        return "fade"
    w, h = shape.width, shape.height
    if st == MSO_SHAPE_TYPE.AUTO_SHAPE and h < Inches(0.15):
        return "wipe_left"            # inçe zolaklar çepden çyzylýar
    if st == MSO_SHAPE_TYPE.AUTO_SHAPE and w < Inches(1.3) and h < Inches(1.3):
        return "zoom"                 # tegelek nomerler, ikonlar
    if layout == "stats" and st == MSO_SHAPE_TYPE.AUTO_SHAPE:
        return "wipe_up"
    return family  # her slaýdda başga effekt maşgalasy


class Ctx:
    def __init__(self, style: dict, level: str, images: dict[int, io.BytesIO]):
        self.s = style
        self.level = level
        self.images = images
        # Dizaýn ähli derejelerde birmeňzeş baý; tapawut diňe animasiýada (build-da)
        self.full = True
        self.medium = False
        self.simple = False
        self.dark = _lum(style["bg"]) < 0.4
        self.tfont = style.get("font", "Calibri")
        self.bfont = style.get("body_font", "Calibri")
        self.on_primary = on_color(style["primary"])
        self.total = 0
        serif = self.tfont in ("Georgia", "Times New Roman")
        # Şrift jübütleri: uly sanlar, ýeňil sözbaşylar, kiçi bellikler
        self.nfont = "Georgia" if serif else "Segoe UI Black"
        self.lfont = self.bfont if serif else "Segoe UI Light"
        self.kfont = self.bfont if serif else "Segoe UI Semibold"
        self.kicker = ""        # häzirki slaýdyň ýokarky belligi
        self.card = style["surface"]  # kartoçka reňki (fon reňkine görä üýtgeýär)
        self.tint = False

    def c(self, key):
        return self.s[key]


def _lum(h):
    from .helpers import luminance
    return luminance(h)


# ----------------------------------------------------------------- decorations
def background(ctx: Ctx, slide, color=None):
    bg = slide.background.fill
    bg.solid()
    if color is None and ctx.tint:
        color = ctx.c("surface")  # käbir slaýdlar reňkli fonda: monoton bolmasyn
    bg.fore_color.rgb = hex2rgb(color or ctx.c("bg"))


def _morph_names(slide, start: int):
    """Täze döredilen bezeg shape-lerine birmeňzeş at: Morph geçişi olary bir slaýddan
    beýlekisine ýuwaşlyk bilen süýşürýär."""
    for k, shp in enumerate(list(slide.shapes)[start:]):
        shp.name = f"!!deco{k}"


def motif(ctx: Ctx, slide, strong=False):
    n0 = len(slide.shapes)
    _motif(ctx, slide, strong)
    _morph_names(slide, n0)


def _motif(ctx: Ctx, slide, strong=False):
    """Stiliň bezeg elementleri."""
    s = ctx.s
    p, sec, acc = s["primary"], s["secondary"], s["accent"]
    if ctx.simple:
        rect(slide, 0, 0, W, 0.12, p)
        return
    m = s.get("motif", "minimal")
    if m == "wave":
        rect(slide, W - 3.2, H - 2.0, 5.0, 4.0, sec, MSO_SHAPE.OVAL, alpha=0.18)
        rect(slide, W - 2.2, H - 1.4, 4.0, 3.2, p, MSO_SHAPE.OVAL, alpha=0.9 if strong else 0.85)
        rect(slide, -1.2, -1.2, 2.6, 2.6, acc, MSO_SHAPE.OVAL, alpha=0.25)
    elif m == "circles":
        rect(slide, W - 2.6, -1.3, 3.6, 3.6, p, MSO_SHAPE.OVAL, alpha=0.9)
        rect(slide, W - 3.4, 1.2, 1.3, 1.3, acc, MSO_SHAPE.OVAL, alpha=0.6)
        rect(slide, -0.6, H - 1.0, 1.6, 1.6, sec, MSO_SHAPE.OVAL, alpha=0.3)
    elif m == "blocks":
        rect(slide, 0, 0, 0.28, H, p)
        rect(slide, 0.28, 0, 0.08, H, acc)
        rect(slide, W - 1.0, H - 1.0, 1.0, 1.0, p)
        rect(slide, W - 1.6, H - 0.6, 0.6, 0.6, acc)
    elif m == "diagonal":
        t = rect(slide, W - 3.0, 0, 3.0, H, p, MSO_SHAPE.RIGHT_TRIANGLE, alpha=0.9)
        t.rotation = 180
        t2 = rect(slide, W - 1.6, 0, 1.6, H, sec, MSO_SHAPE.RIGHT_TRIANGLE, alpha=0.7)
        t2.rotation = 180
        rect(slide, 0, H - 0.1, W, 0.1, acc)
    elif m == "frame":
        rect(slide, 0.3, 0.3, W - 0.6, H - 0.6, None, line=(p, 1.25))
        rect(slide, 0.3, 0.3, 0.9, 0.06, acc)
    else:  # minimal
        rect(slide, 0.7, H - 0.5, 1.2, 0.06, acc)


def content_width(ctx: Ctx) -> float:
    """Bezegler tekstiň üstüne düşmez ýaly."""
    if ctx.simple:
        return W - 1.4
    return {"diagonal": W - 3.4, "circles": W - 3.6}.get(ctx.s.get("motif"), W - 1.6)


def title(ctx: Ctx, slide, txt, y=0.55, x=None):
    x = x if x is not None else (0.85 if ctx.s.get("motif") == "blocks" and not ctx.simple else 0.7)
    w = content_width(ctx) - (x - 0.7)
    size = 34 if len(txt) < 40 else 28
    if ctx.simple:
        size -= 2
    if ctx.kicker:
        rect(slide, x + 0.05, y - 0.14, 0.12, 0.12, ctx.c("accent"))
        text(slide, x + 0.25, y - 0.27, w - 0.3, 0.35, ctx.kicker.upper()[:40], size=11,
             color=ctx.c("secondary") if not ctx.dark else ctx.c("accent"), font=ctx.kfont, cs=250)
    t = text(slide, x, y, w, 1.0, txt, size=size, color=ctx.c("primary") if not ctx.dark else ctx.c("text"),
             bold=True, font=ctx.tfont, anchor="middle")
    bar = None
    if not ctx.simple:
        bar = rect(slide, x + 0.05, y + 1.05, 0.9, 0.07, ctx.c("accent"))
    return t, bar


def page_no(ctx: Ctx, slide, n):
    if ctx.simple:
        return
    text(slide, W - 1.3, H - 0.55, 0.8, 0.35, f"{n:02d}", size=11, color=ctx.c("muted"),
         font=ctx.bfont, align="right")


def placeholder_art(ctx: Ctx, slide, x, y, w, h):
    """Surat ýok bolsa: owadan geometrik kompozisiýa."""
    s = ctx.s
    base = rect(slide, x, y, w, h, s["primary"], MSO_SHAPE.ROUNDED_RECTANGLE)
    round_corners(base, 0.06)
    gradient(base, s["primary"], s["secondary"], 45)
    r = min(w, h)
    rect(slide, x + w - r * 0.7, y - r * 0.15 + h * 0.1, r * 0.8, r * 0.8, s["accent"], MSO_SHAPE.OVAL, alpha=0.35)
    rect(slide, x + w * 0.1, y + h - r * 0.55, r * 0.5, r * 0.5, "#FFFFFF", MSO_SHAPE.OVAL, alpha=0.15)
    rect(slide, x + w * 0.35, y + h * 0.3, r * 0.25, r * 0.25, s["accent"], MSO_SHAPE.OVAL, alpha=0.6)
    return base


def image_or_art(ctx: Ctx, slide, idx, x, y, w, h):
    img = ctx.images.get(idx)
    if img is not None:
        return picture_fill(slide, img, x, y, w, h)
    return placeholder_art(ctx, slide, x, y, w, h)


def place_icon(ctx: Ctx, slide, name, i, x, y, size, color):
    png = icon_png(name, color, i)
    if png is None:
        return None
    return slide.shapes.add_picture(png, Inches(x), Inches(y), Inches(size), Inches(size))


# ------------------------------------------------------------------- layouts
def l_title(ctx: Ctx, slide, d: Slide, idx, deck: Deck):
    s = ctx.s
    anim = []
    if ctx.simple:
        background(ctx, slide, s["primary"])
        rect(slide, 0, H - 0.35, W, 0.35, s["accent"])
        t = text(slide, 1.0, 2.2, W - 2, 1.8, d.title or deck.title, size=44, bold=True,
                 color=ctx.on_primary, font=ctx.tfont, align="center", anchor="middle")
        st = text(slide, 1.5, 4.1, W - 3, 1.0, d.subtitle or deck.subtitle, size=20,
                  color=mix(ctx.on_primary, s["primary"], 0.2), font=ctx.bfont, align="center")
        return [t, st]

    background(ctx, slide)
    # sag tarapda surat / kompozisiýa
    pic = image_or_art(ctx, slide, idx, W * 0.52, 0, W * 0.48, H)
    ov = rect(slide, W * 0.52, 0, W * 0.48, H, s["primary"], alpha=0.25)
    # çep panel
    panel = rect(slide, 0, 0, W * 0.56, H, s["bg"])
    shape_edge = rect(slide, W * 0.56 - 1.0, -0.5, 2.0, H + 1.0, s["bg"], MSO_SHAPE.OVAL)
    rect(slide, 0.7, 1.2, 0.12, 3.6, s["accent"])
    tag = text(slide, 1.05, 1.1, 5.5, 0.4, "PRESENTATION", size=12, bold=True,
               color=s["secondary"] if not ctx.dark else s["accent"], font=ctx.bfont)
    t_txt = d.title or deck.title
    t = text(slide, 1.0, 1.55, 6.3, 2.4, t_txt, size=44 if len(t_txt) < 45 else 36, bold=True,
             color=s["primary"] if not ctx.dark else s["text"], font=ctx.tfont, anchor="middle")
    st = text(slide, 1.05, 4.0, 6.0, 1.0, d.subtitle or deck.subtitle, size=18,
              color=s["muted"], font=ctx.bfont)
    if ctx.full:
        chip = rect(slide, 1.05, 5.4, 2.4, 0.5, s["primary"], MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(chip, 0.5)
        chip.text_frame.text = "2026"
        _fmt_shape_text(chip, 14, ctx.on_primary, ctx.bfont, bold=True)
        anim += [pic, ov, tag, t, st, chip]
    else:
        anim += [t, st]
    _ = panel, shape_edge
    return anim


def _fmt_shape_text(shape, size, color, font, bold=False):
    from pptx.enum.text import PP_ALIGN
    tf = shape.text_frame
    tf.word_wrap = True
    for p in tf.paragraphs:
        p.alignment = PP_ALIGN.CENTER
        for r in p.runs:
            r.font.size = Pt(size)
            r.font.color.rgb = hex2rgb(color)
            r.font.name = font
            r.font.bold = bold


def l_bullets(ctx: Ctx, slide, d: Slide, idx, deck, with_image=False):
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    items = d.bullets or [it.title + ": " + it.text for it in d.items]
    x0 = 0.85 if ctx.s.get("motif") == "blocks" and not ctx.simple else 0.7
    if with_image:
        w = 6.4
        pic = image_or_art(ctx, slide, idx, 7.6, 1.75, 4.9, 4.9)
        if ctx.full:
            rect(slide, 7.35, 1.5, 1.2, 1.2, ctx.c("accent"), MSO_SHAPE.OVAL, alpha=0.8)
    else:
        w = content_width(ctx) - x0 + 0.5
        pic = None
    size = fit(items, 22, int(w * 6.5), 11)
    b = bullets(slide, x0, 1.85, w, 5.0, items, size=size, color=ctx.c("text"), font=ctx.bfont,
                bullet_color=ctx.c("accent") if not ctx.simple else ctx.c("primary"),
                bullet_char="■" if ctx.s.get("motif") == "blocks" else "●")
    return [t, bar, b, pic]


def l_agenda(ctx: Ctx, slide, d: Slide, idx, deck):
    s = ctx.s
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    items = (d.bullets or [i.title for i in d.items])[:6]
    if not items:  # AI mazmuny bermedik bolsa: slaýd sözbaşylaryndan
        items = [x.title for x in deck.slides
                 if x.layout not in ("title", "agenda", "thanks", "quote") and x.title][:6] or [d.title or "—"]
    anim = [t, bar]
    n = len(items)
    cols = 2 if n > 3 else 1
    rows = -(-n // cols)
    cw = (content_width(ctx) - 0.7 - 0.4 * (cols - 1)) / cols
    rh = min(1.05, 4.8 / rows)
    for i, it in enumerate(items):
        c, r = i // rows, i % rows
        x = 0.7 + c * (cw + 0.4)
        y = 1.95 + r * (rh + 0.2)
        num = rect(slide, x, y, rh, rh, s["primary"], MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(num, 0.2)
        num.text_frame.text = f"{i + 1:02d}"
        _fmt_shape_text(num, 20, ctx.on_primary, ctx.tfont, bold=True)
        card = rect(slide, x + rh + 0.15, y, cw - rh - 0.15, rh, ctx.card, MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(card, 0.15)
        shadow(card, blur=8, dist=2, alpha=0.1)
        tx = text(slide, x + rh + 0.35, y, cw - rh - 0.5, rh, it, size=17, color=s["text"],
                  font=ctx.bfont, anchor="middle")
        anim += [num, card, tx] if ctx.full else []
    return anim


def l_cards(ctx: Ctx, slide, d: Slide, idx, deck):
    s = ctx.s
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    items = d.items[:3] or [type("I", (), {"title": b, "text": ""})() for b in d.bullets[:3]]
    n = max(1, len(items))
    gap = 0.35
    total_w = min(content_width(ctx), W - 1.4) - 0.0
    cw = (total_w - gap * (n - 1)) / n
    anim = [t, bar]
    longest = max((len(i.text) for i in items), default=0)
    body = 16 if longest < 120 else 14
    for i, it in enumerate(items):
        x = 0.7 + i * (cw + gap)
        y = 2.05
        card = rect(slide, x, y, cw, 4.5, ctx.card, MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(card, 0.08)
        shadow(card)
        top = rect(slide, x, y, cw, 0.12, [s["primary"], s["secondary"], s["accent"]][i % 3])
        circ = rect(slide, x + 0.35, y + 0.45, 0.85, 0.85, s["primary"], MSO_SHAPE.OVAL)
        ic = place_icon(ctx, slide, getattr(it, "icon", ""), i, x + 0.53, y + 0.63, 0.49, ctx.on_primary)
        if ic is None:
            circ.text_frame.text = str(i + 1)
            _fmt_shape_text(circ, 20, ctx.on_primary, ctx.tfont, bold=True)
        text(slide, x + cw - 1.5, y + 0.25, 1.25, 0.9, f"{i + 1:02d}", size=40, bold=True,
             color=mix(ctx.card, s["primary"], 0.18), font=ctx.nfont, align="right")
        tt = text(slide, x + 0.3, y + 1.5, cw - 0.6, 0.9, it.title, size=19, bold=True,
                  color=s["primary"] if not ctx.dark else s["text"], font=ctx.tfont)
        tx = text(slide, x + 0.3, y + 2.4, cw - 0.6, 2.0, it.text, size=body, color=s["muted"],
                  font=ctx.bfont, spacing=1.1)
        anim += [card, top, circ, ic, tt, tx]
    return anim


def l_two_column(ctx: Ctx, slide, d: Slide, idx, deck):
    s = ctx.s
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    total = min(content_width(ctx), W - 1.4)
    cw = (total - 0.5) / 2
    anim = [t, bar]
    cols = [(d.left_title, d.left_bullets, s["primary"]), (d.right_title, d.right_bullets, s["secondary"])]
    size = min(fit(d.left_bullets, 18, int(cw * 6.5), 9, 12), fit(d.right_bullets, 18, int(cw * 6.5), 9, 12))
    for i, (ht, bl, col) in enumerate(cols):
        x = 0.7 + i * (cw + 0.5)
        head = rect(slide, x, 1.95, cw, 0.75, col, MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(head, 0.2)
        head.text_frame.text = ht
        _fmt_shape_text(head, 19, on_color(col), ctx.tfont, bold=True)
        box = rect(slide, x, 2.85, cw, 3.9, ctx.card, MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(box, 0.06)
        shadow(box)
        b = bullets(slide, x + 0.3, 3.05, cw - 0.6, 3.6, bl, size=size, color=s["text"],
                    font=ctx.bfont, bullet_color=col if not ctx.dark else s["accent"], gap=8)
        anim += [head, box, b]
    if not ctx.simple:
        vs = rect(slide, 0.7 + cw + 0.25 - 0.4, 3.9, 0.8, 0.8, s["accent"], MSO_SHAPE.OVAL)
        vs.text_frame.text = "VS"
        _fmt_shape_text(vs, 14, on_color(s["accent"]), ctx.tfont, bold=True)
        anim.append(vs)
    return anim


def l_stats(ctx: Ctx, slide, d: Slide, idx, deck):
    s = ctx.s
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    stats = d.stats[:4]
    n = max(1, len(stats))
    total = min(content_width(ctx), W - 1.4)
    gap = 0.3
    cw = (total - gap * (n - 1)) / n
    anim = [t, bar]
    for i, st in enumerate(stats):
        x = 0.7 + i * (cw + gap)
        col = [s["primary"], s["secondary"]][i % 2]
        card = rect(slide, x, 2.2, cw, 3.6, col, MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(card, 0.08)
        if ctx.full:
            gradient(card, col, mix(col, s["accent"], 0.35), 60)
        shadow(card)
        oc = on_color(col)
        ic = place_icon(ctx, slide, st.icon, i, x + cw / 2 - 0.25, 2.45, 0.5, oc)
        v = text(slide, x + 0.2, 2.85, cw - 0.4, 1.2, st.value, size=46 if len(st.value) < 6 else 36,
                 bold=True, color=oc, font=ctx.nfont, align="center", anchor="middle")
        ln = rect(slide, x + cw / 2 - 0.4, 4.1, 0.8, 0.05, s["accent"] if col != s["accent"] else oc)
        lb = text(slide, x + 0.25, 4.3, cw - 0.5, 1.3, st.label, size=15, color=oc,
                  font=ctx.bfont, align="center")
        anim += [card, ic, v, ln, lb]
    if d.subtitle:
        anim.append(text(slide, 0.7, 6.1, total, 0.6, d.subtitle, size=14, color=s["muted"],
                         font=ctx.bfont, italic=True))
    return anim


def l_process(ctx: Ctx, slide, d: Slide, idx, deck, timeline=False):
    s = ctx.s
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    items = d.items[:5]
    n = max(1, len(items))
    total = min(content_width(ctx), W - 1.4)
    cw = total / n
    anim = [t, bar]
    line_y = 3.25
    line = rect(slide, 0.7 + cw / 2, line_y - 0.03, total - cw, 0.06, s["muted"], alpha=0.5)
    anim.append(line)
    for i, it in enumerate(items):
        cx = 0.7 + i * cw + cw / 2
        col = [s["primary"], s["secondary"], s["accent"]][i % 3]
        if timeline:
            dot = rect(slide, cx - 0.22, line_y - 0.22, 0.44, 0.44, col, MSO_SHAPE.OVAL)
            yr = text(slide, cx - cw / 2 + 0.1, 2.0, cw - 0.2, 0.8, it.title, size=22, bold=True,
                      color=s["primary"] if not ctx.dark else s["accent"], font=ctx.tfont,
                      align="center", anchor="bottom")
            tx = text(slide, cx - cw / 2 + 0.15, 3.8, cw - 0.3, 2.8, it.text, size=14,
                      color=s["text"], font=ctx.bfont, align="center")
            anim += [dot, yr, tx]
        else:
            dot = rect(slide, cx - 0.55, line_y - 0.55, 1.1, 1.1, col, MSO_SHAPE.OVAL)
            shadow(dot, blur=10, dist=3)
            ic = place_icon(ctx, slide, it.icon, i, cx - 0.27, line_y - 0.27, 0.54, on_color(col))
            if ic is None:
                dot.text_frame.text = f"{i + 1:02d}"
                _fmt_shape_text(dot, 18, on_color(col), ctx.tfont, bold=True)
            tt = text(slide, cx - cw / 2 + 0.1, 4.0, cw - 0.2, 0.8, it.title, size=17, bold=True,
                      color=s["primary"] if not ctx.dark else s["text"], font=ctx.tfont, align="center")
            tx = text(slide, cx - cw / 2 + 0.15, 4.8, cw - 0.3, 2.0, it.text, size=13,
                      color=s["muted"], font=ctx.bfont, align="center")
            anim += [dot, ic, tt, tx]
    return anim


def l_chart(ctx: Ctx, slide, d: Slide, idx, deck):
    s = ctx.s
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    ch = d.chart
    cats = ch.categories[: len(ch.values)]
    vals = ch.values[: len(cats)]
    anim = [t, bar]
    if not cats:
        return anim + [l_bullets(ctx, slide, d, idx, deck)[2]]
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series(ch.series_name or d.title, vals)
    total = min(content_width(ctx), W - 1.4)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.7), Inches(1.9),
                                Inches(total * 0.66), Inches(5.0), cd)
    chart = gf.chart
    chart.has_legend = False
    chart.font.size = Pt(12)
    chart.font.color.rgb = hex2rgb(s["text"])
    chart.font.name = ctx.bfont
    plot = chart.plots[0]
    plot.gap_width = 70
    plot.has_data_labels = True
    plot.data_labels.font.size = Pt(12)
    plot.data_labels.font.bold = True
    plot.data_labels.font.color.rgb = hex2rgb(s["text"])
    ser = plot.series[0]
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = hex2rgb(s["primary"] if not ctx.dark else s["accent"])
    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = hex2rgb(mix(s["bg"], s["muted"], 0.3))
    va.format.line.fill.background()
    va.tick_labels.font.color.rgb = hex2rgb(s["muted"])
    chart.category_axis.format.line.color.rgb = hex2rgb(s["muted"])
    _ = XL_LEGEND_POSITION
    # gapdal insight karta
    x = 0.7 + total * 0.68
    cw = total * 0.32
    card = rect(slide, x, 2.1, cw, 4.4, s["primary"], MSO_SHAPE.ROUNDED_RECTANGLE)
    round_corners(card, 0.08)
    if ctx.full:
        gradient(card, s["primary"], s["secondary"], 70)
    best = cats[vals.index(max(vals))]
    big = text(slide, x + 0.3, 2.4, cw - 0.6, 1.2, _num(max(vals)), size=44, bold=True,
               color=ctx.on_primary, font=ctx.tfont)
    lb = text(slide, x + 0.3, 3.5, cw - 0.6, 0.6, best, size=16, bold=True,
              color=ctx.on_primary, font=ctx.bfont)
    ins = text(slide, x + 0.3, 4.2, cw - 0.6, 2.2, d.subtitle, size=14,
               color=ctx.on_primary, font=ctx.bfont)
    return anim + [gf, card, big, lb, ins]


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}"


def l_section(ctx: Ctx, slide, d: Slide, idx, deck, full_image=False):
    s = ctx.s
    background(ctx, slide, s["primary"])
    anim = []
    if full_image and ctx.images.get(idx) is not None:
        pic = picture_fill(slide, ctx.images[idx], 0, 0, W, H)
        ov = rect(slide, 0, 0, W, H, "#000000", alpha=0.45)
        anim += [pic, ov]
        fg = "#FFFFFF"
    else:
        pic = image_or_art(ctx, slide, idx, W * 0.55, 0.6, W * 0.45 - 0.6, H - 1.2)
        anim.append(pic)
        fg = ctx.on_primary
        rect(slide, -1.5, H - 2.2, 3.5, 3.5, s["secondary"], MSO_SHAPE.OVAL, alpha=0.5)
    w = W - 1.6 if full_image else W * 0.5
    acc = rect(slide, 0.9, 2.3, 1.2, 0.1, s["accent"])
    t = text(slide, 0.85, 2.5, w, 1.8, d.title, size=40, bold=True, color=fg,
             font=ctx.tfont, anchor="middle")
    st = text(slide, 0.9, 4.35, w - 0.4, 1.4, d.subtitle, size=20, color=fg, font=ctx.bfont)
    return anim + [acc, t, st]


def l_quote(ctx: Ctx, slide, d: Slide, idx, deck):
    s = ctx.s
    background(ctx, slide, s["surface"] if not ctx.dark else s["bg"])
    if not ctx.simple:
        rect(slide, 0, 0, 0.35, H, s["primary"])
        rect(slide, W - 3, -1.5, 4.5, 4.5, s["accent"], MSO_SHAPE.OVAL, alpha=0.25)
    q = text(slide, 1.2, 0.6, 2, 2, "“", size=160, bold=True, color=s["accent"], font="Georgia")
    qt = d.quote or d.title
    t = text(slide, 1.6, 2.2, W - 3.4, 2.8, qt, size=32 if len(qt) < 120 else 26, italic=True,
             color=s["text"], font=ctx.tfont, anchor="middle", spacing=1.15)
    a = text(slide, 1.6, 5.2, W - 3.4, 0.7, "— " + d.quote_author if d.quote_author else "",
             size=18, bold=True, color=s["primary"] if not ctx.dark else s["accent"], font=ctx.bfont)
    return [q, t, a]


def l_conclusion(ctx: Ctx, slide, d: Slide, idx, deck):
    s = ctx.s
    if ctx.simple:
        return l_bullets(ctx, slide, d, idx, deck)
    background(ctx, slide)
    left = rect(slide, 0, 0, W * 0.36, H, s["primary"])
    if ctx.full:
        gradient(left, s["primary"], s["secondary"], 90)
    rect(slide, -1.0, H - 2.2, 3.0, 3.0, s["accent"], MSO_SHAPE.OVAL, alpha=0.3)
    t = text(slide, 0.6, 1.0, W * 0.36 - 1.0, 3.5, d.title, size=36, bold=True,
             color=ctx.on_primary, font=ctx.tfont, anchor="middle")
    items = d.bullets[:5]
    anim = [left, t]
    y = 0.9
    hh = min(1.15, 5.8 / max(1, len(items)))
    for i, it in enumerate(items):
        x = W * 0.36 + 0.6
        chk = rect(slide, x, y + hh / 2 - 0.25, 0.5, 0.5, s["accent"], MSO_SHAPE.OVAL)
        chk.text_frame.text = "✓"
        _fmt_shape_text(chk, 14, on_color(s["accent"]), ctx.bfont, bold=True)
        tx = text(slide, x + 0.75, y, W - x - 1.4, hh, it, size=17 if len(it) < 90 else 15,
                  color=s["text"], font=ctx.bfont, anchor="middle")
        anim += [chk, tx]
        y += hh + 0.12
    return anim


def l_thanks(ctx: Ctx, slide, d: Slide, idx, deck):
    s = ctx.s
    background(ctx, slide, s["primary"])
    bg = rect(slide, 0, 0, W, H, s["primary"])
    gradient(bg, s["primary"], s["secondary"], 135)
    c1 = rect(slide, W - 4.5, -2.0, 6.5, 6.5, s["accent"], MSO_SHAPE.OVAL, alpha=0.25)
    c2 = rect(slide, -1.8, H - 3.2, 4.5, 4.5, "#FFFFFF", MSO_SHAPE.OVAL, alpha=0.1)
    c1.name, c2.name = "!!deco0", "!!deco1"
    fg = on_color(s["primary"])
    t = text(slide, 1.0, 2.2, W - 2, 1.8, d.title, size=60, bold=True, color=fg,
             font=ctx.tfont, align="center", anchor="middle")
    ln = rect(slide, W / 2 - 0.8, 4.15, 1.6, 0.08, s["accent"])
    st = text(slide, 1.5, 4.45, W - 3, 1.2, d.subtitle, size=20, color=fg, font=ctx.bfont, align="center")
    _ = c1, c2
    return [t, ln, st]


LAYOUTS = {
    "title": l_title,
    "agenda": l_agenda,
    "bullets": l_bullets,
    "bullets_image": lambda c, sl, d, i, dk: l_bullets(c, sl, d, i, dk, with_image=True),
    "section": l_section,
    "image_full": lambda c, sl, d, i, dk: l_section(c, sl, d, i, dk, full_image=True),
    "cards": l_cards,
    "two_column": l_two_column,
    "stats": l_stats,
    "process": l_process,
    "timeline": lambda c, sl, d, i, dk: l_process(c, sl, d, i, dk, timeline=True),
    "chart": l_chart,
    "quote": l_quote,
    "conclusion": l_conclusion,
    "thanks": l_thanks,
}

# ============================================================ B wariantlar
# Şol bir görnüşli slaýd gaýtalananda başga dizaýn ulanylýar — prezentasiýa monoton bolmasyn.

def _ttl_color(ctx):
    return ctx.c("primary") if not ctx.dark else ctx.c("text")


def l_bullets_image_b(ctx: Ctx, slide, d: Slide, idx, deck):
    """Surat çepde doly beýiklikde, tekst sagda."""
    s = ctx.s
    background(ctx, slide)
    pic = image_or_art(ctx, slide, idx, 0, 0, W * 0.42, H)
    band = rect(slide, W * 0.42, 0, 0.14, H, s["accent"])
    x0 = W * 0.42 + 0.7
    w = W - x0 - 0.7
    k = None
    if ctx.kicker:
        k = text(slide, x0, 0.65, w, 0.35, ctx.kicker.upper()[:40], size=11, color=s["secondary"]
                 if not ctx.dark else s["accent"], font=ctx.kfont, cs=250)
    t = text(slide, x0, 0.95, w, 1.3, d.title, size=32 if len(d.title) < 40 else 26, bold=True,
             color=_ttl_color(ctx), font=ctx.tfont, anchor="middle")
    items = d.bullets or [f"{it.title}: {it.text}" for it in d.items]
    size = fit(items, 20, int(w * 6.5), 11)
    b = bullets(slide, x0, 2.5, w, 4.4, items, size=size, color=s["text"], font=ctx.bfont,
                bullet_color=s["accent"], bullet_char="▸", gap=12)
    return [pic, band, k, t, b]


def l_cards_b(ctx: Ctx, slide, d: Slide, idx, deck):
    """Ýatyk setirler: uly nomer + ikon + tekst."""
    s = ctx.s
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    items = d.items[:4] or [type("I", (), {"title": b, "text": "", "icon": ""})() for b in d.bullets[:4]]
    n = max(1, len(items))
    total = min(content_width(ctx), W - 1.4)
    rh = min(1.25, (5.1 - 0.2 * (n - 1)) / n)
    anim = [t, bar]
    for i, it in enumerate(items):
        y = 1.95 + i * (rh + 0.2)
        row = rect(slide, 0.7, y, total, rh, ctx.card, MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(row, 0.2)
        shadow(row, blur=10, dist=3, alpha=0.12)
        num = text(slide, 0.9, y, 1.3, rh, f"{i + 1:02d}", size=36, bold=True,
                   color=[s["primary"], s["secondary"], s["accent"]][i % 3], font=ctx.nfont, anchor="middle")
        circ = rect(slide, 2.25, y + rh / 2 - 0.36, 0.72, 0.72, s["primary"], MSO_SHAPE.OVAL)
        ic = place_icon(ctx, slide, getattr(it, "icon", ""), i, 2.41, y + rh / 2 - 0.2, 0.4, ctx.on_primary)
        tt = text(slide, 3.25, y + 0.08, 3.4, rh - 0.16, it.title, size=18, bold=True,
                  color=_ttl_color(ctx), font=ctx.tfont, anchor="middle")
        tx = text(slide, 6.8, y + 0.08, total - 6.3, rh - 0.16, it.text, size=14 if len(it.text) < 110 else 12,
                  color=s["muted"], font=ctx.bfont, anchor="middle")
        anim += [row, num, circ, ic, tt, tx]
    return anim


def l_stats_b(ctx: Ctx, slide, d: Slide, idx, deck):
    """Ak fonda uly sanlar, ikonlar we bölüji çyzyklar."""
    s = ctx.s
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    stats = d.stats[:4]
    n = max(1, len(stats))
    total = min(content_width(ctx), W - 1.4)
    cw = total / n
    anim = [t, bar]
    for i, st in enumerate(stats):
        x = 0.7 + i * cw
        if i:
            anim.append(rect(slide, x, 2.4, 0.03, 3.4, s["muted"], alpha=0.35))
        circ = rect(slide, x + 0.35, 2.35, 0.8, 0.8, mix(ctx.c("bg"), s["primary"], 0.12), MSO_SHAPE.OVAL)
        ic = place_icon(ctx, slide, st.icon, i, x + 0.53, 2.53, 0.44, s["primary"] if not ctx.dark else s["accent"])
        v = text(slide, x + 0.3, 3.3, cw - 0.5, 1.4, st.value, size=54 if len(st.value) < 6 else 40, bold=True,
                 color=[s["primary"], s["secondary"]][i % 2] if not ctx.dark else s["accent"],
                 font=ctx.nfont, anchor="middle")
        lb = text(slide, x + 0.35, 4.75, cw - 0.6, 1.2, st.label, size=15, color=s["muted"], font=ctx.bfont)
        anim += [circ, ic, v, lb]
    return anim


def l_agenda_b(ctx: Ctx, slide, d: Slide, idx, deck):
    """Ýatyk sütünler: ullakan '01 02 03' sanlar."""
    s = ctx.s
    background(ctx, slide)
    t, bar = title(ctx, slide, d.title, x=0.7)
    items = (d.bullets or [i.title for i in d.items])[:5]
    if not items:
        items = [x.title for x in deck.slides if x.layout not in ("title", "agenda", "thanks", "quote")][:5] or ["—"]
    n = len(items)
    total = W - 1.4
    cw = total / n
    anim = [t, bar]
    anim.append(rect(slide, 0.7, 3.85, total, 0.04, s["muted"], alpha=0.4))
    for i, it in enumerate(items):
        x = 0.7 + i * cw
        num = text(slide, x, 2.7, cw - 0.2, 1.1, f"{i + 1:02d}", size=60, bold=True,
                   color=[s["primary"], s["secondary"], s["accent"]][i % 3], font=ctx.nfont)
        dot = rect(slide, x, 3.78, 0.18, 0.18, s["accent"], MSO_SHAPE.OVAL)
        longest = max((len(w) for w in it.split()), default=0)
        fits = (cw - 0.3) * 72 / 18 / 0.62  # 18pt bilen bir setire sygýan harp sany
        size = 18 if longest <= fits and len(it) < 40 else (15 if longest <= fits * 1.2 else 13)
        tx = text(slide, x, 4.15, cw - 0.3, 2.5, it, size=size, bold=True,
                  color=s["text"], font=ctx.tfont)
        anim += [num, dot, tx]
    return anim


def l_section_b(ctx: Ctx, slide, d: Slide, idx, deck):
    """Ullakan bölüm nomeri '01' + sözbaşy + tegelek burçly surat."""
    s = ctx.s
    background(ctx, slide, s["bg"])
    num_txt = f"{ctx.section_no:02d}"
    big = text(slide, 0.5, 0.6, 6.0, 3.2, num_txt, size=190, bold=True,
               color=mix(s["bg"], s["primary"], 0.85), font=ctx.nfont)
    k = text(slide, 0.85, 3.9, 6.0, 0.4, (ctx.kicker or "SECTION").upper()[:40], size=12,
             color=s["secondary"] if not ctx.dark else s["accent"], font=ctx.kfont, cs=300)
    t = text(slide, 0.8, 4.3, 6.4, 1.4, d.title, size=36, bold=True, color=_ttl_color(ctx),
             font=ctx.tfont, anchor="top")
    st = text(slide, 0.85, 5.7, 6.0, 1.2, d.subtitle, size=16, color=s["muted"], font=ctx.lfont)
    frame = rect(slide, 7.5, 0.7, 5.2, 6.1, s["primary"], MSO_SHAPE.ROUNDED_RECTANGLE)
    round_corners(frame, 0.06)
    shadow(frame, blur=20, dist=6, alpha=0.2)
    pic = image_or_art(ctx, slide, idx, 7.7, 0.9, 4.8, 5.7)
    acc = rect(slide, 7.1, 5.6, 1.2, 1.2, s["accent"], MSO_SHAPE.OVAL, alpha=0.85)
    return [big, k, t, st, frame, pic, acc]


def l_process_b(ctx: Ctx, slide, d: Slide, idx, deck):
    """Ok (chevron) görnüşli tapgyrlar."""
    s = ctx.s
    background(ctx, slide)
    motif(ctx, slide)
    t, bar = title(ctx, slide, d.title)
    items = d.items[:5]
    n = max(1, len(items))
    total = min(content_width(ctx), W - 1.4)
    cw = total / n
    anim = [t, bar]
    for i, it in enumerate(items):
        x = 0.7 + i * cw
        col = mix(s["primary"], s["secondary"], i / max(1, n - 1))
        chev = rect(slide, x, 2.2, cw + 0.15, 1.1, col, MSO_SHAPE.CHEVRON if i else MSO_SHAPE.PENTAGON)
        ic = place_icon(ctx, slide, it.icon, i, x + cw / 2 - 0.22, 2.53, 0.44, on_color(col))
        num = text(slide, x + 0.1, 3.5, cw - 0.2, 0.6, f"{i + 1:02d}", size=26, bold=True,
                   color=col if not ctx.dark else s["accent"], font=ctx.nfont)
        tt = text(slide, x + 0.1, 4.1, cw - 0.25, 0.7, it.title, size=16, bold=True,
                  color=_ttl_color(ctx), font=ctx.tfont)
        tx = text(slide, x + 0.1, 4.8, cw - 0.3, 2.0, it.text, size=13, color=s["muted"], font=ctx.bfont)
        anim += [chev, ic, num, tt, tx]
    return anim


def l_conclusion_b(ctx: Ctx, slide, d: Slide, idx, deck):
    """2x2 kartoçkalar: barlag ikonlary bilen."""
    s = ctx.s
    background(ctx, slide, s["surface"] if not ctx.dark else s["bg"])
    t, bar = title(ctx, slide, d.title)
    items = d.bullets[:4] or [it.title for it in d.items[:4]]
    anim = [t, bar]
    cw, ch = (W - 1.4 - 0.4) / 2, 2.15
    for i, it in enumerate(items):
        x = 0.7 + (i % 2) * (cw + 0.4)
        y = 1.95 + (i // 2) * (ch + 0.3)
        card = rect(slide, x, y, cw, ch, s["bg"] if not ctx.dark else s["surface"], MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(card, 0.08)
        shadow(card)
        strip = rect(slide, x, y + 0.3, 0.1, ch - 0.6, [s["primary"], s["secondary"], s["accent"]][i % 3])
        ic = place_icon(ctx, slide, "check", i, x + 0.4, y + 0.35, 0.5, s["accent"] if ctx.dark else s["primary"])
        tx = text(slide, x + 1.15, y + 0.25, cw - 1.45, ch - 0.5, it, size=16 if len(it) < 110 else 14,
                  color=s["text"], font=ctx.bfont, anchor="middle")
        anim += [card, strip, ic, tx]
    return anim


def l_two_column_b(ctx: Ctx, slide, d: Slide, idx, deck):
    """Ýarym ekran: çep tarap reňkli, sag tarap ak."""
    s = ctx.s
    background(ctx, slide)
    left = rect(slide, 0, 0, W / 2, H, s["primary"])
    gradient(left, s["primary"], mix(s["primary"], s["secondary"], 0.5), 90)
    fg = on_color(s["primary"])
    k = text(slide, 0.7, 0.45, W / 2 - 1.2, 0.35, (ctx.kicker or "").upper()[:40], size=11, color=fg,
             font=ctx.kfont, cs=250)
    t = text(slide, 0.7, 0.75, W / 2 - 1.2, 1.1, d.title, size=26 if len(d.title) < 34 else 21,
             bold=True, color=fg, font=ctx.tfont, anchor="middle")
    anim = [left, k, t]
    size = min(fit(d.left_bullets, 18, 38, 9, 12), fit(d.right_bullets, 18, 38, 9, 12))
    for i, (ht, bl) in enumerate([(d.left_title, d.left_bullets), (d.right_title, d.right_bullets)]):
        x = 0.7 + i * (W / 2)
        col = fg if i == 0 else _ttl_color(ctx)
        h = text(slide, x, 2.0, W / 2 - 1.4, 0.7, ht, size=22, bold=True, color=col, font=ctx.tfont)
        ln = rect(slide, x, 2.75, 1.0, 0.06, s["accent"])
        b = bullets(slide, x, 3.05, W / 2 - 1.4, 3.9, bl, size=size, color=fg if i == 0 else s["text"],
                    font=ctx.bfont, bullet_color=s["accent"], gap=10)
        anim += [h, ln, b]
    return anim


VARIANTS = {
    "bullets_image": ["bullets_image", l_bullets_image_b],
    "cards": ["cards", l_cards_b],
    "stats": ["stats", l_stats_b],
    "agenda": ["agenda", l_agenda_b],
    "section": [l_section_b, "section"],
    "process": ["process", l_process_b],
    "conclusion": ["conclusion", l_conclusion_b],
    "two_column": ["two_column", l_two_column_b],
}


def pick_layout(layout: str, occurrence: int, seed: int):
    """Görnüşiň näçinji gezek gaýtalanýandygyna görä wariant saýlamak."""
    opts = VARIANTS.get(layout)
    if not opts:
        return LAYOUTS.get(layout, l_bullets)
    v = opts[(occurrence + seed) % len(opts)]
    return LAYOUTS[v] if isinstance(v, str) else v


IMAGE_LAYOUTS = {"title", "bullets_image", "section", "image_full"}


def build(deck: Deck, style: dict, level: str, images: dict[int, io.BytesIO], path: str):
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]
    ctx = Ctx(style, level, images)
    ctx.total = len(deck.slides)
    no_page = {"title", "section", "image_full", "thanks", "quote"}
    plain = no_page | {"conclusion", "agenda"}
    seed = sum(map(ord, deck.title or "")) % 2  # her prezentasiýa başgaça başlaýar
    occ: dict[str, int] = {}
    ctx.section_no = 0
    content_n = 0
    for i, d in enumerate(deck.slides):
        slide = prs.slides.add_slide(blank)
        k = occ.get(d.layout, 0)
        occ[d.layout] = k + 1
        fn = pick_layout(d.layout, k, seed)
        if d.layout in ("section", "image_full"):
            ctx.section_no += 1
        ctx.kicker = d.kicker.strip() if d.kicker else ""
        # her 3-nji mazmun slaýdy reňkli fonda, kartoçkalar ak
        ctx.tint = d.layout not in plain and content_n % 3 == 1
        ctx.card = ctx.c("bg") if ctx.tint else ctx.c("surface")
        if d.layout not in plain:
            content_n += 1
        try:
            anim = fn(ctx, slide, d, i, deck) or []
        except Exception:  # noqa: BLE001 - bir slaýd sebäpli ähli prezentasiýa ýitmesin
            log.exception("layout %s failed, using bullets", d.layout)
            for shp in list(slide.shapes):
                shp._element.getparent().remove(shp._element)
            if not d.bullets:
                d.bullets = [b for b in [d.subtitle, d.quote, *[f"{x.title}: {x.text}" for x in d.items]] if b] or ["—"]
            anim = l_bullets(ctx, slide, d, i, deck) or []
        if d.layout not in no_page:
            page_no(ctx, slide, i + 1)
        if level == "medium":
            add_transition(slide, MEDIUM_TRANSITIONS[i % len(MEDIUM_TRANSITIONS)], "med")
            notes(slide, d.notes)
        elif level == "full":
            add_transition(slide, FULL_TRANSITIONS[i % len(FULL_TRANSITIONS)], "slow")
            fam = FAMILIES[i % len(FAMILIES)]
            steps = [(shp, _effect_for(shp, n, d.layout, fam)) for n, shp in enumerate(anim) if shp is not None]
            # doly ekran suratlar we sözbaşy suratlary ýuwaşlyk bilen ýakynlaşýar (Ken Burns)
            from pptx.enum.shapes import MSO_SHAPE_TYPE
            for shp in anim:
                if (shp is not None and shp.shape_type == MSO_SHAPE_TYPE.PICTURE
                        and d.layout in ("image_full", "title")):
                    steps.append((shp, "kenburns"))
            add_animations(slide, steps, step_ms=170 if len(steps) > 10 else 300)
            notes(slide, d.notes)
    prs.core_properties.title = deck.title
    prs.core_properties.author = "Shiri-Presentation-BOT"
    prs.save(path)
    return path
