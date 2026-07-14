import discord
from datetime import datetime

async def send_owner_alert(guild, action_type, target, moderator, reason=None, duration=None):
    if not guild.owner: return False
    try:
        color_map = {'ban': 0xef4444, 'kick': 0xf97316, 'mute': 0x6366f1, 'warn': 0xf59e0b, 'unban': 0x10b981, 'bot_remove': 0xec4899}
        emoji_map = {'ban': '', 'kick': '👢', 'mute': '🔇', 'warn': '️', 'unban': '🔓', 'bot_remove': '🤖'}
        embed = discord.Embed(title=f"{emoji_map.get(action_type, '⚡')} Punishment Alert - {guild.name}", color=color_map.get(action_type, 0x6366f1), timestamp=datetime.utcnow())
        embed.add_field(name="🎯 Action", value=f"**{action_type.upper()}**", inline=True)
        embed.add_field(name="👤 Target", value=f"{target.mention if hasattr(target, 'mention') else target.name}\n`{target.id}`", inline=True)
        embed.add_field(name="👮 Moderator", value=f"{moderator.mention if hasattr(moderator, 'mention') else moderator.name}\n`{moderator.id}`", inline=True)
        if reason: embed.add_field(name=" Reason", value=str(reason)[:1024], inline=False)
        if duration: embed.add_field(name="⏱️ Duration", value=duration, inline=True)
        embed.add_field(name="📅 Time", value=f"<t:{int(datetime.utcnow().timestamp())}:R>", inline=True)
        embed.set_footer(text="🛡️ Mature Bot Antinuke System", icon_url=guild.icon.url if guild.icon else None)
        await guild.owner.send(embed=embed)
        return True
    except discord.Forbidden: return False
    except Exception as e:
        print(f"Error sending owner alert: {e}")
        return False
