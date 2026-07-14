import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "mature_bot.db"

class GlobalNoPrefix(commands.Cog):
    def __init__(self, bot): self.bot = bot

    async def is_global_noprefix(self, user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT expires_at FROM global_noprefix WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row: return False
            if row[0] is None: return True
            return datetime.fromisoformat(row[0]) > datetime.utcnow()

    @commands.hybrid_command(name="global_noprefix", description="Activate global no-prefix using your premium code")
    async def global_noprefix(self, ctx, code: str = None):
        if not code: return await ctx.send(embed=discord.Embed(title="Global No-Prefix", description="Use `/global_noprefix <code>` to activate.", color=0x8b5cf6))
        if await self.is_global_noprefix(ctx.author.id): return await ctx.send(embed=discord.Embed(title="Already Active", description="You already have global no-prefix access!", color=0x3b82f6))
        
        code = code.upper().strip()
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT days, used FROM premium_codes WHERE code = ?", (code,))
            row = await cursor.fetchone()
            if not row: return await ctx.send(embed=discord.Embed(title="Invalid Code", color=0xef4444))
            days, used = row
            if used: return await ctx.send(embed=discord.Embed(title="Code Already Used", color=0xef4444))
            
            await db.execute("UPDATE premium_codes SET used = 1, user_id = ? WHERE code = ?", (ctx.author.id, code))
            expires_at = None if days == -1 else (datetime.utcnow() + timedelta(days=days)).isoformat()
            await db.execute("INSERT OR REPLACE INTO global_noprefix (user_id, expires_at) VALUES (?, ?)", (ctx.author.id, expires_at))
            await db.commit()
            
        await ctx.send(embed=discord.Embed(title="✅ Global No-Prefix Activated!", description="Works in ALL servers now!", color=0x10b981))

async def setup(bot):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS global_noprefix (user_id INTEGER PRIMARY KEY, expires_at TEXT)""")
        await db.commit()
    await bot.add_cog(GlobalNoPrefix(bot))
