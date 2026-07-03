import discord
from discord.ext import commands
from discord import app_commands, ui
import aiosqlite

DB_PATH = "mature_bot.db"

class AntinukeView(ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    async def get_status(self, program):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT enabled FROM antinuke_settings WHERE guild_id=? AND program=?", 
                (self.guild_id, program)
            )
            row = await cursor.fetchone()
            return row[0] if row else False

    async def toggle_program(self, program, interaction):
        async with aiosqlite.connect(DB_PATH) as db:
            current = await self.get_status(program)
            await db.execute(
                "INSERT OR REPLACE INTO antinuke_settings (guild_id, program, enabled) VALUES (?, ?, ?)",
                (self.guild_id, program, not current)
            )
            await db.commit()
        
        status = await self.get_status(program)
        emoji = "✅" if status else "❌"
        await interaction.response.edit_message(
            content=f"{emoji} **{program.replace('_', ' ').title()}** is now {'**ENABLED**' if status else '**DISABLED**'}",
            view=self
        )

    @ui.button(label="Anti-Ban", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def anti_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_program("anti_ban", interaction)

    @ui.button(label="Anti-Kick", style=discord.ButtonStyle.secondary, emoji="👢")
    async def anti_kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_program("anti_kick", interaction)

    @ui.button(label="Anti-Channel Delete", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def anti_channel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_program("anti_channel_delete", interaction)

    @ui.button(label="Anti-Role Create", style=discord.ButtonStyle.secondary, emoji="🎭")
    async def anti_role_create(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_program("anti_role_create", interaction)

    @ui.button(label="Anti-Bot Add", style=discord.ButtonStyle.secondary, emoji="🤖")
    async def anti_bot_add(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_program("anti_bot_add", interaction)


class WhitelistView(ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    async def get_whitelist(self):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT user_id FROM no_prefix_users WHERE guild_id=?", 
                (self.guild_id,)
            )
            return await cursor.fetchall()

    @ui.button(label="View Whitelist", style=discord.ButtonStyle.primary, emoji="👥")
    async def view_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        whitelist = await self.get_whitelist()
        if not whitelist:
            return await interaction.response.send_message("📋 Whitelist is empty.", ephemeral=True)
        
        embed = discord.Embed(title="🛡️ Whitelisted Users", color=0x10b981, description="Users who can use commands without prefix")
        for i, (user_id,) in enumerate(whitelist, 1):
            user = self.bot.get_user(user_id)
            name = user.name if user else f"Unknown ({user_id})"
            embed.add_field(name=f"{i}. {name}", value=f"ID: `{user_id}`", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Antinuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description="🛡️ Open the Antinuke control panel to manage protection settings")
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx):
        """🛡️ Open the Antinuke control panel to manage protection settings and view whitelisted users"""
        programs = ["anti_ban", "anti_kick", "anti_channel_delete", "anti_role_create", "anti_bot_add"]
        status_text = "🛡️ **Antinuke Control Panel**\n\n"
        
        async with aiosqlite.connect(DB_PATH) as db:
            for program in programs:
                cursor = await db.execute(
                    "SELECT enabled FROM antinuke_settings WHERE guild_id=? AND program=?",
                    (ctx.guild.id, program)
                )
                row = await cursor.fetchone()
                enabled = row[0] if row else False
                emoji = "✅" if enabled else "❌"
                status_text += f"{emoji} **{program.replace('_', ' ').title()}**: {'Enabled' if enabled else 'Disabled'}\n"
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM no_prefix_users WHERE guild_id=?",
                (ctx.guild.id,)
            )
            count = (await cursor.fetchone())[0]
        
        status_text += f"\n **Whitelisted Users**: {count}/10"
        
        embed = discord.Embed(title="️ Antinuke System", description=status_text, color=0xf59e0b)
        embed.set_footer(text="Use buttons below to manage settings")
        
        view = ui.View()
        view.add_item(AntinukeView(self.bot, ctx.guild.id))
        view.add_item(WhitelistView(self.bot, ctx.guild.id))
        
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(description="🛡️ Enable all antinuke protection programs at once")
    @commands.has_permissions(administrator=True)
    async def antinuke_enable(self, ctx):
        """🛡️ Enable all antinuke protection programs at once"""
        programs = ["anti_ban", "anti_kick", "anti_channel_delete", "anti_role_create", "anti_bot_add"]
        async with aiosqlite.connect(DB_PATH) as db:
            for program in programs:
                await db.execute(
                    "INSERT OR REPLACE INTO antinuke_settings (guild_id, program, enabled) VALUES (?, ?, 1)",
                    (ctx.guild.id, program)
                )
            await db.commit()
        await ctx.send("🛡️ All antinuke programs **ENABLED**.")

    @commands.hybrid_command(description="️ Disable all antinuke protection programs at once")
    @commands.has_permissions(administrator=True)
    async def antinuke_disable(self, ctx):
        """🛡️ Disable all antinuke protection programs at once"""
        programs = ["anti_ban", "anti_kick", "anti_channel_delete", "anti_role_create", "anti_bot_add"]
        async with aiosqlite.connect(DB_PATH) as db:
            for program in programs:
                await db.execute(
                    "INSERT OR REPLACE INTO antinuke_settings (guild_id, program, enabled) VALUES (?, ?, 0)",
                    (ctx.guild.id, program)
                )
            await db.commit()
        await ctx.send("🛡️ All antinuke programs **DISABLED**.")

    @commands.hybrid_command(description="👥 Add a user to the whitelist (max 10 users)")
    @commands.has_permissions(administrator=True)
    async def whitelist_add(self, ctx, member: discord.Member):
        """ Add a user to the whitelist (max 10 users)"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM no_prefix_users WHERE guild_id=?",
                (ctx.guild.id,)
            )
            count = (await cursor.fetchone())[0]
            if count >= 10:
                return await ctx.send("❌ Whitelist limit reached (10/10).")
            
            await db.execute(
                "INSERT OR IGNORE INTO no_prefix_users (guild_id, user_id) VALUES (?, ?)",
                (ctx.guild.id, member.id)
            )
            await db.commit()
        await ctx.send(f"✅ Added **{member.name}** to whitelist.")

    @commands.hybrid_command(description=" View all whitelisted users with their names")
    async def whitelist_list(self, ctx):
        """📋 View all whitelisted users with their names"""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT user_id FROM no_prefix_users WHERE guild_id=?",
                (ctx.guild.id,)
            )
            rows = await cursor.fetchall()
        
        if not rows:
            return await ctx.send(" Whitelist is empty.")
        
        embed = discord.Embed(title="🛡️ Whitelisted Users", color=0x10b981, description="Users who can use commands without prefix")
        for i, (user_id,) in enumerate(rows, 1):
            user = self.bot.get_user(user_id)
            name = user.name if user else f"Unknown ({user_id})"
            embed.add_field(name=f"{i}. {name}", value=f"ID: `{user_id}`", inline=False)
        
        await ctx.send(embed=embed, view=WhitelistView(self.bot, ctx.guild.id))

async def setup(bot):
    await bot.add_cog(Antinuke(bot))
