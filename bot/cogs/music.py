import discord
from discord.ext import commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}
        self.loop = {}
        self.volume = {}
        self.paused = {}
        self.now_playing = {}

    @commands.hybrid_command()
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Join a voice channel first!")
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        self.now_playing[ctx.guild.id] = query
        await ctx.send(f"🎵 Now playing: **{query}**")

    @commands.hybrid_command()
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Paused.")
        else:
            await ctx.send("❌ Nothing is playing.")

    @commands.hybrid_command()
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ Resumed.")

    @commands.hybrid_command()
    async def skip(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.send("⏭️ Skipped.")

    @commands.hybrid_command()
    async def stop(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.now_playing.pop(ctx.guild.id, None)
            await ctx.send("⏹️ Stopped and disconnected.")

    @commands.hybrid_command()
    async def queue(self, ctx):
        await ctx.send("📜 Queue is empty.")

    @commands.hybrid_command()
    async def shuffle(self, ctx):
        await ctx.send("🔀 Queue shuffled.")

    @commands.hybrid_command()
    async def loop(self, ctx):
        self.loop[ctx.guild.id] = not self.loop.get(ctx.guild.id, False)
        status = "enabled" if self.loop[ctx.guild.id] else "disabled"
        await ctx.send(f"🔁 Loop {status}.")

    @commands.hybrid_command()
    async def volume(self, ctx, vol: int = 100):
        if 0 <= vol <= 200:
            self.volume[ctx.guild.id] = vol
            await ctx.send(f"🔊 Volume set to {vol}%.")
        else:
            await ctx.send("❌ Volume must be 0-200.")

    @commands.hybrid_command()
    async def join(self, ctx):
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            await ctx.send("✅ Joined voice channel.")

    @commands.hybrid_command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("👋 Left voice channel.")

    @commands.hybrid_command()
    async def lyrics(self, ctx, *, song: str = None):
        song = song or self.now_playing.get(ctx.guild.id, "Unknown")
        await ctx.send(f"📝 Lyrics for **{song}**:\n[Lyrics not available in demo]")

    @commands.hybrid_command()
    async def nowplaying(self, ctx):
        np = self.now_playing.get(ctx.guild.id, "Nothing")
        await ctx.send(f"🎶 Now Playing: **{np}**")

    @commands.hybrid_command()
    async def playlist(self, ctx):
        await ctx.send("📂 Your playlist is empty.")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def _24x7_enable(self, ctx):
        await ctx.send("🔊 24/7 mode enabled.")

    @commands.hybrid_command(name="24x7_disable")
    @commands.has_permissions(administrator=True)
    async def _24x7_disable(self, ctx):
        await ctx.send("🔇 24/7 mode disabled.")

    @commands.hybrid_command(name="24x7_enable")
    @commands.has_permissions(administrator=True)
    async def _24x7_enable_cmd(self, ctx):
        await ctx.send("🔊 24/7 mode enabled.")

async def setup(bot):
    await bot.add_cog(Music(bot))
