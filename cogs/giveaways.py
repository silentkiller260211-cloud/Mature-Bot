import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db
from datetime import datetime, timedelta
import random

class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="giveaway", description="Create a giveaway")
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway(self, interaction: discord.Interaction, duration: str, winners: int, prize: str):
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            seconds = int(duration[:-1]) * units[duration[-1]]
        except:
            embed = discord.Embed(title="❌ Invalid Duration", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        end_time = datetime.now() + timedelta(seconds=seconds)
        embed = discord.Embed(title="🎉 Giveaway!", description=f"Prize: **{prize}**\nWinners: {winners}\nEnds: <t:{int(end_time.timestamp())}:R>")
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("🎉")
        db.execute_query(
            "INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winners, end_time, hosted_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (interaction.guild.id, interaction.channel.id, msg.id, prize, winners, end_time, interaction.user.id)
        )
        embed = discord.Embed(title="✅ Giveaway Started", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="endgiveaway", description="End a giveaway manually")
    @app_commands.default_permissions(manage_guild=True)
    async def endgiveaway(self, interaction: discord.Interaction, message_id: int):
        giveaway = db.fetch_one("SELECT * FROM giveaways WHERE message_id = ? AND guild_id = ? AND ended = 0", (message_id, interaction.guild.id))
        if not giveaway:
            embed = discord.Embed(title="❌ Not Found", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        db.execute_query("UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway["id"],))
        embed = discord.Embed(title="✅ Giveaway Ended", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reroll", description="Reroll a giveaway")
    @app_commands.default_permissions(manage_guild=True)
    async def reroll(self, interaction: discord.Interaction, message_id: int):
        giveaway = db.fetch_one("SELECT * FROM giveaways WHERE message_id = ? AND guild_id = ? AND ended = 1", (message_id, interaction.guild.id))
        if not giveaway:
            embed = discord.Embed(title="❌ Not Found", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        channel = interaction.guild.get_channel(giveaway["channel_id"])
        if not channel:
            embed = discord.Embed(title="❌ Channel Not Found", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        try:
            msg = await channel.fetch_message(message_id)
        except:
            embed = discord.Embed(title="❌ Message Not Found", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = []
        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
        if not users:
            embed = discord.Embed(title="❌ No Participants", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        winners = random.sample(users, min(giveaway["winners"], len(users)))
        winner_mentions = ", ".join([u.mention for u in winners])
        embed = discord.Embed(title="🎉 Rerolled!", description=f"New winner(s): {winner_mentions}", color=discord.Color.gold())
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Rerolled!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
