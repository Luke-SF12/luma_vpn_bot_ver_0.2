import asyncpg
from config.config import DB_URL

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Создает пул подключений к БД"""
        self.pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=10)

    async def close(self):
        """Закрывает пул подключений"""
        await self.pool.close()

    async def create_tables(self):
        """Создает таблицы в базе данных"""
        async with self.pool.acquire() as connection:
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    registration_date TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
                    plan TEXT NOT NULL,
                    start_date TIMESTAMP DEFAULT NOW(),
                    end_date TIMESTAMP,
                    status TEXT DEFAULT 'active'
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
                    payment_id TEXT UNIQUE NOT NULL,
                    amount INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    payment_link TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS files (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    access_level TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS configs (
                    id SERIAL PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    is_available BOOLEAN DEFAULT TRUE
                );
            """)

db = Database()  # Создаём объект базы данных
