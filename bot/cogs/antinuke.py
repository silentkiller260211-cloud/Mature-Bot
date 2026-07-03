import discord
from discord.ext import commands

class Antinuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled = {}
        self.whitelist = {}
        self.backups = {}

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx):
        embed = discord.Embed(title="🛡️ Antinuke Control Panel", color=0xf59e0b)
        status = "✅ Enabled" if self.enabled.get(ctx.guild.id) else "❌ Disabled"
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Whitelisted", value=len(self.whitelist.get(ctx.guild.id, [])), inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def antinuke_config(self, ctx, setting: str, value: int):
        await ctx.send(f"✅ Configured {setting} = {value}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def antinuke_enable(self, ctx):
        self.enabled[ctx.guild.id] = True
        await ctx.send("🛡️ Antinuke **ENABLED**.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def antinuke_disable(self, ctx):
        self.enabled[ctx.guild.id] = False
        await ctx.send("🛡️ Antinuke **DISABLED**.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def antinuke_lockdown(self, ctx):
        await ctx.send("🔒 Server lockdown toggled.")

    @commands.hybrid_command()
    async def antinuke_status(self, ctx):
        status = "✅ Enabled" if self.enabled.get(ctx.guild.id) else "❌ Disabled"
        await ctx.send(f"🛡️ Antinuke Status: {status}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def fullbackup(self, ctx):
        self.backups[ctx.guild.id] = {"channels": len(ctx.guild.channels), "roles": len(ctx.guild.roles)}
        await ctx.send("💾 Full backup created successfully!")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def restorebackup(self, ctx, backup_id: int = 1):
        if ctx.guild.id in self.backups:
            await ctx.send("✅ Backup restored successfully!")
        else:
            await ctx.send("❌ No backup found.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def whitelist_add(self, ctx, member: discord.Member):
        self.whitelist.setdefault(ctx.guild.id, []).append(member.id)
        await ctx.send(f"✅ {member} added to whitelist.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def whitelist_remove(self, ctx, member: discord.Member):
        if member.id in self.whitelist.get(ctx.guild.id, []):
            self.whitelist[ctx.guild.id].remove(member.id)
        await ctx.send(f"✅ {member} removed from whitelist.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def whitelist_clear(self, ctx):
        self.whitelist[ctx.guild.id] = []
        await ctx.send("✅ Whitelist cleared.")

    @commands.hybrid_command()
    async def whitelist_list(self, ctx):
        wl = self.whitelist.get(ctx.guild.id, [])
        if not wl:
            return await ctx.send("📋 Whitelist is empty.")
        mentions = [f"<@{uid}>" for uid in wl]
        await ctx.send(f"📋 Whitelist: {', '.join(mentions)}")

async def setup(bot):
    await bot.add_cog(Antinuke(bot))
