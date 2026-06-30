import discord
from discord.ext import commands
import os
import logging
from dotenv import load_dotenv
from utils.database import init_db
from utils.security import is_owner

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class MatureBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.owner_id = int(os.getenv("OWNER_ID", 0))
        self.start_time = discord.utils.utcnow()
        init_db()

    async def setup_hook(self):
        logging.info("Loading extensions...")
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith("__"):
                try:
                    await self.load_extension(f"cogs.{file[:-3]}")
                    logging.info(f"Loaded {file}")
                except Exception as e:
                    logging.error(f"Failed to load {file}: {e}")
        await self.tree.sync()
        logging.info("Slash commands synced globally.")

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!help | /help"))

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        embed = discord.Embed(title="❌ Error", description=str(error), color=discord.Color.red())
        await ctx.send(embed=embed)

bot = MatureBot()
bot.run(TOKEN)
