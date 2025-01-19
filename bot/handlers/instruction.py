from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.keyboards.inline import instruction_keyboard

router = Router()

@router.callback_query(lambda c: c.data == "instruction")
async def instruction_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📖 Выберите платформу:",
        reply_markup=instruction_keyboard()  # Добавляем кнопку "Назад"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("instruction_"))
async def instruction_handler(callback: types.CallbackQuery):
    platform = callback.data.split("_")[1]

    instructions = {
        "ios": "📖 Инструкция для iOS:\n1. Установите приложение\n2. Вставьте конфиг...",
        "android": "📖 Инструкция для Android:\n1. Установите OpenVPN\n2. Импортируйте конфиг...",
        "windows": "📖 Инструкция для Windows:\n1. Скачайте клиент\n2. Откройте конфиг...",
        "linux": "📖 Инструкция для Linux:\n1. Установите OpenVPN\n2. Запустите команду...",
        "macos": "📖 Инструкция для MacOS:\n1. Установите клиент\n2. Импортируйте конфиг..."
    }

    text = instructions.get(platform, "❌ Инструкция не найдена.")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="instruction")]
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
