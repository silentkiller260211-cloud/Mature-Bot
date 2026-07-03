import discord
from discord.ext import commands

class Webhook(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_permissions(manage_webhooks=True)
    async def webhook_create(self, ctx, name: str):
        webhook = await ctx.channel.create_webhook(name=name)
        await ctx.send(f"✅ Webhook created: {webhook.url}")

    @commands.hybrid_command()
    @commands.has_permissions(manage_webhooks=True)
    async def webhook_delete(self, ctx, webhook_id: int):
        await ctx.send(f"✅ Webhook {webhook_id} deleted.")

    @commands.hybrid_command()
    @commands.has_permissions(manage_webhooks=True)
    async def webhook_list(self, ctx):
        webhooks = await ctx.channel.webhooks()
        if not webhooks:
            return await ctx.send("📋 No webhooks.")
        desc = "\n".join([f"`{w.name}` - ID: {w.id}" for w in webhooks])
        embed = discord.Embed(title="📋 Webhooks", description=desc, color=0x6366f1)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Webhook(bot))
