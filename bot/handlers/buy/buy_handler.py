from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards.inline import inline_menu
from services.yookassa import create_payment
from database.db import db

router = Router()

# Клавиатура с выбором тарифа
def subscription_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц – 129₽", callback_data="buy_1m")],
            [InlineKeyboardButton(text="3 месяца – 369₽", callback_data="buy_3m")],
            [InlineKeyboardButton(text="6 месяцев – 699₽", callback_data="buy_6m")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
        ]
    )

@router.callback_query(lambda c: c.data == "buy")
async def show_subscriptions(callback: types.CallbackQuery):
    async with db.pool.acquire() as conn:
        # Проверяем наличие свободных файлов
        available_configs = await conn.fetchval("""
            SELECT COUNT(*) FROM configs WHERE is_available = TRUE
        """)

        if not available_configs:
            await callback.answer("❌ Свободных файлов нет. Обратитесь к администратору.", show_alert=True)
            return

    await callback.message.edit_text("Выберите тариф для покупки:", reply_markup=subscription_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "unknown"
    plan = callback.data.split("_")[1]

    prices = {"1m": 129, "3m": 369, "6m": 699}
    amount = prices.get(plan, 129)

    async with db.pool.acquire() as connection:
        user = await connection.fetchrow("SELECT * FROM users WHERE tg_id = $1", user_id)
        if not user:
            await connection.execute("INSERT INTO users (tg_id, username) VALUES ($1, $2)", user_id, username)

        payment_id, payment_link = await create_payment(amount, user_id)
        await connection.execute(
            "INSERT INTO payments (user_id, payment_id, amount, status, payment_link) VALUES ($1, $2, $3, $4, $5)",
            user_id, payment_id, amount, "pending", payment_link
        )

    payment_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оплатить", url=payment_link)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_payment_{payment_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="buy")]
        ]
    )

    await callback.message.edit_text(
        f"💳 Оплата подписки ({plan}): {amount}₽\n\n"
        f"Нажмите кнопку ниже, чтобы оплатить.",
        reply_markup=payment_keyboard
    )
    await callback.answer()