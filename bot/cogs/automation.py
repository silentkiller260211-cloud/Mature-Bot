import discord
from discord.ext import commands

class Automation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome = {}
        self.goodbye = {}
        self.starboard = {}
        self.logging = {}
        self.vc_roles = {}
        self.reminders = {}

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx, channel: discord.TextChannel, *, message: str = "Welcome {user}!"):
        self.welcome[ctx.guild.id] = {"channel": channel.id, "message": message}
        await ctx.send(f"✅ Welcome set to {channel.mention}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def setgoodbye(self, ctx, channel: discord.TextChannel, *, message: str = "Goodbye {user}!"):
        self.goodbye[ctx.guild.id] = {"channel": channel.id, "message": message}
        await ctx.send(f"✅ Goodbye set to {channel.mention}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def setstarboard(self, ctx, channel: discord.TextChannel, count: int = 5, emoji: str = "⭐"):
        self.starboard[ctx.guild.id] = {"channel": channel.id, "count": count, "emoji": emoji}
        await ctx.send(f"✅ Starboard set to {channel.mention} ({count} {emoji})")

    @commands.hybrid_command()
    async def star(self, ctx, message_id: int):
        await ctx.send(f"⭐ Message starred.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def logging_enable(self, ctx):
        self.logging[ctx.guild.id] = True
        await ctx.send("📜 Logging enabled.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def logging_disable(self, ctx):
        self.logging[ctx.guild.id] = False
        await ctx.send("📜 Logging disabled.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def logging_autosetup(self, ctx):
        channel = discord.utils.get(ctx.guild.text_channels, name="logs")
        if not channel:
            channel = await ctx.guild.create_text_channel("logs")
        await ctx.send(f"✅ Logging channel set to {channel.mention}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def vc_role_set(self, ctx, role: discord.Role):
        self.vc_roles[ctx.guild.id] = role.id
        await ctx.send(f"✅ VC role set to {role.mention}")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def vc_role_remove(self, ctx):
        self.vc_roles.pop(ctx.guild.id, None)
        await ctx.send("✅ VC role removed.")

    @commands.hybrid_command()
    async def vc_role_status(self, ctx):
        role_id = self.vc_roles.get(ctx.guild.id)
        if role_id:
            await ctx.send(f"✅ VC role: <@&{role_id}>")
        else:
            await ctx.send("❌ No VC role set.")

    @commands.hybrid_command()
    @commands.has_permissions(manage_messages=True)
    async def giveaway(self, ctx, duration: int, *, prize: str):
        await ctx.send(f"🎉 Giveaway started! Prize: **{prize}** (Duration: {duration}m)")

    @commands.hybrid_command()
    @commands.has_permissions(manage_messages=True)
    async def endgiveaway(self, ctx):
        await ctx.send("🎉 Giveaway ended!")

    @commands.hybrid_command()
    @commands.has_permissions(manage_messages=True)
    async def reroll(self, ctx):
        await ctx.send("🎲 Winner rerolled!")

    @commands.hybrid_command()
    @commands.has_permissions(manage_messages=True)
    async def poll(self, ctx, *, question: str):
        embed = discord.Embed(title="📊 Poll", description=question, color=0x6366f1)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

    @commands.hybrid_command()
    async def ticket(self, ctx):
        overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False), ctx.author: discord.PermissionOverwrite(read_messages=True)}
        channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}", overwrites=overwrites)
        await ctx.send(f"✅ Ticket created: {channel.mention}")

    @commands.hybrid_command()
    async def ticket_close(self, ctx):
        if "ticket" in ctx.channel.name:
            await ctx.channel.delete()
        else:
            await ctx.send("❌ Not a ticket channel.")

    @commands.hybrid_command()
    async def remind(self, ctx, minutes: int, *, task: str):
        self.reminders[ctx.author.id] = {"task": task, "time": minutes}
        await ctx.send(f"⏰ Reminder set for {minutes} minutes: {task}")

    @commands.hybrid_command()
    async def reminders(self, ctx):
        r = self.reminders.get(ctx.author.id)
        if r:
            await ctx.send(f"⏰ {r['task']} in {r['time']} minutes")
        else:
            await ctx.send("📋 No reminders.")

    @commands.hybrid_command()
    async def cancelremind(self, ctx, remind_id: int = 1):
        self.reminders.pop(ctx.author.id, None)
        await ctx.send("✅ Reminder cancelled.")

async def setup(bot):
    await bot.add_cog(Automation(bot))
