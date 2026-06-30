import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db
from datetime import datetime, timedelta, date

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Display a user's avatar")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        embed = discord.Embed(title=f"{target.name}'s Avatar", color=discord.Color.blue())
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Display user information")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        embed = discord.Embed(title=f"User Info: {target.name}", color=target.color)
        embed.add_field(name="ID", value=target.id)
        embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d %H:%M:%S"))
        embed.add_field(name="Joined Discord", value=target.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        embed.add_field(name="Top Role", value=target.top_role.mention)
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Display server information")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=guild.name, color=discord.Color.green())
        embed.add_field(name="ID", value=guild.id)
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Channels", value=len(guild.channels))
        embed.add_field(name="Roles", value=len(guild.roles))
        embed.add_field(name="Boost Level", value=guild.premium_tier)
        embed.add_field(name="Boost Count", value=guild.premium_subscription_count)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create a yes/no poll")
    async def poll(self, interaction: discord.Interaction, question: str):
        embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.blue())
        embed.set_footer(text=f"Poll by {interaction.user}")
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await interaction.response.send_message("✅ Poll created!", ephemeral=True)

    @app_commands.command(name="whois", description="Detailed user info")
    async def whois(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        embed = discord.Embed(title=f"🔍 Whois: {target.name}", color=target.color)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Username", value=f"{target.name}#{target.discriminator}")
        embed.add_field(name="User ID", value=target.id)
        embed.add_field(name="Display Name", value=target.display_name)
        embed.add_field(name="Account Created", value=target.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d %H:%M:%S") if target.joined_at else "N/A")
        embed.add_field(name="Top Role", value=target.top_role.mention if target.top_role else "None")
        embed.add_field(name="Roles", value=", ".join([r.mention for r in target.roles if r != target.guild.default_role]) or "None")
        embed.add_field(name="Status", value=str(target.status).title())
        embed.add_field(name="Bot", value="✅ Yes" if target.bot else "❌ No")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(title="🏓 Pong!", description=f"Latency: {latency}ms", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="uptime", description="Check bot uptime")
    async def uptime(self, interaction: discord.Interaction):
        now = discord.utils.utcnow()
        delta = now - self.bot.start_time
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        embed = discord.Embed(title="⏰ Uptime", description=f"{days}d {hours}h {minutes}m {seconds}s", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stats", description="User activity stats (30 days)")
    async def stats(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        guild = interaction.guild
        today = date.today()
        start_date = today - timedelta(days=30)

        rows = db.fetch_all(
            "SELECT messages, voice_seconds FROM daily_stats "
            "WHERE user_id = ? AND guild_id = ? AND date >= ?",
            (target.id, guild.id, start_date.isoformat())
        )

        total_messages = sum(row["messages"] for row in rows)
        total_voice_seconds = sum(row["voice_seconds"] for row in rows)
        total_voice_hours = total_voice_seconds / 3600
        hours = int(total_voice_hours)
        minutes = int((total_voice_hours - hours) * 60)

        embed = discord.Embed(title=f"📊 Activity Stats for {target.name}", color=target.color, timestamp=datetime.utcnow())
        embed.add_field(name="📝 Messages (30 days)", value=str(total_messages), inline=True)
        embed.add_field(name="🎤 Voice Time (30 days)", value=f"{hours}h {minutes}m", inline=True)
        embed.set_footer(text=f"Server: {guild.name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bot_stats", description="Show bot statistics")
    async def bot_stats(self, interaction: discord.Interaction):
        bot = self.bot
        total_servers = len(bot.guilds)
        total_users = sum(g.member_count for g in bot.guilds)
        now = discord.utils.utcnow()
        delta = now - bot.start_time
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        total_commands = len(bot.commands)
        warning_count = db.fetch_one("SELECT COUNT(*) as count FROM warnings")["count"]
        ticket_count = db.fetch_one("SELECT COUNT(*) as count FROM tickets")["count"]

        embed = discord.Embed(title="🤖 Mature Bot Statistics", color=discord.Color.blue(), timestamp=now)
        embed.add_field(name="📊 Servers", value=str(total_servers), inline=True)
        embed.add_field(name="👥 Users", value=str(total_users), inline=True)
        embed.add_field(name="⏰ Uptime", value=uptime_str, inline=True)
        embed.add_field(name="📝 Commands", value=str(total_commands), inline=True)
        embed.add_field(name="⚠️ Warnings", value=str(warning_count), inline=True)
        embed.add_field(name="🎟️ Tickets", value=str(ticket_count), inline=True)
        embed.set_footer(text=f"Started at {bot.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
