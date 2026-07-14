import aiosqlite

DB_PATH = "mature_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS premium (guild_id INTEGER PRIMARY KEY, tier TEXT DEFAULT 'none', duration TEXT DEFAULT 'monthly', expires_at TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS no_prefix_users (guild_id INTEGER, user_id INTEGER, PRIMARY KEY (guild_id, user_id))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS antinuke_whitelist (guild_id INTEGER, user_id INTEGER, PRIMARY KEY (guild_id, user_id))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS global_noprefix (user_id INTEGER PRIMARY KEY, expires_at TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS antinuke_settings (guild_id INTEGER, program TEXT, enabled BOOLEAN DEFAULT 0, PRIMARY KEY (guild_id, program))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS premium_codes (code TEXT PRIMARY KEY, tier TEXT NOT NULL, duration TEXT NOT NULL, days INTEGER NOT NULL, user_id INTEGER, used BOOLEAN DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, used_at TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS payments (payment_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, amount INTEGER NOT NULL, tier TEXT NOT NULL, duration TEXT NOT NULL, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP, completed_at TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS relationships (user1_id INTEGER, user2_id INTEGER, relationship_type TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user1_id, user2_id, relationship_type))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS pending_relationships (requester_id INTEGER, target_id INTEGER, relationship_type TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (requester_id, target_id, relationship_type))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS marriages (user1_id INTEGER, user2_id INTEGER, married_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user1_id, user2_id))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS user_warns (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER, moderator_id INTEGER, reason TEXT, warned_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS warn_config (guild_id INTEGER PRIMARY KEY, threshold INTEGER DEFAULT 3, punishment_type TEXT DEFAULT 'timeout', punishment_duration TEXT DEFAULT '1h')""")
        await db.execute("""CREATE TABLE IF NOT EXISTS vanity_protection (guild_id INTEGER PRIMARY KEY, vanity_code TEXT NOT NULL, protected_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS custom_commands (guild_id INTEGER, name TEXT, response TEXT, created_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (guild_id, name))""")
        await db.commit()
    print("✅ Database initialized successfully.")

async def create_premium_code(code, tier, duration, days, user_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO premium_codes (code, tier, duration, days, user_id) VALUES (?, ?, ?, ?, ?)", (code, tier, duration, days, user_id))
        await db.commit()

async def save_payment(payment_id, user_id, amount, tier, duration, status='pending'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO payments (payment_id, user_id, amount, tier, duration, status) VALUES (?, ?, ?, ?, ?, ?)", (payment_id, user_id, amount, tier, duration, status))
        await db.commit()

async def update_payment_status(payment_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE payment_id = ?", (status, payment_id))
        await db.commit()

async def get_payment_info(payment_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT tier, duration FROM payments WHERE payment_id = ?", (payment_id,))
        return await cursor.fetchone()
