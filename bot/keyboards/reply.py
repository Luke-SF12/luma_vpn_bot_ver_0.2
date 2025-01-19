from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def reply_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Меню")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )
