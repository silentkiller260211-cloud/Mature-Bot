import discord
from discord.ext import commands
from discord import app_commands
import json
from utils import database as db
from utils.security import is_owner

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.programs = {
            "anti_ban": {"name": "Anti-Ban", "emoji": "🔨", "default": 5},
            "anti_kick": {"name": "Anti-Kick", "emoji": "👢", "default": 5},
            "anti_role_delete": {"name": "Anti-Role Delete", "emoji": "🗑️", "default": 3},
            "anti_channel_delete": {"name": "Anti-Channel Delete", "emoji": "📢", "default": 3},
            "anti_webhook": {"name": "Anti-Webhook", "emoji": "🔗", "default": 2},
            "anti_bot": {"name": "Anti-Bot", "emoji": "🤖", "default": 1},
            "anti_permission": {"name": "Anti-Permission", "emoji": "🔐", "default": 5},
            "anti_emoji": {"name": "Anti-Emoji", "emoji": "😢", "default": 3},
            "anti_sticker": {"name": "Anti-Sticker", "emoji": "🧩", "default": 3},
            "anti_slowmode": {"name": "Anti-Slowmode", "emoji": "⏳", "default": 5},
            "anti_nickname": {"name": "Anti-Nickname Spam", "emoji": "✏️", "default": 10},
            "anti_role_create": {"name": "Anti-Role Create", "emoji": "🎭", "default": 3},
            "anti_channel_create": {"name": "Anti-Channel Create", "emoji": "📣", "default": 3},
            "anti_thread": {"name": "Anti-Thread Spam", "emoji": "🧵", "default": 5},
            "anti_webhook_update": {"name": "Anti-Webhook Update", "emoji": "🔄", "default": 2},
            "anti_guild_update": {"name": "Anti-Guild Update", "emoji": "⚙️", "default": 3},
            "anti_voice_mute": {"name": "Anti-Voice Mute Spam", "emoji": "🔇", "default": 5},
            "anti_voice_deafen": {"name": "Anti-Voice Deafen Spam", "emoji": "🔊", "default": 5},
            "anti_link": {"name": "Anti-Link", "emoji": "🔗", "default": 3}
        }

    def get_config(self, guild_id):
        record = db.fetch_one("SELECT antinuke_settings FROM guild_settings WHERE guild_id = ?", (guild_id,))
        if record and record["antinuke_settings"]:
            return json.loads(record["antinuke_settings"])
        return {key: prog["default"] for key, prog in self.programs.items()}

    def save_config(self, guild_id, config):
        db.execute_query("INSERT OR REPLACE INTO guild_settings (guild_id, antinuke_settings) VALUES (?, ?)", (guild_id, json.dumps(config)))

    def is_enabled(self, guild_id):
        record = db.fetch_one("SELECT antinuke_enabled FROM guild_settings WHERE guild_id = ?", (guild_id,))
        return bool(record and record["antinuke_enabled"])

    def set_enabled(self, guild_id, enabled):
        db.execute_query("INSERT OR REPLACE INTO guild_settings (guild_id, antinuke_enabled) VALUES (?, ?)", (guild_id, 1 if enabled else 0))

    @app_commands.command(name="antinuke", description="Manage Anti-Nuke settings")
    @app_commands.default_permissions(administrator=True)
    async def antinuke_menu(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        config = self.get_config(guild_id)
        enabled = self.is_enabled(guild_id)
        embed = discord.Embed(title="🛡️ Anti-Nuke Control Panel", description="Toggle protections, whitelist, or disable all.", color=discord.Color.blue())
        status_text = ""
        for key, prog in self.programs.items():
            threshold = config.get(key, 0)
            active = enabled and threshold > 0
            status = "✅" if active else "❌"
            status_text += f"{prog['emoji']} **{prog['name']}** – {status} (Threshold: {threshold})\n"
        embed.add_field(name="📋 Protections", value=status_text, inline=False)
        view = AntiNukeView(self, guild_id, config, enabled, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)

class AntiNukeView(discord.ui.View):
    def __init__(self, cog, guild_id, config, enabled, user):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.config = config.copy()
        self.enabled = enabled
        self.user = user
        # Toggle buttons for each program
        for i, key in enumerate(cog.programs.keys()):
            row = i // 9
            btn = discord.ui.Button(
                label=f"{cog.programs[key]['emoji']} {'ON' if self.config.get(key, 0)>0 else 'OFF'}",
                style=discord.ButtonStyle.green if self.config.get(key, 0)>0 else discord.ButtonStyle.secondary,
                custom_id=f"toggle_{key}",
                row=row
            )
            btn.callback = self.toggle_program
            self.add_item(btn)
        self.add_item(discord.ui.Button(label="👤 Whitelist Users", style=discord.ButtonStyle.primary, custom_id="whitelist", row=2))
        self.add_item(discord.ui.Button(label="❌ Disable Selected", style=discord.ButtonStyle.danger, custom_id="disable_selected", row=2))
        self.add_item(discord.ui.Button(label="🛑 Disable All", style=discord.ButtonStyle.danger, custom_id="disable_all", row=2))
        self.add_item(discord.ui.Button(label="✅ Enable All", style=discord.ButtonStyle.success, custom_id="enable_all", row=2))
        self.add_item(discord.ui.Button(label="💾 Save", style=discord.ButtonStyle.primary, custom_id="save", row=3))
        self.add_item(discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel", row=3))

    async def toggle_program(self, interaction):
        key = interaction.data["custom_id"].replace("toggle_", "")
        current = self.config.get(key, 0)
        self.config[key] = 0 if current > 0 else self.cog.programs[key]["default"]
        await self.update_menu(interaction)

    async def update_menu(self, interaction):
        embed = discord.Embed(title="🛡️ Anti-Nuke Control Panel", color=discord.Color.blue())
        status_text = ""
        for key, prog in self.cog.programs.items():
            threshold = self.config.get(key, 0)
            active = self.enabled and threshold > 0
            status = "✅" if active else "❌"
            status_text += f"{prog['emoji']} **{prog['name']}** – {status} (Threshold: {threshold})\n"
        embed.add_field(name="📋 Protections", value=status_text, inline=False)
        for child in self.children:
            if child.custom_id and child.custom_id.startswith("toggle_"):
                key = child.custom_id.replace("toggle_", "")
                threshold = self.config.get(key, 0)
                child.label = f"{self.cog.programs[key]['emoji']} {'ON' if threshold>0 else 'OFF'}"
                child.style = discord.ButtonStyle.green if threshold>0 else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction):
        return interaction.user == self.user

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
