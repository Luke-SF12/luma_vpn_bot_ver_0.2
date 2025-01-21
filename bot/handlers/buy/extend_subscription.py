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
            SELECT id, plan, end_date, 
                   (SELECT file_name FROM configs WHERE configs.id = subscriptions.config_id) AS file_name
            FROM subscriptions WHERE user_id = $1 AND status = 'active'
        """, user_id)

        if not subscriptions:
            await send_error_message(callback, "❌ У вас еще нет активных подписок!")
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

        sub = subscriptions[0]
        await renew_subscription(callback, sub["id"])

@router.callback_query(lambda c: c.data.startswith("renew_"))
async def renew_subscription(callback: types.CallbackQuery, subscription_id: int = None):
    """Продлевает подписку пользователя на соответствующий срок"""

    if subscription_id is None:
        subscription_id = int(callback.data.split("_")[1])  # Парсим ID подписки из callback_data

    async with db.pool.acquire() as conn:
        sub = await conn.fetchrow("SELECT plan, end_date FROM subscriptions WHERE id = $1", subscription_id)

        if not sub:
            await send_error_message(callback, "❌ Подписка не найдена.")
            return

        plan_durations = {"1m": timedelta(days=30), "3m": timedelta(days=90), "6m": timedelta(days=180)}
        extension_period = plan_durations.get(sub["plan"], timedelta(days=30))  # По умолчанию 1 месяц

        end_date = sub["end_date"]
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

        new_end_date = end_date + extension_period

        await conn.execute("UPDATE subscriptions SET end_date = $1 WHERE id = $2", new_end_date, subscription_id)

        await callback.answer(f"✅ Подписка продлена! Новый срок действия до: {new_end_date.strftime('%d.%m.%Y')}", show_alert=True)

        await callback.message.delete()

        await callback.message.answer(
            f"✅ Ваша подписка успешно продлена!\n"
            f"📅 Новый срок действия до: <b>{new_end_date.strftime('%d.%m.%Y')}</b>",
            reply_markup=inline_menu()
        )

async def send_error_message(callback: types.CallbackQuery, error_text: str):
    await callback.message.edit_text(f"❌ {error_text}", reply_markup=inline_menu())
    await callback.answer()
