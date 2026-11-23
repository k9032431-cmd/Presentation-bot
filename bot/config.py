"""Bot sazlamalary (.env faýlyndan okalýar)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_NAME = "Shiri-Presentation-BOT"

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()
}
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5").strip()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "bot.db"
OUT_DIR = DATA_DIR / "out"
OUT_DIR.mkdir(exist_ok=True)
PREVIEW_DIR = DATA_DIR / "previews"
PREVIEW_DIR.mkdir(exist_ok=True)
