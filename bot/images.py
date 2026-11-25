"""Slaýdlar üçin suratlar.

Tertip boýunça synanyşylýar:
  1. Pexels   (PEXELS_API_KEY bar bolsa)
  2. Pixabay  (PIXABAY_API_KEY bar bolsa — pixabay.com/api/docs, mugt, dessine berilýär)
  3. Openverse (açar gerek däl: Wikimedia, Flickr we ş.m. açyk ygtyýarnamaly suratlar)
Hiç biri tapmasa, slaýdda geometrik bezeg çyzylýar.
"""
from __future__ import annotations

import asyncio
import io
import logging

import aiohttp
from PIL import Image

from .config import PEXELS_API_KEY, PIXABAY_API_KEY, USE_OPENVERSE

log = logging.getLogger(__name__)

UA = {"User-Agent": "ShiriPresentationBot/1.0 (presentation generator)"}
T_SEARCH = aiohttp.ClientTimeout(total=15)
T_DOWNLOAD = aiohttp.ClientTimeout(total=30)
MAX_BYTES = 15 * 1024 * 1024


async def _get_json(s: aiohttp.ClientSession, url: str, **kw):
    async with s.get(url, timeout=T_SEARCH, **kw) as r:
        if r.status != 200:
            return None
        return await r.json(content_type=None)


async def _pexels(s, q):
    if not PEXELS_API_KEY:
        return []
    d = await _get_json(s, "https://api.pexels.com/v1/search",
                        params={"query": q, "per_page": 3, "orientation": "landscape"},
                        headers={"Authorization": PEXELS_API_KEY})
    return [p["src"]["large2x"] for p in (d or {}).get("photos", [])]


async def _pixabay(s, q):
    if not PIXABAY_API_KEY:
        return []
    d = await _get_json(s, "https://pixabay.com/api/",
                        params={"key": PIXABAY_API_KEY, "q": q, "image_type": "photo",
                                "orientation": "horizontal", "per_page": 3, "safesearch": "true"})
    return [h.get("largeImageURL") or h.get("webformatURL") for h in (d or {}).get("hits", [])]


async def _openverse(s, q):
    if not USE_OPENVERSE:
        return []
    d = await _get_json(s, "https://api.openverse.org/v1/images/", headers=UA,
                        params={"q": q, "page_size": 5, "license_type": "commercial",
                                "category": "photograph", "aspect_ratio": "wide", "mature": "false"})
    out = []
    for r in (d or {}).get("results", []):
        w = r.get("width") or 0
        if w and w < 900:  # gaty kiçi suratlar slaýdda bulaşyk görünýär
            continue
        # Openverse-iň öz serwerinden (1024px) — Flickr/Wikimedia göni ýüklemäni çäklendirýär
        out.append(f"https://api.openverse.org/v1/images/{r['id']}/thumb/?full_size=true")
        if r.get("url"):
            out.append(r["url"])
    return out


def _normalize(data: bytes) -> io.BytesIO | None:
    """Suraty barla, 1920px-e çenli kiçelt, JPEG et (pptx kiçi bolsun)."""
    try:
        im = Image.open(io.BytesIO(data))
        im = im.convert("RGB")
    except Exception:  # noqa: BLE001
        return None
    im.thumbnail((1920, 1920))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    buf.seek(0)
    return buf


async def _download(s, url: str) -> io.BytesIO | None:
    try:
        async with s.get(url, timeout=T_DOWNLOAD, headers=UA) as r:
            if r.status != 200:
                return None
            if int(r.headers.get("Content-Length") or 0) > MAX_BYTES:
                return None
            buf = bytearray()
            async for chunk in r.content.iter_chunked(65536):
                buf += chunk
                if len(buf) > MAX_BYTES:
                    return None
            data = bytes(buf)
        return await asyncio.to_thread(_normalize, data)
    except Exception:  # noqa: BLE001
        return None


async def fetch_image(s: aiohttp.ClientSession, query: str) -> io.BytesIO | None:
    if not query:
        return None
    for provider in (_pexels, _pixabay, _openverse):
        try:
            urls = await provider(s, query)
        except Exception:  # noqa: BLE001 - bir hyzmat işlemese, beýlekisine geç
            log.warning("%s search failed for %r", provider.__name__, query)
            continue
        for url in urls[:4]:
            img = await _download(s, url)
            if img is not None:
                return img
    return None


async def fetch_images(queries: dict[int, str]) -> dict[int, io.BytesIO]:
    """{slide_index: query} -> {slide_index: BytesIO}"""
    if not queries:
        return {}
    async with aiohttp.ClientSession(trust_env=True) as s:
        keys = list(queries)
        res = await asyncio.gather(*(fetch_image(s, queries[k]) for k in keys))
    return {k: b for k, b in zip(keys, res) if b is not None}
