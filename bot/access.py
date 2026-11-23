"""Rugsat: boty diňe admin rugsat beren ulanyjylar ulanyp bilýär."""
from __future__ import annotations

import html
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, TelegramObject, User

from . import db
from . import keyboards as kb
from .config import ADMIN_IDS

log = logging.getLogger(__name__)

PENDING_TEXT = (
    "🔒 Bu boty ulanmak üçin admin rugsady gerek.\n\n"
    "✅ Haýyşyňyz admine iberildi. Rugsat berlende size habar geler."
)
BLOCKED_TEXT = "⛔ Size bu boty ulanmaga rugsat berilmedi."


def is_allowed(uid: int) -> bool:
    return uid in ADMIN_IDS or db.get_status(uid) == "approved"


async def request_access(bot, user: User):
    """Admin(ler)e rugsat haýyşyny bir gezek iberýär."""
    if not db.mark_notified(user.id):
        return
    uname = f"@{user.username}" if user.username else "—"
    text = (f"🆕 <b>Rugsat haýyşy</b>\n\n👤 {html.escape(user.full_name)}\n"
            f"🔗 {uname}\n🆔 <code>{user.id}</code>")
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text, reply_markup=kb.access_request(user.id))
        except Exception:  # noqa: BLE001 - admin boty başlatmadyk bolup biler
            log.warning("admin %s-e habar iberip bolmady", aid)


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or is_allowed(user.id):
            return await handler(event, data)

        db.add_user(user.id, user.full_name, user.username)
        status = db.get_status(user.id)
        text = BLOCKED_TEXT if status == "blocked" else PENDING_TEXT
        if status != "blocked":
            await request_access(data["bot"], user)
        if isinstance(event, Message):
            await event.answer(text, reply_markup=ReplyKeyboardRemove())
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        return None
