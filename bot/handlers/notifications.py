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
        CronTrigger(hour=19, minute=40),  # Каждый день в 19:00
        args=(bot,)
    )

    # Проверка истекших подписок каждый день в 20:00
    scheduler.add_job(
        check_expired_subscriptions,
        CronTrigger(hour=19, minute=45),  # Каждый день в 20:00
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
            SELECT s.user_id, s.end_date, c.name
            FROM subscriptions s
            LEFT JOIN configs c ON s.config_id = c.id
            WHERE s.status = 'active'
              AND DATE(s.end_date) = $1
        """, tomorrow)

        # Отправляем уведомления
        for sub in subscriptions:
            user_id = sub['user_id']
            config_name = sub['name']
            await send_notification(
                bot,
                user_id,
                f"<b>Уведомление!</b> 🔔\n\n"
                f"Срок действия вашей подписки на ключ <b>{config_name}</b> истекает завтра.\n\n"
                f"Чтобы избежать отключения, рекомендуем продлить подписку заранее:\n"
                f"1. В главном меню выберите <b>'🛒 Купить'</b>\n"
                f"2. Выберите тариф.\n"
                f"3. Оплатите удобным способом.\n"
                f"4. Продлите подписку.\n\n"
                f"Если подписка не будет продлена, текущий ключ будет удалён и станет недействительным. "
                f"В этом случае для подключения потребуется приобрести новый ключ.\n\n"
                f"Спасибо, что выбираете <b>LumaVPN</b>!"
            )

async def check_expired_subscriptions(bot: Bot):
    """Проверяет истекшие подписки, обновляет их статус и отправляет уведомления."""
    async with db.pool.acquire() as conn:
        # Получаем подписки, которые истекли
        expired_subscriptions = await conn.fetch("""
            SELECT s.user_id, c.name
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
            config_name = sub['name']
            await send_notification(
                bot,
                user_id,
                f"<b>Срок действия вашей подписки на ключ {config_name} истёк.</b>\n\n"
                "Ключ больше недоступен, но вы всегда можете приобрести подписку и пользоваться VPN без ограничений.\n\n"
                "Ваша <b>LumaVPN</b>!"
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