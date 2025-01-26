import logging
from aiogram import Router, types
from bot.keyboards.inline import inline_menu
from database.db import db

router = Router()

@router.callback_query(lambda c: c.data == "get_config")
async def get_config_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            # Получаем последний успешный платеж
            payment = await conn.fetchrow(
                "SELECT amount FROM payments WHERE user_id = $1 AND status = 'succeeded' ORDER BY created_at DESC LIMIT 1",
                user_id
            )
            if not payment:
                await send_error_message(callback, "❌ Оплата не найдена!")
                return

            amount = payment['amount']
            duration = {129: 1, 369: 3, 699: 6}.get(amount, 1)

            # Блокируем первый доступный конфиг
            config = await conn.fetchrow("""
                SELECT * FROM configs 
                WHERE is_available = TRUE 
                LIMIT 1 
                FOR UPDATE SKIP LOCKED
            """)

            if not config:
                await send_error_message(callback, "❌ Нет свободных ключей!")
                return

            # Обновляем конфиг и создаем подписку
            await conn.execute(
                "UPDATE configs SET is_available = FALSE, user_id = $1 WHERE id = $2",
                user_id, config["id"]
            )

            await conn.execute("""
                INSERT INTO subscriptions (user_id, start_date, end_date, config_id)
                VALUES ($1, NOW(), NOW() + INTERVAL '1 month' * $2, $3)
            """, user_id, duration, config["id"])

            # Логирование
            logging.info(f"Ключ {config['name']} выдан пользователю {user_id}.")

            # Удаляем предыдущее сообщение с кнопками
            await callback.message.delete()

            # Отправляем ключ
            await callback.message.answer(
                f"✅ Ваш ключ готов!\n\n"
                f"🔑 Название: {config['name']}\n"
                f"Ключ: <code>{config['config_key']}</code>\n\n"
                f"Используйте его для настройки VPN."
            )

            # Отправляем главное меню
            await callback.message.answer(
                "📌 Выберите нужный раздел:",
                reply_markup=inline_menu()
            )

    await callback.answer()

async def send_error_message(callback: types.CallbackQuery, error_text: str):
    await callback.message.edit_text(f"❌ {error_text}", reply_markup=inline_menu())
    await callback.answer()