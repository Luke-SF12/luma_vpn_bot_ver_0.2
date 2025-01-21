from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards.inline import instruction_keyboard

router = Router()

@router.callback_query(lambda c: c.data == "instruction")
async def instruction_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите вашу платформу для настройки VPN:",
        reply_markup=instruction_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("instruction_"))
async def detailed_instruction_handler(callback: types.CallbackQuery):
    platform = callback.data.split("_")[1]

    instructions = {
        "ios": (
            "<b>iOS</b>\n\n"
            "1. Установите приложение AmneziaWG: "
            "<b><a href='https://apps.apple.com/ru/app/amneziawg/id6478942365'>Скачать</a></b>\n"
            "2. Приобретите конфигурационный файл через LumaVPN.\n"
            "3. Откройте файл, нажмите «Поделиться» и выберите AmneziaWG.\n"
            "4. Подключитесь и работайте без ограничений."
        ),
        "android": (
            "<b>Android</b>\n\n"
            "1. Установите приложение AmneziaWG: "
            "<b><a href='https://play.google.com/store/apps/details?id=org.amnezia.awg&pcampaignid=web_share'>Скачать</a></b>\n"
            "2. Приобретите конфигурационный файл через LumaVPN.\n"
            "3. Откройте файл, нажмите «Поделиться» и выберите AmneziaWG.\n"
            "4. Подключитесь и наслаждайтесь свободным интернетом."
        ),
        "windows": (
            "<b>Windows</b>\n\n"
            "1. Скачайте и установите AmneziaWG: "
            "<b><a href='https://github.com/amnezia-vpn/amneziawg-windows-client/releases/download/1.0.0/amneziawg-amd64-1.0.0.msi'>Скачать</a></b>\n"
            "2. Приобретите конфигурационный файл через LumaVPN.\n"
            "3. Откройте его в AmneziaWG.\n"
            "4. Подключитесь и забудьте о границах в интернете."
        ),
        "macos": (
            "<b>macOS</b>\n\n"
            "1. Установите AmneziaWG из App Store: "
            "<b><a href='https://apps.apple.com/us/app/amneziawg/id6478942365?l=ru'>Скачать</a></b>\n"
            "2. Приобретите конфигурационный файл через LumaVPN.\n"
            "3. Импортируйте файл в приложение.\n"
            "4. Подключитесь и работайте без ограничений."
        ),
        "tv": (
            "<b>Android TV</b>\n\n"
            "1. Приобретите конфигурационный файл через LumaVPN.\n"
            "2. Перейдите к <b><a href='https://www.amneziawg.ru/androidtv'>официальной инструкции</a></b> и выполните шаги.\n\n"
            "Настройка VPN на ТВ также проста, как и на других устройствах!"
        ),
    }

    text = instructions.get(platform, "Инструкция не найдена.")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="instruction")]
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    await callback.answer()

