import discord
from discord.ext import commands
from datetime import datetime

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="premium",
        description="💎 Premium system - Currently under maintenance",
        usage="/premium",
        help="Premium system is temporarily unavailable"
    )
    async def premium(self, ctx, code: str = None):
        embed = discord.Embed(
            title="⚙️ Premium System - Under Maintenance",
            description="We're working on improving our payment system. Premium features will be available soon!",
            color=0xf59e0b,
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="📝 Status",
            value="Premium system is temporarily disabled for improvements.",
            inline=False
        )
        embed.add_field(
            name="💬 Support",
            value="For inquiries, join our support server:\nhttps://discord.gg/YxeeaEg9V6",
            inline=False
        )
        embed.set_footer(text="Mature Bot Team", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Premium(bot))
