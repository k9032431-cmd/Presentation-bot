"""Claude bilen prezentasiýanyň mazmunyny döretmek."""
from __future__ import annotations

import logging

import anthropic
from pydantic import BaseModel

from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

log = logging.getLogger(__name__)

# ---- Her derejäniň slaýd meýilnamasy ----
PLANS = {
    "simple": ["title", "bullets", "bullets", "bullets", "bullets", "conclusion"],
    "medium": [
        "title", "agenda", "bullets_image", "cards", "two_column",
        "stats", "bullets_image", "quote", "conclusion", "thanks",
    ],
    "full": [
        "title", "agenda", "section", "bullets_image", "cards", "stats", "process",
        "chart", "two_column", "image_full", "timeline", "quote", "conclusion", "thanks",
    ],
}

LAYOUT_HELP = {
    "title": "cover slide: title + subtitle, image_query",
    "agenda": "table of contents: 4-6 short bullets (section names)",
    "bullets": "title + 3-5 bullets",
    "bullets_image": "title + 3-5 bullets + image_query",
    "section": "section divider: title + subtitle (one sentence) + image_query",
    "cards": "title + exactly 3 items (title + 1-2 sentence text)",
    "two_column": "title + left_title/left_bullets and right_title/right_bullets (comparison, 3-4 bullets each)",
    "stats": "title + 3 or 4 stats (value like '85%', '2.4M', '120+' and a short label); realistic, well-known figures",
    "process": "title + 4 items as sequential steps (title + short text)",
    "timeline": "title + 4 or 5 items: item.title is a year/stage, item.text is a short description",
    "chart": "title + subtitle (one-line insight) + chart (4-6 categories, numeric values, series_name)",
    "image_full": "full-bleed photo with overlay: title + subtitle (one strong sentence) + image_query",
    "quote": "quote + quote_author (real, relevant quote)",
    "conclusion": "title + 3-5 key takeaway bullets",
    "thanks": "closing slide: title (e.g. 'Thank you' in the target language) + subtitle (short call to action/questions)",
}

DEPTH = {
    "simple": "Keep it short and clear: bullets are 4-9 words each.",
    "medium": "Bullets are informative, 8-14 words each. Use concrete facts.",
    "full": "Professional, rich content: bullets are 10-18 words each with concrete facts, "
            "numbers and examples. Write speaker notes (2-4 sentences) for every slide.",
}

LANGS = {"tk": "Turkmen (Latin alphabet)", "ru": "Russian", "en": "English"}


class Item(BaseModel):
    title: str
    text: str


class Stat(BaseModel):
    value: str
    label: str


class Chart(BaseModel):
    series_name: str
    categories: list[str]
    values: list[float]


class Slide(BaseModel):
    layout: str
    title: str
    subtitle: str
    bullets: list[str]
    items: list[Item]
    stats: list[Stat]
    left_title: str
    left_bullets: list[str]
    right_title: str
    right_bullets: list[str]
    quote: str
    quote_author: str
    chart: Chart
    image_query: str
    notes: str


class Deck(BaseModel):
    title: str
    subtitle: str
    slides: list[Slide]


SYSTEM = (
    "You are a world-class presentation writer. You write the content for slide decks: "
    "accurate, well structured, engaging and free of filler. Every slide must have a clear title. "
    "Fields that the slide's layout does not use must be empty strings / empty lists "
    "(chart: empty series_name and empty lists). image_query is always in English, "
    "2-4 words, describing a professional stock photo (leave empty if layout has no image)."
)


def _prompt(topic: str, level: str, lang: str) -> str:
    plan = PLANS[level]
    lines = [f"{i + 1}. {lay} — {LAYOUT_HELP[lay]}" for i, lay in enumerate(plan)]
    return (
        f"Create a presentation about:\n<topic>\n{topic}\n</topic>\n\n"
        f"Language of all slide text: {LANGS.get(lang, 'English')}.\n"
        f"{DEPTH[level]}\n\n"
        f"Produce exactly {len(plan)} slides in this order, using these layouts "
        f"(set each slide's `layout` field to the given name):\n" + "\n".join(lines)
    )


_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY or None, timeout=300)
    return _client


class AIError(Exception):
    pass


async def generate_deck(topic: str, level: str, lang: str) -> Deck:
    client = _get_client()
    extra = {}
    # Ätiýaçlyk model (fallback) diňe şu modellerde bar; Haiku-da ýok
    if CLAUDE_MODEL in ("claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-2", "claude-opus-5"):
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    try:
        resp = await client.beta.messages.parse(
            model=CLAUDE_MODEL,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": _prompt(topic, level, lang)}],
            output_format=Deck,
            output_config={"effort": "low" if level == "simple" else "medium"},
            **extra,
        )
    except anthropic.AuthenticationError as e:
        raise AIError("API açary nädogry (ANTHROPIC_API_KEY).") from e
    except anthropic.RateLimitError as e:
        raise AIError("Hyzmat häzir gaty köp ýüklenen, birazdan gaýtadan synanyşyň.") from e
    except anthropic.APIStatusError as e:
        log.exception("Claude API error")
        raise AIError(f"AI hyzmatynda ýalňyşlyk ({e.status_code}).") from e
    except anthropic.APIConnectionError as e:
        raise AIError("AI hyzmatyna birikip bolmady.") from e

    if resp.stop_reason == "refusal":
        raise AIError("Bu tema boýunça prezentasiýa taýýarlap bolmady. Başga tema synanyşyň.")
    deck = resp.parsed_output
    if deck is None or not deck.slides:
        raise AIError("AI jogaby doly gelmedi, gaýtadan synanyşyň.")

    # Layout tertibini meýilnama boýunça berkidýäris
    plan = PLANS[level]
    for i, s in enumerate(deck.slides):
        if i < len(plan):
            s.layout = plan[i]
        elif s.layout not in LAYOUT_HELP:
            s.layout = "bullets"
    return deck
