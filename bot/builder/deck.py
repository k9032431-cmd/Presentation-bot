"""Prezentasiýany gurmak: 3 dereje (simple / medium / full)."""
from __future__ import annotations

import io

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Inches, Pt

from ..ai import Deck, Slide
from .anim import add_entrance, add_transition
from .helpers import (MSO_SHAPE, bullets, fit, gradient, hex2rgb, mix, notes, on_color,
                      picture_fill, rect, round_corners, text)

W, H = 13.333, 7.5

TRANSITION_CYCLE = ["fade", "push", "wipe", "cover", "split"]


class Ctx:
    def __init__(self, style: dict, level: str, images: dict[int, io.BytesIO]):
        self.s = style
        self.level = level
        self.images = images
        self.full = level == "full"
        self.medium = level == "medium"
        self.simple = level == "simple"
        self.dark = _lum(style["bg"]) < 0.4
        self.tfont = style.get("font", "Calibri")
        self.bfont = style.get("body_font", "Calibri")
        self.on_primary = on_color(style["primary"])
        self.total = 0

    def c(self, key):
        return self.s[key]


def _lum(h):
    from .helpers import luminance
    return luminance(h)


# ----------------------------------------------------------------- decorations
def background(ctx: Ctx, slide, color=None):
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = hex2rgb(color or ctx.c("bg"))


def motif(ctx: Ctx, slide, strong=False):
    """Stiliň bezeg elementleri (ýönekeý derejede diňe inçe zolak)."""
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
        card = rect(slide, x + rh + 0.15, y, cw - rh - 0.15, rh, s["surface"], MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(card, 0.15)
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
        card = rect(slide, x, y, cw, 4.5, s["surface"], MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(card, 0.08)
        top = rect(slide, x, y, cw, 0.12, [s["primary"], s["secondary"], s["accent"]][i % 3])
        circ = rect(slide, x + 0.35, y + 0.45, 0.85, 0.85, s["primary"], MSO_SHAPE.OVAL)
        circ.text_frame.text = str(i + 1)
        _fmt_shape_text(circ, 20, ctx.on_primary, ctx.tfont, bold=True)
        tt = text(slide, x + 0.3, y + 1.5, cw - 0.6, 0.9, it.title, size=19, bold=True,
                  color=s["primary"] if not ctx.dark else s["text"], font=ctx.tfont)
        tx = text(slide, x + 0.3, y + 2.4, cw - 0.6, 2.0, it.text, size=body, color=s["muted"],
                  font=ctx.bfont, spacing=1.1)
        anim += [card, top, circ, tt, tx]
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
        box = rect(slide, x, 2.85, cw, 3.9, s["surface"], MSO_SHAPE.ROUNDED_RECTANGLE)
        round_corners(box, 0.06)
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
        oc = on_color(col)
        v = text(slide, x + 0.2, 2.6, cw - 0.4, 1.4, st.value, size=48 if len(st.value) < 6 else 38,
                 bold=True, color=oc, font=ctx.tfont, align="center", anchor="middle")
        ln = rect(slide, x + cw / 2 - 0.4, 4.1, 0.8, 0.05, s["accent"] if col != s["accent"] else oc)
        lb = text(slide, x + 0.25, 4.3, cw - 0.5, 1.3, st.label, size=15, color=oc,
                  font=ctx.bfont, align="center")
        anim += [card, v, ln, lb]
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
            dot.text_frame.text = f"{i + 1:02d}"
            _fmt_shape_text(dot, 18, on_color(col), ctx.tfont, bold=True)
            tt = text(slide, cx - cw / 2 + 0.1, 4.0, cw - 0.2, 0.8, it.title, size=17, bold=True,
                      color=s["primary"] if not ctx.dark else s["text"], font=ctx.tfont, align="center")
            tx = text(slide, cx - cw / 2 + 0.15, 4.8, cw - 0.3, 2.0, it.text, size=13,
                      color=s["muted"], font=ctx.bfont, align="center")
            anim += [dot, tt, tx]
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

IMAGE_LAYOUTS = {"title", "bullets_image", "section", "image_full"}


def build(deck: Deck, style: dict, level: str, images: dict[int, io.BytesIO], path: str):
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]
    ctx = Ctx(style, level, images)
    ctx.total = len(deck.slides)
    no_page = {"title", "section", "image_full", "thanks", "quote"}
    for i, d in enumerate(deck.slides):
        slide = prs.slides.add_slide(blank)
        fn = LAYOUTS.get(d.layout, l_bullets)
        anim = fn(ctx, slide, d, i, deck) or []
        if d.layout not in no_page:
            page_no(ctx, slide, i + 1)
        if ctx.medium:
            add_transition(slide, "fade")
        elif ctx.full:
            add_transition(slide, TRANSITION_CYCLE[i % len(TRANSITION_CYCLE)], "slow" if i == 0 else "med")
            effects = ["fade", "wipe_up", "zoom"] if d.layout in ("cards", "stats", "process", "timeline") else ["fade"]
            add_entrance(slide, anim, effect=effects, step_ms=250 if len(anim) > 8 else 400)
            notes(slide, d.notes)
    prs.core_properties.title = deck.title
    prs.core_properties.author = "Shiri-Presentation-BOT"
    prs.save(path)
    return path
