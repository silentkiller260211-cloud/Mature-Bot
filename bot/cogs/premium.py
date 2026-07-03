import discord
from discord.ext import commands
import aiosqlite
import random
import string
from datetime import datetime, timedelta
from utils.database import get_premium_code, mark_code_used, create_premium_code

DB_PATH = "mature_bot.db"

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description="💎 Redeem a premium code")
    async def premium(self, ctx, code: str = None):
        """💎 Redeem a premium code to activate premium features"""
        if not code:
            embed = discord.Embed(
                title="💎 Premium System",
                description="Use `!premium <code>` to redeem your premium code.\n\nExample: `!premium ABCD1234EFGH5678`",
                color=0x6366f1
            )
            return await ctx.send(embed=embed)
        
        code = code.upper()
        result = await get_premium_code(code)
        
        if not result:
            return await ctx.send("❌ Invalid premium code!")
        
        db_code, tier, duration, days, user_id, used = result
        
        if used:
            return await ctx.send("❌ This code has already been used!")
        
        # Mark code as used
        await mark_code_used(code, ctx.author.id)
        
        # Calculate expiry
        expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
        
        # Activate premium for guild
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO premium (guild_id, tier, duration, expires_at) VALUES (?, ?, ?, ?)",
                (ctx.guild.id, tier, duration, expires_at)
            )
            await db.commit()
        
        # Duration display
        duration_map = {
            'monthly': '1 Month',
            '3months': '3 Months',
            '6months': '6 Months',
            'yearly': '1 Year'
        }
        
        embed = discord.Embed(
            title="✅ Premium Activated!",
            description=f"**Tier:** {tier.title()}\n**Duration:** {duration_map.get(duration, duration)}\n**Expires:** <t:{int(datetime.fromisoformat(expires_at).timestamp())}:R>",
            color=0x10b981
        )
        embed.set_footer(text="Thank you for supporting Mature Bot!")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(description="🎫 Generate a premium code (Developer only)")
    @commands.is_owner()
    async def generatecode(self, ctx, tier: str, duration: str = 'monthly'):
        """🎫 Generate a premium code (Developer only)"""
        if tier.lower() not in ['gold', 'platinum', 'ultimate']:
            return await ctx.send("❌ Invalid tier! Use: gold, platinum, or ultimate")
        
        duration_map = {
            'monthly': 30,
            '3months': 90,
            '6months': 180,
            'yearly': 365
        }
        
        days = duration_map.get(duration.lower(), 30)
        code = generate_code()
        await create_premium_code(code, tier.lower(), duration.lower(), days)
        
        embed = discord.Embed(
            title="🎫 Premium Code Generated",
            description=f"**Code:** `{code}`\n**Tier:** {tier.title()}\n**Duration:** {duration.title()} ({days} days)",
            color=0x6366f1
        )
        embed.set_footer(text="Share this code with users!")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Premium(bot))
