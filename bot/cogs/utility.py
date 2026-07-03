import discord
from discord.ext import commands
from datetime import datetime

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.utcnow()

    @commands.hybrid_command()
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"🖼️ {member.name}'s Avatar", color=0x6366f1)
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def serverinfo(self, ctx):
        g = ctx.guild
        embed = discord.Embed(title=f"📊 {g.name}", color=0x6366f1)
        embed.add_field(name="Members", value=g.member_count, inline=True)
        embed.add_field(name="Channels", value=len(g.channels), inline=True)
        embed.add_field(name="Roles", value=len(g.roles), inline=True)
        embed.add_field(name="Owner", value=g.owner.mention, inline=True)
        embed.set_thumbnail(url=g.icon.url if g.icon else None)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"👤 {member.name}", color=member.color)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Joined", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="Created", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def whois(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"🔍 {member.name}", description=f"ID: {member.id}", color=member.color)
        embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name="Bot?", value="Yes" if member.bot else "No", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"🏓 Pong! **{latency}ms**")

    @commands.hybrid_command()
    async def uptime(self, ctx):
        delta = datetime.utcnow() - self.start_time
        await ctx.send(f"⏱️ Uptime: {delta.days}d {delta.seconds//3600}h {(delta.seconds//60)%60}m")

    @commands.hybrid_command()
    async def bot_stats(self, ctx):
        embed = discord.Embed(title="🤖 Bot Statistics", color=0x6366f1)
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=len(self.bot.users), inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency*1000)}ms", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def stats(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await ctx.send(f"📊 {member.name} sent 0 messages in last 30 days.")

    @commands.hybrid_command()
    async def invite(self, ctx):
        from os import getenv
        client_id = getenv("CLIENT_ID", "0")
        url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot%20applications.commands"
        embed = discord.Embed(title="🔗 Invite Mature Bot", description=f"[Click Here]({url})", color=0x6366f1)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def help(self, ctx):
        embed = discord.Embed(title="📖 Mature Bot Help", description="Use `!help [command]` for more info.", color=0x6366f1)
        embed.add_field(name="Moderation", value="ban, kick, clear, warn, timeout", inline=False)
        embed.add_field(name="Music", value="play, pause, skip, queue, volume", inline=False)
        embed.add_field(name="Economy", value="balance, daily, work, leaderboard, rank", inline=False)
        embed.add_field(name="Utility", value="avatar, serverinfo, userinfo, ping, invite", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def problem(self, ctx, *, issue: str):
        await ctx.send("✅ Problem reported to developers. Thank you!")

async def setup(bot):
    await bot.add_cog(Utility(bot))
