import logging
from logging.handlers import RotatingFileHandler
from aiologger import Logger
from aiologger.handlers.files import AsyncFileHandler
from aiologger.formatters.base import Formatter

# Настройка синхронного логирования (для критически важных событий)
def setup_sync_logger():
    sync_logger = logging.getLogger("sync_logger")
    sync_logger.setLevel(logging.INFO)

    # Ротация логов: максимум 5 файлов по 10 МБ каждый
    handler = RotatingFileHandler(
        "bot.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    sync_logger.addHandler(handler)

    return sync_logger

# Настройка асинхронного логирования (для менее важных событий)
def setup_async_logger():
    async_logger = Logger(name="async_logger")

    # Асинхронный файловый handler с ротацией
    file_handler = AsyncFileHandler("bot_async.log", mode="a", encoding="utf-8")
    file_handler.formatter = Formatter("%(asctime)s - %(levelname)s - %(message)s")
    async_logger.add_handler(file_handler)

    return async_logger

# Инициализация логгеров
sync_logger = setup_sync_logger()
async_logger = setup_async_logger()