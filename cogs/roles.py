import discord
from discord.ext import commands
from discord import app_commands
from utils.security import is_owner

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def can_target(self, author, target):
        if is_owner(target.id):
            return author.id == target.id
        return True

    @app_commands.command(name="addrole", description="Add a role to a member")
    @app_commands.default_permissions(manage_roles=True)
    async def addrole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if not self.can_target(interaction.user, member):
            embed = discord.Embed(title="❌ Cannot Manage", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            embed = discord.Embed(title="❌ Role Too High", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await member.add_roles(role, reason=f"Added by {interaction.user}")
        embed = discord.Embed(title="✅ Role Added", description=f"{role.mention} added to {member.mention}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="removerole", description="Remove a role from a member")
    @app_commands.default_permissions(manage_roles=True)
    async def removerole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        if not self.can_target(interaction.user, member):
            embed = discord.Embed(title="❌ Cannot Manage", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            embed = discord.Embed(title="❌ Role Too High", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await member.remove_roles(role, reason=f"Removed by {interaction.user}")
        embed = discord.Embed(title="✅ Role Removed", description=f"{role.mention} removed from {member.mention}.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Roles(bot))
