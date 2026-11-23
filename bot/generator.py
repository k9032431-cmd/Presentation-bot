"""AI + suratlar + pptx: ähli tapgyrlary birleşdirýär."""
from __future__ import annotations

import asyncio
import re
import time

from .ai import generate_deck
from .builder.deck import IMAGE_LAYOUTS, build
from .config import OUT_DIR
from .images import fetch_images

# Bir wagtda iň köp 3 prezentasiýa döredilýär
_sem = asyncio.Semaphore(3)


def _safe(name: str) -> str:
    name = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip()
    return re.sub(r"\s+", "_", name)[:50] or "prezentasiya"


async def make_presentation(topic: str, level: str, lang: str, style: dict, uid: int,
                            n_slides: int | None = None) -> tuple[str, str]:
    async with _sem:
        deck = await generate_deck(topic, level, lang, n_slides)
        images = {}
        if level != "simple":
            queries = {i: s.image_query for i, s in enumerate(deck.slides)
                       if s.layout in IMAGE_LAYOUTS and s.image_query}
            images = await fetch_images(queries)
        path = OUT_DIR / f"{uid}_{int(time.time())}_{_safe(deck.title)}.pptx"
        await asyncio.to_thread(build, deck, style, level, images, str(path))
        return str(path), deck.title
