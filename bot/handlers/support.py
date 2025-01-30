from aiogram import Router, types
from bot.keyboards.inline import support_keyboard

router = Router()

@router.callback_query(lambda c: c.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        " <b>Поддержка</b>\nЕсли у вас возникли вопросы, свяжитесь с администратором: <b>@luma_vpn_admin</b>\n\n"
        "Постарается ответить как можно скорее! 🚀",
        reply_markup=support_keyboard()  # Добавляем кнопку "Назад"
    )
    await callback.answer()
