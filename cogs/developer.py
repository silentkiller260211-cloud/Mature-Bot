import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db
from utils.security import is_owner
from datetime import datetime, timedelta

class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addpremium", description="Add premium to a server (Owner only)")
    async def addpremium(self, interaction: discord.Interaction, server_id: str, duration_days: int):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("❌ Only bot owner can use this.", ephemeral=True)
            return
        expiry = (datetime.now() + timedelta(days=duration_days)).isoformat()
        db.execute_query("INSERT OR REPLACE INTO premium_servers (guild_id, expiry) VALUES (?, ?)", (int(server_id), expiry))
        embed = discord.Embed(title="✅ Premium Added", description=f"Server {server_id} premium for {duration_days} days.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="noprefix_user", description="Enable no-prefix mode for a user (Owner only)")
    async def noprefix_user(self, interaction: discord.Interaction, user: discord.User):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message("❌ Only bot owner can use this.", ephemeral=True)
            return
        db.execute_query("INSERT OR REPLACE INTO noprefix_users (user_id) VALUES (?)", (user.id,))
        embed = discord.Embed(title="✅ No-Prefix Enabled", description=f"{user.mention} can now use commands without prefix globally.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Developer(bot))
