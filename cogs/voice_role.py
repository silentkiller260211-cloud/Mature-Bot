import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db

class VoiceRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        record = db.fetch_one("SELECT role_id FROM voice_role WHERE guild_id = ?", (member.guild.id,))
        if not record:
            return
        role = member.guild.get_role(record["role_id"])
        if not role:
            return
        if before.channel is None and after.channel is not None:
            await member.add_roles(role, reason="Auto-role on voice join")
        elif before.channel is not None and after.channel is None:
            await member.remove_roles(role, reason="Auto-remove on voice leave")

    @app_commands.command(name="vc_role_set", description="Set role for voice join/leave")
    @app_commands.default_permissions(administrator=True)
    async def vc_role_set(self, interaction: discord.Interaction, role: discord.Role):
        db.execute_query("INSERT OR REPLACE INTO voice_role (guild_id, role_id) VALUES (?, ?)", (interaction.guild.id, role.id))
        embed = discord.Embed(title="✅ Voice Role Set", description=f"Users will get {role.mention} when joining voice.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="vc_role_remove", description="Remove voice role")
    @app_commands.default_permissions(administrator=True)
    async def vc_role_remove(self, interaction: discord.Interaction):
        db.execute_query("DELETE FROM voice_role WHERE guild_id = ?", (interaction.guild.id,))
        embed = discord.Embed(title="✅ Voice Role Removed", description="Auto-role disabled.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="vc_role_status", description="Check voice role status")
    @app_commands.default_permissions(administrator=True)
    async def vc_role_status(self, interaction: discord.Interaction):
        record = db.fetch_one("SELECT role_id FROM voice_role WHERE guild_id = ?", (interaction.guild.id,))
        if not record:
            embed = discord.Embed(title="ℹ️ No Voice Role Set", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)
            return
        role = interaction.guild.get_role(record["role_id"])
        if role:
            embed = discord.Embed(title="🎤 Voice Role", description=f"Current role: {role.mention}", color=discord.Color.green())
        else:
            embed = discord.Embed(title="❌ Role Not Found", color=discord.Color.red())
            db.execute_query("DELETE FROM voice_role WHERE guild_id = ?", (interaction.guild.id,))
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceRole(bot))
