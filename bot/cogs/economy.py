import discord
from discord.ext import commands
import aiosqlite
import random

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_balance(self, user_id, guild_id):
        async with aiosqlite.connect("mature_bot.db") as db:
            cursor = await db.execute("SELECT balance, xp, level FROM economy WHERE user_id=? AND guild_id=?", (user_id, guild_id))
            row = await cursor.fetchone()
            return row if row else (0, 0, 1)

    @commands.hybrid_command()
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        bal, xp, level = await self.get_balance(member.id, ctx.guild.id)
        embed = discord.Embed(title=f"💰 {member.name}'s Balance", color=0x10b981)
        embed.add_field(name="Balance", value=f"₹{bal}", inline=True)
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="XP", value=xp, inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def daily(self, ctx):
        amount = random.randint(100, 500)
        async with aiosqlite.connect("mature_bot.db") as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id, guild_id, balance) VALUES (?, ?, 0)", (ctx.author.id, ctx.guild.id))
            await db.execute("UPDATE economy SET balance = balance + ? WHERE user_id=? AND guild_id=?", (amount, ctx.author.id, ctx.guild.id))
            await db.commit()
        await ctx.send(f"🎁 Daily reward: **₹{amount}**")

    @commands.hybrid_command()
    async def work(self, ctx):
        amount = random.randint(50, 200)
        async with aiosqlite.connect("mature_bot.db") as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id, guild_id, balance) VALUES (?, ?, 0)", (ctx.author.id, ctx.guild.id))
            await db.execute("UPDATE economy SET balance = balance + ? WHERE user_id=? AND guild_id=?", (amount, ctx.author.id, ctx.guild.id))
            await db.commit()
        await ctx.send(f"💼 You worked and earned **₹{amount}**")

    @commands.hybrid_command()
    async def leaderboard(self, ctx):
        async with aiosqlite.connect("mature_bot.db") as db:
            cursor = await db.execute("SELECT user_id, balance FROM economy WHERE guild_id=? ORDER BY balance DESC LIMIT 10", (ctx.guild.id,))
            rows = await cursor.fetchall()
        if not rows:
            return await ctx.send("📊 No data yet.")
        desc = "\n".join([f"{i+1}. <@{r[0]}> - ₹{r[1]}" for i, r in enumerate(rows)])
        embed = discord.Embed(title="🏆 Leaderboard", description=desc, color=0xf59e0b)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def rank(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        bal, xp, level = await self.get_balance(member.id, ctx.guild.id)
        await ctx.send(f"📊 {member.name} is Level **{level}** with **{xp} XP**")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def xp_add(self, ctx, member: discord.Member, amount: int):
        async with aiosqlite.connect("mature_bot.db") as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id, guild_id, xp) VALUES (?, ?, 0)", (member.id, ctx.guild.id))
            await db.execute("UPDATE economy SET xp = xp + ? WHERE user_id=? AND guild_id=?", (amount, member.id, ctx.guild.id))
            await db.commit()
        await ctx.send(f"✅ Added {amount} XP to {member.name}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def xp_remove(self, ctx, member: discord.Member, amount: int):
        async with aiosqlite.connect("mature_bot.db") as db:
            await db.execute("UPDATE economy SET xp = MAX(0, xp - ?) WHERE user_id=? AND guild_id=?", (amount, member.id, ctx.guild.id))
            await db.commit()
        await ctx.send(f"✅ Removed {amount} XP from {member.name}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def xp_reset(self, ctx):
        async with aiosqlite.connect("mature_bot.db") as db:
            await db.execute("UPDATE economy SET xp = 0, level = 1 WHERE guild_id=?", (ctx.guild.id,))
            await db.commit()
        await ctx.send("✅ All XP reset.")

    @commands.hybrid_command()
    async def leveling_channel(self, ctx, channel: discord.TextChannel):
        await ctx.send(f"✅ Level-up channel set to {channel.mention}")

    @commands.hybrid_command()
    async def leveling_channel_remove(self, ctx):
        await ctx.send("✅ Level-up channel removed.")

    @commands.hybrid_command()
    async def leveling_channel_view(self, ctx):
        await ctx.send("📢 No leveling channel set.")

async def setup(bot):
    await bot.add_cog(Economy(bot))
