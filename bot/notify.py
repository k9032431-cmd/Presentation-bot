"""Admin(ler)e duýduryş: API açary / balans meselesi."""
from __future__ import annotations

import html
import logging
import time

from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as IK

from .config import ADMIN_IDS

log = logging.getLogger(__name__)
_last: dict[str, float] = {}
COOLDOWN = 30 * 60  # şol bir duýduryş 30 minutda bir gezek


async def alert_admins(bot, text: str, key: str = "api"):
    now = time.time()
    if now - _last.get(key, 0) < COOLDOWN:
        return
    _last[key] = now
    kb = IK(inline_keyboard=[[B(text="🔑 API sazlamalary", callback_data="api:menu")]])
    msg = ("🚨 <b>API duýduryşy</b>\n\n" + html.escape(text)[:900]
           + "\n\nAPI açaryny ýa-da balansy barlaň. Açary aşakdaky düwme bilen çalşyp bilersiňiz.")
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, msg, reply_markup=kb)
        except Exception:  # noqa: BLE001
            log.warning("admin %s-e duýduryş iberip bolmady", aid)
