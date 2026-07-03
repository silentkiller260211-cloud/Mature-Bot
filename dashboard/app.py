from flask import Flask, request, jsonify, session, redirect, make_response
import requests
import os
import discord
from datetime import datetime

app = Flask(__name__)
# CRITICAL: Hardcoded secret key to prevent login loops
app.secret_key = "MATURE_BOT_NATIVE_APP_KEY_9876543210" 

bot_instance = None
DEVELOPER_USER_ID = int(os.getenv("DEVELOPER_USER_ID", "0"))
CLIENT_ID = os.getenv("CLIENT_ID", "YOUR_CLIENT_ID_HERE") 
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://mature-bot.onrender.com/callback")

DISCORD_API = "https://discord.com/api/v10"
INVITE_URL = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands"

def is_developer(user_id):
    return int(user_id) == DEVELOPER_USER_ID

@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "name": "Mature Bot Dashboard", "short_name": "Mature Bot",
        "start_url": "/", "display": "standalone", "background_color": "#09090b",
        "theme_color": "#6366f1", "orientation": "portrait",
        "icons": [{"src": "https://cdn.discordapp.com/emojis/1092835073522409522.png", "sizes": "192x192", "type": "image/png"}]
    }
    response = make_response(jsonify(manifest_data))
    response.headers['Content-Type'] = 'application/manifest+json'
    return response

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#09090b">
    <link rel="manifest" href="/manifest.json">
    <title>Mature Bot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        [x-cloak] { display: none !important; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #09090b; color: #f8fafc; -webkit-tap-highlight-color: transparent; overscroll-behavior: none; user-select: none; -webkit-user-select: none; }
        input, textarea { user-select: text; -webkit-user-select: text; }
        .g-box { background: rgba(24, 24, 27, 0.6); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; transition: transform 0.1s ease; }
        .g-box:active { transform: scale(0.98); }
        .grad-setup { background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(6, 182, 212, 0.15)); border-color: rgba(16, 185, 129, 0.3); }
        .text-grad { background: linear-gradient(to right, #818cf8, #c084fc, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .btn-glow { background: linear-gradient(135deg, #6366f1, #8b5cf6); transition: all 0.2s; }
        .btn-glow:active { transform: scale(0.95); box-shadow: 0 0 15px rgba(99, 102, 241, 0.6); }
        .bottom-nav { background: rgba(9, 9, 11, 0.9); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-top: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: max(0.5rem, env(safe-area-inset-bottom)); }
        .top-header { padding-top: max(0.75rem, env(safe-area-inset-top)); background: rgba(9, 9, 11, 0.8); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
        .toast-enter { transform: translateY(100%); opacity: 0; }
        .toast-enter-active { transform: translateY(0); opacity: 1; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .toast-leave { transform: translateY(0); opacity: 1; }
        .toast-leave-active { transform: translateY(100%); opacity: 0; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
    </style>
</head>
<body class="h-screen flex flex-col overflow-hidden" x-data="appData()" x-cloak>

    <div class="fixed bottom-24 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2 w-[90%] max-w-sm pointer-events-none">
        <template x-for="toast in toasts" :key="toast.id">
            <div x-show="toast.show" x-transition:enter="toast-enter" x-transition:enter-start="toast-enter" x-transition:enter-end="toast-enter-active" x-transition:leave="toast-leave" x-transition:leave-start="toast-leave" x-transition:leave-end="toast-leave-active" class="g-box p-4 rounded-2xl flex items-center gap-3 shadow-2xl pointer-events-auto border-l-4" :class="toast.type === 'success' ? 'border-emerald-500' : 'border-red-500'">
                <i class="fas" :class="toast.type === 'success' ? 'fa-check-circle text-emerald-400' : 'fa-times-circle text-red-400'"></i>
                <p class="text-sm font-medium text-white flex-1" x-text="toast.msg"></p>
            </div>
        </template>
    </div>

    <div x-show="loading" class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#09090b]">
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-3xl shadow-lg shadow-indigo-500/30 animate-pulse mb-4">🧠</div>
        <p class="text-slate-400 font-medium animate-pulse">Loading App...</p>
    </div>

    <div x-show="!loading && !isLoggedIn" class="fixed inset-0 z-40 flex flex-col items-center justify-center p-6 bg-[#09090b]">
        <div class="text-center w-full max-w-sm">
            <div class="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-4xl shadow-2xl shadow-indigo-500/30 mx-auto mb-6"></div>
            <h1 class="text-3xl font-bold text-white mb-2">Mature Bot</h1>
            <p class="text-slate-400 mb-8">The Ultimate Discord Platform</p>
            <a href="/login" class="btn-glow w-full py-4 rounded-2xl text-white font-bold flex items-center justify-center gap-3 shadow-lg shadow-indigo-500/20">
                <i class="fab fa-discord text-2xl"></i> Login with Discord
            </a>
        </div>
    </div>

    <div x-show="!loading && isLoggedIn" class="flex-1 flex flex-col h-full relative overflow-hidden">
        <header class="top-header px-4 py-3 flex items-center justify-between z-20 border-b border-white/5">
            <div x-show="selectedGuild" class="flex items-center gap-3" x-transition>
                <img :src="selectedGuild.icon || 'https://cdn.discordapp.com/embed/avatars/0.png'" class="w-9 h-9 rounded-xl object-cover border border-white/10">
                <div class="text-left">
                    <p class="font-bold text-white text-sm truncate max-w-[150px]" x-text="selectedGuild.name"></p>
                    <p class="text-[10px] text-emerald-400 font-medium">● Online</p>
                </div>
            </div>
            <div x-show="!selectedGuild" class="flex items-center gap-3">
                <img :src="userAvatar" class="w-9 h-9 rounded-full border border-indigo-500">
                <p class="font-bold text-white text-sm" x-text="user.global_name || user.username"></p>
            </div>
            <a href="/logout" class="text-slate-400 hover:text-red-400 p-2 transition-colors"><i class="fas fa-sign-out-alt text-lg"></i></a>
        </header>

        <main class="flex-1 overflow-y-auto no-scrollbar p-4 pb-28" style="-webkit-overflow-scrolling: touch;">
            <div x-show="activeTab === 'home'" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 translate-y-4" x-transition:enter-end="opacity-100 translate-y-0" class="space-y-6">
                <div x-show="!selectedGuild">
                    <h2 class="text-xl font-bold text-white mb-4">Select a Server</h2>
                    <div class="space-y-3">
                        <template x-for="g in guilds">
                            <button @click="selectGuild(g)" class="g-box p-4 flex items-center gap-4 text-left w-full border border-white/5">
                                <img :src="g.icon || 'https://cdn.discordapp.com/embed/avatars/0.png'" class="w-12 h-12 rounded-xl object-cover">
                                <div class="flex-1 min-w-0">
                                    <p class="font-bold text-white truncate" x-text="g.name"></p>
                                    <p class="text-xs text-slate-400" x-text="g.members + ' Members'"></p>
                                </div>
                                <i class="fas fa-chevron-right text-slate-600"></i>
                            </button>
                        </template>
                    </div>
                </div>

                <div x-show="selectedGuild" class="space-y-6">
                    <div class="g-box grad-setup p-5 relative overflow-hidden">
                        <div class="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 rounded-full blur-2xl -mr-10 -mt-10"></div>
                        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 relative z-10">
                            <div class="flex items-center gap-3">
                                <div class="w-12 h-12 rounded-2xl bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-xl"><i class="fas fa-bolt"></i></div>
                                <div>
                                    <h3 class="text-lg font-bold text-white">1-Click Setup</h3>
                                    <p class="text-slate-400 text-xs">Auto-create channels & roles</p>
                                </div>
                            </div>
                            <button @click="runSetup()" class="btn-glow px-6 py-2.5 rounded-xl text-white font-bold text-sm flex items-center gap-2 whitespace-nowrap">
                                <i class="fas fa-magic"></i> Setup Now
                            </button>
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-3">
                        <div class="g-box p-4 border-l-4 border-l-indigo-500">
                            <i class="fas fa-users text-indigo-400 text-xl mb-2"></i>
                            <p class="text-2xl font-bold text-white" x-text="selectedGuild.members"></p>
                            <p class="text-xs text-slate-400">Members</p>
                        </div>
                        <div class="g-box p-4 border-l-4 border-l-purple-500">
                            <i class="fas fa-crown text-purple-400 text-xl mb-2"></i>
                            <p class="text-2xl font-bold text-white" x-text="userPremium.active ? 'Active' : 'Free'"></p>
                            <p class="text-xs text-slate-400">Premium</p>
                        </div>
                    </div>

                    <div class="grid grid-cols-3 gap-3">
                        <button @click="runCommand('!play')" class="g-box p-4 flex flex-col items-center gap-2 border-t-4 border-t-cyan-500">
                            <i class="fas fa-music text-cyan-400 text-xl"></i><span class="text-xs font-medium text-white">Music</span>
                        </button>
                        <button @click="runCommand('!balance')" class="g-box p-4 flex flex-col items-center gap-2 border-t-4 border-t-emerald-500">
                            <i class="fas fa-coins text-emerald-400 text-xl"></i><span class="text-xs font-medium text-white">Economy</span>
                        </button>
                        <button @click="runCommand('!ban')" class="g-box p-4 flex flex-col items-center gap-2 border-t-4 border-t-red-500">
                            <i class="fas fa-gavel text-red-400 text-xl"></i><span class="text-xs font-medium text-white">Mod</span>
                        </button>
                    </div>
                </div>
            </div>

            <div x-show="activeTab === 'premium'" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 translate-y-4" x-transition:enter-end="opacity-100 translate-y-0" class="space-y-6">
                <div class="text-center mb-6">
                    <h2 class="text-2xl font-bold text-white mb-1">Unlock <span class="text-grad">Premium</span></h2>
                    <p class="text-slate-400 text-sm">Get the ultimate power for your server.</p>
                </div>
                <div class="space-y-4">
                    <div class="g-box p-5 border border-amber-500/30">
                        <div class="flex justify-between items-center mb-2"><h3 class="text-lg font-bold text-amber-400">🥇 Gold</h3><p class="text-xl font-bold text-white">₹125<span class="text-xs text-slate-400">/mo</span></p></div>
                        <p class="text-sm text-slate-400 mb-3">No-prefix mode, +10% drop rates.</p>
                        <button class="w-full py-2.5 rounded-xl bg-amber-500/20 text-amber-400 font-bold text-sm border border-amber-500/30 active:scale-95 transition-transform">Purchase</button>
                    </div>
                    <div class="g-box p-5 border-2 border-indigo-500 relative">
                        <div class="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-indigo-500 text-white text-[10px] font-bold px-3 py-0.5 rounded-full">POPULAR</div>
                        <div class="flex justify-between items-center mb-2"><h3 class="text-lg font-bold text-indigo-400">💎 Platinum</h3><p class="text-xl font-bold text-white">₹249<span class="text-xs text-slate-400">/mo</span></p></div>
                        <p class="text-sm text-slate-400 mb-3">Server-wide no-prefix, +25% drops.</p>
                        <button class="w-full py-2.5 rounded-xl btn-glow text-white font-bold text-sm active:scale-95 transition-transform">Purchase Now</button>
                    </div>
                    <div class="g-box p-5 border border-purple-500/30">
                        <div class="flex justify-between items-center mb-2"><h3 class="text-lg font-bold text-purple-400">👑 Ultimate</h3><p class="text-xl font-bold text-white">₹499<span class="text-xs text-slate-400">/mo</span></p></div>
                        <p class="text-sm text-slate-400 mb-3">Unlimited auto-hunt, VIP badge.</p>
                        <button class="w-full py-2.5 rounded-xl bg-purple-500/20 text-purple-400 font-bold text-sm border border-purple-500/30 active:scale-95 transition-transform">Purchase</button>
                    </div>
                </div>
            </div>

            <div x-show="activeTab === 'settings'" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 translate-y-4" x-transition:enter-end="opacity-100 translate-y-0" class="space-y-6">
                <h2 class="text-xl font-bold text-white mb-4">Settings</h2>
                <div class="g-box p-4 flex items-center justify-between active:scale-98 transition-transform">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400"><i class="fas fa-bell"></i></div>
                        <div><p class="font-medium text-white">Notifications</p><p class="text-xs text-slate-400">Manage alerts</p></div>
                    </div>
                    <i class="fas fa-chevron-right text-slate-600"></i>
                </div>
                <div class="g-box p-4 flex items-center justify-between active:scale-98 transition-transform">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400"><i class="fas fa-shield-alt"></i></div>
                        <div><p class="font-medium text-white">Privacy & Security</p><p class="text-xs text-slate-400">Data & permissions</p></div>
                    </div>
                    <i class="fas fa-chevron-right text-slate-600"></i>
                </div>
            </div>
        </main>

        <nav class="bottom-nav fixed bottom-0 left-0 right-0 z-50">
            <div class="flex justify-around items-center h-16">
                <button @click="activeTab = 'home'" class="flex flex-col items-center justify-center w-full h-full space-y-1 active:scale-90 transition-transform" :class="activeTab === 'home' ? 'text-indigo-400' : 'text-slate-500'">
                    <i class="fas fa-home text-xl" :class="activeTab === 'home' ? 'drop-shadow-[0_0_8px_rgba(99,102,241,0.8)]' : ''"></i>
                    <span class="text-[10px] font-medium">Home</span>
                </button>
                <button @click="activeTab = 'premium'" class="flex flex-col items-center justify-center w-full h-full space-y-1 active:scale-90 transition-transform" :class="activeTab === 'premium' ? 'text-indigo-400' : 'text-slate-500'">
                    <i class="fas fa-crown text-xl" :class="activeTab === 'premium' ? 'drop-shadow-[0_0_8px_rgba(99,102,241,0.8)]' : ''"></i>
                    <span class="text-[10px] font-medium">Premium</span>
                </button>
                <button @click="activeTab = 'settings'" class="flex flex-col items-center justify-center w-full h-full space-y-1 active:scale-90 transition-transform" :class="activeTab === 'settings' ? 'text-indigo-400' : 'text-slate-500'">
                    <i class="fas fa-cog text-xl" :class="activeTab === 'settings' ? 'drop-shadow-[0_0_8px_rgba(99,102,241,0.8)]' : ''"></i>
                    <span class="text-[10px] font-medium">Settings</span>
                </button>
            </div>
        </nav>
    </div>

    <script>
        function appData() {
            return {
                loading: true, isLoggedIn: false, user: null, guilds: [], selectedGuild: null,
                activeTab: 'home', userPremium: {active: false}, toasts: [],
                get userAvatar() { 
                    if (!this.user) return 'https://cdn.discordapp.com/embed/avatars/0.png';
                    const ext = this.user.avatar && this.user.avatar.startsWith('a_') ? 'gif' : 'png';
                    return `https://cdn.discordapp.com/avatars/${this.user.id}/${this.user.avatar}.${ext}`; 
                },
                showToast(msg, type = 'success') {
                    const id = Date.now();
                    this.toasts.push({ id, msg, type, show: true });
                    setTimeout(() => {
                        const t = this.toasts.find(x => x.id === id);
                        if (t) t.show = false;
                        setTimeout(() => this.toasts = this.toasts.filter(x => x.id !== id), 300);
                    }, 3000);
                },
                async init() {
                    try {
                        const res = await fetch('/api/user'); 
                        if(res.ok) { 
                            this.user = await res.json(); 
                            this.isLoggedIn = true; 
                            const gRes = await fetch('/api/guilds');
                            if(gRes.ok) this.guilds = await gRes.json();
                            if(this.guilds.length === 1) this.selectedGuild = this.guilds[0];
                        }
                    } catch(e) { this.showToast('Failed to load session', 'error'); } 
                    this.loading = false;
                },
                selectGuild(g) { this.selectedGuild = g; this.showToast(`Loaded ${g.name}`); },
                runSetup() { this.showToast('⚡ 1-Click Setup initiated!'); },
                runCommand(cmd) { this.showToast(`Executing ${cmd}...`); }
            }
        }
    </script>
</body>
</html>
"""

@app.route('/login')
def login(): return redirect(f"{DISCORD_API}/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return "Error", 400
    r = requests.post(f"{DISCORD_API}/oauth2/token", data={'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI}, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if r.status_code != 200: return f"Error: {r.text}", 500
    tokens = r.json()
    h = {'Authorization': f'Bearer {tokens["access_token"]}'}
    user = requests.get(f"{DISCORD_API}/users/@me", headers=h).json()
    guilds_req = requests.get(f"{DISCORD_API}/users/@me/guilds", headers=h).json()
    bot_guilds = {str(g.id) for g in bot_instance.guilds}
    valid = []
    for g in guilds_req:
        if g['id'] in bot_guilds:
            perms = int(g.get('permissions', 0))
            if is_developer(user['id']) or (perms & 0x8) or (perms & 0x20):
                valid.append({'id': g['id'], 'name': g['name'], 'icon': f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get('icon') else None, 'members': 0})
    session['user'] = user; session['guilds'] = valid; session['access_token'] = tokens['access_token']
    return redirect('/')

@app.route('/api/user')
def api_user(): 
    if 'user' in session: return jsonify(session['user'])
    return jsonify({}), 401

@app.route('/api/guilds')
def api_guilds():
    if 'guilds' not in session: return jsonify([]), 401
    for g in session['guilds']:
        obj = bot_instance.get_guild(int(g['id']))
        if obj: g['members'] = obj.member_count
    return jsonify(session['guilds'])

@app.route('/', methods=['GET'])
def index(): return DASHBOARD_TEMPLATE

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

def run_dashboard(): app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)), threaded=True)
def set_bot_instance(bot): 
    global bot_instance; bot_instance=bot
