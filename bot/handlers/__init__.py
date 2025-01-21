from aiogram import Dispatcher

# Импорты роутеров
from .start import router as start_router
from .buy import register_buy_handlers
from .profile import router as profile_router
from .instruction import router as instruction_router
from .support import router as support_router

def register_handlers(dp: Dispatcher):
    dp.include_router(start_router)
    register_buy_handlers(dp)
    dp.include_router(profile_router)
    dp.include_router(instruction_router)
    dp.include_router(support_router)