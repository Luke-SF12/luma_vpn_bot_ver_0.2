import asyncpg
from config.config import DB_URL

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=20)

    async def close(self):
        await self.pool.close()

    async def add_key(self, name: str, key: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO configs(name, config_key) VALUES($1, $2)",
                name, key
            )

    async def get_inactive_keys_with_subscriptions(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT c.id, c.name 
                FROM configs c
                JOIN subscriptions s ON c.id = s.config_id
                WHERE s.status = 'inactive'
            """)

    async def delete_key_and_subscriptions(self, key_id: int):
        async with self.pool.acquire() as conn:
            # Удаляем подписки, связанные с этим ключом
            await conn.execute("DELETE FROM subscriptions WHERE config_id = $1", key_id)
            # Удаляем сам ключ
            await conn.execute("DELETE FROM configs WHERE id = $1", key_id)

    async def get_stats(self):
        async with self.pool.acquire() as conn:
            users_with_sub = await conn.fetchval("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
            free_keys = await conn.fetchval("SELECT COUNT(*) FROM configs WHERE is_available = TRUE")
            used_keys = await conn.fetchval("SELECT COUNT(*) FROM configs WHERE is_available = FALSE")
            return users_with_sub, free_keys, used_keys

    async def get_detailed_stats(self):
        async with self.pool.acquire() as conn:
            active_subs = await conn.fetchval("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
            expired_subs = await conn.fetchval("SELECT COUNT(*) FROM subscriptions WHERE status = 'inactive'")
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            return active_subs, expired_subs, total_users


    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                -- Сначала создаём базовую таблицу пользователей
                CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                email TEXT,
                registration_date TIMESTAMP DEFAULT NOW()
            );

                -- Затем создаём таблицу с конфигурациями, так как на неё ссылается таблица subscriptions
                CREATE TABLE IF NOT EXISTS configs (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                config_key TEXT NOT NULL,
                user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
                is_available BOOLEAN DEFAULT TRUE
            );

                -- Теперь можно создавать таблицы, которые ссылаются на таблицы выше
                CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
                start_date TIMESTAMP DEFAULT NOW(),
                end_date TIMESTAMP,
                status TEXT DEFAULT 'active',
                config_id INTEGER REFERENCES configs(id) ON DELETE SET NULL
);

                CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
                payment_id TEXT UNIQUE NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                payment_link TEXT, // jikjklj
                created_at TIMESTAMP DEFAULT NOW()
);

                -- Затем создаём необходимые индексы
                CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id);
                CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
                CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
                CREATE INDEX IF NOT EXISTS idx_configs_user_id ON configs(user_id);
            """)

db = Database()