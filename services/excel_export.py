import pandas as pd
from io import BytesIO
from database.db import db

async def generate_xlsx():
    """
    Генерирует XLSX-файл с данными из всех таблиц базы данных.
    :return: BytesIO объект с содержимым XLSX-файла.
    """
    buffer = BytesIO()  # Буфер для хранения файла

    async with db.pool.acquire() as conn:
        # Получаем данные из таблиц
        users = await conn.fetch("SELECT * FROM users")
        subscriptions = await conn.fetch("SELECT * FROM subscriptions")
        payments = await conn.fetch("SELECT * FROM payments")
        configs = await conn.fetch("SELECT * FROM configs")

    # Создаем DataFrame для каждой таблицы
    users_df = pd.DataFrame(users)
    subscriptions_df = pd.DataFrame(subscriptions)
    payments_df = pd.DataFrame(payments)
    configs_df = pd.DataFrame(configs)

    # Создаем Excel-файл
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        subscriptions_df.to_excel(writer, sheet_name="Subscriptions", index=False)
        payments_df.to_excel(writer, sheet_name="Payments", index=False)
        configs_df.to_excel(writer, sheet_name="Configs", index=False)

    buffer.seek(0)  # Перемещаем указатель в начало буфера
    return buffer