from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards import back_to_menu_kb, main_menu_kb, subscription_kb
from services.subscriptions import (
    get_missing_subscriptions,
    has_required_subscriptions,
)
from states import FindMovie

router = Router()


def _welcome_text() -> str:
    return (
        "👋 Добро пожаловать!\n\n"
        "Нажмите «🎬 Найти фильм» и введите код фильма, "
        "чтобы получить информацию."
    )


def _subscription_text() -> str:
    return (
        "📢 <b>Обязательная подписка</b>\n\n"
        "Чтобы пользоваться ботом, подпишитесь на каналы ниже, "
        "затем нажмите «✅ Проверить подписку»."
    )


async def _send_subscription_screen(
    target: Message | CallbackQuery, missing
) -> None:
    text = _subscription_text()
    markup = subscription_kb(missing)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup)


async def _send_welcome_menu(target: Message | CallbackQuery, is_admin: bool) -> None:
    text = _welcome_text()
    markup = main_menu_kb(is_admin)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup)


async def _send_start_screen(
    target: Message | CallbackQuery,
    bot: Bot,
    db: Database,
    is_admin: bool,
) -> None:
    if not await has_required_subscriptions(db):
        await _send_welcome_menu(target, is_admin)
        return

    user_id = target.from_user.id
    missing = await get_missing_subscriptions(bot, db, user_id)
    if missing:
        await _send_subscription_screen(target, missing)
    else:
        await _send_welcome_menu(target, is_admin)


@router.message(CommandStart())
async def cmd_start(
    message: Message, bot: Bot, db: Database, is_admin: bool
) -> None:
    await _send_start_screen(message, bot, db, is_admin)


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(
    callback: CallbackQuery, bot: Bot, db: Database, is_admin: bool, state: FSMContext
) -> None:
    await state.clear()
    await _send_start_screen(callback, bot, db, is_admin)


@router.callback_query(F.data == "check_subs")
async def cb_check_subs(
    callback: CallbackQuery, bot: Bot, db: Database, is_admin: bool
) -> None:
    if not await has_required_subscriptions(db):
        await callback.answer("Обязательных подписок нет.", show_alert=True)
        await _send_welcome_menu(callback, is_admin)
        return

    missing = await get_missing_subscriptions(bot, db, callback.from_user.id)
    if missing:
        await callback.answer(
            "Вы ещё не подписаны на все обязательные каналы.", show_alert=True
        )
        await callback.message.edit_text(
            _subscription_text(), reply_markup=subscription_kb(missing)
        )
        return

    await callback.answer("Подписка подтверждена!")
    await _send_welcome_menu(callback, is_admin)


@router.callback_query(F.data == "find_movie")
async def cb_find_movie(
    callback: CallbackQuery, bot: Bot, db: Database, state: FSMContext, is_admin: bool
) -> None:
    if await has_required_subscriptions(db):
        missing = await get_missing_subscriptions(bot, db, callback.from_user.id)
        if missing:
            await callback.answer(
                "Сначала подпишитесь на обязательные каналы.", show_alert=True
            )
            await _send_subscription_screen(callback, missing)
            return

    await state.set_state(FindMovie.waiting_code)
    await callback.message.edit_text(
        "🔢 Введите код фильма (например: <code>ABC123</code>):",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


@router.message(FindMovie.waiting_code)
async def process_movie_code(
    message: Message, bot: Bot, db: Database, state: FSMContext, is_admin: bool
) -> None:
    if await has_required_subscriptions(db):
        missing = await get_missing_subscriptions(bot, db, message.from_user.id)
        if missing:
            await state.clear()
            await message.answer(
                _subscription_text(),
                reply_markup=subscription_kb(missing),
            )
            return

    code = (message.text or "").strip()
    if not code:
        await message.answer("Введите код фильма.")
        return

    movie = await db.get_movie_by_code(code)
    await state.clear()

    if not movie:
        await message.answer(
            "❌ Фильм с таким кодом не найден. Проверьте код и попробуйте снова.",
            reply_markup=main_menu_kb(is_admin),
        )
        return

    lines = [f"🎬 <b>{movie.title}</b>", f"🔑 Код: <code>{movie.code}</code>"]
    if movie.description:
        lines.append(f"\n{movie.description}")
    if movie.link:
        lines.append(f"\n🔗 <a href=\"{movie.link}\">Смотреть / скачать</a>")

    await message.answer(
        "\n".join(lines),
        reply_markup=main_menu_kb(is_admin),
        disable_web_page_preview=False,
    )
