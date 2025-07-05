import asyncio

from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.keyboards.inline import inline_menu
from services.yookassa import create_payment
from database.db import db
from logger import sync_logger, async_logger
from bot.states.user import UserStates  # Импортируем состояние для email
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.yookassa import check_payment
from database.db import db
from bot.keyboards.inline import inline_menu

router = Router()

# Клавиатура с выбором тарифа
def subscription_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц – 100₽", callback_data="buy_1m")],
            [InlineKeyboardButton(text="3 месяца – 285₽ (5%)", callback_data="buy_3m")],
            [InlineKeyboardButton(text="6 месяцев – 540₽ (10%)", callback_data="buy_6m")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
        ]
    )

@router.callback_query(lambda c: c.data == "buy")
async def show_subscriptions(callback: types.CallbackQuery):
    if datetime.now() - callback.message.date.replace(tzinfo=None) > timedelta(hours=24):
        await callback.answer("❌ Это сообщение устарело. Пожалуйста, начните процесс заново.", show_alert=True)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            "<b>Выберите необходимый раздел ниже:</b>",
            reply_markup=inline_menu()
        )
        return
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
async def buy_handler(callback: types.CallbackQuery, state: FSMContext):
    if datetime.now() - callback.message.date.replace(tzinfo=None) > timedelta(hours=24):
        await callback.answer("❌ Это сообщение устарело. Пожалуйста, начните процесс заново.", show_alert=True)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            "<b>Выберите необходимый раздел ниже:</b>",
            reply_markup=inline_menu()
        )
        return
    user_id = callback.from_user.id
    username = callback.from_user.username or "unknown"
    plan = callback.data.split("_")[1]

    prices = {"1m": 100, "3m": 285, "6m": 540}
    amount = prices.get(plan, 100)

    # Сохраняем данные о платеже в состоянии
    await state.update_data(amount=amount, plan=plan)

    # Проверяем, есть ли пользователь в базе и есть ли у него email
    async with db.pool.acquire() as connection:
        user = await connection.fetchrow("SELECT * FROM users WHERE tg_id = $1", user_id)
        if user and user.get("email"):
            # Если email есть, сразу создаем платеж
            payment_id, payment_link = await create_payment(amount, user_id, user["email"])

            await connection.execute(
                "INSERT INTO payments (user_id, payment_id, amount, status, payment_link) VALUES ($1, $2, $3, $4, $5)",
                user_id, payment_id, amount, "pending", payment_link
            )

            await process_payment(callback, payment_id, payment_link, amount)
        else:
            # Если email отсутствует, запрашиваем его и сохраняем message_id
            email_request_message = await callback.message.edit_text(
                "📧 Пожалуйста, введите ваш email для отправки чека:",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="buy")]
                    ]
                )
            )
            await state.update_data(email_request_message_id=email_request_message.message_id)
            await state.set_state(UserStates.waiting_for_email)

async def process_payment(callback: types.CallbackQuery, payment_id: str, payment_link: str, amount: int):
    """Отправляет пользователю ссылку на оплату"""
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


@router.message(UserStates.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    user_email = message.text

    # Проверяем валидность email
    if "@" not in user_email or "." not in user_email.split("@")[1]:
        await message.answer("❌ Неверный формат email. Пожалуйста, введите корректный email.")
        return

    # Получаем данные о платеже из состояния
    data = await state.get_data()
    amount = data["amount"]
    plan = data["plan"]
    email_request_message_id = data.get("email_request_message_id")

    # Удаляем сообщение, в котором пользователь ввел email
    try:
        await message.delete()
    except Exception:
        pass  # Игнорируем, если сообщение уже удалено

    # Если email успешно сохранён, удаляем сообщение с запросом email
    if email_request_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=email_request_message_id)
        except Exception:
            pass  # Игнорируем, если сообщение уже удалено

    # Сохраняем email в базе данных
    async with db.pool.acquire() as connection:
        user = await connection.fetchrow("SELECT * FROM users WHERE tg_id = $1", message.from_user.id)
        if not user:
            await connection.execute(
                "INSERT INTO users (tg_id, username, email) VALUES ($1, $2, $3)",
                message.from_user.id, message.from_user.username or "unknown", user_email
            )
        else:
            await connection.execute(
                "UPDATE users SET email = $1 WHERE tg_id = $2",
                user_email, message.from_user.id
            )

    # Подтверждение сохранения email (удалится через 2 секунды)
    confirmation_message = await message.answer(f"✅ Ваш email <b>{user_email}</b> успешно сохранен!", parse_mode="HTML")

    await asyncio.sleep(3.5)  # Даем пользователю увидеть сообщение
    try:
        await confirmation_message.delete()
    except Exception:
        pass  # Игнорируем ошибку, если уже удалено

    # Создаем платеж
    payment_id, payment_link = await create_payment(amount, message.from_user.id, user_email)

    # Сохраняем платеж в базе данных
    async with db.pool.acquire() as connection:
        await connection.execute(
            "INSERT INTO payments (user_id, payment_id, amount, status, payment_link) VALUES ($1, $2, $3, $4, $5)",
            message.from_user.id, payment_id, amount, "pending", payment_link
        )

    # Отправляем пользователю ссылку на оплату
    payment_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оплатить", url=payment_link)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_payment_{payment_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="buy")]
        ]
    )

    await message.answer(
        f"💳 <b>Оплата подписки: {amount}₽</b>\n\n"
        f"1. Нажмите кнопку <b>«✅ Оплатить»</b> ниже и завершите оплату.\n"
        f"2. После оплаты вернитесь в бот и нажмите <b>«🔄 Проверить оплату»</b>.\n\n",
        reply_markup=payment_keyboard
    )

    # Сбрасываем состояние
    await state.clear()