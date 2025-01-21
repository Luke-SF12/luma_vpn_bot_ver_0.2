from aiogram import Router, types
from aiogram.filters import Command
from bot.keyboards.reply import reply_menu
from bot.keyboards.inline import inline_menu

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"{user_name}, приветствую в <b>Luma VPN!</b>🌐\n\n"
        f"Нажмите \"Меню\" чтобы начать пользоваться сервисом.",
        reply_markup=reply_menu()
    )


@router.message(lambda message: message.text == "📍 Меню")
async def menu_handler(message: types.Message):
    await message.answer(
        "📌 Выберите нужный раздел ниже:",
        reply_markup=inline_menu()
    )

@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📌 Выберите нужный раздел ниже:",
        reply_markup=inline_menu()
    )
    await callback.answer()
