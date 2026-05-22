import sqlite3
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards import (
    admin_add_sub_type_kb,
    admin_delete_movie_confirm_kb,
    admin_delete_sub_confirm_kb,
    admin_movie_detail_kb,
    admin_movies_kb,
    admin_panel_kb,
    admin_sub_detail_kb,
    admin_subs_kb,
    cancel_fsm_kb,
    main_menu_kb,
)
from services.duration import parse_duration_to_expires_at
from services.sub_format import subscription_period_text
from services.channel_resolve import (
    BotNotAdminError,
    ChannelResolveError,
    InvalidLinkError,
    chat_id_for_db,
    resolve_channel_from_message,
)
from states import AdminAddMovie, AdminAddSub, AdminEditMovie

router = Router()


class AdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, is_admin: bool) -> bool:
        return is_admin


router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


def _movie_detail_text(movie) -> str:
    return (
        f"🎬 <b>{movie.title}</b>\n"
        f"🔑 Код: <code>{movie.code}</code>\n\n"
        f"{movie.description or '—'}\n\n"
        f"🔗 {movie.link or '—'}"
    )


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "⚙️ <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_movies")
async def cb_admin_movies(callback: CallbackQuery, db: Database) -> None:
    movies = await db.list_movies()
    text = "🎬 <b>Фильмы</b>\n\nВыберите фильм или добавьте новый."
    if not movies:
        text += "\n\n<i>Список пуст.</i>"
    await callback.message.edit_text(text, reply_markup=admin_movies_kb(movies))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_movie:"))
async def cb_admin_movie_detail(callback: CallbackQuery, db: Database) -> None:
    movie_id = int(callback.data.split(":")[1])
    movie = await db.get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("Фильм не найден.", show_alert=True)
        return
    await callback.message.edit_text(
        _movie_detail_text(movie),
        reply_markup=admin_movie_detail_kb(movie_id),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_movie")
async def cb_admin_add_movie(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminAddMovie.code)
    await callback.message.answer(
        "➕ <b>Новый фильм</b>\n\nВведите код фильма (уникальный, например ABC123):",
        reply_markup=cancel_fsm_kb(),
    )
    await callback.answer()


@router.message(AdminAddMovie.code)
async def admin_add_movie_code(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return
    code = (message.text or "").strip().upper()
    if not code:
        await message.answer("Код не может быть пустым.")
        return
    await state.update_data(code=code)
    await state.set_state(AdminAddMovie.title)
    await message.answer("Введите название фильма:")


@router.message(AdminAddMovie.title)
async def admin_add_movie_title(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AdminAddMovie.description)
    await message.answer(
        "Введите описание фильма (или отправьте «-» чтобы пропустить):"
    )


@router.message(AdminAddMovie.description)
async def admin_add_movie_desc(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return
    desc = (message.text or "").strip()
    if desc == "-":
        desc = ""
    await state.update_data(description=desc)
    await state.set_state(AdminAddMovie.link)
    await message.answer(
        "Введите ссылку на фильм (или «-» чтобы пропустить):"
    )


@router.message(AdminAddMovie.link)
async def admin_add_movie_link(
    message: Message, state: FSMContext, db: Database
) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return
    link = (message.text or "").strip()
    if link == "-":
        link = ""
    data = await state.get_data()
    await state.clear()
    try:
        await db.add_movie(
            code=data["code"],
            title=data["title"],
            description=data.get("description", ""),
            link=link,
        )
    except sqlite3.IntegrityError:
        await message.answer(
            f"❌ Фильм с кодом <code>{data['code']}</code> уже существует.",
            reply_markup=main_menu_kb(True),
        )
        return
    await message.answer(
        f"✅ Фильм <code>{data['code']}</code> добавлен.",
        reply_markup=main_menu_kb(True),
    )


@router.callback_query(F.data.startswith("admin_edit_movie:"))
async def cb_admin_edit_movie(callback: CallbackQuery, state: FSMContext) -> None:
    movie_id = int(callback.data.split(":")[1])
    await state.update_data(edit_movie_id=movie_id)
    await state.set_state(AdminEditMovie.title)
    await callback.message.answer(
        "✏️ Введите новое название:",
        reply_markup=cancel_fsm_kb(),
    )
    await callback.answer()


@router.message(AdminEditMovie.title)
async def admin_edit_title(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AdminEditMovie.description)
    await message.answer("Введите новое описание (или «-»):")


@router.message(AdminEditMovie.description)
async def admin_edit_desc(message: Message, state: FSMContext) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return
    desc = (message.text or "").strip()
    if desc == "-":
        desc = ""
    await state.update_data(description=desc)
    await state.set_state(AdminEditMovie.link)
    await message.answer("Введите новую ссылку (или «-»):")


@router.message(AdminEditMovie.link)
async def admin_edit_link(
    message: Message, state: FSMContext, db: Database
) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return
    link = (message.text or "").strip()
    if link == "-":
        link = ""
    data = await state.get_data()
    movie_id = data["edit_movie_id"]
    await state.clear()
    await db.update_movie(
        movie_id,
        title=data["title"],
        description=data.get("description", ""),
        link=link,
    )
    movie = await db.get_movie_by_id(movie_id)
    await message.answer(
        "✅ Фильм обновлён.\n\n" + _movie_detail_text(movie),
        reply_markup=admin_movie_detail_kb(movie_id),
    )


@router.callback_query(F.data.startswith("admin_del_movie:"))
async def cb_admin_del_movie_confirm(callback: CallbackQuery, db: Database) -> None:
    movie_id = int(callback.data.split(":")[1])
    movie = await db.get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("Фильм не найден.", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 Удалить фильм <b>{movie.title}</b> "
        f"(код <code>{movie.code}</code>)?\n\nЭто действие нельзя отменить.",
        reply_markup=admin_delete_movie_confirm_kb(movie_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_movie_yes:"))
async def cb_admin_del_movie(callback: CallbackQuery, db: Database) -> None:
    movie_id = int(callback.data.split(":")[1])
    movie = await db.get_movie_by_id(movie_id)
    if movie:
        await db.delete_movie(movie_id)
    movies = await db.list_movies()
    text = "🗑 Фильм удалён.\n\n🎬 <b>Фильмы</b>"
    if not movies:
        text += "\n\n<i>Список пуст.</i>"
    await callback.message.edit_text(text, reply_markup=admin_movies_kb(movies))
    await callback.answer("Удалено")


@router.callback_query(F.data == "admin_subs")
async def cb_admin_subs(callback: CallbackQuery, db: Database) -> None:
    subs = await db.list_subscriptions()
    text = (
        "📢 <b>Обязательные подписки</b>\n\n"
        "При добавлении выберите тип:\n"
        "♾️ пока не отмените — или ⏱ на срок.\n\n"
        "Бот должен быть администратором в канале/чате."
    )
    if not subs:
        text += "\n\n<i>Список пуст.</i>"
    await callback.message.edit_text(text, reply_markup=admin_subs_kb(subs))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_sub:"))
async def cb_admin_sub_detail(callback: CallbackQuery, db: Database) -> None:
    sub_id = int(callback.data.split(":")[1])
    sub = await db.get_subscription(sub_id)
    if not sub:
        await callback.answer("Канал не найден.", show_alert=True)
        return
    link_line = sub.invite_link or "—"
    await callback.message.edit_text(
        f"📢 <b>{sub.title}</b>\n"
        f"ID: <code>{sub.chat_id}</code>\n"
        f"Срок: {subscription_period_text(sub)}\n"
        f"Ссылка: {link_line}",
        reply_markup=admin_sub_detail_kb(sub_id),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_sub")
async def cb_admin_add_sub(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "➕ <b>Добавить обязательную подписку</b>\n\nВыберите тип:",
        reply_markup=admin_add_sub_type_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_sub_type:"))
async def cb_admin_sub_type(callback: CallbackQuery, state: FSMContext) -> None:
    sub_type = callback.data.split(":")[1]
    if sub_type not in ("permanent", "temporary"):
        await callback.answer("Неизвестный тип.", show_alert=True)
        return

    await state.update_data(sub_type=sub_type)
    await state.set_state(AdminAddSub.link)

    type_hint = (
        "Подписка будет действовать, пока вы её не удалите."
        if sub_type == "permanent"
        else "После добавления канала укажете срок действия."
    )
    await callback.message.answer(
        f"➕ Отправьте <b>ссылку</b> на канал или чат:\n"
        f"• https://t.me/username\n"
        f"• @username\n\n"
        f"{type_hint}\n\n"
        "Бот должен быть <b>администратором</b> в канале/чате.\n\n"
        "Для приватного канала — перешлите сообщение из канала.",
        reply_markup=cancel_fsm_kb(),
    )
    await callback.answer()


@router.message(AdminAddSub.link)
async def admin_add_sub_link(
    message: Message, state: FSMContext, db: Database, bot: Bot
) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return

    try:
        chat, invite_link = await resolve_channel_from_message(bot, message)
    except BotNotAdminError as e:
        await message.answer(f"❌ {e}", reply_markup=main_menu_kb(True))
        return
    except InvalidLinkError as e:
        await message.answer(f"❌ {e}", reply_markup=main_menu_kb(True))
        return
    except ChannelResolveError as e:
        await message.answer(f"❌ {e}", reply_markup=main_menu_kb(True))
        return

    data = await state.get_data()
    sub_type = data.get("sub_type", "permanent")
    chat_id = chat_id_for_db(chat)
    title = chat.title or chat.username or chat_id

    await state.update_data(
        pending_chat_id=chat_id,
        pending_title=title,
        pending_invite_link=invite_link,
    )

    if sub_type == "permanent":
        await state.clear()
        await db.add_subscription(
            chat_id=chat_id,
            title=title,
            invite_link=invite_link,
            expires_at=None,
        )
        await message.answer(
            f"✅ Добавлено (бессрочно): <b>{title}</b>\n"
            f"ID: <code>{chat_id}</code>",
            reply_markup=main_menu_kb(True),
        )
        return

    await state.set_state(AdminAddSub.duration)
    await message.answer(
        f"Канал: <b>{title}</b>\n\n"
        "⏱ Укажите срок обязательной подписки:\n"
        "• <code>1ч</code>, <code>24ч</code>, <code>7д</code>, <code>30д</code>\n"
        "• или дату: <code>01.06.2026 18:00</code>",
        reply_markup=cancel_fsm_kb(),
    )


@router.message(AdminAddSub.duration)
async def admin_add_sub_duration(
    message: Message, state: FSMContext, db: Database
) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return

    expires_at = parse_duration_to_expires_at(message.text or "")
    if expires_at is None:
        await message.answer(
            "❌ Не удалось понять срок. Примеры: <code>24ч</code>, <code>7д</code>, "
            "<code>01.06.2026 18:00</code>"
        )
        return

    data = await state.get_data()
    await state.clear()

    chat_id = data["pending_chat_id"]
    title = data["pending_title"]
    invite_link = data.get("pending_invite_link")

    await db.add_subscription(
        chat_id=chat_id,
        title=title,
        invite_link=invite_link,
        expires_at=expires_at,
    )

    until = datetime.fromtimestamp(expires_at).strftime("%d.%m.%Y %H:%M")
    await message.answer(
        f"✅ Добавлено до <b>{until}</b>:\n<b>{title}</b>\n"
        f"ID: <code>{chat_id}</code>",
        reply_markup=main_menu_kb(True),
    )


@router.callback_query(F.data.startswith("admin_del_sub:"))
async def cb_admin_del_sub_confirm(callback: CallbackQuery, db: Database) -> None:
    sub_id = int(callback.data.split(":")[1])
    sub = await db.get_subscription(sub_id)
    if not sub:
        await callback.answer("Канал не найден.", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 Удалить обязательную подписку <b>{sub.title}</b>?",
        reply_markup=admin_delete_sub_confirm_kb(sub_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_sub_yes:"))
async def cb_admin_del_sub(callback: CallbackQuery, db: Database) -> None:
    sub_id = int(callback.data.split(":")[1])
    await db.delete_subscription(sub_id)
    subs = await db.list_subscriptions()
    text = "🗑 Подписка удалена.\n\n📢 <b>Обязательные подписки</b>"
    if not subs:
        text += "\n\n<i>Список пуст.</i>"
    await callback.message.edit_text(text, reply_markup=admin_subs_kb(subs))
    await callback.answer("Удалено")
