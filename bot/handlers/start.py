from aiogram import Router, types
from aiogram.filters import Command
from bot.keyboards.reply import reply_menu
from bot.keyboards.inline import inline_menu
from database.db import db

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_name = message.from_user.first_name

    referral_code = None
    if len(message.text.split()) > 1 and message.text.split()[1].startswith('ref_'):
        referral_code = message.text.split()[1][4:]  # Извлекаем ID пригласившего

    # 2. Регистрация/обновление пользователя
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE tg_id = $1",
            message.from_user.id
        )

        if not user:
            # Новый пользователь
            await conn.execute(
                """INSERT INTO users (tg_id, username, referral_code, registration_date)
                VALUES ($1, $2, $3, NOW())""",
                message.from_user.id,
                message.from_user.username,
                f"ref_{message.from_user.id}"
            )

            # Если есть реферальный код
            if referral_code:
                try:
                    referrer_id = int(referral_code)
                    if referrer_id != message.from_user.id:
                        await db.create_referral(referrer_id, message.from_user.id)

                        # Уведомляем пригласившего
                        try:
                            await message.bot.send_message(
                                chat_id=referrer_id,
                                text=f"🎉 Новый пользователь по вашей ссылке!\n"
                                     f"@{message.from_user.username or 'Аноним'} зарегистрировался.\n"
                                     f"Когда он оплатит подписку - вы получите +20 дней!"
                            )
                        except:
                            pass
                except ValueError:
                    pass
        else:
            # Существующий пользователь - убедимся есть ли у него referral_code
            if not user.get('referral_code'):
                await conn.execute(
                    "UPDATE users SET referral_code = $1 WHERE tg_id = $2",
                    f"ref_{message.from_user.id}",
                    message.from_user.id
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
