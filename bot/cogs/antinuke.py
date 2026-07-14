import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime

DB_PATH = "mature_bot.db"

async def is_whitelisted(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM antinuke_whitelist WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        return await cursor.fetchone() is not None

async def check_antinuke(guild_id, program):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT enabled FROM antinuke_settings WHERE guild_id=? AND program=?", (guild_id, program))
        row = await cursor.fetchone()
        return bool(row[0]) if row else False

async def punish_user(guild, user, reason):
    try:
        if guild.me.guild_permissions.ban_members:
            await guild.ban(user, reason=f"Antinuke: {reason}")
            from utils.owner_alerts import send_owner_alert
            await send_owner_alert(guild=guild, action_type='ban', target=user, moderator=user, reason=f"Antinuke Violation: {reason}")
    except Exception as e: print(f"Failed to punish: {e}")

class Antinuke(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="whitelist_add", description="🛡️ Add user to Antinuke Whitelist")
    @commands.has_permissions(administrator=True)
    async def whitelist_add(self, ctx, member: discord.Member = None):
        if not member: return await ctx.send(embed=discord.Embed(title="Error", description="Mention a user!", color=0xef4444))
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT 1 FROM antinuke_whitelist WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
            if await cursor.fetchone(): return await ctx.send(embed=discord.Embed(title="Already Whitelisted", description=f"{member.mention} is already safe.", color=0x3b82f6))
            await db.execute("INSERT INTO antinuke_whitelist (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(embed=discord.Embed(title="🛡️ User Whitelisted", description=f"**{member.mention}** is now safe from Antinuke punishments.", color=0x10b981))

    @commands.hybrid_command(name="whitelist_remove", description="️ Remove user from Antinuke Whitelist")
    @commands.has_permissions(administrator=True)
    async def whitelist_remove(self, ctx, member: discord.Member = None):
        if not member: return await ctx.send(embed=discord.Embed(title="Error", description="Mention a user!", color=0xef4444))
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM antinuke_whitelist WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(embed=discord.Embed(title="🛡️ Removed from Whitelist", description=f"**{member.mention}** will now be punished by Antinuke.", color=0xef4444))

    @commands.hybrid_command(name="whitelist_list", description="🛡️ View Antinuke Whitelisted Users")
    @commands.has_permissions(administrator=True)
    async def whitelist_list(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT user_id FROM antinuke_whitelist WHERE guild_id=?", (ctx.guild.id,))
            rows = await cursor.fetchall()
        if not rows: return await ctx.send(embed=discord.Embed(title="🛡️ Whitelist Empty", description="No users are currently whitelisted.", color=0x6366f1))
        embed = discord.Embed(title="️ Antinuke Whitelist", description=f"Total **{len(rows)}** users can bypass protection.", color=0x6366f1, timestamp=datetime.utcnow())
        for (user_id,) in rows:
            member = ctx.guild.get_member(user_id)
            display_name = member.display_name if member else f"👻 Left Server ({user_id})"
            field_value = f"**User:** @{member.name}\n**ID:** `{user_id}`" if member else "User is no longer in this server."
            embed.add_field(name=display_name, value=field_value, inline=True)
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    # --- EVENT LISTENERS ---
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if not await check_antinuke(guild.id, "anti_ban"): return
        executor = None
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == user.id: executor = entry.user; break
        if executor and executor != self.bot.user and not await is_whitelisted(guild.id, executor.id):
            try: await guild.unban(user); await punish_user(guild, executor, "Unauthorized Ban")
            except: pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if not await check_antinuke(guild.id, "anti_unban"): return
        executor = None
        async for entry in guild.audit_logs(action=discord.AuditLogAction.unban, limit=1):
            if entry.target.id == user.id: executor = entry.user; break
        if executor and executor != self.bot.user and not await is_whitelisted(guild.id, executor.id):
            try: await guild.ban(user, reason="Antinuke: Re-banning"); await punish_user(guild, executor, "Unauthorized Unban")
            except: pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot and await check_antinuke(member.guild.id, "anti_bot_remove"):
            executor = None
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
                if entry.target.id == member.id: executor = entry.user; break
            if executor and executor != self.bot.user and not await is_whitelisted(member.guild.id, executor.id): await punish_user(member.guild, executor, "Unauthorized Bot Removal")
        elif not member.bot and await check_antinuke(member.guild.id, "anti_prune"):
            executor = None
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
                if entry.target.id == member.id: executor = entry.user; break
            if executor and executor != self.bot.user and not await is_whitelisted(member.guild.id, executor.id): await punish_user(member.guild, executor, "Unauthorized Prune/Kick")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not await check_antinuke(channel.guild.id, "anti_channel_delete"): return
        executor = None
        async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1): executor = entry.user; break
        if executor and executor != self.bot.user and not await is_whitelisted(channel.guild.id, executor.id): await punish_user(channel.guild, executor, "Unauthorized Channel Deletion")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if not await check_antinuke(channel.guild.id, "anti_channel_create"): return
        executor = None
        async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=1):
            if entry.target == channel: executor = entry.user; break
        if executor and executor != self.bot.user and not await is_whitelisted(channel.guild.id, executor.id): await channel.delete(); await punish_user(channel.guild, executor, "Unauthorized Channel Creation")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        if not await check_antinuke(role.guild.id, "anti_role_create"): return
        executor = None
        async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=1):
            if entry.target == role: executor = entry.user; break
        if executor and executor != self.bot.user and not await is_whitelisted(role.guild.id, executor.id): await role.delete(); await punish_user(role.guild, executor, "Unauthorized Role Creation")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, guild, role):
        if not await check_antinuke(guild.id, "anti_role_delete"): return
        executor = None
        async for entry in guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1): executor = entry.user; break
        if executor and executor != self.bot.user and not await is_whitelisted(guild.id, executor.id):
            try: await guild.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, mentionable=role.mentionable, reason="Antinuke: Recreate")
            except: pass
            await punish_user(guild, executor, "Unauthorized Role Deletion")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        guild = after.guild
        executor = None
        async for entry in guild.audit_logs(action=discord.AuditLogAction.role_update, limit=1):
            if entry.target.id == after.id: executor = entry.user; break
        if not executor or executor == self.bot.user or await is_whitelisted(guild.id, executor.id): return
        if await check_antinuke(guild.id, "anti_role_update") and (before.name != after.name or before.color != after.color):
            try: await after.edit(name=before.name, color=before.color, reason="Antinuke: Revert")
            except: pass
            await punish_user(guild, executor, "Unauthorized Role Update")
        if await check_antinuke(guild.id, "anti_role_permission") and before.permissions != after.permissions:
            try: await after.edit(permissions=before.permissions, reason="Antinuke: Revert Perms")
            except: pass
            await punish_user(guild, executor, "Unauthorized Permission Change")

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        if await check_antinuke(guild.id, "anti_emoji_create"):
            added = set(after) - set(before)
            if added:
                executor = None
                async for entry in guild.audit_logs(action=discord.AuditLogAction.emoji_create, limit=1): executor = entry.user; break
                if executor and executor != self.bot.user and not await is_whitelisted(guild.id, executor.id):
                    for emoji in added: await emoji.delete()
                    await punish_user(guild, executor, "Unauthorized Emoji Creation")
        if await check_antinuke(guild.id, "anti_emoji_delete"):
            deleted = set(before) - set(after)
            if deleted:
                executor = None
                async for entry in guild.audit_logs(action=discord.AuditLogAction.emoji_delete, limit=1): executor = entry.user; break
                if executor and executor != self.bot.user and not await is_whitelisted(guild.id, executor.id): await punish_user(guild, executor, "Unauthorized Emoji Deletion")

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if not await check_antinuke(after.id, "anti_server_update"): return
        executor = None
        async for entry in after.audit_logs(action=discord.AuditLogAction.guild_update, limit=1): executor = entry.user; break
        if executor and executor != self.bot.user and not await is_whitelisted(after.id, executor.id):
            try:
                if before.name != after.name: await after.edit(name=before.name, reason="Antinuke: Revert Name")
                if before.icon != after.icon: await after.edit(icon=before.icon, reason="Antinuke: Revert Icon")
                await punish_user(after, executor, "Unauthorized Server Update")
            except: pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot and await check_antinuke(member.guild.id, "anti_bot_add"):
            executor = None
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1): executor = entry.user; break
            if executor and executor != self.bot.user and not await is_whitelisted(member.guild.id, executor.id):
                await member.kick(reason="Antinuke: Unauthorized Bot Add"); await punish_user(member.guild, executor, "Unauthorized Bot Add")

async def setup(bot): await bot.add_cog(Antinuke(bot))
