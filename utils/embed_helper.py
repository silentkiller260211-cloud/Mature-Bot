import discord
from datetime import datetime

def create_success_embed(title, description, user=None, color=0x10b981):
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    if user:
        embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    else:
        embed.set_footer(text="Mature Bot")
    return embed

def create_error_embed(title, description, user=None):
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=0xef4444,
        timestamp=datetime.utcnow()
    )
    if user:
        embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed

def create_info_embed(title, description, user=None, color=0x6366f1):
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    if user:
        embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed

def create_warning_embed(title, description, user=None):
    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=description,
        color=0xf59e0b,
        timestamp=datetime.utcnow()
    )
    if user:
        embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed

def create_stats_embed(title, fields, user=None, color=0x8b5cf6):
    embed = discord.Embed(
        title=f"📊 {title}",
        color=color,
        timestamp=datetime.utcnow()
    )
    for field_name, field_value, inline in fields:
        embed.add_field(name=field_name, value=field_value, inline=inline)
    if user:
        embed.set_footer(text=f"Requested by {user.name}", icon_url=user.display_avatar.url)
    return embed

def create_action_embed(action, target, moderator, reason=None, color=0x6366f1):
    embed = discord.Embed(
        title=f"🔨 {action}",
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Target", value=target.mention, inline=True)
    embed.add_field(name="Moderator", value=moderator.mention, inline=True)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(
        text=f"Action by {moderator.name}",
        icon_url=moderator.display_avatar.url
    )
    return embed
