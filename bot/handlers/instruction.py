from aiogram import Router, types
from bot.keyboards.inline import instruction_keyboard

router = Router()

@router.callback_query(lambda c: c.data == "instruction")
async def instruction_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📖 Выберите платформу:",
        reply_markup=instruction_keyboard()  # Добавляем кнопку "Назад"
    )
    await callback.answer()
