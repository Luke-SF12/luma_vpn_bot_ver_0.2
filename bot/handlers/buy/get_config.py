import logging
from aiogram import Router, types
from bot.keyboards.inline import inline_menu
from database.db import db
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.yookassa import check_payment
from database.db import db
from bot.keyboards.inline import inline_menu
from datetime import datetime, timedelta, timezone

router = Router()

@router.callback_query(lambda c: c.data == "get_config")
async def get_config_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if datetime.now(timezone.utc) - callback.message.date > timedelta(hours=24):
        await callback.answer("❌ Это сообщение устарело. Пожалуйста, начните процесс заново.", show_alert=True)
        await callback.message.delete()
        await callback.message.answer(
            "<b>Выберите необходимый раздел ниже:</b>",
            reply_markup=inline_menu()
        )
        return

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            # Получаем последний успешный платеж
            payment = await conn.fetchrow(
                "SELECT amount FROM payments WHERE user_id = $1 AND status = 'succeeded' ORDER BY created_at DESC LIMIT 1",
                user_id
            )
            if not payment:
                await send_error_message(callback, "Оплата не найдена!")
                return

            amount = payment['amount']
            duration = {100: 1, 285: 3, 540: 6}.get(amount, 1)

            # Блокируем первый доступный конфиг
            config = await conn.fetchrow("""
                SELECT * FROM configs 
                WHERE is_available = TRUE 
                LIMIT 1 
                FOR UPDATE SKIP LOCKED
            """)

            if not config:
                await callback.answer("❌ Нет свободных ключей!", show_alert=True)
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

            payment = await conn.fetchrow(
                "SELECT id FROM payments WHERE user_id = $1 AND status = 'succeeded' ORDER BY created_at DESC LIMIT 1",
                user_id
            )
            if payment:
                bonus_applied = await db.apply_referral_bonus(user_id, payment['id'])
                if bonus_applied:
                    referrer_id = await conn.fetchval(
                        "SELECT referrer_id FROM referrals WHERE referred_id = $1",
                        user_id
                    )
                    if referrer_id:
                        try:
                            await callback.bot.send_message(
                                chat_id=referrer_id,
                                text=f"🎉 Ваш реферал оплатил подписку!\n"
                                     f"Вам начислено +20 дней к подписке!"
                            )
                        except:
                            pass

            # Логирование
            logging.info(f"Ключ {config['name']} выдан пользователю {user_id}.")

            # Удаляем предыдущее сообщение с кнопками
            await callback.message.delete()

            # Отправляем ключ
            await callback.message.answer(
                f"✅ <b>Ваш VPN-ключ успешно создан!</b>\n\n"
                f"<b>- Название:</b> {config['name']}\n"
                f"<b>- Ключ:</b> <code>{config['config_key']}</code>\n\n"
                f"Спасибо, что вы выбрали LumaVPN. Ваша безопасность и свобода — приоритет.\n\n"
                f"<b>Скопируйте этот ключ и используйте его для настройки VPN.</b>"
            )

            # Отправляем главное меню
            await callback.message.answer(
                "<b>Выберите необходимый раздел ниже:</b>",
                reply_markup=inline_menu()
            )

    await callback.answer()

async def send_error_message(callback: types.CallbackQuery, error_text: str):
    await callback.message.edit_text(f"❌ {error_text}", reply_markup=inline_menu())
    await callback.answer()