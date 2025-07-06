import asyncpg
from config.config import DB_URL

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=20)

    async def close(self):
        await self.pool.close()

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    email TEXT,
                    registration_date TIMESTAMP DEFAULT NOW(),
                    referral_code TEXT
                );

                CREATE TABLE IF NOT EXISTS configs (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    config_key TEXT NOT NULL,
                    user_id BIGINT REFERENCES users(tg_id) ON DELETE CASCADE,
                    is_available BOOLEAN DEFAULT TRUE
                );

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
                    payment_link TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS referrals (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
                    referred_id BIGINT NOT NULL UNIQUE REFERENCES users(tg_id) ON DELETE CASCADE,
                    referral_date TIMESTAMP DEFAULT NOW(),
                    bonus_applied BOOLEAN DEFAULT FALSE,
                    payment_id INTEGER REFERENCES payments(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id);
                CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
                CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
                CREATE INDEX IF NOT EXISTS idx_configs_user_id ON configs(user_id);
                CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
            """)

    async def migrate_existing_users(self):
        """Генерирует реферальные коды для существующих пользователей"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users 
                SET referral_code = 'ref_' || tg_id
                WHERE referral_code IS NULL
            """)

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
            await conn.execute("DELETE FROM subscriptions WHERE config_id = $1", key_id)
            await conn.execute("DELETE FROM configs WHERE id = $1", key_id)

    async def get_stats(self):
        async with self.pool.acquire() as conn:
            users_with_sub = await conn.fetchval(
                "SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"
            )
            free_keys = await conn.fetchval(
                "SELECT COUNT(*) FROM configs WHERE is_available = TRUE"
            )
            used_keys = await conn.fetchval(
                "SELECT COUNT(*) FROM configs WHERE is_available = FALSE"
            )
            return users_with_sub, free_keys, used_keys

    async def get_detailed_stats(self):
        async with self.pool.acquire() as conn:
            active_subs = await conn.fetchval(
                "SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"
            )
            expired_subs = await conn.fetchval(
                "SELECT COUNT(*) FROM subscriptions WHERE status = 'inactive'"
            )
            total_users = await conn.fetchval(
                "SELECT COUNT(*) FROM users"
            )
            return active_subs, expired_subs, total_users

    async def create_referral(self, referrer_id: int, referred_id: int):
        """Создает запись о реферале"""
        async with self.pool.acquire() as conn:
            if referrer_id == referred_id:
                return False

            exists = await conn.fetchval(
                "SELECT 1 FROM referrals WHERE referred_id = $1",
                referred_id
            )
            if exists:
                return False

            await conn.execute(
                "INSERT INTO referrals (referrer_id, referred_id) VALUES ($1, $2)",
                referrer_id, referred_id
            )
            return True

    async def apply_referral_bonus(self, referred_id: int, payment_id: int):
        """Начисляет бонус за приглашение"""
        async with self.pool.acquire() as conn:
            paid_before = await conn.fetchval(
                "SELECT COUNT(*) FROM payments WHERE user_id = $1 AND status = 'succeeded'",
                referred_id
            )
            if paid_before > 1:
                return False

            referral = await conn.fetchrow(
                """SELECT referrer_id FROM referrals 
                WHERE referred_id = $1 
                AND NOT bonus_applied
                AND payment_id IS NULL""",
                referred_id
            )
            if not referral:
                return False

            await conn.execute("""
                UPDATE subscriptions 
                SET end_date = end_date + INTERVAL '20 days'
                WHERE user_id = $1 AND status = 'active'
            """, referral['referrer_id'])

            await conn.execute(
                """UPDATE referrals 
                SET bonus_applied = TRUE, 
                    payment_id = $1
                WHERE referred_id = $2""",
                payment_id, referred_id
            )
            return True

    async def get_user_referral_stats(self, user_id: int):
        """Возвращает статистику по рефералам"""
        async with self.pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM referrals WHERE referrer_id = $1",
                user_id
            )
            applied = await conn.fetchval(
                "SELECT COUNT(*) FROM referrals WHERE referrer_id = $1 AND bonus_applied",
                user_id
            )
            pending = total - applied
            return total, applied, pending

db = Database()