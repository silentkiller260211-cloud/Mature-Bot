import discord
from discord.ext import commands
from discord import app_commands

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="quicksetup", description="⚡ Auto-setup your server in 5 seconds!")
    @commands.has_permissions(manage_guild=True)
    async def quicksetup(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        embed = discord.Embed(title="⚡ Mature Bot Quick Setup", color=0x10b981)
        
        category = discord.utils.get(guild.categories, name="Mature Bot")
        if not category:
            category = await guild.create_category("Mature Bot")
            embed.add_field(name="📁 Category Created", value="`Mature Bot`", inline=False)

        channels_to_create = [("welcome", "👋"), ("logs", ""), ("bot-commands", "🤖")]
        created_channels = []
        for name, emoji in channels_to_create:
            if not discord.utils.get(guild.text_channels, name=name):
                await guild.create_text_channel(name, category=category)
                created_channels.append(f"{emoji} `#{name}`")
        if created_channels: embed.add_field(name="💬 Channels Created", value="\n".join(created_channels), inline=False)

        roles_to_create = [("Mature Member", 0x10b981), ("Mature Mod", 0xf59e0b)]
        created_roles = []
        for name, color in roles_to_create:
            if not discord.utils.get(guild.roles, name=name):
                await guild.create_role(name=name, color=color)
                created_roles.append(f"🛡️ `{name}`")
        if created_roles: embed.add_field(name="🛡️ Roles Created", value="\n".join(created_roles), inline=False)

        embed.add_field(name="⚙️ Bot Configured", value="✅ Welcome, Logging & Antinuke enabled.", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SetupCog(bot))
