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
        self.custom_cmds = {}

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

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def addpremium(self, ctx, guild_id: int, tier: str="gold", duration: str="monthly"):
        """Add premium to a server (Developer only)"""
        duration_map = {
            'monthly': 30,
            '3months': 90,
            '6months': 180,
            'yearly': 365
        }
        
        days = duration_map.get(duration.lower(), 30)
        expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO premium (guild_id, tier, duration, expires_at) VALUES (?, ?, ?, ?)",
                (guild_id, tier.lower(), duration.lower(), expires_at)
            )
            await db.commit()
        
        await ctx.send(f"💎 Premium {tier.title()} ({duration}) added to server {guild_id}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def noprefix_user(self, ctx, member: discord.Member):
        """Add a user to no-prefix list"""
        async with aiosqlite.connect(DB_PATH) as db:
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
        """Add a custom command"""
        self.custom_cmds.setdefault(ctx.guild.id, {})[name] = response
        await ctx.send(f"✅ Custom command `!{name}` added.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def delcmd(self, ctx, name: str):
        """Delete a custom command"""
        if name in self.custom_cmds.get(ctx.guild.id, {}):
            del self.custom_cmds[ctx.guild.id][name]
            await ctx.send(f"✅ Custom command `!{name}` deleted.")
        else:
            await ctx.send("❌ Command not found.")

    @commands.hybrid_command()
    async def cmds(self, ctx):
        """View all custom commands"""
        cmds = self.custom_cmds.get(ctx.guild.id, {})
        if not cmds:
            return await ctx.send("📋 No custom commands.")
        desc = "\n".join([f"`!{k}` → {v[:30]}..." for k, v in cmds.items()])
        embed = discord.Embed(title="📋 Custom Commands", description=desc, color=0x6366f1)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Premium(bot))
