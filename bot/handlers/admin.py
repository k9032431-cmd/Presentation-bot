import asyncio
import html
import re

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message

from .. import db
from .. import keyboards as kb
from ..builder.helpers import mix
from ..config import ADMIN_IDS
from .. import settings
from ..ai import test_api
from ..preview import render_preview
from ..style_ai import style_from_image

router = Router()
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))

HEX = re.compile(r"#?([0-9a-fA-F]{6})\b")


class AddStyle(StatesGroup):
    photo = State()
    name = State()
    colors = State()
    motif = State()
    font = State()
    confirm = State()


class Broadcast(StatesGroup):
    text = State()


@router.message(Command("admin"))
@router.message(F.text == kb.BTN_ADMIN)
async def admin(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("⚙️ <b>Admin panel</b>", reply_markup=kb.admin_menu())


@router.callback_query(F.data == "adm:menu")
async def admin_cb(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text("⚙️ <b>Admin panel</b>", reply_markup=kb.admin_menu())
    await c.answer()


@router.callback_query(F.data == "adm:stats")
async def stats(c: CallbackQuery):
    users, made, styles = db.stats()
    await c.message.edit_text(
        f"📊 <b>Statistika</b>\n\n👤 Ulanyjylar: <b>{users}</b>\n"
        f"   ✅ rugsatly: <b>{db.count_status('approved')}</b> · ⏳ garaşýan: "
        f"<b>{db.count_status('pending')}</b> · ⛔ ret edilen: <b>{db.count_status('blocked')}</b>\n"
        f"📑 Döredilen prezentasiýalar: <b>{made}</b>\n🎨 Stiller: <b>{styles}</b>",
        reply_markup=kb.admin_menu())
    await c.answer()


# ---------------- rugsatlar ----------------
async def _set_access(bot, uid: int, status: str) -> str:
    db.set_status(uid, status)
    msg = {
        "approved": "✅ Size boty ulanmaga rugsat berildi! Başlamak üçin /start basyň.",
        "blocked": "⛔ Size bu boty ulanmaga rugsat berilmedi.",
    }[status]
    try:
        await bot.send_message(uid, msg)
    except Exception:  # noqa: BLE001 - ulanyjy boty bloklan bolup biler
        pass
    u = db.get_user(uid)
    name = html.escape(u["name"]) if u and u["name"] else str(uid)
    return name


@router.callback_query(F.data.startswith("acc:"))
async def access_cb(c: CallbackQuery):
    _, action, uid = c.data.split(":")
    uid = int(uid)
    status = "approved" if action == "ok" else "blocked"
    name = await _set_access(c.bot, uid, status)
    if action == "rm":
        await c.answer(f"🚫 {name}: rugsat aýryldy")
        await approved_list(c)
        return
    await c.answer("✅ Rugsat berildi" if status == "approved" else "⛔ Ret edildi")
    if c.message.text and c.message.text.startswith("🆕"):
        await c.message.edit_text(
            c.message.html_text + ("\n\n✅ <b>Rugsat berildi</b>" if status == "approved" else "\n\n⛔ <b>Ret edildi</b>"))
    else:
        await pending_list(c)


@router.callback_query(F.data == "adm:pending")
async def pending_list(c: CallbackQuery):
    users = db.list_users("pending")
    await c.message.edit_text(
        f"⏳ <b>Rugsat garaşýanlar ({db.count_status('pending')})</b>\n✅ — rugsat ber, ⛔ — ret et"
        if users else "⏳ Rugsat garaşýan ýok.", reply_markup=kb.pending_users(users))
    await c.answer()


@router.callback_query(F.data == "adm:approved")
async def approved_list(c: CallbackQuery):
    users = db.list_users("approved")
    await c.message.edit_text(
        f"👥 <b>Rugsatly ulanyjylar ({db.count_status('approved')})</b>\nRugsady aýyrmak üçin basyň."
        if users else "👥 Entek rugsatly ulanyjy ýok.", reply_markup=kb.approved_users(users))
    await c.answer()


@router.message(Command("allow", "deny"))
async def allow_cmd(m: Message, command: CommandObject):
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await m.answer(f"Ulanyş: <code>/{command.command} 123456789</code> (ulanyjynyň Telegram ID-si)")
        return
    status = "approved" if command.command == "allow" else "blocked"
    name = await _set_access(m.bot, int(arg), status)
    await m.answer(f"{'✅ Rugsat berildi' if status == 'approved' else '⛔ Rugsat aýryldy'}: {name}")


# ---------------- stiller ----------------
@router.callback_query(F.data == "adm:list")
async def list_styles(c: CallbackQuery):
    styles = db.list_styles()
    await c.message.edit_text(f"📋 <b>Stiller ({len(styles)})</b>\nPozmak üçin basyň:",
                              reply_markup=kb.admin_styles(styles))
    await c.answer()


@router.callback_query(F.data.startswith("adm:del:"))
async def del_style(c: CallbackQuery):
    sid = int(c.data.split(":")[2])
    s = db.get_style(sid)
    if not s:
        await c.answer("Tapylmady")
        return
    await c.message.edit_text(f"«{s['name']}» stilini pozmalymy?", reply_markup=kb.confirm_delete(sid))
    await c.answer()


@router.callback_query(F.data.startswith("adm:delok:"))
async def del_ok(c: CallbackQuery):
    db.delete_style(int(c.data.split(":")[2]))
    await c.answer("🗑 Pozuldy")
    await list_styles(c)


@router.callback_query(F.data == "adm:add")
async def add_start(c: CallbackQuery, state: FSMContext):
    await state.set_state(AddStyle.name)
    await c.message.answer("➕ <b>Täze stil</b>\n\n1/4. Stiliň <b>adyny</b> ýazyň (mysal: <code>Ocean Blue</code>).\n"
                           "Ýatyrmak: /cancel")
    await c.answer()


@router.message(AddStyle.name, F.text)
async def add_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip()[:40])
    await state.set_state(AddStyle.colors)
    await m.answer(
        "2/4. <b>5 reňk</b> ýazyň (HEX kod), şu tertipde:\n"
        "<b>fon, esasy, ikinji, üns (accent), tekst</b>\n\n"
        "Mysal (ak fonly gök):\n<code>#FFFFFF #0B3C78 #1F7AE0 #38BDF8 #13233A</code>\n\n"
        "Mysal (gara fonly altyn):\n<code>#111111 #D4AF37 #8C7355 #F5E6C8 #F5F5F5</code>\n\n"
        "💡 Reňk kodlaryny Pinterest suratlaryndan <i>imagecolorpicker.com</i> arkaly alyp bilersiňiz.")


@router.message(AddStyle.colors, F.text)
async def add_colors(m: Message, state: FSMContext):
    found = ["#" + h.upper() for h in HEX.findall(m.text)]
    if len(found) < 5:
        await m.answer("⚠️ 5 sany HEX reňk gerek. Mysal:\n<code>#FFFFFF #0B3C78 #1F7AE0 #38BDF8 #13233A</code>")
        return
    bg, primary, secondary, accent, text = found[:5]
    await state.update_data(
        bg=bg, primary=primary, secondary=secondary, accent=accent, text=text,
        surface=mix(bg, primary, 0.08), muted=mix(text, bg, 0.4))
    await state.set_state(AddStyle.motif)
    await m.answer(
        "3/4. <b>Bezeg görnüşini</b> saýlaň:\n"
        "• wave — tolkun/tegelek burçlar\n• circles — tegelekler\n• blocks — gapdal zolaklar\n"
        "• diagonal — burçly üçburçluklar\n• minimal — juda arassa\n• frame — inçe ramka (lýuks)",
        reply_markup=kb.motifs())


@router.callback_query(AddStyle.motif, F.data.startswith("mot:"))
async def add_motif(c: CallbackQuery, state: FSMContext):
    await state.update_data(motif=c.data.split(":", 1)[1])
    await state.set_state(AddStyle.font)
    await c.message.edit_text("4/4. <b>Şrifti</b> saýlaň:", reply_markup=kb.fonts())
    await c.answer()


@router.callback_query(AddStyle.font, F.data.startswith("fnt:"))
async def add_font(c: CallbackQuery, state: FSMContext):
    font = c.data.split(":", 1)[1]
    await state.update_data(font=font, body_font="Calibri" if font not in ("Arial", "Verdana") else font)
    await state.set_state(AddStyle.confirm)
    data = await state.get_data()
    await c.message.delete()
    await c.message.answer_photo(FSInputFile(render_preview(data)),
                                 caption=f"👀 «{data['name']}» stili şeýle görüner. Ýatda saklaýynmy?",
                                 reply_markup=kb.save_style())
    await c.answer()


@router.callback_query(AddStyle.confirm, F.data == "adm:save")
async def add_save(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sid = db.add_style(data)
    await state.clear()
    await c.message.edit_caption(caption=f"✅ «{data['name']}» stili goşuldy (ID {sid}). "
                                         "Indi ulanyjylar ony saýlap bilerler.")
    await c.answer()


@router.callback_query(F.data == "adm:cancel")
async def add_cancel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_caption(caption="❌ Ýatyryldy.")
    await c.answer()


# ---------------- suratdan awtomatik stil ----------------
@router.callback_query(F.data == "adm:photo")
async def photo_start(c: CallbackQuery, state: FSMContext):
    await state.set_state(AddStyle.photo)
    await c.message.answer(
        "🖼 <b>Suratdan stil</b>\n\nHalaýan prezentasiýa dizaýnyňyzyň suratyny iberiň "
        "(Pinterest, skrinşot we ş.m.).\nBot reňkleri, bezegi we şrifti özi saýlar.\n\n"
        "💡 Islän wagtyňyz admin panele girmän hem göni surat iberip bilersiňiz.\nÝatyrmak: /cancel")
    await c.answer()


def _is_image_doc(m: Message) -> bool:
    return bool(m.document and (m.document.mime_type or "").startswith("image/"))


@router.message(StateFilter(None, AddStyle.photo, AddStyle.name, AddStyle.colors),
                F.photo | F.func(_is_image_doc))
async def photo_style(m: Message, state: FSMContext):
    note = await m.answer("🔍 Surat derňelýär, stil döredilýär...")
    file_id = m.photo[-1].file_id if m.photo else m.document.file_id
    buf = await m.bot.download(file_id)
    try:
        spec, used_ai = await style_from_image(buf.read())
    except Exception:  # noqa: BLE001
        await note.edit_text("⚠️ Suraty okap bolmady. Başga surat iberiň.")
        return
    await state.set_state(AddStyle.confirm)
    await state.set_data(spec)
    await note.delete()
    how = "🤖 AI derňedi" if used_ai else "🎨 Reňkler suratdan hasaplandy (AI elýeterli däl)"
    await m.answer_photo(
        FSInputFile(render_preview(spec)),
        caption=(f"👀 <b>{html.escape(spec['name'])}</b> — {how}\n\n"
                 f"Fon {spec['bg']} · Esasy {spec['primary']} · Ikinji {spec['secondary']}\n"
                 f"Üns {spec['accent']} · Tekst {spec['text']}\n"
                 f"Bezeg: {spec['motif']} · Şrift: {spec['font']}\n\n"
                 "Ýatda saklaýynmy? Adyny üýtgetmek üçin täze ady ýazyp iberiň."),
        reply_markup=kb.save_style_auto())


async def _show_confirm(m: Message, state: FSMContext):
    data = await state.get_data()
    await m.answer_photo(FSInputFile(render_preview(data)),
                         caption=f"👀 <b>{html.escape(data['name'])}</b> · {data['motif']} · {data['font']}\n"
                                 "Ýatda saklaýynmy?",
                         reply_markup=kb.save_style_auto())


@router.message(AddStyle.confirm, F.text, ~F.text.startswith("/"))
async def rename_style(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip()[:40])
    await _show_confirm(m, state)


@router.callback_query(AddStyle.confirm, F.data == "adm:remotif")
async def remotif(c: CallbackQuery):
    await c.message.answer("🎨 Bezeg görnüşini saýlaň:", reply_markup=kb.motifs())
    await c.answer()


@router.callback_query(AddStyle.confirm, F.data == "adm:refont")
async def refont(c: CallbackQuery):
    await c.message.answer("🔤 Şrifti saýlaň:", reply_markup=kb.fonts())
    await c.answer()


@router.callback_query(AddStyle.confirm, F.data.startswith("mot:"))
async def confirm_motif(c: CallbackQuery, state: FSMContext):
    await state.update_data(motif=c.data.split(":", 1)[1])
    await c.message.delete()
    await _show_confirm(c.message, state)
    await c.answer()


@router.callback_query(AddStyle.confirm, F.data.startswith("fnt:"))
async def confirm_font(c: CallbackQuery, state: FSMContext):
    font = c.data.split(":", 1)[1]
    await state.update_data(font=font, body_font="Calibri" if font not in ("Arial", "Verdana") else font)
    await c.message.delete()
    await _show_confirm(c.message, state)
    await c.answer()


# ---------------- API sazlamalary ----------------
class ApiSet(StatesGroup):
    key = State()
    base = State()
    main = State()
    full = State()
    fb = State()


def _api_text(extra: str = "") -> str:
    src = lambda k: "panel" if db.get_setting(k) is not None else ".env"  # noqa: E731
    fb = ", ".join(settings.fallback_models()) or "—"
    return (
        "🔑 <b>API sazlamalary</b>\n\n"
        f"Açar: <code>{html.escape(settings.mask(settings.api_key()))}</code> <i>({src('api_key')})</i>\n"
        f"Base URL: <code>{html.escape(settings.base_url() or 'Anthropic (resmi)')}</code> <i>({src('base_url')})</i>\n"
        f"Ýönekeý/Orta modeli: <code>{html.escape(settings.level_model('simple'))}</code>\n"
        f"Doly modeli: <code>{html.escape(settings.level_model('full'))}</code>\n"
        f"Ätiýaçlyk: <code>{html.escape(fb)}</code>"
        + (f"\n\n{extra}" if extra else "")
    )


@router.callback_query(F.data == "api:menu")
async def api_menu(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer(_api_text(), reply_markup=kb.api_menu())
    await c.answer()


@router.callback_query(F.data == "api:test")
async def api_test(c: CallbackQuery):
    await c.answer("🧪 Barlanýar...")
    ok, info = await test_api()
    res = ("✅ API işleýär" if ok else "❌ API işlemeýär") + f"\n<code>{html.escape(info)}</code>"
    await c.message.answer(_api_text(res), reply_markup=kb.api_menu())


@router.callback_query(F.data == "api:key")
async def api_key_start(c: CallbackQuery, state: FSMContext):
    await state.set_state(ApiSet.key)
    await c.message.answer("🔑 Täze API açaryny iberiň.\n"
                           "🔒 Howpsuzlyk üçin habaryňyz şol bada pozular.\nÝatyrmak: /cancel")
    await c.answer()


@router.message(ApiSet.key, F.text)
async def api_key_set(m: Message, state: FSMContext):
    key = m.text.strip()
    try:
        await m.delete()  # açar çatda galmasyn
    except Exception:  # noqa: BLE001
        pass
    if len(key) < 10 or " " in key:
        await m.answer("⚠️ Bu API açaryna meňzänok. Gaýtadan iberiň ýa-da /cancel.")
        return
    settings.set_value("api_key", key)
    await state.clear()
    note = await m.answer("✅ Açar ýatda saklandy. 🧪 Barlanýar...")
    ok, info = await test_api()
    await note.delete()
    res = ("✅ API işleýär" if ok else "❌ API işlemeýär") + f"\n<code>{html.escape(info)}</code>"
    await m.answer(_api_text(res), reply_markup=kb.api_menu())


@router.callback_query(F.data == "api:base")
async def api_base_start(c: CallbackQuery, state: FSMContext):
    await state.set_state(ApiSet.base)
    await c.message.answer(
        "🌐 Base URL iberiň.\n\nMysal: <code>https://triklz27.ru/v1</code>\n"
        "Anthropic-iň resmi API-si üçin: <code>-</code>\nÝatyrmak: /cancel")
    await c.answer()


@router.message(ApiSet.base, F.text)
async def api_base_set(m: Message, state: FSMContext):
    v = m.text.strip()
    if v in ("-", "0", "anthropic", "boş"):
        v = ""
    elif not v.startswith(("http://", "https://")):
        await m.answer("⚠️ URL <code>https://</code> bilen başlamaly. Gaýtadan iberiň.")
        return
    settings.set_value("base_url", v)
    await state.clear()
    await m.answer(_api_text("✅ Base URL täzelendi. «🧪 Barla» bilen synap görüň."), reply_markup=kb.api_menu())


MODEL_HINT = ("\n\nMysallar (basyp göçüriň):\n"
              "<code>claude-haiku-4-5</code>\n<code>claude-fable-5-2</code>\n<code>claude-fable-5-1</code>\n"
              "<code>claude-opus-5-5</code>\n<code>claude-sonnet-5-5</code>\n<code>claude-haiku-5-5</code>")


@router.callback_query(F.data == "api:models")
async def api_models_start(c: CallbackQuery, state: FSMContext):
    await state.set_state(ApiSet.main)
    await c.message.answer("🤖 1/3. <b>Ýönekeý we Orta</b> prezentasiýalar üçin model adyny ýazyň." + MODEL_HINT,
                           reply_markup=kb.skip("api:skip_main"))
    await c.answer()


async def _ask_full(m: Message, state: FSMContext):
    await state.set_state(ApiSet.full)
    await m.answer("🤖 2/3. <b>Doly</b> prezentasiýa üçin model adyny ýazyň." + MODEL_HINT,
                   reply_markup=kb.skip("api:skip_full"))


async def _ask_fb(m: Message, state: FSMContext):
    await state.set_state(ApiSet.fb)
    await m.answer("🤖 3/3. <b>Ätiýaçlyk modeller</b> (esasy işlemese), otur bilen. "
                   "Mysal: <code>claude-haiku-4-5</code>\nBoş goýmak üçin: <code>-</code>",
                   reply_markup=kb.skip("api:skip_fb"))


def _model_ok(v: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._:/@-]{3,80}", v))


@router.message(ApiSet.main, F.text)
async def api_main_set(m: Message, state: FSMContext):
    v = m.text.strip()
    if not _model_ok(v):
        await m.answer("⚠️ Model adyny dogry ýazyň, mysal: <code>claude-haiku-4-5</code>")
        return
    settings.set_value("model_main", v)
    await _ask_full(m, state)


@router.callback_query(ApiSet.main, F.data == "api:skip_main")
async def api_main_skip(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await _ask_full(c.message, state)


@router.message(ApiSet.full, F.text)
async def api_full_set(m: Message, state: FSMContext):
    v = m.text.strip()
    if not _model_ok(v):
        await m.answer("⚠️ Model adyny dogry ýazyň, mysal: <code>claude-fable-5-2</code>")
        return
    settings.set_value("model_full", v)
    await _ask_fb(m, state)


@router.callback_query(ApiSet.full, F.data == "api:skip_full")
async def api_full_skip(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await _ask_fb(c.message, state)


@router.message(ApiSet.fb, F.text)
async def api_fb_set(m: Message, state: FSMContext):
    v = m.text.strip()
    models = [] if v == "-" else [x.strip() for x in v.split(",") if x.strip()]
    if not all(_model_ok(x) for x in models):
        await m.answer("⚠️ Model atlaryny otur bilen ýazyň, mysal: <code>claude-haiku-4-5</code>")
        return
    settings.set_value("fallback_models", ",".join(models))
    await state.clear()
    await m.answer(_api_text("✅ Modeller täzelendi. «🧪 Barla» bilen synap görüň."), reply_markup=kb.api_menu())


@router.callback_query(ApiSet.fb, F.data == "api:skip_fb")
async def api_fb_skip(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer(_api_text("✅ Modeller täzelendi."), reply_markup=kb.api_menu())
    await c.answer()


# ---------------- habar ýaýratmak ----------------
@router.callback_query(F.data == "adm:bc")
async def bc_start(c: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.text)
    await c.message.answer("📢 Ähli ulanyjylara iberiljek habary ýazyň (ýa-da surat/wideo iberiň).\nÝatyrmak: /cancel")
    await c.answer()


@router.message(Broadcast.text)
async def bc_send(m: Message, state: FSMContext):
    await state.clear()
    ids = db.all_user_ids()
    ok = 0
    note = await m.answer(f"⏳ {len(ids)} ulanyja iberilýär...")
    for uid in ids:
        try:
            await m.copy_to(uid)
            ok += 1
        except Exception:  # noqa: BLE001 - boty bloklan ulanyjylar
            pass
        await asyncio.sleep(0.05)
    await note.edit_text(f"✅ Iberildi: {ok} / {len(ids)}")
