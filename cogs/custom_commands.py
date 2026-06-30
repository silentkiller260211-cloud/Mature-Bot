import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db

class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addcmd", description="Add a custom command")
    @app_commands.default_permissions(administrator=True)
    async def addcmd(self, interaction: discord.Interaction, name: str, response: str):
        db.execute_query("INSERT OR IGNORE INTO custom_commands (guild_id, command_name, response) VALUES (?, ?, ?)", (interaction.guild.id, name, response))
        embed = discord.Embed(title="✅ Command Added", description=f"Custom command `{name}` added.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delcmd", description="Delete a custom command")
    @app_commands.default_permissions(administrator=True)
    async def delcmd(self, interaction: discord.Interaction, name: str):
        db.execute_query("DELETE FROM custom_commands WHERE guild_id = ? AND command_name = ?", (interaction.guild.id, name))
        embed = discord.Embed(title="✅ Command Deleted", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cmds", description="List custom commands")
    async def cmds(self, interaction: discord.Interaction):
        records = db.fetch_all("SELECT command_name, response FROM custom_commands WHERE guild_id = ?", (interaction.guild.id,))
        if not records:
            embed = discord.Embed(title="ℹ️ No Custom Commands", color=discord.Color.blue())
        else:
            embed = discord.Embed(title="📝 Custom Commands", color=discord.Color.blue())
            for rec in records:
                embed.add_field(name=rec["command_name"], value=rec["response"], inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
