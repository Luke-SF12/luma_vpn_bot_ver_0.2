from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.keyboards.reply import reply_menu
from bot.keyboards.inline import inline_menu
from database.db import db
import logging

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    try:
        await state.clear()  # Сбрасываем все состояния

        user_name = message.from_user.first_name
        user_id = message.from_user.id

        # Обработка реферальной ссылки
        referral_code = None
        if len(message.text.split()) > 1 and message.text.split()[1].startswith('ref_'):
            referral_code = message.text.split()[1][4:]

        async with db.pool.acquire() as conn:
            # Регистрация/обновление пользователя
            user = await conn.fetchrow("SELECT * FROM users WHERE tg_id = $1", user_id)

            if not user:
                await conn.execute(
                    """INSERT INTO users (tg_id, username, referral_code, registration_date)
                    VALUES ($1, $2, $3, NOW())""",
                    user_id,
                    message.from_user.username,
                    f"ref_{user_id}"
                )

                # Обработка реферала
                if referral_code:
                    try:
                        referrer_id = int(referral_code)
                        if referrer_id != user_id:
                            await db.create_referral(referrer_id, user_id)
                            try:
                                await message.bot.send_message(
                                    chat_id=referrer_id,
                                    text=f"🎉 Новый пользователь по вашей ссылке!\n"
                                         f"@{message.from_user.username or 'Аноним'} зарегистрировался.\n"
                                         f"Когда он оплатит подписку - вы получите +20 дней!"
                                )
                            except Exception as e:
                                logging.error(f"Не удалось уведомить реферера: {e}")
                    except ValueError:
                        logging.warning(f"Неверный реферальный код: {referral_code}")
            elif not user.get('referral_code'):
                await conn.execute(
                    "UPDATE users SET referral_code = $1 WHERE tg_id = $2",
                    f"ref_{user_id}",
                    user_id
                )

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
            f"— Канал с информацией: <b><a href='https://t.me/+IzUMlniBS700MDU8'>LumaVPN</a></b>\n\n"
            f"Нажмите <b>«Меню🗿»</b>, чтобы начать пользоваться LumaVPN!",

            reply_markup=reply_menu()
        )

    except Exception as e:
        logging.error(f"Ошибка в start_handler: {e}", exc_info=True)
        await message.answer("⚠️ Произошла ошибка, попробуйте позже")


@router.message(lambda message: message.text == "Меню🗿")
async def menu_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>Выберите необходимый раздел ниже:</b>",
        reply_markup=inline_menu()
    )


@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "<b>Выберите необходимый раздел ниже:</b>",
        reply_markup=inline_menu()
    )
    await callback.answer()