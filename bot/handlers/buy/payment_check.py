from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.yookassa import check_payment
from database.db import db

router = Router()

@router.callback_query(lambda c: c.data.startswith("check_payment_"))
async def check_payment_handler(callback: types.CallbackQuery):
    payment_id = callback.data.split("_")[2]

    async with db.pool.acquire() as connection:
        payment = await connection.fetchrow(
            "SELECT * FROM payments WHERE payment_id = $1 AND status = 'pending'", payment_id
        )

        if not payment:
            await callback.answer("❌ Нет ожидаемых платежей.")
            return

        is_paid = await check_payment(payment_id)

        if is_paid:
            await connection.execute("UPDATE payments SET status = 'success' WHERE payment_id = $1", payment_id)
            await callback.message.edit_text(
                "✅ Оплата прошла успешно!\n\nВыберите дальнейшие действия:",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🎟 Получить", callback_data="get_config")],
                        [InlineKeyboardButton(text="🔄 Продлить", callback_data="extend_subscription")]
                    ]
                )
            )
        else:
            await callback.answer("⚠ Оплата не найдена. Попробуйте позже.")
