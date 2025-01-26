from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config.config import ADMINS
from bot.keyboards.admin import admin_menu, stats_menu
from database.db import db
from aiogram.fsm.context import FSMContext
from bot.states.admin import AddKeyState, AddAdminState
from aiogram.types import BufferedInputFile
from services.excel_export import generate_xlsx

router = Router()


# Обработчик команды /admin
@router.message(Command("admin"))
async def admin_command(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("Доступ запрещен!")

    await message.answer(
        "👑 Админ-панель",
        reply_markup=admin_menu()
    )


# Обработчик кнопки "Добавить ключ"
@router.callback_query(F.data == "add_key")
async def add_key_handler(callback: CallbackQuery, state: FSMContext):
    # Редактируем сообщение с запросом ввода
    await callback.message.edit_text(
        "Введите имя и ключ через пробел:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]]
        )
    )
    await state.set_state(AddKeyState.waiting_for_name_and_key)  # Устанавливаем состояние


# Обработчик ввода имени и ключа
@router.message(AddKeyState.waiting_for_name_and_key)
async def process_add_key(message: Message, state: FSMContext):
    try:
        # Разделяем ввод на имя и ключ
        name, key = message.text.split(maxsplit=1)

        # Добавляем ключ в базу данных
        await db.add_key(name, key)

        # Удаляем сообщение с запросом ввода
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)

        # Отправляем подтверждение и возвращаем в главное меню
        await message.answer("✅ Ключ успешно добавлен!", reply_markup=admin_menu())
    except ValueError:
        # Если ввод некорректный
        await message.answer("❌ Неверный формат. Введите имя и ключ через пробел.")

        # Возвращаем в главное меню
        await message.answer("👑 Админ-панель", reply_markup=admin_menu())
    finally:
        # Сбрасываем состояние
        await state.clear()


# Обработчик кнопки "Удалить ключи"
@router.callback_query(F.data == "remove_keys")
async def remove_keys_handler(callback: CallbackQuery):
    # Получаем список неактивных ключей
    inactive_keys = await db.get_inactive_keys_with_subscriptions()

    if not inactive_keys:
        return await callback.answer("Нет неактивных ключей для удаления!")

    # Создаем клавиатуру с кнопками для каждого ключа
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
                            [InlineKeyboardButton(text=f"🗑 {key['name']}", callback_data=f"delete_key_{key['id']}")]
                            for key in inactive_keys
                        ] + [
                            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
                        ]
    )

    # Редактируем сообщение с списком ключей
    await callback.message.edit_text(
        "Выберите ключ для удаления:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("delete_key_"))
async def delete_key_handler(callback: CallbackQuery):
    # Извлекаем ID ключа из callback_data
    key_id = int(callback.data.split("_")[2])

    # Удаляем ключ и связанные подписки
    await db.delete_key_and_subscriptions(key_id)

    # Уведомляем пользователя
    await callback.answer("✅ Ключ и связанные подписки удалены!")

    # Возвращаемся к списку ключей
    await remove_keys_handler(callback)


from aiogram.exceptions import TelegramBadRequest

@router.callback_query(F.data == "export_xlsx")
async def export_xlsx_handler(callback: CallbackQuery):
    try:
        # Генерируем XLSX-файл
        xlsx_buffer = await generate_xlsx()

        # Пытаемся удалить старое сообщение с кнопками
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            # Если сообщение слишком старое и его нельзя удалить, просто игнорируем
            pass

        # Отправляем файл пользователю
        await callback.message.answer_document(
            document=BufferedInputFile(xlsx_buffer.getvalue(), filename="export.xlsx"),
            caption="📁 Экспорт данных завершён!"
        )

        # Отправляем новое сообщение с кнопками
        await callback.message.answer(
            "👑 Админ-панель",
            reply_markup=admin_menu()
        )

        # Уведомляем пользователя
        await callback.answer("✅ Файл успешно экспортирован!")
    except Exception as e:
        await callback.answer("❌ Произошла ошибка при экспорте данных.")


# Обработчик кнопки "Статистика"
@router.callback_query(F.data == "stats")
async def stats_handler(callback: CallbackQuery):
    users_with_sub, free_keys, used_keys = await db.get_stats()
    active_subs, expired_subs, total_users = await db.get_detailed_stats()
    await callback.message.edit_text(  # Редактируем сообщение
        f"📊 Статистика:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"👤 Пользователи с подпиской: {users_with_sub}\n"
        f"🔑 Свободные ключи: {free_keys}\n"
        f"🔐 Используемые ключи: {used_keys}\n"
        f"✅ Активные подписки: {active_subs}\n"
        f"❌ Истекшие подписки: {expired_subs}",
        reply_markup=stats_menu()
    )


# Обработчик кнопки "Добавить админа"
@router.callback_query(F.data == "add_admin")
async def add_admin_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(  # Редактируем сообщение
        "Введите Telegram ID нового администратора:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]]
        )
    )
    await state.set_state(AddAdminState.waiting_for_admin_id)  # Устанавливаем состояние

# Обработчик ввода Telegram ID администратора
@router.message(AddAdminState.waiting_for_admin_id)
async def process_add_admin(message: Message, state: FSMContext):
    try:
        # Пытаемся преобразовать введённый текст в число (Telegram ID)
        new_admin_id = int(message.text)

        # Проверяем, что ID ещё не в списке администраторов
        if new_admin_id in ADMINS:
            await message.answer("❌ Этот пользователь уже является администратором.")
        else:
            # Добавляем ID в список администраторов
            ADMINS.append(new_admin_id)
            await message.answer(f"✅ Пользователь {new_admin_id} добавлен в администраторы!")
    except ValueError:
        # Если введённый текст не является числом
        await message.answer("❌ Неверный формат. Введите числовой Telegram ID.")
    finally:
        # Сбрасываем состояние
        await state.clear()

        # Возвращаем пользователя в главное меню
        await message.answer(
            "👑 Админ-панель",
            reply_markup=admin_menu()
        )

@router.callback_query(F.data == "view_admins")
async def view_admins_handler(callback: CallbackQuery):
    # Формируем список администраторов
    if not ADMINS:
        admins_text = "❌ Список администраторов пуст."
    else:
        admins_text = "👥 Список администраторов:\n\n" + "\n".join([f"🆔 {admin_id}" for admin_id in ADMINS])

    # Редактируем сообщение с списком администраторов
    await callback.message.edit_text(
        admins_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]]
        )
    )



# Обработчик кнопки "Назад" (возврат в админ-панель)
@router.callback_query(F.data == "admin_back")
async def admin_back_handler(callback: CallbackQuery):
    await callback.message.edit_text(  # Редактируем сообщение
        "👑 Админ-панель",
        reply_markup=admin_menu()
    )
