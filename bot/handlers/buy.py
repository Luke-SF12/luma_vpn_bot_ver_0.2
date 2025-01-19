from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from services.yookassa import create_payment, check_payment
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
    await callback.message.edit_text("Выберите тариф:", reply_markup=subscription_keyboard())
    await callback.answer()

# Оформление подписки
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

# Проверка оплаты
@router.callback_query(lambda c: c.data.startswith("check_payment_"))
async def check_payment_handler(callback: types.CallbackQuery):
    payment_id = callback.data.split("_")[2]

    async with db.pool.acquire() as connection:
        payment = await connection.fetchrow(
            "SELECT * FROM payments WHERE payment_id = $1 AND status = 'pending'", payment_id
        )

        if not payment:
            await callback.answer("❌ Нет ожидаемых платежей.")
            return

        is_paid = await check_payment(payment_id)

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

# Выдача конфигурационного файла
@router.callback_query(lambda c: c.data == "get_config")
async def get_config_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    async with db.pool.acquire() as connection:
        config = await connection.fetchrow(
            "SELECT * FROM configs WHERE is_available = TRUE LIMIT 1"
        )

        if not config:
            await callback.message.edit_text(
                "❌ Свободных конфигов нет. Обратитесь к администратору.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="📍 Меню", callback_data="back_to_menu")]
                    ]
                )
            )
            return

        file_path = config["file_path"]
        file_name = config["file_name"]

        # Отправляем конфиг пользователю
        file = FSInputFile(file_path, filename=file_name)
        await callback.message.answer_document(file, caption="🎉 Ваш конфиг готов!")

        # Отмечаем конфиг как занятый
        await connection.execute(
            "UPDATE configs SET is_available = FALSE WHERE id = $1", config["id"]
        )

    await callback.answer()

# Продление подписки
@router.callback_query(lambda c: c.data == "extend_subscription")
async def extend_subscription_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    async with db.pool.acquire() as connection:
        subscription = await connection.fetchrow(
            "SELECT * FROM subscriptions WHERE user_id = $1 AND status = 'active'", user_id
        )

        if not subscription:
            await callback.answer("❌ У вас нет активной подписки.")
            return

        # Определяем новый срок подписки
        plan_durations = {"1m": "1 month", "3m": "3 months", "6m": "6 months"}
        plan = subscription["plan"]
        if plan not in plan_durations:
            await callback.answer("⚠ Ошибка: неподдерживаемый план подписки.")
            return

        new_end_date = subscription["end_date"] + plan_durations[plan]

        # Обновляем дату окончания подписки
        await connection.execute(
            "UPDATE subscriptions SET end_date = $1 WHERE user_id = $2",
            new_end_date, user_id
        )

        await callback.message.edit_text("✅ Подписка продлена!")
    await callback.answer()
