from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню админ-панели
def admin_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ключ", callback_data="add_key")],
            [InlineKeyboardButton(text="🗑 Удалить ключи", callback_data="remove_keys")],
            [InlineKeyboardButton(text="📁 Экспорт XLSX", callback_data="export_xlsx")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="👨💻 Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton(text="👥 Список администраторов", callback_data="view_admins")]
        ]
    )

# Меню статистики
def stats_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ]
    )