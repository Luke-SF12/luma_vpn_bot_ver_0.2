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

from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram import F, Bot
from datetime import datetime
import asyncio
from bot.states.admin import BroadcastState
from bot.keyboards.admin import admin_menu, confirm_broadcast_keyboard

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


@router.callback_query(F.data == "broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📢 Введите сообщение для рассылки всем пользователям:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_back")]]
        )
    )
    await state.set_state(BroadcastState.waiting_for_broadcast_message)


@router.message(BroadcastState.waiting_for_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    await state.update_data(broadcast_message=message.html_text)
    await message.answer(
        f"📢 Вы собираетесь отправить это сообщение всем пользователям:\n\n"
        f"{message.html_text}\n\n"
        f"Подтвердите отправку:",
        reply_markup=confirm_broadcast_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastState.confirmation)


@router.callback_query(BroadcastState.confirmation, F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    broadcast_message = data.get("broadcast_message", "")

    if not broadcast_message:
        await callback.answer("❌ Ошибка: сообщение не найдено")
        return

    await callback.message.edit_text("⏳ Начинаю рассылку...")

    # Получаем всех пользователей
    async with db.pool.acquire() as conn:
        users = await conn.fetch("SELECT tg_id FROM users")

    total = len(users)
    success = 0
    failed = 0

    # Отправляем сообщения с интервалом, чтобы не превысить лимиты Telegram
    for i, user in enumerate(users, 1):
        try:
            await bot.send_message(
                chat_id=user['tg_id'],
                text=broadcast_message,
                parse_mode="HTML"
            )
            success += 1
        except Exception as e:
            failed += 1

        # Обновляем статус каждые 10 сообщений
        if i % 10 == 0 or i == total:
            try:
                await callback.message.edit_text(
                    f"📢 Рассылка в процессе...\n"
                    f"✅ Успешно: {success}\n"
                    f"❌ Ошибок: {failed}\n"
                    f"📊 Всего: {total}"
                )
            except:
                pass

        # Задержка между сообщениями (0.1 секунды)
        await asyncio.sleep(0.1)

    # Финальный отчет
    await callback.message.answer(
        f"📢 Рассылка завершена!\n"
        f"✅ Успешно отправлено: {success}\n"
        f"❌ Не удалось отправить: {failed}\n"
        f"📊 Всего пользователей: {total}",
        reply_markup=admin_menu()
    )
    await state.clear()


@router.callback_query(BroadcastState.confirmation, F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Рассылка отменена",
        reply_markup=admin_menu()
    )
