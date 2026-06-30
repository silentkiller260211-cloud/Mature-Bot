import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        settings = db.fetch_one(
            "SELECT channel_id, star_count, emoji FROM starboard_settings WHERE guild_id = ?",
            (reaction.message.guild.id,)
        )
        if not settings:
            return
        channel_id = settings["channel_id"]
        star_count = settings["star_count"]
        emoji = settings["emoji"] or "⭐"

        if str(reaction.emoji) != emoji:
            return
        existing = db.fetch_one(
            "SELECT star_message_id FROM starboard_entries WHERE message_id = ?",
            (reaction.message.id,)
        )
        if existing and existing["star_message_id"]:
            return
        if reaction.count >= star_count:
            channel = reaction.message.guild.get_channel(channel_id)
            if not channel:
                return
            embed = discord.Embed(
                title="⭐ Starboard",
                color=discord.Color.gold()
            )
            embed.description = reaction.message.content or "No content"
            embed.add_field(name="Author", value=reaction.message.author.mention)
            embed.add_field(name="Channel", value=reaction.message.channel.mention)
            embed.add_field(name="Stars", value=str(reaction.count))
            embed.set_footer(text=f"ID: {reaction.message.id}")
            if reaction.message.attachments:
                embed.set_image(url=reaction.message.attachments[0].url)
            star_msg = await channel.send(embed=embed)
            db.execute_query(
                "INSERT OR REPLACE INTO starboard_entries (message_id, guild_id, star_message_id, star_count) VALUES (?, ?, ?, ?)",
                (reaction.message.id, reaction.message.guild.id, star_msg.id, reaction.count)
            )

    @app_commands.command(name="starboard_set", description="Configure starboard channel, count, and emoji")
    @app_commands.default_permissions(administrator=True)
    async def starboard_set(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        star_count: int,
        emoji: str = "⭐"
    ):
        if star_count < 1:
            embed = discord.Embed(title="❌ Invalid Star Count", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        db.execute_query(
            "INSERT OR REPLACE INTO starboard_settings (guild_id, channel_id, star_count, emoji) VALUES (?, ?, ?, ?)",
            (interaction.guild.id, channel.id, star_count, emoji)
        )
        embed = discord.Embed(
            title="✅ Starboard Configured",
            description=f"Channel: {channel.mention}\nStars: {star_count}\nEmoji: {emoji}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="star", description="Manually star a message")
    async def star(self, interaction: discord.Interaction, message_id: int):
        try:
            msg = await interaction.channel.fetch_message(message_id)
            # Simulate a reaction event
            await self.on_reaction_add(discord.Reaction(msg, "⭐", msg.author), interaction.user)
            embed = discord.Embed(title="⭐ Starred!", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.NotFound:
            embed = discord.Embed(title="❌ Message Not Found", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Starboard(bot))
