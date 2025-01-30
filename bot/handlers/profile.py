from aiogram import Router, types
from database.db import db
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

router = Router()

@router.callback_query(lambda c: c.data == "profile")
async def profile_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    async with db.pool.acquire() as connection:
        # Получаем подписки пользователя без дублирования файлов
        subscriptions = await connection.fetch("""
            SELECT DISTINCT ON (c.id) s.end_date, c.name, p.amount
            FROM subscriptions s
            LEFT JOIN configs c ON s.config_id = c.id
            LEFT JOIN payments p ON s.user_id = p.user_id AND p.status = 'succeeded'
            WHERE s.user_id = $1 AND s.status = 'active'
            ORDER BY c.id, s.end_date DESC
        """, user_id)

    if not subscriptions:
        await callback.message.edit_text(
            "❌ Нет активных подписок",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]]
            )
        )
        return

    profile_text = ("👤 <b>Профиль</b>\n\n"
                    "<b>Подписки:</b>\n")
    for sub in subscriptions:
        end_date = sub['end_date']
        days_left = (end_date - datetime.now()).days if end_date else None

        profile_text += (
        f"🔑 <b>Название:</b> {sub['name'] or '❌'}\n"
        f"📅 <b>Действует до:</b> {end_date.strftime('%d.%m.%Y') if end_date else '❌'}\n"
        f"⏳ <b>Осталось дней:</b> {days_left if days_left else '❌'}\n\n"
    )

    await callback.message.edit_text(
        profile_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]]
        )
    )