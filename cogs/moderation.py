import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db
from utils.security import is_owner
import re
from datetime import timedelta, datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def can_target(self, author, target):
        if is_owner(target.id):
            return author.id == target.id
        if target.guild_permissions.administrator and not author.guild_permissions.administrator:
            return False
        return True

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if not self.can_target(interaction.user, member):
            embed = discord.Embed(title="❌ Cannot Kick", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await member.kick(reason=reason)
        embed = discord.Embed(title="✅ Member Kicked", description=f"{member.mention} kicked.\nReason: {reason}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if not self.can_target(interaction.user, member):
            embed = discord.Embed(title="❌ Cannot Ban", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await member.ban(reason=reason)
        embed = discord.Embed(title="✅ Member Banned", description=f"{member.mention} banned.\nReason: {reason}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unban", description="Unban a user")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_name: str):
        async for entry in interaction.guild.bans():
            if str(entry.user) == user_name:
                await interaction.guild.unban(entry.user)
                embed = discord.Embed(title="✅ User Unbanned", color=discord.Color.green())
                await interaction.response.send_message(embed=embed)
                return
        embed = discord.Embed(title="❌ Not Found", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Delete messages")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            embed = discord.Embed(title="❌ Invalid Amount", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(title="✅ Deleted", description=f"Deleted {len(deleted)} messages.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.default_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if not self.can_target(interaction.user, member):
            embed = discord.Embed(title="❌ Cannot Warn", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        db.execute_query("INSERT INTO warnings (user_id, guild_id, reason, moderator_id) VALUES (?, ?, ?, ?)",
                         (member.id, interaction.guild.id, reason, interaction.user.id))
        embed = discord.Embed(title="⚠️ Warned", description=f"{member.mention} warned.\nReason: {reason}", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warnings", description="Check warnings")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        records = db.fetch_all("SELECT reason, created_at FROM warnings WHERE user_id = ? AND guild_id = ?", (target.id, interaction.guild.id))
        if not records:
            embed = discord.Embed(title="ℹ️ No Warnings", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)
            return
        embed = discord.Embed(title=f"⚠️ Warnings for {target.name}", color=discord.Color.orange())
        for idx, rec in enumerate(records, 1):
            embed.add_field(name=f"#{idx}", value=f"Reason: {rec['reason']}\nDate: {rec['created_at']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unwarn", description="Remove a warning")
    @app_commands.default_permissions(manage_messages=True)
    async def unwarn(self, interaction: discord.Interaction, warn_id: int):
        record = db.fetch_one("SELECT user_id FROM warnings WHERE id = ? AND guild_id = ?", (warn_id, interaction.guild.id))
        if not record:
            embed = discord.Embed(title="❌ Not Found", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if not self.can_target(interaction.user, interaction.guild.get_member(record["user_id"])):
            embed = discord.Embed(title="❌ Cannot Remove", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        db.execute_query("DELETE FROM warnings WHERE id = ? AND guild_id = ?", (warn_id, interaction.guild.id))
        embed = discord.Embed(title="✅ Removed", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason"):
        if not self.can_target(interaction.user, member):
            embed = discord.Embed(title="❌ Cannot Timeout", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        match = re.match(r'^(\d+)([smhd])$', duration)
        if not match:
            embed = discord.Embed(title="❌ Invalid Duration", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        num, unit = match.groups()
        seconds = int(num) * units[unit]
        if seconds <= 0 or seconds > 2419200:
            embed = discord.Embed(title="❌ Invalid Duration", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await member.timeout(timedelta(seconds=seconds), reason=reason)
        embed = discord.Embed(title="⏰ Timed Out", description=f"{member.mention} timed out for {duration}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="untimeout", description="Remove timeout")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        if not self.can_target(interaction.user, member):
            embed = discord.Embed(title="❌ Cannot Remove", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await member.timeout(None)
        embed = discord.Embed(title="✅ Timeout Removed", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lock", description="Lock the channel")
    @app_commands.default_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        embed = discord.Embed(title="🔒 Locked", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unlock", description="Unlock the channel")
    @app_commands.default_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
        embed = discord.Embed(title="🔓 Unlocked", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slowmode", description="Set slowmode")
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        if seconds < 0 or seconds > 21600:
            embed = discord.Embed(title="❌ Invalid", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.channel.edit(slowmode_delay=seconds)
        embed = discord.Embed(title="⏳ Slowmode Set", description=f"{seconds}s", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
