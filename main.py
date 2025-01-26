import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

# Импорт handlers

from bot.handlers.notifications import start_notification_scheduler
from config.config import BOT_TOKEN
from bot.handlers import register_handlers
from database.db import db

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


async def main():
    # Подключение к БД
    await db.connect()

    # Регистрация всех обработчиков
    register_handlers(dp)  # Основные обработчики

    # Запуск планировщика уведомлений
    await start_notification_scheduler(bot)

    # Запуск бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())