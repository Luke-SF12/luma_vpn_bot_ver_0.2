import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

# Импорт handlers
from bot.handlers.notifications import start_notification_scheduler
from config.config import BOT_TOKEN
from bot.handlers import register_handlers
from database.db import db

from logger import sync_logger, async_logger

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

async def main():
    try:
        await db.connect()
        sync_logger.info("Подключение к базе данных успешно.")

        await db.create_tables()
        sync_logger.info("Таблицы успешно созданы.")

        register_handlers(dp)
        sync_logger.info("Обработчики успешно зарегистрированы.")

        await start_notification_scheduler(bot)
        sync_logger.info("Планировщик уведомлений запущен.")

        sync_logger.info("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        sync_logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
    finally:
        sync_logger.info("Закрытие соединения с базой данных...")
        await db.close()
        sync_logger.info("Соединение с базой данных закрыто.")


if __name__ == "__main__":
    asyncio.run(main())