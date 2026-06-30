import discord
from discord.ext import commands
from utils import database as db
from datetime import datetime, date

class Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_start = {}  # (user_id, guild_id) -> datetime

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        today = date.today()
        db.execute_query(
            "INSERT INTO daily_stats (user_id, guild_id, date, messages) VALUES (?, ?, ?, 1) "
            "ON CONFLICT(user_id, guild_id, date) DO UPDATE SET messages = messages + 1",
            (message.author.id, message.guild.id, today.isoformat())
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        key = (member.id, member.guild.id)
        now = datetime.utcnow()

        if before.channel is None and after.channel is not None:
            self.voice_start[key] = now

        elif after.channel is None:
            if key in self.voice_start:
                start = self.voice_start.pop(key)
                duration = (now - start).total_seconds()
                if duration > 0:
                    today = date.today()
                    db.execute_query(
                        "INSERT INTO daily_stats (user_id, guild_id, date, voice_seconds) VALUES (?, ?, ?, ?) "
                        "ON CONFLICT(user_id, guild_id, date) DO UPDATE SET voice_seconds = voice_seconds + ?",
                        (member.id, member.guild.id, today.isoformat(), duration, duration)
                    )

        elif before.channel != after.channel and after.channel is not None:
            if key not in self.voice_start:
                self.voice_start[key] = now

async def setup(bot):
    await bot.add_cog(Tracking(bot))
