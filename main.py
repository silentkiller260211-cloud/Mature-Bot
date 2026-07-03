import os
import asyncio
import threading
from dotenv import load_dotenv
import discord
from discord.ext import commands
from utils.database import init_db, get_no_prefix_users
from dashboard.app import run_dashboard, set_bot_instance

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!", 
    intents=intents, 
    help_command=None, 
    activity=discord.Activity(type=discord.ActivityType.watching, name="Mature Bot v2.0")
)

@bot.event
async def on_ready():
    print(f"🧠 Mature Bot is ONLINE as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    
    # Smooth No-Prefix Check (Async DB)
    no_prefix_users = await get_no_prefix_users(message.guild.id)
    if message.author.id in no_prefix_users and not message.content.startswith('!'):
        message.content = '!' + message.content

    await bot.process_commands(message)

async def load_cogs():
    for filename in os.listdir("./bot/cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await bot.load_extension(f"bot.cogs.{filename[:-3]}")
                print(f"✅ Loaded cog: {filename}")
            except Exception as e:
                print(f"❌ Failed to load cog {filename}: {e}")

async def start_bot():
    await init_db()
    await load_cogs()
    set_bot_instance(bot)
    
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    
    await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(start_bot())
