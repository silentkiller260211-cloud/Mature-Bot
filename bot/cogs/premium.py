import discord
from discord.ext import commands
import aiosqlite

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.custom_cmds = {}

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def addpremium(self, ctx, guild_id: int, tier: str = "gold"):
        async with aiosqlite.connect("mature_bot.db") as db:
            await db.execute("INSERT OR REPLACE INTO premium (guild_id, tier) VALUES (?, ?)", (guild_id, tier))
            await db.commit()
        await ctx.send(f"💎 Premium {tier} added to server {guild_id}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def noprefix_user(self, ctx, member: discord.Member):
        async with aiosqlite.connect("mature_bot.db") as db:
            cursor = await db.execute("SELECT COUNT(*) FROM no_prefix_users WHERE guild_id=?", (ctx.guild.id,))
            count = (await cursor.fetchone())[0]
            if count >= 10:
                return await ctx.send("❌ Limit of 10 users reached.")
            await db.execute("INSERT OR IGNORE INTO no_prefix_users (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(f"⚡ {member} added to no-prefix list.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def addcmd(self, ctx, name: str, *, response: str):
        self.custom_cmds.setdefault(ctx.guild.id, {})[name] = response
        await ctx.send(f"✅ Custom command `!{name}` added.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def delcmd(self, ctx, name: str):
        if name in self.custom_cmds.get(ctx.guild.id, {}):
            del self.custom_cmds[ctx.guild.id][name]
            await ctx.send(f"✅ Custom command `!{name}` deleted.")
        else:
            await ctx.send("❌ Command not found.")

    @commands.hybrid_command()
    async def cmds(self, ctx):
        cmds = self.custom_cmds.get(ctx.guild.id, {})
        if not cmds:
            return await ctx.send("📋 No custom commands.")
        desc = "\n".join([f"`!{k}` → {v[:30]}..." for k, v in cmds.items()])
        embed = discord.Embed(title="📋 Custom Commands", description=desc, color=0x6366f1)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Premium(bot))
