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

    @app_commands.command(name="ticket", description="Create a ticket")
    async def ticket_open(self, interaction: discord.Interaction, reason: str = "No reason"):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role in interaction.guild.roles:
            if role.name.lower() in ["staff", "mod", "moderator", "admin"]:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await interaction.guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            overwrites=overwrites,
            topic=f"Ticket by {interaction.user} – {reason}"
        )
        db.execute_query("INSERT INTO tickets (guild_id, channel_id, author_id, status) VALUES (?, ?, ?, ?)",
                         (interaction.guild.id, channel.id, interaction.user.id, "open"))
        embed = discord.Embed(title="🎟️ Ticket Created", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await channel.send(f"{interaction.user.mention} – Staff will assist you.")

    @app_commands.command(name="ticket_close", description="Close the ticket")
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
            await interaction.response.send_message("❌ You cannot close this.", ephemeral=True)
            return
        db.execute_query("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (channel.id,))
        await interaction.response.send_message("🔒 Closing...")
        await channel.delete(delay=5)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
