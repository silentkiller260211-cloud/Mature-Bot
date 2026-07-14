import discord
from discord.ext import commands
import aiosqlite

DB_PATH = "mature_bot.db"

class PremiumFeatures(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="noprefix_add", description="Add user to No-Prefix list (Use commands without '!')")
    @commands.has_permissions(administrator=True)
    async def noprefix_add(self, ctx, member: discord.Member = None):
        if not member: return await ctx.send("Please mention a user.")
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM no_prefix_users WHERE guild_id=?", (ctx.guild.id,))
            if (await cursor.fetchone())[0] >= 10: return await ctx.send("Limit reached (10 users).")
            await db.execute("INSERT OR IGNORE INTO no_prefix_users (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(embed=discord.Embed(title="✅ No-Prefix Enabled", description=f"{member.mention} can now use commands without '!' prefix.", color=0x10b981))

    @commands.hybrid_command(name="noprefix_remove", description="Remove user from No-Prefix list")
    @commands.has_permissions(administrator=True)
    async def noprefix_remove(self, ctx, member: discord.Member = None):
        if not member: return await ctx.send("Please mention a user.")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM no_prefix_users WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(embed=discord.Embed(title="✅ No-Prefix Removed", description=f"{member.mention} must now use '!' prefix.", color=0xef4444))

async def setup(bot): await bot.add_cog(PremiumFeatures(bot))
