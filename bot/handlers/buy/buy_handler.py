from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards.inline import inline_menu
from services.yookassa import create_payment
from database.db import db
from logger import sync_logger, async_logger

router = Router()

# Клавиатура с выбором тарифа
def subscription_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц – 129₽", callback_data="buy_1m")],
            [InlineKeyboardButton(text="3 месяца – 369₽ (5%)", callback_data="buy_3m")],
            [InlineKeyboardButton(text="6 месяцев – 699₽ (10%)", callback_data="buy_6m")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
        ]
    )

@router.callback_query(lambda c: c.data == "buy")
async def show_subscriptions(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    sync_logger.info(f"Пользователь {user_id} начал процесс покупки.")
    async with db.pool.acquire() as conn:
        # Проверяем наличие активных подписок
        active_subs = await conn.fetchval(
            "SELECT COUNT(*) FROM subscriptions WHERE user_id = $1 AND status = 'active'",
            user_id
        )

        if active_subs == 0:
            # Для новых пользователей проверяем ключи
            available_configs = await conn.fetchval(
                "SELECT COUNT(*) FROM configs WHERE is_available = TRUE"
            )
            if not available_configs:
                sync_logger.warning(f"Нет свободных ключей для пользователя {user_id}.")
                await callback.answer("❌ Нет свободных ключей!", show_alert=True)
                return

    # Показываем тарифы, если проверки пройдены
    await callback.message.edit_text("<b>Выберите необходимый тариф ниже:</b>", reply_markup=subscription_keyboard())

@router.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "unknown"
    plan = callback.data.split("_")[1]

    prices = {"1m": 129, "3m": 369, "6m": 699}
    amount = prices.get(plan, 129)

    sync_logger.info(f"Пользователь {user_id} выбрал тариф: {plan} ({amount}₽).")

    async with db.pool.acquire() as connection:
        user = await connection.fetchrow("SELECT * FROM users WHERE tg_id = $1", user_id)
        if not user:
            sync_logger.info(f"Новый пользователь {user_id} добавлен в базу данных.")
            await connection.execute("INSERT INTO users (tg_id, username) VALUES ($1, $2)", user_id, username)

        payment_id, payment_link = await create_payment(amount, user_id)
        sync_logger.info(f"Платеж создан: ID={payment_id}, Ссылка={payment_link}.")
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
        f"💳 <b>Оплата подписки: {amount}₽</b>\n\n"
        f"1. Нажмите кнопку <b>«✅ Оплатить»</b> ниже и завершите оплату.\n"
        f"2. После оплаты вернитесь в бот и нажмите <b>«🔄 Проверить оплату»</b>.\n\n",
        reply_markup=payment_keyboard
    )
    await callback.answer()