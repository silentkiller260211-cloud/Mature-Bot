import discord
from discord.ext import commands
from discord import ui
import aiosqlite
from datetime import datetime
from utils.embed_helper import create_success_embed, create_error_embed, create_info_embed

DB_PATH = "mature_bot.db"

VALID_RELATIONSHIPS = [
    "friend", "bestfriend", "brother", "sister",
    "crush", "couple", "mentor", "partner"
]

class RelationshipRequestView(ui.View):
    def __init__(self, requester, target, relationship_type, bot):
        super().__init__(timeout=120)
        self.requester = requester
        self.target = target
        self.relationship_type = relationship_type
        self.bot = bot
        self.message = None

    @ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message(
                "❌ Only the mentioned user can accept this request!",
                ephemeral=True
            )
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM relationships WHERE (user1_id=? OR user2_id=?) AND relationship_type=?",
                (self.target.id, self.target.id, self.relationship_type)
            )
            if (await cursor.fetchone())[0] > 0:
                return await interaction.response.send_message(
                    f"❌ You already have a {self.relationship_type} relationship!",
                    ephemeral=True
                )
            
            ids = sorted([self.requester.id, self.target.id])
            await db.execute(
                "INSERT INTO relationships (user1_id, user2_id, relationship_type, created_at) VALUES (?, ?, ?, ?)",
                (*ids, self.relationship_type, datetime.utcnow().isoformat())
            )
            await db.execute(
                "DELETE FROM pending_relationships WHERE requester_id=? AND target_id=? AND relationship_type=?",
                (self.requester.id, self.target.id, self.relationship_type)
            )
            await db.commit()
        
        self.clear_items()
        embed = discord.Embed(
            title=f"✅ {self.relationship_type.title()} Request Accepted!",
            description=f"**{self.requester.mention}** and **{self.target.mention}** are now **{self.relationship_type}s**! 🎉",
            color=0x10b981,
            timestamp=datetime.utcnow()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @ui.button(label="❌ Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message(
                "❌ Only the mentioned user can reject this request!",
                ephemeral=True
            )
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM pending_relationships WHERE requester_id=? AND target_id=? AND relationship_type=?",
                (self.requester.id, self.target.id, self.relationship_type)
            )
            await db.commit()
        
        self.clear_items()
        embed = discord.Embed(
            title=f"❌ {self.relationship_type.title()} Request Rejected",
            description=f"**{self.target.mention}** rejected the request from **{self.requester.mention}**.",
            color=0xef4444,
            timestamp=datetime.utcnow()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM pending_relationships WHERE requester_id=? AND target_id=? AND relationship_type=?",
                (self.requester.id, self.target.id, self.relationship_type)
            )
            await db.commit()
        try:
            if self.message:
                embed = discord.Embed(
                    title="⏰ Request Expired",
                    description=f"The {self.relationship_type} request has expired.",
                    color=0x6b7280,
                    timestamp=datetime.utcnow()
                )
                await self.message.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Error in on_timeout: {e}")


class Relationship(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="relationship",
        description="👥 Send a relationship request to someone",
        usage="!relationship @user <type>",
        help="Send relationship request. Types: friend, bestfriend, brother, sister, crush, couple, mentor, partner"
    )
    async def relationship(self, ctx, member: discord.Member = None, relationship_type: str = None):
        if not member and not relationship_type:
            return await self.show_pending_requests(ctx)
        
        if member and not relationship_type:
            embed = create_error_embed(
                "Missing Relationship Type",
                f"Please specify a relationship type!\n\n**Valid types:** {', '.join(VALID_RELATIONSHIPS)}",
                ctx.author
            )
            return await ctx.send(embed=embed)
        
        if relationship_type.lower() not in VALID_RELATIONSHIPS:
            embed = create_error_embed(
                "Invalid Relationship Type",
                f"**Valid types:** {', '.join(VALID_RELATIONSHIPS)}",
                ctx.author
            )
            return await ctx.send(embed=embed)
        
        relationship_type = relationship_type.lower()
        
        if member.id == ctx.author.id:
            return await ctx.send(embed=create_error_embed("Invalid Target", "You cannot send request to yourself!", ctx.author))
        
        if member.bot:
            return await ctx.send(embed=create_error_embed("Invalid Target", "You cannot send request to a bot!", ctx.author))
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM relationships WHERE (user1_id=? OR user2_id=?) AND relationship_type=?",
                (ctx.author.id, ctx.author.id, relationship_type)
            )
            if (await cursor.fetchone())[0] > 0:
                return await ctx.send(embed=create_error_embed(
                    "Already in Relationship",
                    f"You already have a **{relationship_type}** relationship!",
                    ctx.author
                ))
            
            cursor = await db.execute(
                "SELECT COUNT(*) FROM pending_relationships WHERE requester_id=? AND target_id=? AND relationship_type=?",
                (ctx.author.id, member.id, relationship_type)
            )
            if (await cursor.fetchone())[0] > 0:
                return await ctx.send(embed=create_error_embed(
                    "Request Already Sent",
                    f"You already sent a **{relationship_type}** request to {member.mention}!",
                    ctx.author
                ))
            
            cursor = await db.execute(
                "SELECT COUNT(*) FROM pending_relationships WHERE requester_id=? AND target_id=? AND relationship_type=?",
                (member.id, ctx.author.id, relationship_type)
            )
            if (await cursor.fetchone())[0] > 0:
                return await ctx.send(embed=create_info_embed(
                    "Incoming Request Found!",
                    f"{member.mention} already sent you a **{relationship_type}** request!\n\nUse `!relationship accept {member.mention} {relationship_type}`",
                    ctx.author
                ))
            
            await db.execute(
                "INSERT INTO pending_relationships (requester_id, target_id, relationship_type, created_at) VALUES (?, ?, ?, ?)",
                (ctx.author.id, member.id, relationship_type, datetime.utcnow().isoformat())
            )
            await db.commit()
        
        embed = discord.Embed(
            title=f"💝 {relationship_type.title()} Request",
            description=f"**{ctx.author.mention}** wants to be your **{relationship_type}**!\n\nWill you accept?",
            color=0xec4899,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Request from {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        view = RelationshipRequestView(ctx.author, member, relationship_type, self.bot)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    async def show_pending_requests(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT requester_id, relationship_type FROM pending_relationships WHERE target_id=?",
                (ctx.author.id,)
            )
            incoming = await cursor.fetchall()
            
            cursor = await db.execute(
                "SELECT target_id, relationship_type FROM pending_relationships WHERE requester_id=?",
                (ctx.author.id,)
            )
            outgoing = await cursor.fetchall()
        
        embed = discord.Embed(
            title="📋 Relationship Requests",
            color=0x6366f1,
            timestamp=datetime.utcnow()
        )
        
        if incoming:
            incoming_text = ""
            for requester_id, rel_type in incoming:
                requester = ctx.guild.get_member(requester_id)
                if requester:
                    incoming_text += f"• **{requester.mention}** wants to be your **{rel_type}**\n"
            embed.add_field(name="📥 Incoming Requests", value=incoming_text or "None", inline=False)
        else:
            embed.add_field(name="📥 Incoming Requests", value="No pending requests", inline=False)
        
        if outgoing:
            outgoing_text = ""
            for target_id, rel_type in outgoing:
                target = ctx.guild.get_member(target_id)
                if target:
                    outgoing_text += f"• You sent a **{rel_type}** request to **{target.mention}**\n"
            embed.add_field(name="📤 Outgoing Requests", value=outgoing_text or "None", inline=False)
        else:
            embed.add_field(name="📤 Outgoing Requests", value="No sent requests", inline=False)
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="accept",
        description="✅ Accept a relationship request",
        usage="!accept @user <type>",
        help="Accept a pending relationship request"
    )
    async def accept(self, ctx, member: discord.Member, relationship_type: str):
        if relationship_type.lower() not in VALID_RELATIONSHIPS:
            return await ctx.send(embed=create_error_embed(
                "Invalid Relationship Type",
                f"**Valid types:** {', '.join(VALID_RELATIONSHIPS)}",
                ctx.author
            ))
        
        relationship_type = relationship_type.lower()
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM pending_relationships WHERE requester_id=? AND target_id=? AND relationship_type=?",
                (member.id, ctx.author.id, relationship_type)
            )
            if (await cursor.fetchone())[0] == 0:
                return await ctx.send(embed=create_error_embed(
                    "No Request Found",
                    f"{member.mention} hasn't sent you a **{relationship_type}** request!",
                    ctx.author
                ))
            
            ids = sorted([member.id, ctx.author.id])
            await db.execute(
                "INSERT INTO relationships (user1_id, user2_id, relationship_type, created_at) VALUES (?, ?, ?, ?)",
                (*ids, relationship_type, datetime.utcnow().isoformat())
            )
            await db.execute(
                "DELETE FROM pending_relationships WHERE requester_id=? AND target_id=? AND relationship_type=?",
                (member.id, ctx.author.id, relationship_type)
            )
            await db.commit()
        
        embed = discord.Embed(
            title=f"✅ {relationship_type.title()} Request Accepted!",
            description=f"**{ctx.author.mention}** and **{member.mention}** are now **{relationship_type}s**! 🎉",
            color=0x10b981,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Accepted by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="removerel",
        description="💔 Remove a relationship",
        usage="!removerel @user <type>",
        help="Remove an existing relationship"
    )
    async def removerel(self, ctx, member: discord.Member, relationship_type: str):
        if relationship_type.lower() not in VALID_RELATIONSHIPS:
            return await ctx.send(embed=create_error_embed(
                "Invalid Relationship Type",
                f"**Valid types:** {', '.join(VALID_RELATIONSHIPS)}",
                ctx.author
            ))
        
        relationship_type = relationship_type.lower()
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM relationships WHERE (user1_id=? OR user2_id=?) AND relationship_type=?",
                (ctx.author.id, ctx.author.id, relationship_type)
            )
            if (await cursor.fetchone())[0] == 0:
                return await ctx.send(embed=create_error_embed(
                    "No Relationship Found",
                    f"You don't have a **{relationship_type}** relationship with {member.mention}!",
                    ctx.author
                ))
            
            await db.execute(
                "DELETE FROM relationships WHERE (user1_id=? OR user2_id=?) AND relationship_type=?",
                (ctx.author.id, ctx.author.id, relationship_type)
            )
            await db.commit()
        
        embed = create_success_embed(
            "Relationship Removed",
            f"Your **{relationship_type}** relationship with **{member.mention}** has been removed.",
            ctx.author,
            color=0xef4444
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="relationships",
        description="👀 View your or someone's relationships",
        usage="!relationships [@user]",
        help="View all relationships of a user"
    )
    async def relationships(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT user1_id, user2_id, relationship_type FROM relationships WHERE user1_id=? OR user2_id=?",
                (member.id, member.id)
            )
            relationships = await cursor.fetchall()
        
        embed = discord.Embed(
            title=f"👥 {member.display_name}'s Relationships",
            color=0x6366f1,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        if not relationships:
            embed.description = "No relationships yet! 💔"
        else:
            rel_text = ""
            for user1_id, user2_id, rel_type in relationships:
                partner_id = user2_id if user1_id == member.id else user1_id
                partner = ctx.guild.get_member(partner_id)
                if partner:
                    rel_text += f"• **{rel_type.title()}** with {partner.mention}\n"
                else:
                    rel_text += f"• **{rel_type.title()}** with Unknown User\n"
            embed.description = rel_text
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                user1_id INTEGER,
                user2_id INTEGER,
                relationship_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user1_id, user2_id, relationship_type)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_relationships (
                requester_id INTEGER,
                target_id INTEGER,
                relationship_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (requester_id, target_id, relationship_type)
            )
        """)
        await db.commit()
    await bot.add_cog(Relationship(bot))
