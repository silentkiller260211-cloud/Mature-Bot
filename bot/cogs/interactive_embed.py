import discord
from discord.ext import commands
from discord import ui
from datetime import datetime
import re

class InteractiveEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="colourembed",
        description="🎨 Create an embed with custom hex color",
        usage="!colourembed Embed Title: [Title] Embed Description: [Desc] Embed Colour: #aaaaaa",
        help="Create embed with title, description, and hex color"
    )
    @commands.has_permissions(manage_messages=True)
    async def colourembed(self, ctx, *, content: str):
        title = "Embed"
        description = ""
        color = 0x6366f1
        
        title_match = re.search(r'Embed Title:\s*\[([^\]]+)\]', content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        
        desc_match = re.search(r'Embed Description:\s*\[([^\]]+)\]', content, re.IGNORECASE)
        if desc_match:
            description = desc_match.group(1).strip()
        
        color_match = re.search(r'Embed Colou?r:\s*(#[0-9a-fA-F]{6})', content, re.IGNORECASE)
        if color_match:
            try:
                color = int(color_match.group(1).lstrip('#'), 16)
            except:
                color = 0x6366f1
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Created by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="embed",
        description="🎨 Create a basic embed",
        usage="!embed <title> | <description>",
        help="Create a simple embed"
    )
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx, *, content: str):
        if '|' in content:
            parts = content.split('|', 1)
            title = parts[0].strip()
            description = parts[1].strip() if len(parts) > 1 else ""
        else:
            title = content
            description = ""
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x6366f1,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Created by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InteractiveEmbed(bot))
