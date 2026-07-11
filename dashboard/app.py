from flask import Flask, request, jsonify, session, redirect, make_response, render_template_string
import requests
import os
import discord
import aiosqlite
import asyncio
import random
import string
from datetime import datetime, timedelta
from functools import wraps
from utils.database import (
    create_premium_code, get_premium_code, mark_code_used,
    save_payment, update_payment_status, get_payment_info
)

app = Flask(__name__)
app.secret_key = "MATURE_BOT_PRO_DASHBOARD_2026_SECURE"

bot_instance = None
DEVELOPER_USER_ID = int(os.getenv("DEVELOPER_USER_ID", "0"))
CLIENT_ID = os.getenv("CLIENT_ID", "YOUR_CLIENT_ID_HERE")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://mature-bot.onrender.com/callback")

DISCORD_API = "https://discord.com/api/v10"
INVITE_URL = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands"
DB_PATH = "mature_bot.db"

# COMPLETE PAYMENT LINKS - ALL 12 PLANS
PAYMENT_LINKS = {
    'silver': {
        'monthly': {'price': 125, 'days': 30, 'label': 'Monthly', 'link': 'https://imjo.in/FMXmx4'},
        '3months': {'price': 325, 'days': 90, 'label': '3 Months', 'link': 'https://imjo.in/hzyJZV'},
        '6months': {'price': 599, 'days': 180, 'label': '6 Months', 'link': 'https://imjo.in/py7b5W'},
        'yearly': {'price': 999, 'days': 365, 'label': 'Yearly', 'link': 'https://imjo.in/K9JgCV'}
    },
    'gold': {
        'monthly': {'price': 249, 'days': 30, 'label': 'Monthly', 'link': 'https://imjo.in/Nzmnky'},
        '3months': {'price': 649, 'days': 90, 'label': '3 Months', 'link': 'https://imjo.in/XZZtKx'},
        '6months': {'price': 1199, 'days': 180, 'label': '6 Months', 'link': 'https://imjo.in/hTWGMm'},
        'yearly': {'price': 1999, 'days': 365, 'label': 'Yearly', 'link': 'https://imjo.in/bptbjB'}
    },
    'black': {
        'monthly': {'price': 499, 'days': 30, 'label': 'Monthly', 'link': 'https://imjo.in/YT9Vgz'},
        '3months': {'price': 1299, 'days': 90, 'label': '3 Months', 'link': 'https://imjo.in/K4e44A'},
        '6months': {'price': 2399, 'days': 180, 'label': '6 Months', 'link': 'https://imjo.in/5qJwZp'},
        'yearly': {'price': 3999, 'days': 365, 'label': 'Yearly', 'link': 'https://imjo.in/RdFkFq'}
    }
}

def is_developer(user_id):
    return int(user_id) == DEVELOPER_USER_ID

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Not logged in"}), 401
        return f(*args, **kwargs)
    return decorated_function

def generate_premium_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "name": "Mature Bot Dashboard",
        "short_name": "Mature Bot",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f0f23",
        "theme_color": "#6366f1",
        "orientation": "portrait",
        "icons": [{"src": "https://cdn.discordapp.com/emojis/1092835073522409522.png", "sizes": "192x192", "type": "image/png"}]
    }
    response = make_response(jsonify(manifest_data))
    response.headers['Content-Type'] = 'application/manifest+json'
    return response

def run_async(coro):
    if bot_instance and bot_instance.loop:
        future = asyncio.run_coroutine_threadsafe(coro, bot_instance.loop)
        return future.result(timeout=15)
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

@app.route('/api/payment/create', methods=['POST'])
@login_required
def create_payment():
    data = request.json
    tier = data.get('tier', 'silver')
    duration = data.get('duration', 'monthly')
    
    if tier not in PAYMENT_LINKS or duration not in PAYMENT_LINKS[tier]:
        return jsonify({'success': False, 'error': 'Invalid plan'}), 400
    
    plan = PAYMENT_LINKS[tier][duration]
    payment_id = f"payment_{random.randint(100000, 999999)}"
    
    try:
        asyncio.run(save_payment(payment_id, int(session['user']['id']), plan['price'] * 100, tier, duration))
        
        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'payment_link': plan['link'],
            'amount': plan['price'],
            'tier': tier,
            'duration': duration
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/payment/verify', methods=['POST'])
@login_required
def verify_payment():
    data = request.json
    payment_id = data.get('payment_id')
    
    try:
        asyncio.run(update_payment_status(payment_id, 'completed'))
        
        code = generate_premium_code()
        
        payment_info = asyncio.run(get_payment_info(payment_id))
        if payment_info:
            tier, duration = payment_info
            days = PAYMENT_LINKS[tier][duration]['days']
            
            asyncio.run(create_premium_code(code, tier, duration, days))
            
            if bot_instance:
                async def send_dm():
                    user_id = int(session.get('user', {}).get('id', 0))
                    if user_id:
                        user = await bot_instance.fetch_user(user_id)
                        if user:
                            embed = discord.Embed(
                                title="🎉 Payment Successful!",
                                description=f"Your premium code is: `{code}`\n\n**Tier:** {tier.title()}\n**Duration:** {PAYMENT_LINKS[tier][duration]['label']}\n\nUse `!premium {code}` in any server to activate!",
                                color=0x10b981
                            )
                            try:
                                await user.send(embed=embed)
                            except:
                                pass
                
                asyncio.run_coroutine_threadsafe(send_dm(), bot_instance.loop).result(timeout=5)
        
        return jsonify({'success': True, 'code': code})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# DASHBOARD HTML TEMPLATE
# ============================================
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mature Bot Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        [x-cloak] { display: none !important; }
        body { font-family: 'Inter', sans-serif; background: #0f0f23; color: #e2e8f0; min-height: 100vh; }
        .gradient-text { background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .glass { background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px; }
        .btn-primary { background: linear-gradient(135deg, #6366f1, #8b5cf6, #a855f7); transition: all 0.3s; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 40px rgba(99, 102, 241, 0.5); }
        .btn-secondary { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); transition: all 0.3s; }
        .btn-secondary:hover { background: rgba(255, 255, 255, 0.1); }
    </style>
</head>
<body x-data="appData()" x-cloak class="min-h-screen">

    <!-- Loading Screen -->
    <div x-show="loading" class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0f0f23]">
        <div class="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-4xl animate-pulse">🧠</div>
        <p class="text-slate-400 font-medium mt-6">Loading Mature Bot...</p>
    </div>

    <!-- LANDING PAGE (Before Login) -->
    <div x-show="!loading && !isLoggedIn" class="min-h-screen">
        <nav class="sticky top-0 z-50 glass border-b border-white/10 px-4 py-4">
            <div class="max-w-7xl mx-auto flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xl">🧠</div>
                    <h1 class="text-2xl font-black gradient-text">MATURE BOT</h1>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/login" class="btn-secondary px-4 py-2 rounded-xl text-sm font-medium text-white flex items-center gap-2">
                        <i class="fas fa-sign-in-alt"></i><span>Login</span>
                    </a>
                    <a :href="inviteUrl" target="_blank" class="btn-primary px-4 py-2 rounded-xl text-sm font-bold text-white flex items-center gap-2">
                        <i class="fas fa-rocket"></i><span>Invite</span>
                    </a>
                </div>
            </div>
        </nav>

        <!-- Hero Section -->
        <section class="py-20 px-4 text-center">
            <div class="max-w-5xl mx-auto">
                <h1 class="text-5xl md:text-7xl font-black mb-6">
                    <span class="gradient-text">The Ultimate</span><br>
                    <span class="text-white">Discord Bot</span>
                </h1>
                <p class="text-xl text-slate-400 mb-10 max-w-3xl mx-auto">
                    Advanced security, powerful moderation, and seamless community management for modern Discord servers.
                </p>
                <div class="flex flex-col sm:flex-row gap-4 justify-center">
                    <a :href="inviteUrl" target="_blank" class="btn-primary px-8 py-4 rounded-2xl text-white font-bold text-lg flex items-center justify-center gap-3">
                        <i class="fas fa-rocket"></i><span>Add to Discord</span>
                    </a>
                    <a href="/login" class="btn-secondary px-8 py-4 rounded-2xl text-white font-bold text-lg flex items-center justify-center gap-3">
                        <i class="fas fa-chart-line"></i><span>Dashboard</span>
                    </a>
                </div>
            </div>
        </section>

        <!-- Live Stats -->
        <section class="py-16 px-4" x-data="statsData()">
            <div class="max-w-7xl mx-auto">
                <div class="glass p-8 rounded-3xl">
                    <div class="flex items-center justify-between mb-8">
                        <div>
                            <h2 class="text-3xl md:text-4xl font-bold mb-2"><span class="gradient-text">⚡ Live Performance</span></h2>
                            <p class="text-slate-400">Real-time statistics</p>
                        </div>
                        <div class="flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/30">
                            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            <span class="text-sm text-emerald-400 font-medium">LIVE</span>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                        <div class="bg-slate-800/50 p-5 rounded-2xl text-center">
                            <i class="fas fa-server text-indigo-400 text-2xl mb-2"></i>
                            <p class="text-2xl font-bold text-white" x-text="stats.servers">0</p>
                            <p class="text-xs text-slate-400">Servers</p>
                        </div>
                        <div class="bg-slate-800/50 p-5 rounded-2xl text-center">
                            <i class="fas fa-users text-purple-400 text-2xl mb-2"></i>
                            <p class="text-2xl font-bold text-white" x-text="stats.users">0</p>
                            <p class="text-xs text-slate-400">Users</p>
                        </div>
                        <div class="bg-slate-800/50 p-5 rounded-2xl text-center">
                            <i class="fas fa-user-check text-emerald-400 text-2xl mb-2"></i>
                            <p class="text-2xl font-bold text-white" x-text="stats.online_users">0</p>
                            <p class="text-xs text-slate-400">Active</p>
                        </div>
                        <div class="bg-slate-800/50 p-5 rounded-2xl text-center">
                            <i class="fas fa-bolt text-amber-400 text-2xl mb-2"></i>
                            <p class="text-2xl font-bold text-white" x-text="stats.latency + 'ms'">0ms</p>
                            <p class="text-xs text-slate-400">Latency</p>
                        </div>
                        <div class="bg-slate-800/50 p-5 rounded-2xl text-center">
                            <i class="fas fa-clock text-blue-400 text-2xl mb-2"></i>
                            <p class="text-xl font-bold text-white" x-text="stats.uptime">0h</p>
                            <p class="text-xs text-slate-400">Uptime</p>
                        </div>
                        <div class="bg-slate-800/50 p-5 rounded-2xl text-center">
                            <i class="fas fa-terminal text-pink-400 text-2xl mb-2"></i>
                            <p class="text-2xl font-bold text-white">76+</p>
                            <p class="text-xs text-slate-400">Commands</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Features -->
        <section class="py-16 px-4">
            <div class="max-w-7xl mx-auto">
                <h2 class="text-4xl font-bold text-center mb-12"><span class="gradient-text">🛡️ Powerful Features</span></h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div class="glass p-6 hover:transform hover:-translate-y-2 transition-all">
                        <div class="w-14 h-14 rounded-2xl bg-red-500/20 flex items-center justify-center mb-4"><i class="fas fa-shield-alt text-2xl text-red-400"></i></div>
                        <h3 class="text-xl font-bold text-white mb-2">🛡️ 24 Antinuke Modules</h3>
                        <p class="text-slate-400 text-sm">Complete protection against all types of server attacks.</p>
                    </div>
                    <div class="glass p-6 hover:transform hover:-translate-y-2 transition-all">
                        <div class="w-14 h-14 rounded-2xl bg-purple-500/20 flex items-center justify-center mb-4"><i class="fas fa-link text-2xl text-purple-400"></i></div>
                        <h3 class="text-xl font-bold text-white mb-2">🔗 Vanity Protection</h3>
                        <p class="text-slate-400 text-sm">Auto-monitoring to protect your custom invite URL.</p>
                    </div>
                    <div class="glass p-6 hover:transform hover:-translate-y-2 transition-all">
                        <div class="w-14 h-14 rounded-2xl bg-blue-500/20 flex items-center justify-center mb-4"><i class="fas fa-palette text-2xl text-blue-400"></i></div>
                        <h3 class="text-xl font-bold text-white mb-2">🎨 Embed Builder</h3>
                        <p class="text-slate-400 text-sm">Create stunning custom embeds with interactive buttons.</p>
                    </div>
                    <div class="glass p-6 hover:transform hover:-translate-y-2 transition-all">
                        <div class="w-14 h-14 rounded-2xl bg-emerald-500/20 flex items-center justify-center mb-4"><i class="fas fa-ticket-alt text-2xl text-emerald-400"></i></div>
                        <h3 class="text-xl font-bold text-white mb-2">🎟️ Ticket System</h3>
                        <p class="text-slate-400 text-sm">Professional support ticket management.</p>
                    </div>
                    <div class="glass p-6 hover:transform hover:-translate-y-2 transition-all">
                        <div class="w-14 h-14 rounded-2xl bg-amber-500/20 flex items-center justify-center mb-4"><i class="fas fa-gavel text-2xl text-amber-400"></i></div>
                        <h3 class="text-xl font-bold text-white mb-2">⚙️ Advanced Moderation</h3>
                        <p class="text-slate-400 text-sm">Powerful tools with auto-punishment warn system.</p>
                    </div>
                    <div class="glass p-6 hover:transform hover:-translate-y-2 transition-all">
                        <div class="w-14 h-14 rounded-2xl bg-pink-500/20 flex items-center justify-center mb-4"><i class="fas fa-heart text-2xl text-pink-400"></i></div>
                        <h3 class="text-xl font-bold text-white mb-2">❤️ Social Features</h3>
                        <p class="text-slate-400 text-sm">Marriage, relationships, and community engagement.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Footer -->
        <footer class="py-12 px-4 border-t border-white/10">
            <div class="max-w-7xl mx-auto text-center">
                <p class="text-slate-500 text-sm">© 2026 Mature Bot. All rights reserved.</p>
                <div class="mt-4 flex justify-center gap-4">
                    <a href="https://discord.gg/YxeeaEg9V6" target="_blank" class="text-slate-400 hover:text-white"><i class="fab fa-discord text-xl"></i></a>
                </div>
            </div>
        </footer>
    </div>

    <!-- DASHBOARD (After Login) -->
    <div x-show="!loading && isLoggedIn" class="min-h-screen">
        <header class="glass border-b border-white/10 px-4 py-3 flex items-center justify-between sticky top-0 z-40">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xl">🧠</div>
                <h1 class="text-xl font-black gradient-text">MATURE BOT</h1>
            </div>
            <div class="flex items-center gap-3">
                <a :href="inviteUrl" target="_blank" class="btn-secondary px-3 py-2 rounded-xl text-sm text-white flex items-center gap-2">
                    <i class="fas fa-plus"></i><span class="hidden md:inline">Invite</span>
                </a>
                <div class="flex items-center gap-2">
                    <img :src="userAvatar" class="w-8 h-8 rounded-full border-2 border-indigo-500">
                    <a href="/logout" class="btn-secondary px-3 py-2 rounded-xl text-sm text-red-400 flex items-center gap-2">
                        <i class="fas fa-sign-out-alt"></i><span class="hidden md:inline">Logout</span>
                    </a>
                </div>
            </div>
        </header>

        <main class="p-4 max-w-7xl mx-auto">
            <!-- Premium Panel - Maintenance Notice -->
            <div x-show="activePanel === 'premium'" class="space-y-6">
                <div class="glass p-8 text-center">
                    <div class="w-20 h-20 rounded-full bg-amber-500/20 flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-tools text-4xl text-amber-400"></i>
                    </div>
                    <h2 class="text-3xl font-bold text-white mb-3">Premium System Under Maintenance</h2>
                    <p class="text-slate-400 mb-6">We're working on improving our payment system. Premium features will be available soon!</p>
                    <a href="https://discord.gg/YxeeaEg9V6" target="_blank" class="btn-primary inline-flex items-center gap-2 px-6 py-3 rounded-xl text-white font-bold">
                        <i class="fab fa-discord"></i><span>Join Support Server</span>
                    </a>
                </div>
            </div>

            <!-- Home Panel -->
            <div x-show="activePanel === 'home'" class="space-y-6">
                <div class="glass p-6">
                    <h2 class="text-2xl font-bold text-white mb-2">Welcome to Mature Bot Dashboard</h2>
                    <p class="text-slate-400">Manage your servers with powerful tools and features.</p>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <button @click="activePanel = 'premium'" class="glass p-6 hover:transform hover:-translate-y-2 transition-all text-left">
                        <i class="fas fa-crown text-3xl text-yellow-400 mb-3"></i>
                        <h3 class="text-lg font-bold text-white">Premium</h3>
                        <p class="text-sm text-slate-400">View plans and status</p>
                    </button>
                    <a :href="inviteUrl" target="_blank" class="glass p-6 hover:transform hover:-translate-y-2 transition-all">
                        <i class="fas fa-rocket text-3xl text-indigo-400 mb-3"></i>
                        <h3 class="text-lg font-bold text-white">Invite Bot</h3>
                        <p class="text-sm text-slate-400">Add to your server</p>
                    </a>
                    <a href="https://discord.gg/YxeeaEg9V6" target="_blank" class="glass p-6 hover:transform hover:-translate-y-2 transition-all">
                        <i class="fab fa-discord text-3xl text-blue-400 mb-3"></i>
                        <h3 class="text-lg font-bold text-white">Support</h3>
                        <p class="text-sm text-slate-400">Join our Discord</p>
                    </a>
                </div>
            </div>
        </main>

        <nav class="fixed bottom-0 left-0 right-0 glass border-t border-white/10">
            <div class="flex justify-around items-center h-16 max-w-7xl mx-auto">
                <button @click="activePanel = 'home'" class="flex flex-col items-center" :class="activePanel === 'home' ? 'text-indigo-400' : 'text-slate-500'">
                    <i class="fas fa-home text-xl"></i><span class="text-[10px] mt-1">Home</span>
                </button>
                <button @click="activePanel = 'premium'" class="flex flex-col items-center" :class="activePanel === 'premium' ? 'text-purple-400' : 'text-slate-500'">
                    <i class="fas fa-crown text-xl"></i><span class="text-[10px] mt-1">Premium</span>
                </button>
            </div>
        </nav>
    </div>

    <script>
        function statsData() {
            return {
                stats: { servers: 0, users: 0, online_users: 0, latency: 0, uptime: '0h' },
                async init() {
                    await this.fetchStats();
                    setInterval(() => this.fetchStats(), 5000);
                },
                async fetchStats() {
                    try {
                        const res = await fetch('/api/stats?_=' + Date.now(), { cache: 'no-cache' });
                        if (res.ok) this.stats = await res.json();
                    } catch (e) { console.error('Stats error:', e); }
                }
            }
        }

        function appData() {
            return {
                inviteUrl: 'https://discord.com/api/oauth2/authorize?client_id={{ CLIENT_ID }}&permissions=8&scope=bot%20applications.commands',
                loading: true,
                isLoggedIn: false,
                user: null,
                activePanel: 'home',
                get userAvatar() {
                    if (!this.user) return 'https://cdn.discordapp.com/embed/avatars/0.png';
                    return `https://cdn.discordapp.com/avatars/${this.user.id}/${this.user.avatar}.png`;
                },
                async init() {
                    try {
                        const res = await fetch('/api/user');
                        if (res.ok) {
                            this.user = await res.json();
                            this.isLoggedIn = true;
                        }
                    } catch (e) { console.error(e); }
                    this.loading = false;
                }
            }
        }
    </script>
</body>
</html>
"""

# ============================================
# AUTH ROUTES
# ============================================
@app.route('/login')
def login():
    return redirect(f"{DISCORD_API}/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Error", 400
    r = requests.post(f"{DISCORD_API}/oauth2/token", data={
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI
    }, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if r.status_code != 200:
        return f"Error: {r.text}", 500
    tokens = r.json()
    h = {'Authorization': f'Bearer {tokens["access_token"]}'}
    user = requests.get(f"{DISCORD_API}/users/@me", headers=h).json()
    guilds_req = requests.get(f"{DISCORD_API}/users/@me/guilds", headers=h).json()
    bot_guilds = {str(g.id) for g in bot_instance.guilds} if bot_instance else set()
    valid = []
    for g in guilds_req:
        if g['id'] in bot_guilds:
            perms = int(g.get('permissions', 0))
            if is_developer(user['id']) or (perms & 0x8) or (perms & 0x20):
                valid.append({
                    'id': g['id'], 'name': g['name'],
                    'icon': f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get('icon') else None,
                    'members': 0
                })
    session['user'] = user
    session['guilds'] = valid
    session['access_token'] = tokens['access_token']
    return redirect('/')

@app.route('/api/user')
@login_required
def api_user():
    return jsonify(session['user'])

@app.route('/api/guilds')
@login_required
def api_guilds():
    guilds = session.get('guilds', [])
    for g in guilds:
        obj = bot_instance.get_guild(int(g['id']))
        if obj:
            g['members'] = obj.member_count
    return jsonify(guilds)

# ============================================
# ANTINUKE API
# ============================================
@app.route('/api/antinuke/<int:guild_id>')
@login_required
def api_get_antinuke(guild_id):
    async def get_settings():
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT program, enabled FROM antinuke_settings WHERE guild_id=?", (guild_id,))
            rows = await cursor.fetchall()
            return [{"program": r[0], "enabled": bool(r[1])} for r in rows]
    return jsonify(run_async(get_settings()))

@app.route('/api/antinuke/<int:guild_id>/<program>', methods=['POST'])
@login_required
def api_toggle_antinuke(guild_id, program):
    async def toggle():
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT enabled FROM antinuke_settings WHERE guild_id=? AND program=?", (guild_id, program))
            row = await cursor.fetchone()
            current = row[0] if row else False
            await db.execute("INSERT OR REPLACE INTO antinuke_settings (guild_id, program, enabled) VALUES (?, ?, ?)", (guild_id, program, not current))
            await db.commit()
            return not current
    return jsonify({"success": True, "enabled": run_async(toggle())})

# ============================================
# WHITELIST API
# ============================================
@app.route('/api/whitelist/<int:guild_id>')
@login_required
def api_get_whitelist(guild_id):
    async def get_users():
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT user_id FROM no_prefix_users WHERE guild_id=?", (guild_id,))
            rows = await cursor.fetchall()
            users = []
            for (user_id,) in rows:
                user = bot_instance.get_user(user_id)
                users.append({
                    "id": user_id,
                    "name": user.name if user else f"Unknown ({user_id})",
                    "avatar": user.display_avatar.url if user else "https://cdn.discordapp.com/embed/avatars/0.png"
                })
            return users
    return jsonify(run_async(get_users()))

@app.route('/api/whitelist/<int:guild_id>', methods=['POST'])
@login_required
def api_add_whitelist(guild_id):
    data = request.json
    user_id = int(data.get('user_id', 0))
    async def add():
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM no_prefix_users WHERE guild_id=?", (guild_id,))
            count = (await cursor.fetchone())[0]
            if count >= 10:
                return {"success": False, "error": "Limit of 10 users reached"}
            await db.execute("INSERT OR IGNORE INTO no_prefix_users (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
            await db.commit()
            return {"success": True}
    return jsonify(run_async(add()))

@app.route('/api/whitelist/<int:guild_id>/<int:user_id>', methods=['DELETE'])
@login_required
def api_remove_whitelist(guild_id, user_id):
    async def remove():
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM no_prefix_users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            await db.commit()
            return {"success": True}
    return jsonify(run_async(remove()))

# ============================================
# PREMIUM STATUS API
# ============================================
@app.route('/api/premium-status/<int:guild_id>')
@login_required
def api_premium_status(guild_id):
    async def check():
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT tier, duration, expires_at FROM premium WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            if row:
                tier, duration, expires_at = row
                expires = datetime.fromisoformat(expires_at) if expires_at else None
                is_active = expires is None or expires > datetime.utcnow()
                return {
                    'active': is_active,
                    'tier': tier if is_active else None,
                    'duration': duration if is_active else None,
                    'expires_at': expires_at if is_active else None
                }
            return {'active': False, 'tier': None, 'duration': None, 'expires_at': None}
    return jsonify(run_async(check()))

# ============================================
# COMMAND EXECUTION API
# ============================================
@app.route('/api/command', methods=['POST'])
@login_required
def api_command():
    data = request.json
    guild_id = int(data.get('guild_id', 0))
    command_name = data.get('command', '').lower()
    
    if command_name.startswith('!'):
        command_name = command_name[1:]
    
    guild = bot_instance.get_guild(guild_id)
    if not guild:
        return jsonify({"success": False, "error": "Guild not found"}), 404
    
    channel = None
    for ch in guild.text_channels:
        if ch.permissions_for(guild.me).send_messages:
            channel = ch
            break
    
    if not channel:
        return jsonify({"success": False, "error": "No writable text channel found"}), 400
    
    user_id = int(session['user']['id'])
    member = guild.get_member(user_id)
    
    if not member:
        return jsonify({"success": False, "error": "You are not a member of this server"}), 403
    
    class FakeUser:
        id = user_id
        name = session['user']['username']
        display_name = session['user'].get('global_name') or session['user']['username']
        bot = False
        guild_permissions = member.guild_permissions
        top_role = member.top_role
    
    class FakeMessage:
        content = '!' + command_name
        author = FakeUser()
        channel = channel
        guild = guild
        created_at = datetime.utcnow()
        attachments = []
        embeds = []
        mentions = []
        role_mentions = []
        channel_mentions = []
        reaction_add = None
        reaction_remove = None
        reactions = []
    
    async def run():
        try:
            ctx = await bot_instance.get_context(FakeMessage())
            
            if ctx.command is None:
                cmd = bot_instance.get_command(command_name)
                if cmd:
                    ctx.command = cmd
                else:
                    return {"success": False, "error": f"Command '{command_name}' not found"}
            
            if not ctx.valid:
                return {"success": False, "error": f"Command '{command_name}' is invalid"}
            
            if not await ctx.command.can_run(ctx):
                return {"success": False, "error": "You don't have permission to use this command"}
            
            await bot_instance.invoke(ctx)
            return {"success": True, "message": f"Command '{command_name}' executed successfully"}
                
        except discord.errors.Forbidden:
            return {"success": False, "error": "Bot doesn't have permission to execute this command"}
        except discord.errors.HTTPException as e:
            return {"success": False, "error": f"HTTP Error: {str(e)}"}
        except Exception as e:
            print(f"Command error: {type(e).__name__}: {str(e)}")
            return {"success": False, "error": f"Error: {type(e).__name__}: {str(e)}"}
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run())
        return jsonify(result)
    finally:
        loop.close()

# ============================================
# LIVE STATS API (NEW)
# ============================================
@app.route('/api/stats')
def api_stats():
    """Get real-time bot statistics"""
    if not bot_instance:
        return jsonify({'error': 'Bot not ready'}), 503
    
    # Calculate uptime
    if hasattr(bot_instance, 'start_time'):
        delta = datetime.utcnow() - bot_instance.start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_formatted = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
    else:
        uptime_formatted = "0h 0m"
    
    # Real-time stats
    total_guilds = len(bot_instance.guilds)
    total_users = sum(g.member_count for g in bot_instance.guilds)
    total_online = 0
    
    for guild in bot_instance.guilds:
        try:
            online_count = sum(1 for member in guild.members if member.status != discord.Status.offline)
            total_online += online_count
        except:
            total_online += int(guild.member_count * 0.2)
    
    latency = round(bot_instance.latency * 1000)
    
    try:
        import psutil
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_percent = psutil.cpu_percent()
    except:
        memory_usage = 0
        cpu_percent = 0
    
    response = jsonify({
        'servers': total_guilds,
        'users': total_users,
        'online_users': total_online,
        'latency': latency,
        'uptime': uptime_formatted,
        'memory': f"{memory_usage:.1f}MB",
        'cpu': f"{cpu_percent}%",
        'ping': latency,
        'shards': 1,
        'commands': 76,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

# ============================================
# MAIN ROUTES
# ============================================
@app.route('/', methods=['GET'])
def index():
    return render_template_string(DASHBOARD_TEMPLATE, CLIENT_ID=CLIENT_ID)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/oauth-success')
def oauth_success():
    return redirect('/')

# ============================================
# DASHBOARD RUNNER
# ============================================
def run_dashboard():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)), threaded=True)

def set_bot_instance(bot):
    global bot_instance
    bot_instance = bot