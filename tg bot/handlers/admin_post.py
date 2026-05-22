from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards import admin_panel_kb, admin_post_confirm_kb, cancel_fsm_kb, main_menu_kb
from services.broadcast import broadcast_post
from states import AdminPost

router = Router()


class AdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, is_admin: bool) -> bool:
        return is_admin


router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.callback_query(F.data == "admin_post")
async def cb_admin_post(
    callback: CallbackQuery, state: FSMContext, db: Database
) -> None:
    await state.clear()
    count = await db.count_broadcast_users()
    await state.set_state(AdminPost.waiting_content)
    await callback.message.edit_text(
        "📝 <b>Написать пост</b>\n\n"
        f"Получателей в базе: <b>{count}</b>\n"
        "(все, кто писал боту или нажимал кнопки)\n\n"
        "Отправьте текст поста или сообщение с фото/видео.\n"
        "Поддерживается форматирование Telegram.",
        reply_markup=None,
    )
    await callback.message.answer(
        "Жду ваш пост…",
        reply_markup=cancel_fsm_kb(),
    )
    await callback.answer()


@router.message(AdminPost.waiting_content)
async def admin_post_content(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb(True))
        return

    if not message.text and not (
        message.photo
        or message.video
        or message.document
        or message.animation
        or message.voice
        or message.video_note
    ):
        await message.answer(
            "Отправьте текст или медиа (фото, видео, документ)."
        )
        return

    await state.update_data(
        post_chat_id=message.chat.id,
        post_message_id=message.message_id,
    )
    await state.set_state(AdminPost.confirm)

    await message.answer("👁 <b>Предпросмотр поста:</b>")
    await bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await message.answer(
        "Отправить этот пост всем пользователям?",
        reply_markup=admin_post_confirm_kb(),
    )


@router.message(AdminPost.confirm, F.text == "❌ Отмена")
async def admin_post_confirm_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb(True))


@router.callback_query(F.data == "admin_post_cancel")
async def cb_admin_post_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Публикация отменена.",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_post_send")
async def cb_admin_post_send(
    callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot
) -> None:
    data = await state.get_data()
    chat_id = data.get("post_chat_id")
    message_id = data.get("post_message_id")
    if not chat_id or not message_id:
        await callback.answer("Пост не найден. Создайте заново.", show_alert=True)
        return

    total_users = await db.count_broadcast_users()
    if total_users == 0:
        await callback.answer(
            "В базе 0 пользователей. Пусть пользователи напишут боту /start.",
            show_alert=True,
        )
        return

    await state.clear()
    await callback.message.edit_text(
        f"📤 Рассылка началась ({total_users} получателей), подождите…"
    )

    result = await broadcast_post(
        bot,
        db,
        from_chat_id=int(chat_id),
        message_id=int(message_id),
    )

    await callback.message.edit_text(
        "✅ <b>Рассылка завершена</b>\n\n"
        f"Всего в базе: {result.total}\n"
        f"Доставлено: {result.sent}\n"
        f"Заблокировали бота: {result.blocked}\n"
        f"Ошибок: {result.failed}",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()
