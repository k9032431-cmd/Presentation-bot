"""Bot sazlamalary (.env faýlyndan okalýar)."""
import os
import re
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
# Başga saýtdan alnan API üçin (mysal: https://triklz27.ru/v1). Boş = Anthropic-iň özi
ANTHROPIC_BASE_URL = re.sub(r"/v1/?$", "", os.getenv("ANTHROPIC_BASE_URL", "").strip().rstrip("/"))
# Her dereje üçin model (boş bolsa CLAUDE_MODEL ulanylýar)
LEVEL_MODELS = {
    "simple": os.getenv("MODEL_SIMPLE", "").strip(),
    "medium": os.getenv("MODEL_MEDIUM", "").strip(),
    "full": os.getenv("MODEL_FULL", "").strip(),
}
# Esasy model işlemese, tertip boýunça synanyşyljak modeller
FALLBACK_MODELS = [m.strip() for m in os.getenv("FALLBACK_MODELS", "").split(",") if m.strip()]
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "bot.db"
OUT_DIR = DATA_DIR / "out"
OUT_DIR.mkdir(exist_ok=True)
PREVIEW_DIR = DATA_DIR / "previews"
PREVIEW_DIR.mkdir(exist_ok=True)
