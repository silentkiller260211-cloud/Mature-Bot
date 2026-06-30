import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_staff(self, member):
        if member.guild.owner_id == member.id:
            return True
        if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
            return True
        for role in member.roles:
            if role.name.lower() in ["staff", "mod", "moderator", "admin"]:
                return True
        return False

    def get_ticket_author(self, channel_id):
        record = db.fetch_one("SELECT author_id FROM tickets WHERE channel_id = ? AND status = 'open'", (channel_id,))
        return record["author_id"] if record else None

    @app_commands.command(name="ticket", description="Create a support ticket")
    async def ticket_open(self, interaction: discord.Interaction, reason: str = "No reason"):
        # ... (same as before)
        pass

    @app_commands.command(name="ticket_close", description="Close the current ticket channel")
    async def ticket_close(self, interaction: discord.Interaction):
        channel = interaction.channel

        if not channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ Not a ticket.", ephemeral=True)
            return

        author_id = self.get_ticket_author(channel.id)
        if not author_id:
            await interaction.response.send_message("❌ Already closed.", ephemeral=True)
            return

        user_id = interaction.user.id
        if not (user_id == author_id or self.is_staff(interaction.user) or user_id == interaction.guild.owner_id):
            await interaction.response.send_message("❌ No permission.", ephemeral=True)
            return

        # ✅ CHECK BOT PERMISSION FIRST
        if not channel.permissions_for(interaction.guild.me).manage_channels:
            await interaction.response.send_message(
                "❌ I don't have `Manage Channels` permission. Please give me that permission and try again.",
                ephemeral=True
            )
            return

        db.execute_query("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (channel.id,))
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")

        try:
            await channel.delete(delay=5)
        except discord.Forbidden:
            await interaction.followup.send("❌ I still lack permission to delete the channel.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
