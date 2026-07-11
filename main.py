import os
import asyncio
import threading
from datetime import datetime
from dotenv import load_dotenv
import discord
from discord.ext import commands
import aiosqlite

from utils.database import init_db, get_no_prefix_users
from dashboard.app import run_dashboard, set_bot_instance

load_dotenv()

# Bot Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.presences = True
intents.bans = True
intents.emojis = True
intents.webhooks = True

# Bot Initialization
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    activity=discord.Activity(type=discord.ActivityType.watching, name="Mature Bot v2.0")
)

# Global Variables
DB_PATH = "mature_bot.db"
DEVELOPER_USER_ID = int(os.getenv("DEVELOPER_USER_ID", "0"))

# Bot Events
@bot.event
async def on_ready():
    bot.start_time = datetime.utcnow()
    print(f"🧠 Mature Bot is ONLINE as {bot.user}")
    print(f"📊 Serving {len(bot.guilds)} servers")
    print(f"👥 Total Users: {sum(g.member_count for g in bot.guilds)}")
    
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# Load Cogs
async def load_cogs():
    for filename in os.listdir("./bot/cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            if filename == "economy.py":
                continue  # Skip economy
            
            try:
                await bot.load_extension(f"bot.cogs.{filename[:-3]}")
                print(f"✅ Loaded cog: {filename}")
            except Exception as e:
                print(f"❌ Failed to load cog {filename}: {e}")

# Start Bot
async def start_bot():
    await init_db()
    await load_cogs()
    set_bot_instance(bot)
    
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    
    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(start_bot())
