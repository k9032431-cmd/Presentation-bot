from aiogram.types import (InlineKeyboardButton as B, InlineKeyboardMarkup as IK,
                           KeyboardButton as KB, ReplyKeyboardMarkup as RK)

from .default_styles import FONTS, MOTIFS

BTN_CREATE = "🎨 Prezentasiýa döret"
BTN_HELP = "ℹ️ Kömek"
BTN_ADMIN = "⚙️ Admin panel"

LEVEL_NAMES = {
    "simple": "🟢 Ýönekeý",
    "medium": "🟡 Orta",
    "full": "🔴 Doly (Full)",
}
LEVEL_DESC = {
    "simple": "6 slaýd · arassa we ýönekeý dizaýn",
    "medium": "10 slaýd · suratlar, kartoçkalar, statistika, geçişler",
    "full": "14 slaýd · diagramma, timeline, animasiýalar, spiker bellikleri",
}
LANG_NAMES = {"tk": "🇹🇲 Türkmençe", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}


def main_menu(is_admin: bool):
    rows = [[KB(text=BTN_CREATE)], [KB(text=BTN_HELP)]]
    if is_admin:
        rows.append([KB(text=BTN_ADMIN)])
    return RK(keyboard=rows, resize_keyboard=True)


def levels():
    return IK(inline_keyboard=[
        [B(text=f"{LEVEL_NAMES[k]} — {LEVEL_DESC[k].split(' · ')[0]}", callback_data=f"lvl:{k}")]
        for k in LEVEL_NAMES
    ])


def styles_nav(i: int, n: int, sid: int):
    return IK(inline_keyboard=[
        [B(text="◀️", callback_data=f"st:{(i - 1) % n}"),
         B(text=f"{i + 1} / {n}", callback_data="noop"),
         B(text="▶️", callback_data=f"st:{(i + 1) % n}")],
        [B(text="✅ Şu stili saýla", callback_data=f"pick:{sid}")],
        [B(text="⬅️ Derejä gaýt", callback_data="back:levels")],
    ])


def langs():
    return IK(inline_keyboard=[[B(text=v, callback_data=f"lang:{k}")] for k, v in LANG_NAMES.items()])


def admin_menu():
    return IK(inline_keyboard=[
        [B(text="➕ Täze stil goş", callback_data="adm:add")],
        [B(text="📋 Stiller / pozmak", callback_data="adm:list")],
        [B(text="📊 Statistika", callback_data="adm:stats")],
        [B(text="📢 Ähli ulanyjylara habar", callback_data="adm:bc")],
    ])


def admin_styles(styles):
    rows = [[B(text=f"🗑 {s['id']}. {s['name']}", callback_data=f"adm:del:{s['id']}")] for s in styles]
    rows.append([B(text="⬅️ Yza", callback_data="adm:menu")])
    return IK(inline_keyboard=rows)


def confirm_delete(sid):
    return IK(inline_keyboard=[[B(text="✅ Hawa, poz", callback_data=f"adm:delok:{sid}"),
                                B(text="❌ Ýok", callback_data="adm:list")]])


def motifs():
    return IK(inline_keyboard=[[B(text=m, callback_data=f"mot:{m}") for m in MOTIFS[i:i + 3]]
                               for i in range(0, len(MOTIFS), 3)])


def fonts():
    return IK(inline_keyboard=[[B(text=f, callback_data=f"fnt:{f}") for f in FONTS[i:i + 2]]
                               for i in range(0, len(FONTS), 2)])


def save_style():
    return IK(inline_keyboard=[[B(text="✅ Ýatda sakla", callback_data="adm:save"),
                                B(text="❌ Ýatyr", callback_data="adm:cancel")]])
