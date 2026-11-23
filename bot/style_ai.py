"""Suratdan (Pinterest we ş.m.) prezentasiýa stilini awtomatik çykarmak."""
from __future__ import annotations

import base64
import colorsys
import io
import logging
import re
from typing import Literal

import anthropic
from PIL import Image
from pydantic import BaseModel

from .ai import _get_client, model_chain
from .builder.helpers import luminance, mix
from .default_styles import FONTS

log = logging.getLogger(__name__)

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class StyleSpec(BaseModel):
    name: str
    bg: str
    primary: str
    secondary: str
    accent: str
    text: str
    motif: Literal["wave", "circles", "blocks", "diagonal", "minimal", "frame"]
    font: Literal["Arial", "Calibri", "Georgia", "Segoe UI", "Verdana", "Times New Roman"]


PROMPT = (
    "This image shows presentation slide designs. Extract a reusable slide style from it.\n"
    "- name: short catchy English style name (2-3 words) describing the look\n"
    "- bg: main slide background color\n"
    "- primary: the dominant brand color used for big blocks/headings (must contrast with bg)\n"
    "- secondary: second brand color\n"
    "- accent: highlight color used for small details\n"
    "- text: body text color (must be readable on bg)\n"
    "- motif: decoration that best matches: wave (big rounded/organic shapes), circles (round shapes), "
    "blocks (rectangular bars/panels), diagonal (angled cuts), minimal (very clean), frame (thin border, luxury)\n"
    "- font: closest headline font: sans-serif modern → 'Segoe UI', serif/elegant → 'Georgia'\n"
    "All colors as #RRGGBB hex."
)


def _prepare(data: bytes) -> tuple[str, Image.Image]:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((1568, 1568))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return base64.standard_b64encode(buf.getvalue()).decode(), im


def _palette_fallback(im: Image.Image) -> dict:
    """AI bolmasa: suratdaky esasy reňkleri hasaplap stil düzmek."""
    small = im.copy()
    small.thumbnail((240, 240))
    q = small.quantize(colors=24, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    cols = []
    for cnt, idx in q.getcolors():
        r, g, b = pal[idx * 3: idx * 3 + 3]
        _, l, _ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        chroma = (max(r, g, b) - min(r, g, b)) / 255
        cols.append({"hex": "#%02X%02X%02X" % (r, g, b), "n": cnt, "l": l, "c": chroma})
    bg = max(cols, key=lambda c: c["n"])
    dark_bg = bg["l"] < 0.4
    colorful = [c for c in cols if c["c"] > 0.18 and 0.12 < c["l"] < 0.9]
    if not colorful:
        colorful = sorted(cols, key=lambda c: -c["n"])[1:4] or [bg]
    by_weight = sorted(colorful, key=lambda c: c["n"] * (0.5 + c["c"]), reverse=True)
    # esasy: fondan ep-esli tapawutly, köp ulanylýan reňk
    primary = next((c for c in by_weight if abs(c["l"] - bg["l"]) > 0.35), by_weight[0])
    secondary = next((c for c in by_weight if c is not primary and abs(c["l"] - primary["l"]) > 0.08),
                     primary)
    light = [c for c in colorful if c["l"] > primary["l"] + 0.15]
    accent = (max(light, key=lambda c: c["n"] * c["c"])["hex"] if light
              else mix(primary["hex"], "#FFFFFF", 0.55))
    text_cands = [c for c in cols if (c["l"] < 0.25 if not dark_bg else c["l"] > 0.8)]
    text = max(text_cands, key=lambda c: c["n"] * (1.2 - c["c"]))["hex"] if text_cands else (
        "#14181F" if not dark_bg else "#F4F6FA")
    return {
        "name": "Custom Style",
        "bg": bg["hex"], "primary": primary["hex"], "secondary": secondary["hex"],
        "accent": accent, "text": text, "motif": "circles", "font": "Segoe UI",
    }


async def _ai_spec(b64: str) -> dict | None:
    client = _get_client()
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
        {"type": "text", "text": PROMPT},
    ]
    for model in model_chain("simple"):
        try:
            try:
                resp = await client.beta.messages.parse(
                    model=model, max_tokens=4000, output_format=StyleSpec,
                    messages=[{"role": "user", "content": content}])
                if resp.parsed_output:
                    return resp.parsed_output.model_dump()
            except anthropic.BadRequestError:
                pass
            # ýönekeý JSON tertibi (structured outputs goldanmasa)
            resp = await client.beta.messages.create(
                model=model, max_tokens=4000,
                messages=[{"role": "user", "content": content + [{
                    "type": "text", "text": "Answer ONLY with a JSON object with keys: "
                    + ", ".join(StyleSpec.model_fields)}]}])
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            m = re.search(r"\{.*\}", text, re.S)
            if m:
                return StyleSpec.model_validate_json(m.group(0)).model_dump()
        except anthropic.AuthenticationError:
            return None
        except Exception:  # noqa: BLE001 - indiki modeli synanyş
            log.warning("style extraction failed with %s", model, exc_info=True)
    return None


def _fix(spec: dict) -> dict:
    """Reňkleri barlamak we okalmagyny üpjün etmek."""
    for k in ("bg", "primary", "secondary", "accent", "text"):
        v = str(spec.get(k, "")).strip()
        if not v.startswith("#"):
            v = "#" + v
        spec[k] = v.upper() if HEX_RE.match(v) else ("#FFFFFF" if k == "bg" else "#333333")
    bg_l, tx_l = luminance(spec["bg"]), luminance(spec["text"])
    if abs(bg_l - tx_l) < 0.45:  # tekst fonda okalmaýar
        spec["text"] = "#14181F" if bg_l > 0.5 else "#F4F6FA"
    if abs(luminance(spec["primary"]) - bg_l) < 0.2:  # esasy reňk fona gaty ýakyn
        spec["primary"], spec["secondary"] = spec["secondary"], spec["primary"]
    if spec.get("font") not in FONTS:
        spec["font"] = "Segoe UI"
    spec["body_font"] = "Calibri" if spec["font"] not in ("Arial", "Verdana") else spec["font"]
    spec["surface"] = mix(spec["bg"], spec["primary"], 0.08)
    spec["muted"] = mix(spec["text"], spec["bg"], 0.4)
    spec["name"] = (spec.get("name") or "Custom Style").strip()[:40]
    return spec


async def style_from_image(data: bytes) -> tuple[dict, bool]:
    """(stil, AI ulanyldymy)"""
    b64, im = _prepare(data)
    spec = await _ai_spec(b64)
    used_ai = spec is not None
    if spec is None:
        spec = _palette_fallback(im)
    return _fix(spec), used_ai

