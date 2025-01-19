from aiogram import Router, types
from aiogram.filters import Command
from bot.keyboards.reply import reply_menu
from bot.keyboards.inline import inline_menu

router = Router()

# Обработчик команды /start
@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_name = message.from_user.first_name  # Получаем имя пользователя
    await message.answer(
        f"👋 Привет, {user_name}! Добро пожаловать в Luma VPN.",
        reply_markup=reply_menu()  # Добавляем Reply-кнопку "Меню"
    )

# Обработчик нажатия на Reply-кнопку "Меню"
@router.message(lambda message: message.text == "📍 Меню")
async def menu_handler(message: types.Message):
    await message.answer(
        "📌 Выберите действие:",
        reply_markup=inline_menu()  # Показываем инлайн-кнопки
    )

# Обработчик кнопки "🔙 Назад" (возвращает в главное меню)
@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📌 Выберите действие:",
        reply_markup=inline_menu()  # Показываем главное меню
    )
    await callback.answer()
