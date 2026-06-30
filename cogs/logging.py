import discord
from discord.ext import commands
from discord import app_commands
import json
from utils import database as db

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="logging_autosetup", description="Automatically set up logging channels")
    @app_commands.default_permissions(administrator=True)
    async def logging_autosetup(self, interaction: discord.Interaction):
        await interaction.response.defer()   # ✅ PREVENT TIMEOUT

        category = discord.utils.get(interaction.guild.categories, name="📊 Logs")
        if not category:
            category = await interaction.guild.create_category("📊 Logs")

        log_types = {
            "moderation": "🛡️ moderation",
            "voice": "🎤 voice",
            "message": "📝 message",
            "member": "👤 member",
            "join_leave": "🚪 join-leave"
        }
        channels = {}
        for key, name in log_types.items():
            channel = discord.utils.get(interaction.guild.text_channels, name=name)
            if not channel:
                channel = await interaction.guild.create_text_channel(
                    name,
                    category=category,
                    overwrites={interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False)}
                )
            channels[key] = channel.id

        db.execute_query(
            "INSERT OR REPLACE INTO guild_settings (guild_id, log_channels) VALUES (?, ?)",
            (interaction.guild.id, json.dumps(channels))
        )

        embed = discord.Embed(
            title="✅ Logging Setup Complete",
            description="All logging channels created and configured.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)   # ✅ SEND AFTER WORK

    @app_commands.command(name="logging_enable", description="Enable logging")
    @app_commands.default_permissions(administrator=True)
    async def logging_enable(self, interaction: discord.Interaction):
        await interaction.response.defer()
        record = db.fetch_one("SELECT log_channels FROM guild_settings WHERE guild_id = ?", (interaction.guild.id,))
        if not record:
            embed = discord.Embed(
                title="❌ Error",
                description="Run /logging_autosetup first.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(
            title="✅ Logging Enabled",
            description="All logging channels are now active.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="logging_disable", description="Disable logging")
    @app_commands.default_permissions(administrator=True)
    async def logging_disable(self, interaction: discord.Interaction):
        await interaction.response.defer()
        record = db.fetch_one("SELECT log_channels FROM guild_settings WHERE guild_id = ?", (interaction.guild.id,))
        if not record:
            embed = discord.Embed(
                title="❌ Error",
                description="Run /logging_autosetup first.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        db.execute_query("UPDATE guild_settings SET log_channels = '{}' WHERE guild_id = ?", (interaction.guild.id,))
        embed = discord.Embed(
            title="✅ Logging Disabled",
            description="All logging channels have been disabled.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
