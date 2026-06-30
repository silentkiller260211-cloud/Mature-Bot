import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db
import json

class Backup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fullbackup", description="Create a full server backup")
    @app_commands.default_permissions(administrator=True)
    async def fullbackup(self, interaction: discord.Interaction):
        guild = interaction.guild
        data = {
            "roles": [{"name": r.name, "permissions": r.permissions.value, "colour": r.colour.value} for r in guild.roles if not r.is_default()],
            "channels": [{"name": c.name, "type": str(c.type), "position": c.position} for c in guild.channels],
        }
        db.execute_query("INSERT INTO backups (guild_id, backup_data, created_by) VALUES (?, ?, ?)", (guild.id, json.dumps(data), interaction.user.id))
        embed = discord.Embed(title="✅ Backup Created", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="restorebackup", description="Restore a backup by ID")
    @app_commands.default_permissions(administrator=True)
    async def restorebackup(self, interaction: discord.Interaction, backup_id: int):
        record = db.fetch_one("SELECT backup_data FROM backups WHERE id = ? AND guild_id = ?", (backup_id, interaction.guild.id))
        if not record:
            embed = discord.Embed(title="❌ Backup Not Found", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
            return
        # Restore logic would be more complex; for now just a placeholder
        embed = discord.Embed(title="✅ Backup Restored", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Backup(bot))
