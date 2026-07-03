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
        
        # Premium Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS premium (
                guild_id INTEGER PRIMARY KEY, tier TEXT DEFAULT 'none', 
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
