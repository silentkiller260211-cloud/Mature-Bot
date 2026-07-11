import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime
from utils.embed_helper import create_success_embed, create_error_embed, create_info_embed

DB_PATH = "mature_bot.db"

class CustomCommandsHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="addcmd",
        description="➕ Add a custom command to the server",
        usage="!addcmd <name> <response>",
        help="Create a custom command. Example: !addcmd welcome Welcome to the server!"
    )
    @commands.has_permissions(administrator=True)
    async def addcmd(self, ctx, name: str, *, response: str):
        if name.startswith('!'):
            name = name[1:]
        
        reserved = ['ban', 'kick', 'warn', 'mute', 'help', 'antinuke', 'premium']
        if name.lower() in reserved:
            return await ctx.send(embed=create_error_embed(
                "Invalid Command Name",
                "You cannot override built-in commands!",
                ctx.author
            ))
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO custom_commands (guild_id, name, response, created_by) VALUES (?, ?, ?, ?)",
                (ctx.guild.id, name.lower(), response, ctx.author.id)
            )
            await db.commit()
        
        embed = create_success_embed(
            "Custom Command Created",
            f"Command `!{name}` has been created successfully!",
            ctx.author
        )
        embed.add_field(name="📝 Command", value=f"`!{name}`", inline=True)
        embed.add_field(name="💬 Response", value=response[:100] + "..." if len(response) > 100 else response, inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="delcmd",
        description="🗑️ Delete a custom command",
        usage="!delcmd <name>",
        help="Delete a custom command"
    )
    @commands.has_permissions(administrator=True)
    async def delcmd(self, ctx, name: str):
        if name.startswith('!'):
            name = name[1:]
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM custom_commands WHERE guild_id=? AND name=?",
                (ctx.guild.id, name.lower())
            )
            await db.commit()
            
            if cursor.rowcount == 0:
                return await ctx.send(embed=create_error_embed(
                    "Command Not Found",
                    f"Command `!{name}` does not exist!",
                    ctx.author
                ))
        
        embed = create_success_embed(
            "Command Deleted",
            f"Custom command `!{name}` has been deleted.",
            ctx.author
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="cmds",
        description="📋 View all custom commands",
        usage="!cmds",
        help="List all custom commands"
    )
    async def cmds(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT name, response FROM custom_commands WHERE guild_id=?",
                (ctx.guild.id,)
            )
            rows = await cursor.fetchall()
        
        if not rows:
            return await ctx.send(embed=create_info_embed(
                "No Custom Commands",
                "No custom commands have been created yet!",
                ctx.author
            ))
        
        embed = discord.Embed(
            title="📋 Custom Commands",
            description=f"Total: {len(rows)} commands",
            color=0x6366f1,
            timestamp=datetime.utcnow()
        )
        
        commands_text = ""
        for name, response in rows[:10]:
            commands_text += f"• `!{name}`\n"
        
        embed.add_field(name="Available Commands", value=commands_text, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        if not message.content.startswith('!'):
            return
        
        cmd_name = message.content.split()[0][1:].lower()
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT response FROM custom_commands WHERE guild_id=? AND name=?",
                (message.guild.id, cmd_name)
            )
            row = await cursor.fetchone()
        
        if row:
            response = row[0]
            await message.channel.send(response)

async def setup(bot):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_commands (
                guild_id INTEGER,
                name TEXT,
                response TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, name)
            )
        """)
        await db.commit()
    await bot.add_cog(CustomCommandsHandler(bot))
