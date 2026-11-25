import html
import logging
import os

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message

from .. import db
from .. import keyboards as kb
from ..access import AccessMiddleware
from ..ai import DEFAULT_COUNT, MAX_SLIDES, MIN_SLIDES, AIError
from .. import settings
from ..config import ADMIN_IDS, BOT_NAME
from ..notify import alert_admins
from ..generator import make_presentation
from ..preview import render_preview

router = Router()
router.message.middleware(AccessMiddleware())
router.callback_query.middleware(AccessMiddleware())
log = logging.getLogger(__name__)
_busy: set[int] = set()


class Make(StatesGroup):
    level = State()
    count = State()
    style = State()
    lang = State()
    topic = State()


WELCOME = (
    f"👋 Salam, <b>{{name}}</b>!\n\n"
    f"Men <b>{BOT_NAME}</b> — size birnäçe minutda owadan prezentasiýa taýýarlap berýärin.\n\n"
    "1️⃣ Görnüşini saýlaň: <b>Ýönekeý</b>, <b>Orta</b> ýa-da <b>Doly</b>\n"
    "2️⃣ Slaýd sanyny saýlaň ýa-da özüňiz ýazyň\n"
    "3️⃣ Halaýan stiliňizi saýlaň\n"
    "4️⃣ Temany ýazyň — we taýýar <b>.pptx</b> faýly alyň!\n\n"
    f"Başlamak üçin «{kb.BTN_CREATE}» düwmesine basyň."
)

HELP = (
    "ℹ️ <b>Nädip ulanmaly?</b>\n\n"
    f"• «{kb.BTN_CREATE}» basyň\n"
    "• Derejäni saýlaň:\n"
    f"   {kb.LEVEL_NAMES['simple']} — {kb.LEVEL_DESC['simple']}\n"
    f"   {kb.LEVEL_NAMES['medium']} — {kb.LEVEL_DESC['medium']}\n"
    f"   {kb.LEVEL_NAMES['full']} — {kb.LEVEL_DESC['full']}\n"
    f"• Slaýd sanyny saýlaň ýa-da özüňiz ýazyň ({MIN_SLIDES}–{MAX_SLIDES})\n"
    "• Stili ◀️ ▶️ düwmeleri bilen görüp saýlaň\n"
    "• Dili saýlaň we temany ýazyň\n\n"
    "Faýly PowerPoint, Google Slides ýa-da WPS Office bilen açyp, üýtgedip bilersiňiz.\n"
    "Animasiýalary görmek üçin PowerPoint-de slaýd görkezişini açyň (F5)."
)


@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    db.add_user(m.from_user.id, m.from_user.full_name, m.from_user.username)
    await m.answer(WELCOME.format(name=m.from_user.first_name or ""),
                   reply_markup=kb.main_menu(m.from_user.id in ADMIN_IDS))


@router.message(Command("help"))
@router.message(F.text == kb.BTN_HELP)
async def help_(m: Message):
    await m.answer(HELP)


@router.message(Command("cancel"))
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("❌ Ýatyryldy.", reply_markup=kb.main_menu(m.from_user.id in ADMIN_IDS))


@router.message(Command("new"))
@router.message(F.text == kb.BTN_CREATE)
async def create(m: Message, state: FSMContext):
    db.add_user(m.from_user.id, m.from_user.full_name, m.from_user.username)
    await state.clear()
    await state.set_state(Make.level)
    text = "📊 <b>Prezentasiýanyň görnüşini saýlaň:</b>\n\n" + "\n".join(
        f"{kb.LEVEL_NAMES[k]}\n<i>{kb.LEVEL_DESC[k]}</i>\n" for k in kb.LEVEL_NAMES)
    await m.answer(text, reply_markup=kb.levels())


@router.callback_query(F.data == "noop")
async def noop(c: CallbackQuery):
    await c.answer()


@router.callback_query(F.data == "back:levels")
async def back_levels(c: CallbackQuery, state: FSMContext):
    await state.set_state(Make.level)
    await c.message.delete()
    text = "📊 <b>Prezentasiýanyň görnüşini saýlaň:</b>\n\n" + "\n".join(
        f"{kb.LEVEL_NAMES[k]}\n<i>{kb.LEVEL_DESC[k]}</i>\n" for k in kb.LEVEL_NAMES)
    await c.message.answer(text, reply_markup=kb.levels())
    await c.answer()


def _style_caption(s, level, count):
    return (f"🎨 <b>{s['name']}</b>\n"
            f"Görnüş: {kb.LEVEL_NAMES[level]} · {count} slaýd\n\n"
            "◀️ ▶️ bilen beýleki stilleri görüň we halanyňyzy saýlaň.")


@router.callback_query(F.data.startswith("lvl:"))
async def pick_level(c: CallbackQuery, state: FSMContext):
    level = c.data.split(":")[1]
    await state.update_data(level=level)
    await state.set_state(Make.count)
    await c.message.edit_text(
        f"{kb.LEVEL_NAMES[level]}\n\n🔢 <b>Näçe slaýd bolsun?</b>\n"
        f"Aşakdan saýlaň ýa-da özüňiz san ýazyň ({MIN_SLIDES}–{MAX_SLIDES}).\n"
        f"⭐ — maslahat berilýän san.",
        reply_markup=kb.slide_counts(level, DEFAULT_COUNT[level]))
    await c.answer()


async def _show_styles(message: Message, state: FSMContext, count: int):
    styles = db.list_styles()
    if not styles:
        await message.answer("Stil ýok. Admin stil goşmaly.")
        return
    await state.update_data(count=count)
    await state.set_state(Make.style)
    level = (await state.get_data()).get("level", "medium")
    s = styles[0]
    await message.answer_photo(FSInputFile(render_preview(s)), caption=_style_caption(s, level, count),
                               reply_markup=kb.styles_nav(0, len(styles), s["id"]))


@router.callback_query(Make.count, F.data.startswith("cnt:"))
async def pick_count(c: CallbackQuery, state: FSMContext):
    count = int(c.data.split(":")[1])
    await c.message.delete()
    await _show_styles(c.message, state, count)
    await c.answer()


@router.message(Make.count, F.text)
async def typed_count(m: Message, state: FSMContext):
    t = m.text.strip()
    if not t.isdigit() or not (MIN_SLIDES <= int(t) <= MAX_SLIDES):
        await m.answer(f"⚠️ {MIN_SLIDES}-den {MAX_SLIDES}-a çenli san ýazyň. Mysal: <code>12</code>")
        return
    await _show_styles(m, state, int(t))


@router.callback_query(F.data.startswith("st:"))
async def nav_style(c: CallbackQuery, state: FSMContext):
    styles = db.list_styles()
    if not styles:
        await c.answer()
        return
    i = int(c.data.split(":")[1]) % len(styles)
    s = styles[i]
    data = await state.get_data()
    level = data.get("level", "medium")
    count = data.get("count", DEFAULT_COUNT[level])
    await c.message.edit_media(
        InputMediaPhoto(media=FSInputFile(render_preview(s)), caption=_style_caption(s, level, count)),
        reply_markup=kb.styles_nav(i, len(styles), s["id"]))
    await c.answer()


@router.callback_query(F.data.startswith("pick:"))
async def pick_style(c: CallbackQuery, state: FSMContext):
    sid = int(c.data.split(":")[1])
    s = db.get_style(sid)
    if not s:
        await c.answer("Bu stil pozuldy, başgasyny saýlaň.", show_alert=True)
        return
    await state.update_data(style_id=sid)
    await state.set_state(Make.lang)
    await c.message.edit_caption(caption=f"✅ Stil saýlandy: <b>{s['name']}</b>")
    await c.message.answer("🌐 Prezentasiýa haýsy dilde bolsun?", reply_markup=kb.langs())
    await c.answer()


@router.callback_query(F.data.startswith("lang:"))
async def pick_lang(c: CallbackQuery, state: FSMContext):
    lang = c.data.split(":")[1]
    await state.update_data(lang=lang)
    await state.set_state(Make.topic)
    await c.message.edit_text(
        f"🌐 Dil: {kb.LANG_NAMES[lang]}\n\n"
        "✍️ Indi prezentasiýanyň <b>temasyny</b> ýazyň.\n\n"
        "<i>Mysal: «Emeli aň we bilim ulgamy» ýa-da «Kofe dükanynyň biznes meýilnamasy».\n"
        "Goşmaça maglumat (maksat, diňleýjiler, möhüm sanlar) hem ýazyp bilersiňiz.</i>")
    await c.answer()


@router.message(Make.topic, F.text)
async def got_topic(m: Message, state: FSMContext):
    topic = m.text.strip()
    if len(topic) < 3:
        await m.answer("Tema gaty gysga, has giňişleýin ýazyň.")
        return
    if len(topic) > 3000:
        topic = topic[:3000]
    uid = m.from_user.id
    if uid in _busy:
        await m.answer("⏳ Öňki prezentasiýaňyz taýýarlanýar, garaşyň...")
        return
    if not settings.api_key():
        await m.answer("⚠️ Bot entek sazlanmadyk (API açary ýok). Admine habar berildi.")
        await alert_admins(m.bot, "API açary goýulmandyr — ulanyjylar prezentasiýa ýasap bilmeýär.")
        return
    data = await state.get_data()
    style = db.get_style(data.get("style_id", 0)) or (db.list_styles() or [None])[0]
    level, lang = data.get("level", "medium"), data.get("lang", "tk")
    count = data.get("count", DEFAULT_COUNT[level])
    await state.clear()

    _busy.add(uid)
    wait = await m.answer(
        f"⏳ Prezentasiýa taýýarlanýar...\n\n"
        f"📌 Tema: <i>{html.escape(topic[:200])}</i>\n"
        f"📊 Görnüş: {kb.LEVEL_NAMES[level]} · {count} slaýd\n🎨 Stil: {style['name']}\n\n"
        "Bu 1-3 minut wagt alyp biler.")
    try:
        await m.bot.send_chat_action(m.chat.id, "upload_document")
        path, title = await make_presentation(topic, level, lang, style, uid, count)
        await m.answer_document(
            FSInputFile(path, filename=os.path.basename(path).split("_", 2)[-1]),
            caption=f"✅ <b>{html.escape(title)}</b>\n{kb.LEVEL_NAMES[level]} · {count} slaýd · {style['name']}\n\n"
                    f"Täzesini döretmek üçin «{kb.BTN_CREATE}» basyň.",
            reply_markup=kb.main_menu(uid in ADMIN_IDS))
        db.inc_made(uid)
        try:
            os.remove(path)
        except OSError:
            pass
    except AIError as e:
        is_admin = uid in ADMIN_IDS
        if e.alert and not is_admin:
            text = "⚠️ Bot wagtlaýyn işlemeýär. Admine habar berildi, birazdan gaýtadan synanyşyň."
        else:
            text = f"⚠️ {html.escape(str(e))}"
        if is_admin and e.detail:
            text += f"\n\n<code>{html.escape(e.detail)[:700]}</code>"
        await m.answer(text)
        if e.alert:
            await alert_admins(m.bot, f"{e}\n{e.detail}")
    except Exception as e:  # noqa: BLE001
        log.exception("generation failed")
        detail = f"\n\n<code>{html.escape(type(e).__name__ + ': ' + str(e))[:500]}</code>" if uid in ADMIN_IDS else ""
        await m.answer("⚠️ Garaşylmadyk ýalňyşlyk ýüze çykdy. Gaýtadan synanyşyň." + detail)
    finally:
        _busy.discard(uid)
        try:
            await wait.delete()
        except Exception:  # noqa: BLE001
            pass


@router.message(Make.topic)
async def topic_not_text(m: Message):
    await m.answer("Temany tekst görnüşinde ýazyň.")
