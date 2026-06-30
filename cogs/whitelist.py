import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db

class Whitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="whitelist_add", description="Whitelist a user for a specific anti-program")
    @app_commands.default_permissions(administrator=True)
    async def whitelist_add(self, interaction: discord.Interaction, feature: str, user: discord.User):
        db.execute_query("INSERT OR IGNORE INTO whitelist (guild_id, feature, user_id) VALUES (?, ?, ?)", (interaction.guild.id, feature, user.id))
        embed = discord.Embed(title="✅ Whitelisted", description=f"{user.mention} whitelisted for {feature}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="whitelist_remove", description="Remove from whitelist")
    @app_commands.default_permissions(administrator=True)
    async def whitelist_remove(self, interaction: discord.Interaction, feature: str, user: discord.User):
        db.execute_query("DELETE FROM whitelist WHERE guild_id = ? AND feature = ? AND user_id = ?", (interaction.guild.id, feature, user.id))
        embed = discord.Embed(title="✅ Removed from Whitelist", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="whitelist_list", description="List whitelisted users for a feature")
    @app_commands.default_permissions(administrator=True)
    async def whitelist_list(self, interaction: discord.Interaction, feature: str):
        records = db.fetch_all("SELECT user_id FROM whitelist WHERE guild_id = ? AND feature = ?", (interaction.guild.id, feature))
        if not records:
            embed = discord.Embed(title="ℹ️ No Whitelisted Users", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)
            return
        users = []
        for rec in records:
            user = interaction.guild.get_member(rec["user_id"])
            if user:
                users.append(user.mention)
        embed = discord.Embed(title=f"👤 Whitelisted Users for {feature}", description="\n".join(users) or "None", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="whitelist_clear", description="Clear all whitelist for a feature")
    @app_commands.default_permissions(administrator=True)
    async def whitelist_clear(self, interaction: discord.Interaction, feature: str):
        db.execute_query("DELETE FROM whitelist WHERE guild_id = ? AND feature = ?", (interaction.guild.id, feature))
        embed = discord.Embed(title="✅ Whitelist Cleared", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Whitelist(bot))
