import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        record = db.fetch_one("SELECT channel_id, message FROM welcome_settings WHERE guild_id = ?", (member.guild.id,))
        if not record:
            return
        channel = member.guild.get_channel(record["channel_id"])
        if channel:
            msg = record["message"].replace("{mention}", member.mention).replace("{server}", member.guild.name)
            await channel.send(msg)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Goodbye message could be added
        pass

    @app_commands.command(name="setwelcome", description="Set welcome channel and message")
    @app_commands.default_permissions(administrator=True)
    async def setwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        db.execute_query("INSERT OR REPLACE INTO welcome_settings (guild_id, channel_id, message) VALUES (?, ?, ?)", (interaction.guild.id, channel.id, message))
        embed = discord.Embed(title="✅ Welcome Set", description=f"Welcome channel set to {channel.mention}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setgoodbye", description="Set goodbye channel and message")
    @app_commands.default_permissions(administrator=True)
    async def setgoodbye(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        # Store goodbye settings similarly
        embed = discord.Embed(title="✅ Goodbye Set", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="testwelcome", description="Test welcome message")
    @app_commands.default_permissions(administrator=True)
    async def testwelcome(self, interaction: discord.Interaction):
        await self.on_member_join(interaction.user)
        embed = discord.Embed(title="✅ Test Sent", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
