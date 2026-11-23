"""Pexels-den surat almak (islege görä: PEXELS_API_KEY bar bolsa)."""
from __future__ import annotations

import io
import logging

import aiohttp

from .config import PEXELS_API_KEY

log = logging.getLogger(__name__)


async def fetch_image(session: aiohttp.ClientSession, query: str, landscape=True) -> bytes | None:
    if not PEXELS_API_KEY or not query:
        return None
    try:
        async with session.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 1,
                    "orientation": "landscape" if landscape else "portrait"},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as r:
            if r.status != 200:
                return None
            data = await r.json()
        photos = data.get("photos") or []
        if not photos:
            return None
        url = photos[0]["src"]["large"]
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status != 200:
                return None
            return await r.read()
    except Exception:  # noqa: BLE001 - surat bolmasa hem prezentasiýa döredilýär
        log.warning("image fetch failed for %r", query)
        return None


async def fetch_images(queries: dict[int, str]) -> dict[int, io.BytesIO]:
    """{slide_index: query} -> {slide_index: BytesIO}"""
    out: dict[int, io.BytesIO] = {}
    if not PEXELS_API_KEY:
        return out
    import asyncio

    async with aiohttp.ClientSession() as s:
        keys = list(queries)
        res = await asyncio.gather(*(fetch_image(s, queries[k]) for k in keys))
    for k, b in zip(keys, res):
        if b:
            out[k] = io.BytesIO(b)
    return out
