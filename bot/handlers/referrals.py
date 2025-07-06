from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link
from database.db import db
from config.config import BOT_USERNAME
import logging

router = Router()


@router.callback_query(lambda c: c.data == "referral_system")
async def referral_handler(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id

        # Создаем реферальную ссылку
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

        # Получаем статистику
        total_refs, applied_refs, pending_refs = await db.get_user_referral_stats(user_id)

        # Формируем сообщение
        text = f"""🎁 <b>Реферальная программа</b>

<b>Ваша ссылка для приглашения:</b>
<code>{ref_link}</code>

<b>Как это работает?</b>
1. Отправьте другу ссылку выше
2. Друг должен перейти по ней и бот автоматически запустится (Не вручную!!!)
3. Когда он оплатит подписку - вы получите <b>+20 дней</b>
4. 🚨 <b>Важно: Друг должен активировать бота впервые и только по вашей ссылке — иначе бонус не начислится.</b>

📊 <b>Ваша статистика:</b>
├ Всего приглашено: <b>{total_refs}</b>
├ Бонусов получено: <b>{applied_refs}</b>
└ Ожидают оплаты: <b>{pending_refs}</b>"""

        # Создаем клавиатуру
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться ссылкой",
                                  url=f"https://t.me/share/url?url={ref_link}&text=Присоединяйся к LumaVPN через мое приглашение!")],
            [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_ref_{user_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])

        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    except Exception as e:
        logging.error(f"Error in referral handler: {str(e)}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке реферальной системы", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("copy_ref_"))
async def copy_ref_link(callback: types.CallbackQuery):
    user_id = callback.data.split("_")[-1]
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    await callback.answer(f"Ссылка скопирована: {ref_link}", show_alert=True)