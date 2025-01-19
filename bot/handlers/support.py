from aiogram import Router, types
from bot.keyboards.inline import support_keyboard

router = Router()

@router.callback_query(lambda c: c.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🛠 Свяжитесь с поддержкой: @your_support",
        reply_markup=support_keyboard()  # Добавляем кнопку "Назад"
    )
    await callback.answer()
