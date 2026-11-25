import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from . import db
from . import settings
from .config import ADMIN_IDS, BOT_NAME, BOT_TOKEN
from .handlers import admin, user


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not BOT_TOKEN:
        sys.exit("BOT_TOKEN ýok! .env faýlyny barlaň.")
    if not ADMIN_IDS:
        logging.warning("ADMIN_IDS ýok — admin panel hiç kime açyk däl.")
    db.init_db()
    if not settings.api_key():
        logging.warning("API açary ýok — admin paneliň «🔑 API sazlamalary» bölüminden goşuň.")
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(user.router)  # /start, /cancel hemişe birinji işlesin
    dp.include_router(admin.router)
    await bot.set_my_commands([
        BotCommand(command="start", description="Başlamak"),
        BotCommand(command="new", description="Täze prezentasiýa"),
        BotCommand(command="help", description="Kömek"),
        BotCommand(command="cancel", description="Ýatyrmak"),
    ])
    logging.info("%s işe başlady", BOT_NAME)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
