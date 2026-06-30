import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
from utils.helpers import format_duration

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -bufsize 64k -b:a 192k -ac 2 -ar 48000'
}

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, guild_id):
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(self.bot, guild_id)
        return self.players[guild_id]

    async def ensure_voice(self, interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ You are not in a voice channel.", ephemeral=True)
            return None
        voice = interaction.guild.voice_client
        if voice and voice.is_connected():
            if voice.channel.id == interaction.user.voice.channel.id:
                return voice
            await interaction.response.send_message("❌ I am already in another voice channel.", ephemeral=True)
            return None
        try:
            voice = await interaction.user.voice.channel.connect()
            return voice
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not connect: {e}", ephemeral=True)
            return None

    @app_commands.command(name="play", description="Play a song")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        voice = await self.ensure_voice(interaction)
        if not voice:
            return
        player = self.get_player(interaction.guild.id)
        if not player.voice_client:
            player.voice_client = voice
        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                song = {
                    'title': info.get('title', 'Unknown'),
                    'url': info.get('url'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'web_url': info.get('webpage_url', '')
                }
                if player.is_playing:
                    player.add_to_queue(song)
                    embed = discord.Embed(title="🎵 Added to Queue", description=f"[{song['title']}]({song['web_url']})", color=discord.Color.green())
                    embed.add_field(name="Position", value=len(player.queue), inline=True)
                    embed.add_field(name="Duration", value=format_duration(song['duration']), inline=True)
                    await interaction.followup.send(embed=embed)
                else:
                    await player.play_song(song)
                    embed = discord.Embed(title="🎵 Now Playing", description=f"[{song['title']}]({song['web_url']})", color=discord.Color.blue())
                    embed.add_field(name="Duration", value=format_duration(song['duration']), inline=True)
                    if song['thumbnail']:
                        embed.set_thumbnail(url=song['thumbnail'])
                    await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="❌ Error", description=str(e), color=discord.Color.red())
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if not voice or not voice.is_playing():
            await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
            return
        voice.pause()
        embed = discord.Embed(title="⏸️ Paused", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resume", description="Resume the current song")
    async def resume(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if not voice or not voice.is_paused():
            await interaction.response.send_message("❌ Nothing paused.", ephemeral=True)
            return
        voice.resume()
        embed = discord.Embed(title="▶️ Resumed", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if not voice or not voice.is_playing():
            await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
            return
        voice.stop()
        embed = discord.Embed(title="⏭️ Skipped", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stop", description="Stop the player and clear queue")
    async def stop(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if not voice:
            await interaction.response.send_message("❌ Not in voice.", ephemeral=True)
            return
        player = self.get_player(interaction.guild.id)
        player.queue.clear()
        voice.stop()
        await voice.disconnect()
        self.players.pop(interaction.guild.id, None)
        embed = discord.Embed(title="⏹️ Stopped", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="queue", description="Show the current queue")
    async def queue(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        if not player.queue and not player.current_song:
            await interaction.response.send_message("📭 Queue is empty.", ephemeral=True)
            return
        embed = discord.Embed(title="📋 Music Queue", color=discord.Color.blue())
        if player.current_song:
            embed.add_field(name="Now Playing", value=f"**{player.current_song['title']}**", inline=False)
        if player.queue:
            queue_list = ""
            for i, song in enumerate(player.queue[:10], 1):
                queue_list += f"`{i}.` {song['title'][:50]} - {format_duration(song['duration'])}\n"
            if len(player.queue) > 10:
                queue_list += f"... and {len(player.queue) - 10} more"
            embed.add_field(name="Queue", value=queue_list, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Adjust volume (0-200)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        voice = interaction.guild.voice_client
        if not voice or not voice.source:
            await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
            return
        if volume < 0 or volume > 200:
            await interaction.response.send_message("❌ Volume must be between 0 and 200.", ephemeral=True)
            return
        voice.source.volume = volume / 100
        embed = discord.Embed(title="🔊 Volume Set", description=f"Volume set to {volume}%", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Show current playing song")
    async def nowplaying(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        if not player.current_song:
            await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
            return
        song = player.current_song
        embed = discord.Embed(title="🎵 Now Playing", description=f"**{song['title']}**", color=discord.Color.blue())
        embed.add_field(name="Duration", value=format_duration(song['duration']), inline=True)
        if song['thumbnail']:
            embed.set_thumbnail(url=song['thumbnail'])
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loop", description="Toggle loop mode")
    async def loop(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        player.loop = not player.loop
        embed = discord.Embed(title="🔁 Loop " + ("Enabled" if player.loop else "Disabled"), color=discord.Color.green() if player.loop else discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shuffle", description="Shuffle the queue")
    async def shuffle(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        if len(player.queue) < 2:
            await interaction.response.send_message("❌ Not enough songs to shuffle.", ephemeral=True)
            return
        player.shuffle()
        embed = discord.Embed(title="🔀 Queue Shuffled", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="join", description="Make bot join your voice channel")
    async def join(self, interaction: discord.Interaction):
        voice = await self.ensure_voice(interaction)
        if voice:
            embed = discord.Embed(title="🔊 Joined", description=f"Joined {interaction.user.voice.channel.mention}", color=discord.Color.green())
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leave", description="Make bot leave voice channel")
    async def leave(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if not voice:
            await interaction.response.send_message("❌ Not in voice.", ephemeral=True)
            return
        player = self.get_player(interaction.guild.id)
        player.queue.clear()
        await voice.disconnect()
        self.players.pop(interaction.guild.id, None)
        embed = discord.Embed(title="🔇 Left", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="autoplay_enable", description="Enable autoplay (any user)")
    async def autoplay_enable(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        player.autoplay = True
        embed = discord.Embed(title="🔁 Autoplay Enabled", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="autoplay_disable", description="Disable autoplay")
    async def autoplay_disable(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        player.autoplay = False
        embed = discord.Embed(title="🔁 Autoplay Disabled", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="24x7_enable", description="Enable 24/7 mode (admin)")
    @app_commands.default_permissions(administrator=True)
    async def enable_24x7(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        player.mode_24x7 = True
        embed = discord.Embed(title="🕒 24/7 Mode Enabled", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="24x7_disable", description="Disable 24/7 mode")
    @app_commands.default_permissions(administrator=True)
    async def disable_24x7(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild.id)
        player.mode_24x7 = False
        embed = discord.Embed(title="🕒 24/7 Mode Disabled", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="playlist", description="Manage your personal playlist")
    async def playlist(self, interaction: discord.Interaction, action: str, query: str = None):
        # Simplified: only list, add (to queue) for now
        if action.lower() == "list":
            # Placeholder – you'd fetch from DB
            await interaction.response.send_message("Playlist feature coming soon.", ephemeral=True)
        else:
            await interaction.response.send_message("Use `/playlist list` or `/playlist add` (coming soon).", ephemeral=True)

class MusicPlayer:
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.queue = []
        self.current_song = None
        self.voice_client = None
        self.is_playing = False
        self.loop = False
        self.autoplay = False
        self.mode_24x7 = False

    def add_to_queue(self, song):
        self.queue.append(song)
        return len(self.queue)

    def shuffle(self):
        import random
        random.shuffle(self.queue)

    async def play_song(self, song):
        self.current_song = song
        self.is_playing = True
        source = discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS)
        self.voice_client.play(source, after=lambda e: self.bot.loop.create_task(self._after_play()))

    async def _after_play(self):
        self.is_playing = False
        if self.loop:
            await self.play_song(self.current_song)
        elif self.queue:
            next_song = self.queue.pop(0)
            await self.play_song(next_song)
        elif self.autoplay:
            # Autoplay logic would fetch similar songs – placeholder
            pass
        else:
            self.current_song = None
            if not self.mode_24x7 and self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None

async def setup(bot):
    await bot.add_cog(Music(bot))
