import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from config.config import BOT_TOKEN
from bot.handlers import register_handlers  # Импорт обработчиков
from database import db

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

async def main():
    await db.connect()  # Подключаемся к БД
    #await db.create_tables()  # Создаем таблицы (если нет)
    register_handlers(dp)  # Подключаем обработчики
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
