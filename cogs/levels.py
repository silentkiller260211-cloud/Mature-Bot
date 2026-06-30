import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db
from datetime import datetime, timedelta

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        key = (message.author.id, message.guild.id)
        now = datetime.now()
        if key in self.cooldown and (now - self.cooldown[key]) < timedelta(seconds=60):
            return
        self.cooldown[key] = now
        record = db.fetch_one("SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?", (message.author.id, message.guild.id))
        if not record:
            xp, level = 0, 0
            db.execute_query("INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, 0, 0)", (message.author.id, message.guild.id))
        else:
            xp, level = record["xp"], record["level"]
        xp_gain = 15 + (len(message.content.split()) // 3)
        xp_gain = min(xp_gain, 25)
        xp += xp_gain
        required = 5 * (level ** 2) + 50 * level + 100
        while xp >= required:
            level += 1
            xp -= required
            required = 5 * (level ** 2) + 50 * level + 100
            channel_record = db.fetch_one("SELECT channel_id FROM leveling_channels WHERE guild_id = ? AND user_id = ?", (message.guild.id, message.author.id))
            target_channel = message.guild.get_channel(channel_record["channel_id"]) if channel_record else message.channel
            if target_channel:
                await target_channel.send(f"🎉 {message.author.mention} reached level **{level}**!")
        db.execute_query("UPDATE levels SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?", (xp, level, message.author.id, message.guild.id))

    @app_commands.command(name="rank", description="Check your or another's rank")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        record = db.fetch_one("SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?", (target.id, interaction.guild.id))
        if not record:
            embed = discord.Embed(title="ℹ️ No XP", description=f"{target.mention} has no XP yet.", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)
            return
        xp, level = record["xp"], record["level"]
        required = 5 * (level ** 2) + 50 * level + 100
        embed = discord.Embed(title=f"📊 {target.name}'s Rank", color=target.color)
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="XP", value=f"{xp}/{required}", inline=True)
        embed.add_field(name="Progress", value=f"{(xp/required)*100:.1f}%", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Top 10 users by level")
    async def leaderboard(self, interaction: discord.Interaction):
        records = db.fetch_all("SELECT user_id, level, xp FROM levels WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10", (interaction.guild.id,))
        if not records:
            embed = discord.Embed(title="ℹ️ No XP", description="No XP data yet.", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)
            return
        embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())
        desc = ""
        for idx, rec in enumerate(records, 1):
            user = interaction.guild.get_member(rec["user_id"])
            if user:
                desc += f"{idx}. {user.mention} - Level {rec['level']} ({rec['xp']} XP)\n"
        embed.description = desc
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leveling_channel", description="Set personal leveling channel")
    async def leveling_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db.execute_query("INSERT OR REPLACE INTO leveling_channels (guild_id, user_id, channel_id) VALUES (?, ?, ?)", (interaction.guild.id, interaction.user.id, channel.id))
        embed = discord.Embed(title="✅ Leveling Channel Set", description=f"Level-ups will be sent to {channel.mention}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leveling_channel_remove", description="Remove personal leveling channel")
    async def leveling_channel_remove(self, interaction: discord.Interaction):
        db.execute_query("DELETE FROM leveling_channels WHERE guild_id = ? AND user_id = ?", (interaction.guild.id, interaction.user.id))
        embed = discord.Embed(title="✅ Leveling Channel Removed", description="Level-ups will go to current channel.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leveling_channel_view", description="View personal leveling channel")
    async def leveling_channel_view(self, interaction: discord.Interaction):
        record = db.fetch_one("SELECT channel_id FROM leveling_channels WHERE guild_id = ? AND user_id = ?", (interaction.guild.id, interaction.user.id))
        if not record:
            embed = discord.Embed(title="ℹ️ No Channel Set", description="You have no personal leveling channel.", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed)
            return
        channel = interaction.guild.get_channel(record["channel_id"])
        if channel:
            embed = discord.Embed(title="📌 Your Leveling Channel", description=f"{channel.mention}", color=discord.Color.green())
        else:
            embed = discord.Embed(title="❌ Channel Not Found", description="Your leveling channel was deleted.", color=discord.Color.red())
            db.execute_query("DELETE FROM leveling_channels WHERE guild_id = ? AND user_id = ?", (interaction.guild.id, interaction.user.id))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="xp_reset", description="Reset all users' XP (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def xp_reset(self, interaction: discord.Interaction):
        await interaction.response.defer()
        db.execute_query("DELETE FROM levels WHERE guild_id = ?", (interaction.guild.id,))
        embed = discord.Embed(title="✅ XP Reset Complete", description="All XP reset for this server.", color=discord.Color.green())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="xp_add", description="Add XP to a user (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def xp_add(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if amount <= 0:
            embed = discord.Embed(title="❌ Invalid Amount", description="Amount must be positive.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        record = db.fetch_one("SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?", (user.id, interaction.guild.id))
        if not record:
            db.execute_query("INSERT INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, 0, 0)", (user.id, interaction.guild.id))
            xp, level = 0, 0
        else:
            xp, level = record["xp"], record["level"]
        new_xp = xp + amount
        db.execute_query("UPDATE levels SET xp = ? WHERE user_id = ? AND guild_id = ?", (new_xp, user.id, interaction.guild.id))
        embed = discord.Embed(title="✅ XP Added", description=f"Added {amount} XP to {user.mention}. New total: {new_xp}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="xp_remove", description="Remove XP from a user (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def xp_remove(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if amount <= 0:
            embed = discord.Embed(title="❌ Invalid Amount", description="Amount must be positive.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        record = db.fetch_one("SELECT xp, level FROM levels WHERE user_id = ? AND guild_id = ?", (user.id, interaction.guild.id))
        if not record:
            embed = discord.Embed(title="❌ User Not Found", description=f"{user.mention} has no XP.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        xp, level = record["xp"], record["level"]
        new_xp = max(0, xp - amount)
        db.execute_query("UPDATE levels SET xp = ? WHERE user_id = ? AND guild_id = ?", (new_xp, user.id, interaction.guild.id))
        embed = discord.Embed(title="✅ XP Removed", description=f"Removed {amount} XP from {user.mention}. New total: {new_xp}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Levels(bot))
