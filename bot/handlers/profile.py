from aiogram import Router, types
from database.db import db
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.callback_query(lambda c: c.data == "profile")
async def profile_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    async with db.pool.acquire() as connection:
        # Получаем подписки пользователя (даже если нет привязанного конфига)
        subscriptions = await connection.fetch("""
            SELECT s.plan, s.end_date, COALESCE(c.file_name, '❌ Нет конфига') AS file_name
            FROM subscriptions s
            LEFT JOIN configs c ON s.config_id = c.id
            WHERE s.user_id = $1 AND s.status = 'active'
        """, user_id)

    # Если подписок нет, отправляем сообщение
    if not subscriptions:
        await callback.message.edit_text(
            "❌ У вас нет активных подписок.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]]
            )
        )
        return

    # 📌 Формируем текст профиля
    profile_text = "📌 <b>Ваши подписки:</b>\n\n"
    for sub in subscriptions:
        # Проверяем, есть ли `end_date`, иначе ставим "❌ Неизвестно"
        end_date = sub['end_date']
        formatted_date = end_date.strftime('%d.%m.%Y') if end_date else "❌ Неизвестно"

        profile_text += (
            f"🗂 <b>Файл:</b> {sub['file_name']}\n"
            f"📅 <b>Истекает:</b> {formatted_date}\n"
            f"📦 <b>Тариф:</b> {sub['plan']}\n\n"
        )

    # Отправляем пользователю данные о подписке
    await callback.message.edit_text(
        profile_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]]
        )
    )
