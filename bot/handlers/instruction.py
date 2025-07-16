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
            "<b>📱 iOS</b>\n\n"
            "1. Установите приложение v2RayTun: "
            "<b><a href='https://apps.apple.com/ru/app/v2raytun/id6476628951'>Скачать</a></b>\n"
            "2. Получите ключ (ссылку) и скопируйте для подключения.\n"
            "3. Откройте v2RayTun, нажмите «+» и выберите «Добавить из буфера».\n"
            "4. Подключитесь и пользуйтесь интернетом без ограничений. 🔒"
        ),
        "android": (
            "<b>🤖 Android</b>\n\n"
            "1. Установите приложение v2RayNG: "
            "<b><a href='https://play.google.com/store/apps/details?id=com.v2raytun.android'>Скачать</a></b>\n"
            "2. Получите ключ (ссылку) и скопируйте для подключения.\n"
            "3. Откройте v2RayNG, нажмите «+» и выберите «Импорт из буфера обмена».\n"
            "4. Подключитесь и наслаждайтесь свободным интернетом! 🚀"
        ),
        "windows": (
            "<b>💻 Windows</b>\n\n"
            "1. Скачайте и установите Hidify VPN: "
            "<b><a href='https://github.com/hiddify/hiddify-app/releases/latest/download/Hiddify-Windows-Setup-x64.Msix'>Скачать</a></b>\n"
            "2. Получите ключ (ссылку) и скопируйте для подключения.\n"
            "3. Откройте Hidify VPN и выберете регион: Другой.\n"
            "4. Скопируйте ключ, который выдал вам бот.\n"
            "5. Нажмите '+ Новый профиль' и 'Добавить из буфера обмена'.\n"
            "6. Подключитесь и пользуйтесь интернетом без ограничений. 🔒"
        ),
        "macos": (
            "<b>🍏 macOS</b>\n\n"
            "1. Установите v2RayTun: "
            "<b><a href='https://apps.apple.com/ru/app/v2raytun/id6476628951'>Скачать</a></b>\n"
            "2. Получите ключ (ссылку) и скопируйте для подключения.\n"
            "3. Откройте v2RayTun, нажмите «+» и выберите «Добавить из буфера».\n"
            "4. Подключитесь и пользуйтесь интернетом без ограничений. 🔒"
        ),
        "tv": (
            "<b>📺 Android TV</b>\n\n"
            "1. Установите приложение <b>v2RayTun</b> на телевизор: "
            "<b><a href='https://play.google.com/store/apps/details?id=com.v2raytun.android'>Скачать</a></b>\n"
            "2. Получите ключ (ссылку) для подключения.\n"
            "3. Скопируйте ключ на телефоне и откройте одно из приложений для управления ТВ:\n"
            "   - <b><a href='https://apps.apple.com/ru/app/remote-for-android-tv/id1668755298'>iOS: Remote for Android TV</a></b>\n"
            "   - <b><a href='https://play.google.com/store/apps/details?id=tech.simha.androidtvremote'>Android: Remote for Android TV</a></b>\n"
            "4. Используя телефон как клавиатуру, вставьте ключ в v2RayNG на телевизоре.\n"
            "5. Сохраните настройки и подключитесь к VPN! 📡"
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
