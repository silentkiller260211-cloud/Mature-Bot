import discord
from datetime import datetime

def create_success_embed(title, description, user=None, color=0x10b981):
    embed = discord.Embed(title=f"✅ {title}", description=description, color=color, timestamp=datetime.utcnow())
    if user: embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed

def create_error_embed(title, description, user=None):
    embed = discord.Embed(title=f"❌ {title}", description=description, color=0xef4444, timestamp=datetime.utcnow())
    if user: embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed

def create_info_embed(title, description, user=None, color=0x6366f1):
    embed = discord.Embed(title=f"ℹ️ {title}", description=description, color=color, timestamp=datetime.utcnow())
    if user: embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed
