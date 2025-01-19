from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.yookassa import create_payment
from database.db import connect_db
from services.yookassa import check_payment

router = Router()


@router.callback_query(lambda c: c.data == "buy")
async def show_subscriptions(callback: types.CallbackQuery):
    await callback.message.edit_text("Выберите тариф:", reply_markup=subscription_keyboard())
    await callback.answer()

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


@router.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "unknown"
    plan = callback.data.split("_")[1]

    prices = {"1m": 129, "3m": 369, "6m": 699}
    amount = prices.get(plan, 129)

    conn = await connect_db()
    async with conn.acquire() as connection:
        user = await connection.fetchrow("SELECT * FROM users WHERE tg_id = $1", user_id)
        if not user:
            await connection.execute("INSERT INTO users (tg_id, username) VALUES ($1, $2)", user_id, username)

        # Генерируем ID платежа и ссылку на оплату
        payment_id, payment_link = await create_payment(amount, user_id)

        # Сохраняем ID платежа в БД (а не ссылку)
        await connection.execute(
            "INSERT INTO payments (user_id, payment_id, amount, status, payment_link) VALUES ($1, $2, $3, $4, $5)",
            user_id, payment_id, amount, "pending", payment_link
        )

    # Отправляем пользователю сообщение
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




@router.callback_query(lambda c: c.data.startswith("check_payment_"))
async def check_payment_handler(callback: types.CallbackQuery):
    payment_id = callback.data.split("_")[2]  # Получаем payment_id, а не user_id!

    conn = await connect_db()
    async with conn.acquire() as connection:
        payment = await connection.fetchrow(
            "SELECT * FROM payments WHERE payment_id = $1 AND status = 'pending'", payment_id
        )

        if not payment:
            await callback.answer("❌ Нет ожидаемых платежей.")
            return

        is_paid = await check_payment(payment_id)  # Проверяем платеж в YooKassa

        if is_paid:
            await connection.execute("UPDATE payments SET status = 'success' WHERE payment_id = $1", payment_id)

            action_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🎟 Приобрести", callback_data="get_config")],
                    [InlineKeyboardButton(text="🔄 Продлить", callback_data="extend_subscription")]
                ]
            )

            await callback.message.edit_text("✅ Оплата прошла успешно!", reply_markup=action_keyboard)
        else:
            await callback.answer("⚠ Оплата не найдена. Попробуйте позже.")
