"""python-pptx üçin kömekçi funksiýalar."""
from __future__ import annotations

import io

from lxml import etree
from PIL import Image
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt


def hex2rgb(h: str) -> RGBColor:
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def luminance(h: str) -> float:
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def on_color(h: str) -> str:
    """Berlen fonda okalýan tekst reňki."""
    return "#FFFFFF" if luminance(h) < 0.6 else "#111111"


def mix(h1: str, h2: str, t: float) -> str:
    a, b = h1.lstrip("#"), h2.lstrip("#")
    c = [round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(c)


def set_alpha(shape, alpha: float):
    """Doldurma reňkiniň aç-açyklygy (0..1)."""
    sf = shape.fill._xPr.find(qn("a:solidFill"))
    if sf is None:
        return
    clr = sf[0]
    for a in clr.findall(qn("a:alpha")):
        clr.remove(a)
    el = etree.SubElement(clr, qn("a:alpha"))
    el.set("val", str(int(alpha * 100000)))


def rect(slide, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE, alpha=None, line=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if color:
        s.fill.solid()
        s.fill.fore_color.rgb = hex2rgb(color)
        if alpha is not None:
            set_alpha(s, alpha)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = hex2rgb(line[0])
        s.line.width = Pt(line[1])
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    return s


def gradient(shape, c1: str, c2: str, angle: float = 45):
    shape.fill.gradient()
    shape.fill.gradient_angle = angle
    stops = shape.fill.gradient_stops
    stops[0].color.rgb = hex2rgb(c1)
    stops[0].position = 0
    stops[1].color.rgb = hex2rgb(c2)
    stops[1].position = 1.0


def round_corners(shape, val=0.12):
    try:
        shape.adjustments[0] = val
    except (IndexError, ValueError):
        pass


def shadow(shape, blur=14, dist=4, alpha=0.16):
    """Kartoçkalar üçin ýumşak kölege."""
    spPr = shape._element.spPr
    eff = spPr.find(qn("a:effectLst"))
    if eff is None:
        eff = etree.SubElement(spPr, qn("a:effectLst"))
    for old in list(eff):
        eff.remove(old)
    sh = etree.SubElement(eff, qn("a:outerShdw"))
    sh.set("blurRad", str(int(Pt(blur))))
    sh.set("dist", str(int(Pt(dist))))
    sh.set("dir", "5400000")
    sh.set("algn", "t")
    sh.set("rotWithShape", "0")
    clr = etree.SubElement(sh, qn("a:srgbClr"))
    clr.set("val", "000000")
    a = etree.SubElement(clr, qn("a:alpha"))
    a.set("val", str(int(alpha * 100000)))
    return shape


def text(slide, x, y, w, h, txt, size=18, color="#000000", bold=False, font="Calibri",
         align="left", anchor="top", italic=False, spacing=None, cs=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE,
                          "bottom": MSO_ANCHOR.BOTTOM}[anchor]
    lines = str(txt).split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER,
                       "right": PP_ALIGN.RIGHT}[align]
        if spacing:
            p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        f = r.font
        f.size = Pt(size)
        f.bold = bold
        f.italic = italic
        f.name = font
        f.color.rgb = hex2rgb(color)
        if cs:  # harplaryň arasy (1/100 pt), mysal: 300 = giň ýazgy
            r._r.get_or_add_rPr().set("spc", str(cs))
    return tb


def bullets(slide, x, y, w, h, items, size=18, color="#000000", font="Calibri",
            bullet_color="#000000", bullet_char="●", gap=10):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = 1.1
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(Inches(0.38)))
        pPr.set("indent", str(-Inches(0.38)))
        buClr = etree.SubElement(pPr, qn("a:buClr"))
        srgb = etree.SubElement(buClr, qn("a:srgbClr"))
        srgb.set("val", bullet_color.lstrip("#"))
        buSz = etree.SubElement(pPr, qn("a:buSzPct"))
        buSz.set("val", "80000")
        buFont = etree.SubElement(pPr, qn("a:buFont"))
        buFont.set("typeface", "Arial")
        bu = etree.SubElement(pPr, qn("a:buChar"))
        bu.set("char", bullet_char)
        r = p.add_run()
        r.text = item
        r.font.size = Pt(size)
        r.font.name = font
        r.font.color.rgb = hex2rgb(color)
    return tb


def fit(items: list[str], base: int, per_line_chars: int, max_lines: int, minimum=12) -> int:
    """Tekstiň mukdaryna görä şrift ölçegini kiçeltmek."""
    size = base
    while size > minimum:
        cpl = per_line_chars * base / size
        lines = sum(max(1, -(-len(t) // int(cpl))) for t in items) + len(items) * 0.35
        if lines <= max_lines * base / size:
            break
        size -= 1
    return size


def picture_fill(slide, stream: io.BytesIO, x, y, w, h):
    """Suraty berlen meýdana 'cover' görnüşde ýerleşdirmek (kesip)."""
    stream.seek(0)
    im = Image.open(stream)
    iw, ih = im.size
    stream.seek(0)
    pic = slide.shapes.add_picture(stream, Inches(x), Inches(y), Inches(w), Inches(h))
    box_r = w / h
    img_r = iw / ih
    if img_r > box_r:  # surat giňräk -> gapdallaryny kes
        crop = (1 - box_r / img_r) / 2
        pic.crop_left = pic.crop_right = crop
    else:
        crop = (1 - img_r / box_r) / 2
        pic.crop_top = pic.crop_bottom = crop
    return pic


def notes(slide, txt: str):
    if txt:
        slide.notes_slide.notes_text_frame.text = txt


__all__ = [
    "Emu", "Inches", "Pt", "MSO_SHAPE", "hex2rgb", "luminance", "on_color", "mix",
    "set_alpha", "rect", "gradient", "round_corners", "text", "bullets", "fit", "shadow",
    "picture_fill", "notes",
]
