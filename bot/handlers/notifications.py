import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from datetime import datetime, timedelta

# Планировщик
scheduler = AsyncIOScheduler()

async def start_notification_scheduler(bot: Bot):
    """Запускает планировщик для проверки подписок."""
    # Проверка подписок, которые заканчиваются завтра, каждый день в 19:00
    scheduler.add_job(
        check_expiring_subscriptions,
        CronTrigger(hour=19, minute=00),  # Каждый день в 19:00
        args=(bot,)
    )

    # Проверка истекших подписок каждый день в 00:00
    scheduler.add_job(
        check_expired_subscriptions,
        CronTrigger(hour=0, minute=0),  # Каждый день в 00:00
        args=(bot,)
    )

    scheduler.start()

async def check_expiring_subscriptions(bot: Bot):
    """Проверяет подписки, которые заканчиваются завтра, и отправляет уведомления."""
    today = datetime.now().date()  # Сегодняшняя дата
    tomorrow = today + timedelta(days=1)  # Завтрашняя дата

    async with db.pool.acquire() as conn:
        # Получаем подписки, которые заканчиваются завтра (любое время)
        subscriptions = await conn.fetch("""
            SELECT s.user_id, s.end_date, c.file_name
            FROM subscriptions s
            LEFT JOIN configs c ON s.config_id = c.id
            WHERE s.status = 'active'
              AND DATE(s.end_date) = $1
        """, tomorrow)

        # Отправляем уведомления
        for sub in subscriptions:
            user_id = sub['user_id']
            file_name = sub['file_name']
            await send_notification(
                bot,
                user_id,
                f"⚠️ Ваша подписка на файл <b>{file_name}</b> заканчивается завтра!\n"
                "Не забудьте продлить её вовремя."
            )

async def check_expired_subscriptions(bot: Bot):
    """Проверяет истекшие подписки, обновляет их статус и отправляет уведомления."""
    async with db.pool.acquire() as conn:
        # Получаем подписки, которые истекли
        expired_subscriptions = await conn.fetch("""
            SELECT s.user_id, c.file_name
            FROM subscriptions s
            LEFT JOIN configs c ON s.config_id = c.id
            WHERE s.end_date < NOW() AND s.status = 'active'
        """)

        # Обновляем статус подписок на 'inactive'
        await conn.execute("""
            UPDATE subscriptions
            SET status = 'inactive'
            WHERE end_date < NOW() AND status = 'active'
        """)

        # Отправляем уведомления пользователям
        for sub in expired_subscriptions:
            user_id = sub['user_id']
            file_name = sub['file_name']
            await send_notification(
                bot,
                user_id,
                f"⚠️ Ваша подписка на файл <b>{file_name}</b> истекла.\n"
                "Доступ к файлу отключен."
            )

    logging.info("Статусы подписок обновлены.")

async def send_notification(bot: Bot, user_id: int, message_text: str):
    """Отправляет уведомление пользователю с кнопкой 'Понятно'."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Понятно", callback_data="dismiss_notification")]
    ])

    try:
        await bot.send_message(
            user_id,
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

# Обработчик для кнопки "Понятно"
from aiogram import Router

router = Router()

@router.callback_query(lambda c: c.data == "dismiss_notification")
async def handle_dismiss(callback: types.CallbackQuery):
    """Удаляет сообщение с уведомлением при нажатии на кнопку."""
    await callback.message.delete()
    await callback.answer()