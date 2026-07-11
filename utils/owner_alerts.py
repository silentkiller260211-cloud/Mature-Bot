import discord
from datetime import datetime

async def send_owner_alert(guild, action_type, target, moderator, reason=None, duration=None):
    """Send DM alert to server owner when punishment is given"""
    if not guild.owner:
        return False
    
    try:
        color_map = {
            'ban': 0xef4444,
            'kick': 0xf97316,
            'mute': 0x6366f1,
            'warn': 0xf59e0b,
            'unban': 0x10b981,
            'bot_remove': 0xec4899,
            'role_permission': 0x8b5cf6
        }
        
        emoji_map = {
            'ban': '🔨',
            'kick': '👢',
            'mute': '🔇',
            'warn': '⚠️',
            'unban': '🔓',
            'bot_remove': '🤖',
            'role_permission': '🔐'
        }
        
        color = color_map.get(action_type, 0x6366f1)
        emoji = emoji_map.get(action_type, '⚡')
        
        embed = discord.Embed(
            title=f"{emoji} Punishment Alert - {guild.name}",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="🎯 Action Taken",
            value=f"**{action_type.upper()}**",
            inline=True
        )
        
        target_value = f"{target.mention if hasattr(target, 'mention') else target.name}\n`{target.id}`"
        embed.add_field(name="👤 Target", value=target_value, inline=True)
        
        mod_value = f"{moderator.mention if hasattr(moderator, 'mention') else moderator.name}\n`{moderator.id}`"
        embed.add_field(name="👮 Moderator", value=mod_value, inline=True)
        
        if reason:
            embed.add_field(name="📝 Reason", value=str(reason)[:1024], inline=False)
        
        if duration:
            embed.add_field(name="⏱️ Duration", value=duration, inline=True)
        
        embed.add_field(
            name="📅 Time",
            value=f"<t:{int(datetime.utcnow().timestamp())}:R>",
            inline=True
        )
        
        embed.set_footer(
            text="🛡️ Mature Bot Antinuke System",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        await guild.owner.send(embed=embed)
        return True
        
    except discord.Forbidden:
        print(f"Could not DM owner of {guild.name} - DMs disabled")
        return False
    except Exception as e:
        print(f"Error sending owner alert: {e}")
        return False


async def send_owner_alert_manual(guild, action_type, target, moderator, reason=None, duration=None):
    """Send DM alert for manual commands (ban, kick, mute, warn)"""
    return await send_owner_alert(guild, action_type, target, moderator, reason, duration)
