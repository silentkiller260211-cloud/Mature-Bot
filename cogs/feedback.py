import discord
from discord.ext import commands
from discord import app_commands
from utils.security import OWNER_ID

class Feedback(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="problem", description="Submit a problem directly to the bot developer")
    async def problem(self, interaction: discord.Interaction, problem: str):
        await interaction.response.defer(ephemeral=True)

        owner = self.bot.get_user(OWNER_ID)
        if not owner:
            embed = discord.Embed(title="❌ Error", description="Could not find the bot developer.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        now = discord.utils.utcnow()
        embed = discord.Embed(title="📝 New Problem Submitted", color=discord.Color.orange(), timestamp=now)
        embed.add_field(name="👤 User", value=f"{interaction.user} (ID: {interaction.user.id})", inline=False)
        embed.add_field(name="🌐 Server", value=f"{interaction.guild.name} (ID: {interaction.guild.id})", inline=False)
        embed.add_field(name="❓ Problem", value=problem, inline=False)
        full_time = discord.utils.format_dt(now, 'F')
        relative_time = discord.utils.format_dt(now, 'R')
        embed.add_field(name="⏰ Submitted At", value=f"**{full_time}**\n( {relative_time} )", inline=False)
        embed.set_footer(text="Reply to the user in DMs.")

        try:
            await owner.send(embed=embed)
            confirm = discord.Embed(title="✅ Problem Submitted", description="Your problem has been sent to the bot developer.", color=discord.Color.green())
            await interaction.followup.send(embed=confirm, ephemeral=True)
        except discord.Forbidden:
            embed = discord.Embed(title="❌ Error", description="Developer DMs are disabled.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="❌ Error", description=str(e), color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Feedback(bot))
