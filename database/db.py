import asyncpg
from config.config import DB_URL

async def connect_db():
    return await asyncpg.create_pool(DB_URL)

async def create_tables():
    conn = await connect_db()
    async with conn.acquire() as connection:
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
        """)
    await conn.close()
