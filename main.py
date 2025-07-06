import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from bot.handlers.notifications import start_notification_scheduler
from config.config import BOT_TOKEN
from bot.handlers import register_handlers
from database.db import db
from logger import sync_logger, async_logger

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


async def migrate_database():
    """Миграция базы данных для существующих пользователей"""
    try:
        await db.connect()
        async with db.pool.acquire() as conn:
            # Добавляем новые поля и таблицы если их нет
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS referral_code TEXT
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL REFERENCES users(tg_id),
                    referred_id BIGINT NOT NULL UNIQUE REFERENCES users(tg_id),
                    referral_date TIMESTAMP DEFAULT NOW(),
                    bonus_applied BOOLEAN DEFAULT FALSE,
                    payment_id INTEGER REFERENCES payments(id)
                )
            """)
            # Обновляем referral_code для существующих пользователей
            await conn.execute("""
                UPDATE users 
                SET referral_code = 'ref_' || tg_id::text
                WHERE referral_code IS NULL
            """)
        sync_logger.info("Миграция БД успешно завершена")
    except Exception as e:
        sync_logger.error(f"Ошибка миграции БД: {e}", exc_info=True)
    finally:
        await db.close()


async def main():
    try:
        # Выполняем миграцию перед запуском
        await migrate_database()

        await db.connect()
        sync_logger.info("Подключение к базе данных успешно.")

        await db.create_tables()
        sync_logger.info("Таблицы успешно созданы/проверены.")

        register_handlers(dp)
        sync_logger.info("Обработчики зарегистрированы.")

        await start_notification_scheduler(bot)
        sync_logger.info("Планировщик уведомлений запущен.")

        sync_logger.info("Запуск бота...")
        await dp.start_polling(bot)

    except Exception as e:
        sync_logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        sync_logger.info("Завершение работы...")
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())