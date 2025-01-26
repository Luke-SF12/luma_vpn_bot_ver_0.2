import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.handlers.notifications import start_notification_scheduler, check_expiring_subscriptions, \
    check_expired_subscriptions
from config.config import BOT_TOKEN
from bot.handlers import register_handlers
from database.db import db

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

async def main():
    await db.connect()  # Подключение к БД
    #await db.create_tables()  # Создание таблиц
    register_handlers(dp)  # Регистрация обработчиков
    await start_notification_scheduler(bot)

    #await check_expired_subscriptions(bot)
    #await check_expiring_subscriptions(bot)

    await dp.start_polling(bot)  # Запуск бота

if __name__ == "__main__":
    asyncio.run(main())