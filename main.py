import os
import asyncio
import threading
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands
import aiosqlite
from utils.database import init_db

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.presences = True
intents.bans = True
intents.emojis = True
intents.webhooks = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    activity=discord.Activity(type=discord.ActivityType.watching, name="Mature Bot v2.0")
)

DB_PATH = "mature_bot.db"

async def check_global_noprefix(user_id):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT expires_at FROM global_noprefix WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row: return False
            if row[0] is None: return True
            return datetime.fromisoformat(row[0]) > datetime.utcnow()
    except Exception: return False

async def check_server_noprefix(guild_id, user_id):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT 1 FROM no_prefix_users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            return await cursor.fetchone() is not None
    except Exception: return False

@bot.event
async def on_ready():
    bot.start_time = datetime.utcnow()
    print(f" Mature Bot is ONLINE as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Sync error: {e}")

@bot.event
async def on_message(message):
    if message.author.bot: return

    is_global = await check_global_noprefix(message.author.id)
    is_server = await check_server_noprefix(message.guild.id, message.author.id) if message.guild else False

    if (is_global or is_server) and not message.content.startswith('!'):
        message.content = '!' + message.content

    await bot.process_commands(message)

async def load_cogs():
    for filename in os.listdir("./bot/cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            if filename == "economy.py": continue
            try:
                await bot.load_extension(f"bot.cogs.{filename[:-3]}")
                print(f"✅ Loaded: {filename}")
            except Exception as e:
                print(f"❌ Failed to load {filename}: {e}")

async def start_bot():
    await init_db()
    await load_cogs()
    from dashboard.app import run_dashboard, set_bot_instance
    set_bot_instance(bot)
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(start_bot())
