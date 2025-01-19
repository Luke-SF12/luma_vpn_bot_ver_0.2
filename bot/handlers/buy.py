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

    async with db.pool.acquire() as conn:
        # Получаем свободный конфиг
        config = await conn.fetchrow("SELECT * FROM configs WHERE is_available = TRUE LIMIT 1")

        if not config:
            await callback.message.answer("❌ Нет доступных конфигов. Обратитесь к администратору.")
            return

        # Привязываем конфиг к пользователю
        await conn.execute("UPDATE configs SET is_available = FALSE, user_id = $1 WHERE id = $2", user_id, config["id"])

        # Создаём подписку
        await conn.execute("""
            INSERT INTO subscriptions (user_id, plan, start_date, end_date, status, config_id)
            VALUES ($1, '1m', NOW(), NOW() + INTERVAL '1 month', 'active', $2)
        """, user_id, config["id"])

        # Отправляем конфиг
        file = FSInputFile(config["file_path"], filename=config["file_name"])
        await callback.message.answer_document(file, caption="✅ Ваш конфиг готов!")

    await callback.answer()







# Продление подписки
@router.callback_query(lambda c: c.data == "extend_subscription")
async def extend_subscription_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    async with db.pool.acquire() as conn:
        subs = await conn.fetch("""
            SELECT id, plan, end_date, 
                   (SELECT file_name FROM configs WHERE configs.id = subscriptions.config_id) AS file_name
            FROM subscriptions WHERE user_id = $1 AND status = 'active'
        """, user_id)

        if not subs:
            await callback.message.answer("❌ У вас нет активных подписок.")
            return

        if len(subs) > 1:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=sub["file_name"], callback_data=f"renew_{sub['id']}")]
                    for sub in subs
                ]
            )
            await callback.message.edit_text("Выберите подписку для продления:", reply_markup=keyboard)
            return

        sub = subs[0]
        await renew_subscription(callback, sub["id"])


@router.callback_query(lambda c: c.data.startswith("renew_"))
async def renew_subscription(callback: types.CallbackQuery, subscription_id: int = None):
    """Продлевает подписку пользователя"""
    if subscription_id is None:
        subscription_id = int(callback.data.split("_")[1])

    async with db.pool.acquire() as conn:
        sub = await conn.fetchrow("SELECT * FROM subscriptions WHERE id = $1", subscription_id)

        if not sub:
            await callback.message.answer("❌ Подписка не найдена.")
            return

        # Определяем новую дату окончания подписки
        extension_map = {"1m": "1 month", "3m": "3 months", "6m": "6 months"}
        extension = extension_map.get(sub["plan"], "1 month")

        await conn.execute(f"""
            UPDATE subscriptions 
            SET end_date = end_date + INTERVAL '{extension}' 
            WHERE id = $1
        """, subscription_id)

        await callback.message.edit_text("✅ Подписка успешно продлена!")
        await callback.answer()