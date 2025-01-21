from aiogram import Router, types
from aiogram.types import FSInputFile
from bot.keyboards.inline import inline_menu
from database.db import db

router = Router()

@router.callback_query(lambda c: c.data == "get_config")
async def get_config_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    async with db.pool.acquire() as conn:
        config = await conn.fetchrow("SELECT * FROM configs WHERE is_available = TRUE LIMIT 1")

        if not config:
            await send_error_message(callback, "Свободных конфигураций нет. Обратитесь в поддержку.")
            return

        await conn.execute(
            "UPDATE configs SET is_available = FALSE, user_id = $1 WHERE id = $2", user_id, config["id"]
        )

        # Создаем подписку
        await conn.execute("""
            INSERT INTO subscriptions (user_id, plan, start_date, end_date, status, config_id)
            VALUES ($1, '1m', NOW(), NOW() + INTERVAL '1 month', 'active', $2)
        """, user_id, config["id"])

        # Отправляем файл
        file = FSInputFile(config["file_path"], filename=config["file_name"])
        await callback.message.delete()
        await callback.message.answer_document(file, caption="✅ Ваш конфиг готов!")
        await callback.message.answer("📌 Выберите нужный раздел ниже:", reply_markup=inline_menu())

    await callback.answer()

async def send_error_message(callback: types.CallbackQuery, error_text: str):
    """Универсальный метод для отправки ошибок"""
    await callback.message.edit_text(f"❌ {error_text}", reply_markup=inline_menu())
    await callback.answer()
