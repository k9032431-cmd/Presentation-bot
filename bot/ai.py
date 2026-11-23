"""Claude bilen prezentasiýanyň mazmunyny döretmek."""
from __future__ import annotations

import json
import logging
import re

import anthropic
from pydantic import BaseModel

from .config import (ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, CLAUDE_MODEL, FALLBACK_MODELS,
                     LEVEL_MODELS)

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

# Ulanyjy slaýd sanyny özi saýlanda orta bölek şu görnüşlerden düzülýär
POOLS = {
    "simple": ["bullets"],
    "medium": ["bullets_image", "cards", "two_column", "stats", "bullets_image", "quote"],
    "full": ["bullets_image", "cards", "stats", "section", "process", "chart",
             "two_column", "image_full", "timeline", "quote"],
}
DEFAULT_COUNT = {k: len(v) for k, v in PLANS.items()}
MIN_SLIDES, MAX_SLIDES = 3, 30


def make_plan(level: str, n: int | None = None) -> list[str]:
    n = max(MIN_SLIDES, min(MAX_SLIDES, n or DEFAULT_COUNT[level]))
    if n == DEFAULT_COUNT[level]:
        return list(PLANS[level])
    head = ["title"]
    tail = ["conclusion"] if level == "simple" else ["conclusion", "thanks"]
    if level != "simple" and n >= 7:
        head.append("agenda")
    while len(head) + len(tail) >= n and len(tail) > 1:
        tail.pop()
    middle_n = n - len(head) - len(tail)
    pool = POOLS[level]
    middle = [pool[i % len(pool)] for i in range(middle_n)]
    return head + middle + tail


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


def _prompt(topic: str, level: str, lang: str, plan: list[str]) -> str:
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
        _client = anthropic.AsyncAnthropic(
            api_key=ANTHROPIC_API_KEY or None,
            base_url=ANTHROPIC_BASE_URL or None,  # başga üpjün ediji (proxy) üçin
            timeout=600,
        )
    return _client


class AIError(Exception):
    pass


def _supports_effort(model: str) -> bool:
    # Köne modeller (Haiku 4.5, Sonnet 4.5, Claude 3...) "effort" sazlamasyny kabul etmeýär
    return not model.startswith(("claude-haiku-4", "claude-sonnet-4-5", "claude-opus-4-5",
                                 "claude-opus-4-1", "claude-sonnet-4-0", "claude-3"))


def _extract_json(text: str) -> Deck | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return Deck.model_validate_json(m.group(0))
    except ValueError:
        return None


async def _call(client, structured: bool, kwargs: dict):
    if structured:
        async with client.beta.messages.stream(output_format=Deck, **kwargs) as stream:
            resp = await stream.get_final_message()
        deck = resp.parsed_output
    else:
        # Ýönekeý JSON tertibi: käbir üpjün edijiler structured outputs goldamaýar
        kwargs = dict(kwargs)
        kwargs["system"] = (kwargs["system"] + "\n\nReturn ONLY a JSON object (no markdown, no comments) "
                            "that validates against this JSON schema:\n"
                            + json.dumps(Deck.model_json_schema(), ensure_ascii=False))
        async with client.beta.messages.stream(**kwargs) as stream:
            resp = await stream.get_final_message()
        deck = None
    if deck is None:
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        deck = _extract_json(text)
    return resp, deck


def model_chain(level: str) -> list[str]:
    """Derejä görä esasy model + ätiýaçlyk modeller (gaýtalanmasyz)."""
    first = LEVEL_MODELS.get(level) or CLAUDE_MODEL
    chain = []
    for m in [first, *FALLBACK_MODELS]:
        if m and m not in chain:
            chain.append(m)
    return chain


def _kwargs(model: str, level: str, prompt: str) -> dict:
    kw = dict(
        model=model,
        max_tokens=32000 if model.startswith("claude-haiku-4") else 64000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    if _supports_effort(model):
        kw["output_config"] = {"effort": "low" if level == "simple" else "medium"}
    # Serwer tarapyndaky fallback diňe Anthropic-iň öz API-sinde we şu modellerde bar
    if not ANTHROPIC_BASE_URL and model in (
            "claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-2", "claude-opus-5"):
        kw["betas"] = ["server-side-fallback-2026-07-01"]
        kw["fallbacks"] = "default"
    return kw


async def _try_model(client, model: str, level: str, prompt: str):
    kw = _kwargs(model, level, prompt)
    try:
        return await _call(client, True, kw)
    except (anthropic.BadRequestError, ValueError) as e:
        # Üpjün ediji structured outputs-y goldamaýan ýa-da jogap JSON däl bolsa,
        # ýönekeý JSON tertibi bilen gaýtadan synanyşýarys
        log.warning("%s: structured output failed (%s), retrying with plain JSON", model, e)
        kw.pop("output_config", None)
        return await _call(client, False, kw)


async def generate_deck(topic: str, level: str, lang: str, n_slides: int | None = None) -> Deck:
    plan = make_plan(level, n_slides)
    client = _get_client()
    prompt = _prompt(topic, level, lang, plan)
    last_err = "AI jogaby doly gelmedi, gaýtadan synanyşyň."
    deck = None
    for model in model_chain(level):
        try:
            resp, deck = await _try_model(client, model, level, prompt)
        except anthropic.AuthenticationError as e:
            # Açar nädogry bolsa beýleki modeller hem işlemez
            raise AIError("API açary nädogry (ANTHROPIC_API_KEY).") from e
        except anthropic.PermissionDeniedError:
            last_err = "API açarynyň modele rugsady ýok ýa-da balans gutardy."
        except anthropic.RateLimitError:
            last_err = "Hyzmat häzir gaty köp ýüklenen, birazdan gaýtadan synanyşyň."
        except anthropic.APIStatusError as e:
            last_err = f"AI hyzmatynda ýalňyşlyk ({e.status_code})."
        except (anthropic.APIConnectionError, anthropic.APIResponseValidationError):
            last_err = "AI hyzmatyna birikip bolmady."
        except Exception as e:  # noqa: BLE001 - garaşylmadyk: indiki modeli synanyş
            log.exception("model %s unexpected error", model)
            last_err = f"AI ýalňyşlygy: {type(e).__name__}: {str(e)[:200]}"
        else:
            if resp.stop_reason == "refusal":
                raise AIError("Bu tema boýunça prezentasiýa taýýarlap bolmady. Başga tema synanyşyň.")
            if deck is not None and deck.slides:
                log.info("deck generated with %s (%s, %d slides)", model, level, len(plan))
                break
            last_err = "AI jogaby doly gelmedi, gaýtadan synanyşyň."
        log.warning("model %s failed: %s — trying next model", model, last_err)
        deck = None
    if deck is None:
        raise AIError(last_err)

    # Layout tertibini meýilnama boýunça berkidýäris
    for i, s in enumerate(deck.slides):
        if i < len(plan):
            s.layout = plan[i]
        elif s.layout not in LAYOUT_HELP:
            s.layout = "bullets"
    return deck
