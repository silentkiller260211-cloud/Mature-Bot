import discord
from discord.ext import commands
from discord import app_commands

class Webhook(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="webhook_create", description="Create a webhook")
    @app_commands.default_permissions(manage_webhooks=True)
    async def webhook_create(self, interaction: discord.Interaction, name: str):
        channel = interaction.channel
        webhook = await channel.create_webhook(name=name)
        embed = discord.Embed(title="✅ Webhook Created", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="webhook_delete", description="Delete a webhook")
    @app_commands.default_permissions(manage_webhooks=True)
    async def webhook_delete(self, interaction: discord.Interaction, webhook_id: str):
        try:
            webhook = await self.bot.fetch_webhook(int(webhook_id))
            await webhook.delete()
            embed = discord.Embed(title="✅ Webhook Deleted", color=discord.Color.green())
        except:
            embed = discord.Embed(title="❌ Error", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="webhook_list", description="List webhooks")
    @app_commands.default_permissions(manage_webhooks=True)
    async def webhook_list(self, interaction: discord.Interaction):
        webhooks = await interaction.guild.webhooks()
        if not webhooks:
            embed = discord.Embed(title="ℹ️ No Webhooks", color=discord.Color.blue())
        else:
            embed = discord.Embed(title="🔗 Webhooks", color=discord.Color.blue())
            for wh in webhooks:
                embed.add_field(name=wh.name, value=f"ID: {wh.id}", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Webhook(bot))
