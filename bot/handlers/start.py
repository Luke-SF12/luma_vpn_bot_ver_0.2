from aiogram import Router, types
from aiogram.filters import Command
from bot.keyboards.reply import reply_menu
from bot.keyboards.inline import inline_menu

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"<b>{user_name}</b>, Добро пожаловать в <b>Luma VPN!</b>🌐\n\n"
        f"<b>Открывайте интернет без границ!</b>\n"
        f"С VPN вы сможете обойти блокировки и получить доступ к любимым сервисам:\n"
        f"<b>— Instagram, TikTok, YouTube, Discord, Reddit</b>\n"
        f"<b>— Аниме сайты: jut.su, AnimeGO</b>\n\n"
        f"<b>🔒 Полная анонимность и защита.</b>\n"
        f"Ваши данные остаются в безопасности, а соединение — стабильным и быстрым.\n\n"
        f"<b>Приятные плюсы:</b>\n"
        f"— Месяц подписки всего 100₽.\n"
        f"— Возможность включения VPN через панель управления.\n"
        f"— Один ключ - 3 устройства!\n"
        f"— Канал с информацией: @LumaVPN_channel\n\n"
        f"Нажмите <b>«Меню🗿»</b>, чтобы начать пользоваться LumaVPN!",

        reply_markup=reply_menu()
    )


@router.message(lambda message: message.text == "Меню🗿")
async def menu_handler(message: types.Message):
    await message.answer(
        "<b>Выберите необходимый раздел ниже:</b>",
        reply_markup=inline_menu()
    )

@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "<b>Выберите необходимый раздел ниже:</b>",
        reply_markup=inline_menu()
    )
    await callback.answer()
