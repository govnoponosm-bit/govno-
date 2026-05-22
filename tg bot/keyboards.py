from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from database import Movie, Subscription


def main_menu_kb(is_admin: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎬 Найти фильм", callback_data="find_movie")
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")
        )
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")]
        ]
    )


def subscription_kb(subs: list[Subscription]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sub in subs:
        url = sub.invite_link
        if not url and sub.chat_id.startswith("@"):
            url = f"https://t.me/{sub.chat_id.lstrip('@')}"
        if url:
            builder.row(
                InlineKeyboardButton(text=f"📢 {sub.title}", url=url)
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text=f"📢 {sub.title}",
                    callback_data="check_subs",
                )
            )
    builder.row(
        InlineKeyboardButton(
            text="✅ Проверить подписку", callback_data="check_subs"
        )
    )
    return builder.as_markup()


def admin_panel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎬 Фильмы", callback_data="admin_movies"),
        InlineKeyboardButton(text="📢 Подписки", callback_data="admin_subs"),
    )
    builder.row(
        InlineKeyboardButton(text="📝 Написать пост", callback_data="admin_post"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")
    )
    return builder.as_markup()


def admin_post_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📤 Отправить всем", callback_data="admin_post_send"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_post_cancel"),
    )
    return builder.as_markup()


def admin_movies_kb(movies: list[Movie]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить фильм", callback_data="admin_add_movie")
    )
    for movie in movies:
        title = movie.title[:22] + "…" if len(movie.title) > 22 else movie.title
        builder.row(
            InlineKeyboardButton(
                text=f"🎬 {movie.code} — {title}",
                callback_data=f"admin_movie:{movie.id}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"admin_del_movie:{movie.id}",
            ),
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Админ-панель", callback_data="admin_panel")
    )
    return builder.as_markup()


def admin_delete_movie_confirm_kb(movie_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"admin_del_movie_yes:{movie_id}",
        ),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_movies"),
    )
    return builder.as_markup()


def admin_movie_detail_kb(movie_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ Редактировать", callback_data=f"admin_edit_movie:{movie_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить", callback_data=f"admin_del_movie:{movie_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ К списку", callback_data="admin_movies")
    )
    return builder.as_markup()


def _sub_list_label(sub: Subscription) -> str:
    title = sub.title[:16] + "…" if len(sub.title) > 16 else sub.title
    if sub.is_permanent:
        badge = "♾️"
    elif sub.is_active:
        badge = "⏱"
    else:
        badge = "⌛"
    return f"{badge} {title}"


def admin_add_sub_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="♾️ Пока не отменю",
            callback_data="admin_sub_type:permanent",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⏱ На определённое время",
            callback_data="admin_sub_type:temporary",
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_subs")
    )
    return builder.as_markup()


def admin_subs_kb(subs: list[Subscription]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin_add_sub")
    )
    for sub in subs:
        builder.row(
            InlineKeyboardButton(
                text=_sub_list_label(sub),
                callback_data=f"admin_sub:{sub.id}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"admin_del_sub:{sub.id}",
            ),
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Админ-панель", callback_data="admin_panel")
    )
    return builder.as_markup()


def admin_delete_sub_confirm_kb(sub_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"admin_del_sub_yes:{sub_id}",
        ),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subs"),
    )
    return builder.as_markup()


def admin_sub_detail_kb(sub_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить", callback_data=f"admin_del_sub:{sub_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ К списку", callback_data="admin_subs")
    )
    return builder.as_markup()


def cancel_fsm_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)
