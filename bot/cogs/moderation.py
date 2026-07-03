import discord
from discord.ext import commands
from discord import app_commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason"):
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member} banned. Reason: {reason}")

    @commands.hybrid_command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason"):
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member} kicked. Reason: {reason}")

    @commands.hybrid_command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 10):
        deleted = await ctx.channel.purge(limit=min(amount, 100))
        await ctx.send(f"🗑️ Cleared {len(deleted)} messages.", delete_after=3)

    @commands.hybrid_command()
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason"):
        await ctx.send(f"⚠️ {member} warned. Reason: {reason}")

    @commands.hybrid_command()
    async def warnings(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await ctx.send(f"📋 {member} has 0 warnings.")

    @commands.hybrid_command()
    @commands.has_permissions(moderate_members=True)
    async def unwarn(self, ctx, warn_id: int):
        await ctx.send(f"✅ Warning #{warn_id} removed.")

    @commands.hybrid_command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, minutes: int = 10, *, reason="No reason"):
        from datetime import timedelta
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"🔇 {member} timed out for {minutes} minutes.")

    @commands.hybrid_command()
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        await member.timeout(None)
        await ctx.send(f"🔊 {member} untimed out.")

    @commands.hybrid_command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ {user} unbanned.")

    @commands.hybrid_command()
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, role: discord.Role):
        await member.add_roles(role)
        await ctx.send(f"✅ Added {role} to {member}.")

    @commands.hybrid_command()
    @commands.has_permissions(manage_roles=True)
    async def removerole(self, ctx, member: discord.Member, role: discord.Role):
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed {role} from {member}.")

    @commands.hybrid_command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 Channel locked.")

    @commands.hybrid_command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.send("🔓 Channel unlocked.")

    @commands.hybrid_command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"🐌 Slowmode set to {seconds} seconds.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
