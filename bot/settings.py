"""API sazlamalary: admin panelden üýtgedilen bahalar (bazada) .env-den öňde durýar."""
from __future__ import annotations

import re

from . import config, db

KEYS = ("api_key", "base_url", "model_main", "model_full", "fallback_models")


def _get(key: str) -> str | None:
    return db.get_setting(key)


def api_key() -> str:
    v = _get("api_key")
    return v if v is not None else config.ANTHROPIC_API_KEY


def base_url() -> str:
    v = _get("base_url")
    raw = v if v is not None else config.ANTHROPIC_BASE_URL
    return re.sub(r"/v1/?$", "", (raw or "").strip().rstrip("/"))


def main_model() -> str:
    return _get("model_main") or config.CLAUDE_MODEL


def level_model(level: str) -> str:
    if level == "full":
        v = _get("model_full")
        if v is not None:
            return v or main_model()
    elif _get("model_main"):
        # admin esasy modeli çalşan bolsa, Ýönekeý/Orta şony ulanýar
        return main_model()
    return config.LEVEL_MODELS.get(level) or main_model()


def fallback_models() -> list[str]:
    v = _get("fallback_models")
    if v is None:
        return list(config.FALLBACK_MODELS)
    return [m.strip() for m in v.split(",") if m.strip()]


def set_value(key: str, value: str):
    assert key in KEYS
    db.set_setting(key, value.strip())


def mask(key: str) -> str:
    if not key:
        return "— (ýok)"
    return key[:7] + "…" + key[-4:] if len(key) > 14 else "•••"


def version() -> tuple:
    """Müşderini (client) täzeden döretmeli wagty bilmek üçin."""
    return api_key(), base_url()
