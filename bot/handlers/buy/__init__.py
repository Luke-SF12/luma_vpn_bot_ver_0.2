from aiogram import Dispatcher
from .buy_handler import router as buy_router
from .payment_check import router as payment_check_router
from .get_config import router as get_config_router
from .extend_subscription import router as extend_subscription_router

def register_buy_handlers(dp: Dispatcher):
    dp.include_router(buy_router)
    dp.include_router(payment_check_router)
    dp.include_router(get_config_router)
    dp.include_router(extend_subscription_router)
