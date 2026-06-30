import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "bot_database.db")

def get_connection():
    return sqlite3.connect(DB_PATH, row_factory=sqlite3.Row)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id INTEGER PRIMARY KEY,
        antinuke_settings TEXT DEFAULT '{}',
        antinuke_enabled BOOLEAN DEFAULT 1,
        log_channels TEXT DEFAULT '{}',
        premium_servers TEXT DEFAULT '{}'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS noprefix_users (
        user_id INTEGER PRIMARY KEY
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        channel_id INTEGER,
        author_id INTEGER,
        status TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS warnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        guild_id INTEGER,
        reason TEXT,
        moderator_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS levels (
        user_id INTEGER,
        guild_id INTEGER,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, guild_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS leveling_channels (
        guild_id INTEGER,
        user_id INTEGER,
        channel_id INTEGER,
        PRIMARY KEY (guild_id, user_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS giveaways (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        channel_id INTEGER,
        message_id INTEGER,
        prize TEXT,
        winners INTEGER,
        end_time TIMESTAMP,
        hosted_by INTEGER,
        ended BOOLEAN DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        channel_id INTEGER,
        message TEXT,
        remind_time TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS welcome_settings (
        guild_id INTEGER PRIMARY KEY,
        channel_id INTEGER,
        message TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS starboard_settings (
        guild_id INTEGER PRIMARY KEY,
        channel_id INTEGER,
        star_count INTEGER DEFAULT 5,
        emoji TEXT DEFAULT '⭐'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS starboard_entries (
        message_id INTEGER PRIMARY KEY,
        guild_id INTEGER,
        star_message_id INTEGER,
        star_count INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS custom_commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        command_name TEXT,
        response TEXT,
        UNIQUE(guild_id, command_name)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        backup_data TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS whitelist (
        guild_id INTEGER,
        feature TEXT,
        user_id INTEGER,
        role_id INTEGER,
        PRIMARY KEY (guild_id, feature, user_id, role_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS voice_role (
        guild_id INTEGER PRIMARY KEY,
        role_id INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_stats (
        user_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        date DATE NOT NULL,
        messages INTEGER DEFAULT 0,
        voice_seconds INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, guild_id, date)
    )''')
    conn.commit()
    conn.close()

def fetch_one(query, params=()):
    conn = get_connection()
    c = conn.cursor()
    c.execute(query, params)
    row = c.fetchone()
    conn.close()
    return row

def fetch_all(query, params=()):
    conn = get_connection()
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

def execute_query(query, params=()):
    conn = get_connection()
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    return last_id
