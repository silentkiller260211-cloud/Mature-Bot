import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db
from datetime import datetime, timedelta

class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="remind", description="Set a reminder")
    async def remind(self, interaction: discord.Interaction, duration: str, message: str):
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            seconds = int(duration[:-1]) * units[duration[-1]]
        except:
            embed = discord.Embed(title="❌ Invalid Duration", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        remind_time = datetime.now() + timedelta(seconds=seconds)
        db.execute_query("INSERT INTO reminders (user_id, channel_id, message, remind_time) VALUES (?, ?, ?, ?)", (interaction.user.id, interaction.channel.id, message, remind_time))
        embed = discord.Embed(title="✅ Reminder Set", description=f"I'll remind you in {duration}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reminders", description="List your reminders")
    async def reminders(self, interaction: discord.Interaction):
        records = db.fetch_all("SELECT id, message, remind_time FROM reminders WHERE user_id = ? ORDER BY remind_time", (interaction.user.id,))
        if not records:
            embed = discord.Embed(title="ℹ️ No Reminders", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)
            return
        embed = discord.Embed(title="📋 Your Reminders", color=discord.Color.blue())
        for rec in records:
            embed.add_field(name=f"ID: {rec['id']}", value=f"{rec['message']} at {rec['remind_time']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cancelremind", description="Cancel a reminder by ID")
    async def cancelremind(self, interaction: discord.Interaction, reminder_id: int):
        db.execute_query("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, interaction.user.id))
        embed = discord.Embed(title="✅ Reminder Cancelled", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Reminders(bot))
