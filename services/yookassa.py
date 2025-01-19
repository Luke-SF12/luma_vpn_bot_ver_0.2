from yookassa import Configuration, Payment
from config.config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

# Настройка API-ключей
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

async def create_payment(amount: int, user_id: int) -> tuple:
    """
    Создает платеж через YooKassa и возвращает (ID платежа, ссылку на оплату).
    """
    payment = Payment.create({
        "amount": {
            "value": f"{amount}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/luma_vpn_bot"  # Сюда пользователь вернется после оплаты
        },
        "capture": True,
        "description": f"Оплата подписки для пользователя {user_id}"
    })

    return payment.id, payment.confirmation.confirmation_url  # Возвращаем ID и ссылку на оплату


async def check_payment(payment_id: str) -> bool:
    """
    Проверяет статус платежа в YooKassa.
    """
    payment = Payment.find_one(payment_id)  # Используем find_one вместо fetch
    return payment.status == "succeeded"


