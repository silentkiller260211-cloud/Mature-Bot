import discord
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime
from utils.embed_helper import create_success_embed, create_error_embed, create_info_embed

DB_PATH = "mature_bot.db"

class VanityProtection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_vanity.start()

    def cog_unload(self):
        self.check_vanity.cancel()

    @tasks.loop(minutes=5)
    async def check_vanity(self):
        for guild in self.bot.guilds:
            if not guild.vanity_invite:
                continue
            
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT vanity_code FROM vanity_protection WHERE guild_id=?",
                    (guild.id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    saved_code = row[0]
                    current_code = guild.vanity_invite.code
                    
                    if saved_code != current_code:
                        channel = None
                        async for text_channel in guild.text_channels:
                            if text_channel.permissions_for(guild.me).send_messages:
                                channel = text_channel
                                break
                        
                        if channel:
                            embed = discord.Embed(
                                title="⚠️ Vanity URL Changed!",
                                description="The server vanity URL has been changed!",
                                color=0xf59e0b,
                                timestamp=datetime.utcnow()
                            )
                            embed.add_field(name="Old Code", value=f"`{saved_code}`", inline=True)
                            embed.add_field(name="New Code", value=f"`{current_code}`", inline=True)
                            embed.set_footer(text="Vanity Protection System")
                            await channel.send(embed=embed)
                            
                            await db.execute(
                                "UPDATE vanity_protection SET vanity_code=? WHERE guild_id=?",
                                (current_code, guild.id)
                            )
                            await db.commit()

    @check_vanity.before_loop
    async def before_check_vanity(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(
        name="vanity",
        description="🔗 Protect your server's vanity URL",
        usage="!vanity <setup/remove/check>",
        help="Manage vanity URL protection. setup/remove/check"
    )
    @commands.has_permissions(administrator=True)
    async def vanity(self, ctx, action: str = None):
        if not action:
            embed = discord.Embed(
                title="🔗 Vanity Protection",
                description="Protect your server's vanity URL from unauthorized changes",
                color=0x6366f1,
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="📝 Commands",
                value="`!vanity setup` - Enable protection\n`!vanity remove` - Disable protection\n`!vanity check` - View status",
                inline=False
            )
            embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)
        
        if action.lower() == "setup":
            if not ctx.guild.vanity_invite:
                return await ctx.send(embed=create_error_embed(
                    "No Vanity URL",
                    "This server doesn't have a vanity URL!",
                    ctx.author
                ))
            
            vanity_code = ctx.guild.vanity_invite.code
            
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO vanity_protection (guild_id, vanity_code, protected_at) VALUES (?, ?, ?)",
                    (ctx.guild.id, vanity_code, datetime.utcnow().isoformat())
                )
                await db.commit()
            
            embed = discord.Embed(
                title="✅ Vanity Protection Enabled",
                description="Your vanity URL is now being protected!",
                color=0x10b981,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="🔗 Vanity Code", value=f"`{vanity_code}`", inline=True)
            embed.add_field(name="🔗 Vanity URL", value=f"discord.gg/{vanity_code}", inline=True)
            embed.add_field(name="🔄 Check Interval", value="Every 5 minutes", inline=True)
            embed.set_footer(text=f"Protected by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        
        elif action.lower() == "remove":
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("DELETE FROM vanity_protection WHERE guild_id=?", (ctx.guild.id,))
                await db.commit()
            
            embed = create_success_embed(
                "Vanity Protection Disabled",
                "Vanity URL protection has been removed.",
                ctx.author
            )
            await ctx.send(embed=embed)
        
        elif action.lower() == "check":
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT vanity_code, protected_at FROM vanity_protection WHERE guild_id=?",
                    (ctx.guild.id,)
                )
                row = await cursor.fetchone()
            
            if not row:
                return await ctx.send(embed=create_error_embed(
                    "Not Protected",
                    "Vanity protection is not enabled!",
                    ctx.author
                ))
            
            vanity_code, protected_at = row
            protected_time = datetime.fromisoformat(protected_at)
            
            embed = discord.Embed(
                title="🔗 Vanity Protection Status",
                description="Your vanity URL is being protected",
                color=0x10b981,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="🔗 Vanity Code", value=f"`{vanity_code}`", inline=True)
            embed.add_field(name="🔗 Vanity URL", value=f"discord.gg/{vanity_code}", inline=True)
            embed.add_field(name="📅 Protected Since", value=protected_time.strftime("%d/%m/%Y %H:%M"), inline=True)
            embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        
        else:
            await ctx.send(embed=create_error_embed(
                "Invalid Action",
                "Use `!vanity setup`, `!vanity remove`, or `!vanity check`",
                ctx.author
            ))

    @commands.hybrid_command(
        name="vanityinfo",
        description="ℹ️ View your server's vanity URL information",
        usage="!vanityinfo",
        help="Displays vanity URL information"
    )
    async def vanityinfo(self, ctx):
        if not ctx.guild.vanity_invite:
            return await ctx.send(embed=create_error_embed(
                "No Vanity URL",
                "This server doesn't have a vanity URL!",
                ctx.author
            ))
        
        vanity = ctx.guild.vanity_invite
        code = vanity.code
        uses = vanity.uses
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT protected_at FROM vanity_protection WHERE guild_id=?",
                (ctx.guild.id,)
            )
            row = await cursor.fetchone()
        
        protected = "✅ Yes" if row else "❌ No"
        
        embed = discord.Embed(
            title="🔗 Vanity URL Information",
            description=f"Information about {ctx.guild.name}'s vanity URL",
            color=0x6366f1,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="🔗 Vanity Code", value=f"`{code}`", inline=True)
        embed.add_field(name="🔗 Vanity URL", value=f"discord.gg/{code}", inline=True)
        embed.add_field(name="📊 Uses", value=f"{uses:,} uses", inline=True)
        embed.add_field(name="🛡️ Protected", value=protected, inline=True)
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vanity_protection (
                guild_id INTEGER PRIMARY KEY,
                vanity_code TEXT NOT NULL,
                protected_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    await bot.add_cog(VanityProtection(bot))
