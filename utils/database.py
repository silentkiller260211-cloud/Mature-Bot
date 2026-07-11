import aiosqlite

DB_PATH = "mature_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Premium Table
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
        
        # Premium Codes Table
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
        
        # Payments Table
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
        
        # Marriages Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS marriages (
                user1_id INTEGER,
                user2_id INTEGER,
                married_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user1_id, user2_id)
            )
        """)
        
        # Warns Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                warned_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Warn Config Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warn_config (
                guild_id INTEGER PRIMARY KEY,
                threshold INTEGER DEFAULT 3,
                punishment_type TEXT DEFAULT 'timeout',
                punishment_duration TEXT DEFAULT '1h'
            )
        """)
        
        # User Warns Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                warned_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Saved Embeds Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS saved_embeds (
                guild_id INTEGER,
                name TEXT,
                data TEXT,
                PRIMARY KEY (guild_id, name)
            )
        """)
        
        # Relationships Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                user1_id INTEGER,
                user2_id INTEGER,
                relationship_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user1_id, user2_id, relationship_type)
            )
        """)
        
        # Pending Relationships Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_relationships (
                requester_id INTEGER,
                target_id INTEGER,
                relationship_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (requester_id, target_id, relationship_type)
            )
        """)
        
        # Vanity Protection Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vanity_protection (
                guild_id INTEGER PRIMARY KEY,
                vanity_code TEXT NOT NULL,
                protected_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Custom Commands Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_commands (
                guild_id INTEGER,
                name TEXT,
                response TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, name)
            )
        """)
        
        # Payment Requests Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                tier TEXT,
                duration TEXT,
                amount INTEGER,
                reference_id TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                payment_method TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                verified_at TEXT,
                verified_by INTEGER
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
