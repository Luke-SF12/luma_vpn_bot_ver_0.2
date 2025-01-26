from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards.inline import inline_menu
from database.db import db

router = Router()

@router.callback_query(lambda c: c.data == "extend_subscription")
async def extend_subscription_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    async with db.pool.acquire() as conn:
        subscriptions = await conn.fetch("""
            SELECT s.id, s.end_date, c.file_name
            FROM subscriptions s
            LEFT JOIN configs c ON s.config_id = c.id
            WHERE s.user_id = $1 AND s.status = 'active'
        """, user_id)

        if not subscriptions:
            await callback.answer("❌ У вас еще нет активных подписок!", show_alert=True)
            return

        if len(subscriptions) > 1:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=sub["file_name"], callback_data=f"renew_{sub['id']}")]
                    for sub in subscriptions
                ]
            )
            await callback.message.edit_text("Выберите подписку для продления:", reply_markup=keyboard)
            return

        # Если подписка одна, сразу продлеваем её
        await renew_subscription(callback, subscriptions[0]['id'])

@router.callback_query(lambda c: c.data.startswith("renew_"))
async def renew_subscription(callback: types.CallbackQuery, subscription_id: int = None):
    """Продлевает подписку пользователя на соответствующий срок"""
    if subscription_id is None:
        # Если subscription_id не передан, извлекаем его из callback.data
        subscription_id = int(callback.data.split("_")[1])  # Парсим ID подписки из callback_data

    async with db.pool.acquire() as conn:
        # Получаем последний успешный платеж пользователя
        payment = await conn.fetchrow(
            "SELECT amount FROM payments WHERE user_id = $1 AND status = 'succeeded' ORDER BY created_at DESC LIMIT 1",
            callback.from_user.id
        )

        if not payment:
            await send_error_message(callback, "❌ Оплата не найдена. Обратитесь в поддержку.")
            return

        amount = payment['amount']
        duration = {129: 1, 369: 3, 699: 6}.get(amount, 1)  # Определяем длительность продления

        # Продлеваем подписку
        await conn.execute("""
            UPDATE subscriptions 
            SET end_date = end_date + INTERVAL '1 month' * $1 
            WHERE id = $2
        """, duration, subscription_id)

        # Получаем новую дату окончания
        new_end_date = await conn.fetchval("""
            SELECT end_date FROM subscriptions WHERE id = $1
        """, subscription_id)

        await callback.answer(
            f"✅ Подписка продлена! Новый срок действия до: {new_end_date.strftime('%d.%m.%Y')}",
            show_alert=True
        )

        await callback.message.delete()
        await callback.message.answer(
            f"✅ Ваша подписка успешно продлена!\n"
            f"📅 Новый срок действия до: <b>{new_end_date.strftime('%d.%m.%Y')}</b>",
            reply_markup=inline_menu()
        )

async def send_error_message(callback: types.CallbackQuery, error_text: str):
    """Универсальный метод для отправки ошибок"""
    await callback.message.edit_text(f"❌ {error_text}", reply_markup=inline_menu())
    await callback.answer()