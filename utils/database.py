import aiosqlite
import os

DB_PATH = "mature_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Economy Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                user_id INTEGER, guild_id INTEGER, balance INTEGER DEFAULT 0, 
                xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, 
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        # Premium Table (UPDATED with duration)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS premium (
                guild_id INTEGER PRIMARY KEY, 
                tier TEXT DEFAULT 'none',
                duration TEXT DEFAULT 'monthly',
                expires_at TEXT
            )
        """)
        
        # No-Prefix Users Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS no_prefix_users (
                guild_id INTEGER, user_id INTEGER, 
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        
        # Antinuke Settings Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS antinuke_settings (
                guild_id INTEGER, program TEXT, enabled BOOLEAN DEFAULT 0, 
                PRIMARY KEY (guild_id, program)
            )
        """)
        
        # Premium Codes Table (NEW)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS premium_codes (
                code TEXT PRIMARY KEY,
                tier TEXT NOT NULL,
                duration TEXT NOT NULL,
                days INTEGER NOT NULL,
                user_id INTEGER,
                used BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                used_at TEXT
            )
        """)
        
        # Payments Table (NEW)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                tier TEXT NOT NULL,
                duration TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        """)
        
        await db.commit()
    print("✅ Database initialized successfully.")

async def get_no_prefix_users(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM no_prefix_users WHERE guild_id = ?", (guild_id,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def add_no_prefix_user(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM no_prefix_users WHERE guild_id = ?", (guild_id,))
        count = (await cursor.fetchone())[0]
        if count >= 10:
            return False, "Limit of 10 users reached."
        try:
            await db.execute("INSERT INTO no_prefix_users (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
            await db.commit()
            return True, "User added successfully."
        except Exception:
            return False, "User already has no-prefix access."

async def remove_no_prefix_user(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM no_prefix_users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()
        return True

# NEW: Premium Code Functions
async def create_premium_code(code, tier, duration, days, user_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO premium_codes (code, tier, duration, days, user_id) VALUES (?, ?, ?, ?, ?)",
            (code, tier, duration, days, user_id)
        )
        await db.commit()

async def get_premium_code(code):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT code, tier, duration, days, user_id, used FROM premium_codes WHERE code = ?",
            (code,)
        )
        return await cursor.fetchone()

async def mark_code_used(code, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE premium_codes SET used = 1, used_at = CURRENT_TIMESTAMP, user_id = ? WHERE code = ?",
            (user_id, code)
        )
        await db.commit()

async def save_payment(payment_id, user_id, amount, tier, duration, status='pending'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO payments (payment_id, user_id, amount, tier, duration, status) VALUES (?, ?, ?, ?, ?, ?)",
            (payment_id, user_id, amount, tier, duration, status)
        )
        await db.commit()

async def update_payment_status(payment_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE payment_id = ?",
            (status, payment_id)
        )
        await db.commit()

async def get_payment_info(payment_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT tier, duration FROM payments WHERE payment_id = ?",
            (payment_id,)
        )
        return await cursor.fetchone()
