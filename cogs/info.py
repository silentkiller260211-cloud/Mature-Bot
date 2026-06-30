import discord
from discord.ext import commands
from discord import app_commands

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📚 Help", description="Use slash commands (/command) to interact with the bot.\nPrefix: `!`", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite", description="Get bot invite link")
    async def invite(self, interaction: discord.Interaction):
        invite = discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions.all())
        embed = discord.Embed(title="🔗 Invite Me", description=f"[Click here]({invite}) to invite the bot.", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Info(bot))
