import logging

from yookassa import Configuration, Payment
from config.config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

# Настройки API-ключей
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

async def create_payment(amount: int, user_id: int, user_email: str) -> tuple:
    """Создает платеж в YooKassa и возвращает ID платежа и ссылку"""
    payment = Payment.create({
        "amount": {
            "value": f"{amount}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/luma_vpn_bot"
        },
        "capture": True,
        "description": f"Оплата подписки {user_id}",
        "receipt": {
            "customer": {
                "email": user_email  # Замените на email пользователя, если есть
            },
            "items": [
                {
                    "description": "Подписка: Доступ к сети",
                    "quantity": "1",
                    "amount": {
                        "value": f"{amount}.00",
                        "currency": "RUB"
                    },
                    "vat_code": "1",
                    "payment_mode": "full_payment",
                    "payment_subject": "service"
                }
            ]
        }
    })
    return payment.id, payment.confirmation.confirmation_url

async def check_payment(payment_id: str) -> bool:
    """Проверяет статус платежа в YooKassa"""
    try:
        payment = Payment.find_one(payment_id)
        return payment.status == "succeeded"
    except Exception as e:
        logging.error(f"Ошибка при проверке платежа: {e}")
        return False
