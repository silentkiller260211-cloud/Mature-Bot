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

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#0f0f23">
    <link rel="manifest" href="/manifest.json">
    <title>Mature Bot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        [x-cloak] { display: none !important; }
        body { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #0f0f23 0%, #1e1b4b 50%, #312e81 100%); color: #e2e8f0; min-height: 100vh; -webkit-tap-highlight-color: transparent; }
        .glass { background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px; }
        .gradient-text { background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .btn-primary { background: linear-gradient(135deg, #6366f1, #8b5cf6, #a855f7); transition: all 0.3s; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(99, 102, 241, 0.5); }
        .btn-primary:active { transform: scale(0.95); }
        .category-menu { position: fixed; top: 0; left: -340px; width: 340px; height: 100vh; background: linear-gradient(180deg, rgba(15, 15, 35, 0.98), rgba(30, 27, 75, 0.98)); backdrop-filter: blur(20px); z-index: 100; transition: left 0.3s ease; overflow-y: auto; box-shadow: 10px 0 40px rgba(0, 0, 0, 0.5); }
        .category-menu.open { left: 0; }
        .category-header { padding: 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); display: flex; align-items: center; justify-content: space-between; }
        .category-item { margin: 8px 12px; border-radius: 16px; overflow: hidden; transition: all 0.3s ease; border: 1px solid rgba(255, 255, 255, 0.05); }
        .category-item-header { padding: 14px 16px; cursor: pointer; display: flex; align-items: center; gap: 12px; transition: all 0.3s ease; }
        .category-item-header:hover { background: linear-gradient(90deg, rgba(99, 102, 241, 0.2), transparent); }
        .category-item.active .category-item-header { background: linear-gradient(90deg, rgba(99, 102, 241, 0.3), rgba(168, 85, 247, 0.2)); border-left: 3px solid #6366f1; }
        .category-icon { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
        .category-name { flex: 1; font-weight: 600; font-size: 15px; }
        .category-arrow { transition: transform 0.3s ease; font-size: 12px; }
        .category-arrow.rotate { transform: rotate(180deg); }
        .submenu { padding: 0 12px 12px 12px; background: rgba(0, 0, 0, 0.2); }
        .submenu-item { padding: 12px 16px; margin: 4px 0; border-radius: 12px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; display: flex; align-items: center; justify-content: space-between; border: 1px solid transparent; }
        .submenu-item:hover { background: rgba(99, 102, 241, 0.15); border-color: rgba(99, 102, 241, 0.3); transform: translateX(4px); }
        .submenu-item-content { display: flex; align-items: center; gap: 10px; }
        .submenu-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
        .server-selector { background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 8px 12px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.3s; }
        .server-selector:hover { border-color: rgba(99, 102, 241, 0.5); background: rgba(30, 41, 59, 0.95); }
        .account-dropdown { position: relative; }
        .account-menu { 
            position: absolute; 
            top: 100%; 
            right: 0; 
            margin-top: 8px; 
            background: rgba(30, 41, 59, 0.98); 
            border: 1px solid rgba(255, 255, 255, 0.1); 
            border-radius: 12px; 
            padding: 8px; 
            min-width: 200px; 
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5); 
            z-index: 1000;
        }
        .account-menu-item { padding: 10px 12px; border-radius: 8px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 10px; width: 100%; text-align: left; background: none; border: none; color: inherit; font-size: 14px; }
        .account-menu-item:hover { background: rgba(99, 102, 241, 0.2); }
        .toggle-switch { width: 48px; height: 24px; background: #374151; border-radius: 12px; cursor: pointer; position: relative; transition: background 0.3s; }
        .toggle-switch.active { background: linear-gradient(135deg, #10b981, #059669); }
        .toggle-switch::after { content: ''; position: absolute; top: 2px; left: 2px; width: 20px; height: 20px; background: white; border-radius: 50%; transition: transform 0.3s; }
        .toggle-switch.active::after { transform: translateX(24px); }
        .overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px); z-index: 99; opacity: 0; pointer-events: none; transition: opacity 0.3s; }
        .overlay.show { opacity: 1; pointer-events: auto; }
        .bottom-nav { background: linear-gradient(180deg, rgba(15, 15, 35, 0.95), rgba(30, 27, 75, 0.95)); backdrop-filter: blur(20px); border-top: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: max(0.5rem, env(safe-area-inset-bottom)); }
        .top-header { padding-top: max(0.75rem, env(safe-area-inset-top)); background: linear-gradient(180deg, rgba(15, 15, 35, 0.9), rgba(30, 27, 75, 0.8)); backdrop-filter: blur(12px); }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .config-card { background: linear-gradient(135deg, rgba(30, 41, 59, 0.5), rgba(15, 23, 42, 0.5)); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 16px; margin-bottom: 12px; }
        .status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .status-online { background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2)); color: #10b981; }
        .payment-card { background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1)); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 16px; padding: 20px; cursor: pointer; transition: all 0.3s; }
        .payment-card:hover { transform: translateY(-2px); border-color: rgba(99, 102, 241, 0.6); box-shadow: 0 10px 30px rgba(99, 102, 241, 0.3); }
        .duration-btn { padding: 8px 16px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(255, 255, 255, 0.05); color: #94a3b8; cursor: pointer; transition: all 0.2s; font-size: 13px; }
        .duration-btn.active { background: linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(168, 85, 247, 0.2)); border-color: rgba(99, 102, 241, 0.6); color: white; }
        .premium-gradient { background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899); }
    </style>
</head>
<body class="h-screen flex flex-col overflow-hidden" x-data="appData()" x-cloak>

    <div class="overlay" :class="showMenu ? 'show' : ''" @click="showMenu = false"></div>
    <div class="overlay" :class="showPayment ? 'show' : ''" @click="showPayment = false"></div>

    <div class="category-menu" :class="showMenu ? 'open' : ''">
        <div class="category-header">
            <h2 class="text-xl font-bold text-white">Categories</h2>
            <button @click="showMenu = false" class="text-slate-400 hover:text-white"><i class="fas fa-times text-xl"></i></button>
        </div>
        <div class="p-4 space-y-2">
            <template x-for="cat in categories" :key="cat.id">
                <div>
                    <div class="category-item" :class="activeCategory === cat.id ? 'active' : ''">
                        <div class="category-item-header" @click="toggleCategory(cat.id)">
                            <div class="category-icon" :class="cat.bgColor">
                                <i :class="cat.icon" :class="cat.color"></i>
                            </div>
                            <span class="category-name" x-text="cat.name"></span>
                            <i class="fas fa-chevron-down category-arrow" :class="expandedCategory === cat.id ? 'rotate' : ''"></i>
                        </div>
                        <div x-show="expandedCategory === cat.id" class="submenu" x-transition>
                            <template x-for="cmd in cat.commands" :key="cmd.name">
                                <div class="submenu-item" @click="executeCommand(cmd.name)">
                                    <div class="submenu-item-content">
                                        <div class="submenu-icon" :class="cmd.bgColor">
                                            <i :class="cmd.icon" :class="cmd.color"></i>
                                        </div>
                                        <span x-text="cmd.label"></span>
                                    </div>
                                    <i class="fas fa-chevron-right text-xs text-slate-600"></i>
                                </div>
                            </template>
                        </div>
                    </div>
                </div>
            </template>
        </div>
    </div>

    <div x-show="showPayment" class="fixed inset-0 z-[120] flex items-center justify-center p-4" @click.self="showPayment = false">
        <div class="glass p-6 rounded-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-6">
                <h3 class="text-2xl font-bold gradient-text">Complete Payment</h3>
                <button @click="showPayment = false" class="text-slate-400 hover:text-white text-xl"><i class="fas fa-times"></i></button>
            </div>
            
            <div class="mb-6 p-4 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30">
                <p class="text-sm text-slate-300 mb-2">Selected Plan:</p>
                <p class="text-2xl font-bold text-white" x-text="selectedPlan.name + ' ' + selectedPlan.durationLabel"></p>
                <p class="text-xs text-slate-400" x-text="'₹' + selectedPlan.price"></p>
            </div>

            <div class="mb-6 text-center">
                <p class="text-sm text-slate-300 mb-4">Scan QR Code to Pay</p>
                <div class="bg-white p-4 rounded-xl inline-block">
                    <img :src="'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(selectedPlan.link)" alt="Payment QR Code" class="w-48 h-48">
                </div>
                <p class="text-xs text-slate-400 mt-3">Or use the payment link below</p>
            </div>

            <a :href="selectedPlan.link" target="_blank" class="btn-primary w-full py-4 rounded-xl text-white font-bold text-center flex items-center justify-center gap-3 mb-4">
                <i class="fas fa-external-link-alt"></i>
                <span>Open Payment Page</span>
            </a>

            <div class="p-4 rounded-xl bg-slate-800/50 border border-slate-700">
                <p class="text-xs text-slate-400 mb-2"><i class="fas fa-info-circle mr-1"></i> Payment Steps:</p>
                <ol class="text-xs text-slate-300 space-y-1 ml-4">
                    <li>1. Scan QR code or click payment link</li>
                    <li>2. Complete payment via UPI/Card</li>
                    <li>3. Send screenshot to support</li>
                    <li>4. You'll receive premium code via DM</li>
                    <li>5. Use <code class="bg-slate-700 px-1 rounded">!premium</code> to activate</li>
                </ol>
            </div>
        </div>
    </div>

    <div class="fixed bottom-24 left-1/2 -translate-x-1/2 z-[110] flex flex-col gap-2 w-[90%] max-w-sm pointer-events-none">
        <template x-for="toast in toasts" :key="toast.id">
            <div x-show="toast.show" x-transition class="glass p-4 rounded-2xl flex items-center gap-3 shadow-2xl pointer-events-auto border-l-4" :class="toast.type === 'success' ? 'border-emerald-500' : 'border-red-500'">
                <i class="fas" :class="toast.type === 'success' ? 'fa-check-circle text-emerald-400' : 'fa-times-circle text-red-400'"></i>
                <p class="text-sm font-medium text-white flex-1" x-text="toast.msg"></p>
            </div>
        </template>
    </div>

    <div x-show="loading" class="fixed inset-0 z-50 flex flex-col items-center justify-center">
        <div class="w-20 h-20 rounded-3xl premium-gradient flex items-center justify-center text-4xl shadow-2xl mb-4 animate-pulse">🧠</div>
        <p class="text-slate-400 font-medium">Loading Mature Bot...</p>
    </div>

    <div x-show="!loading && !isLoggedIn" class="fixed inset-0 z-40 flex flex-col items-center justify-center p-6">
        <div class="text-center w-full max-w-md">
            <div class="w-24 h-24 rounded-3xl premium-gradient flex items-center justify-center text-5xl shadow-2xl mx-auto mb-6">🧠</div>
            <h1 class="text-4xl font-bold gradient-text mb-3">Mature Bot</h1>
            <p class="text-slate-400 mb-8">The Ultimate Discord Management Platform</p>
            
            <div class="space-y-3">
                <a href="/login" class="btn-primary w-full py-4 rounded-2xl text-white font-bold flex items-center justify-center gap-3 shadow-lg">
                    <i class="fab fa-discord text-2xl"></i> Login with Discord
                </a>
                
                <a :href="inviteUrl" target="_blank" class="glass w-full py-4 rounded-2xl text-indigo-400 font-bold flex items-center justify-center gap-3 hover:bg-indigo-500/10 transition-all">
                    <i class="fas fa-plus text-2xl"></i>
                    <span>Invite Me to Your Server</span>
                </a>
            </div>
        </div>
    </div>

    <div x-show="!loading && isLoggedIn" class="flex-1 flex flex-col h-full relative overflow-hidden">
        <header class="top-header px-4 py-3 flex items-center justify-between z-20 border-b border-white/10">
            <div class="flex items-center gap-3">
                <button @click="showMenu = true" class="p-2 rounded-xl hover:bg-white/10 transition-colors"><i class="fas fa-bars text-xl text-white"></i></button>
                
                <div class="account-dropdown" x-data="{ open: false }">
                    <button @click="open = !open" @click.away="open = false" class="server-selector">
                        <img :src="selectedGuild?.icon || 'https://cdn.discordapp.com/embed/avatars/0.png'" class="w-8 h-8 rounded-lg object-cover">
                        <span class="text-sm font-medium text-white truncate max-w-[150px]" x-text="selectedGuild?.name || 'Select Server'"></span>
                        <i class="fas fa-chevron-down text-xs text-slate-400"></i>
                    </button>
                    <div x-show="open" 
                         x-transition:enter="transition ease-out duration-200"
                         x-transition:enter-start="opacity-0 translate-y-2"
                         x-transition:enter-end="opacity-100 translate-y-0"
                         x-transition:leave="transition ease-in duration-150"
                         x-transition:leave-start="opacity-100 translate-y-0"
                         x-transition:leave-end="opacity-0 translate-y-2"
                         class="account-menu"
                         @click.away="open = false">
                        <template x-for="g in guilds" :key="g.id">
                            <button @click="selectGuild(g); open = false" class="account-menu-item">
                                <img :src="g.icon || 'https://cdn.discordapp.com/embed/avatars/0.png'" class="w-8 h-8 rounded-lg object-cover">
                                <div class="flex-1 min-w-0">
                                    <p class="text-sm font-medium text-white truncate" x-text="g.name"></p>
                                    <p class="text-xs text-slate-400" x-text="g.members + ' members'"></p>
                                </div>
                                <i class="fas fa-check text-emerald-400" x-show="selectedGuild?.id === g.id"></i>
                            </button>
                        </template>
                    </div>
                </div>
            </div>
            
            <div class="flex items-center gap-2">
                <a :href="inviteUrl" target="_blank" class="glass px-4 py-2 rounded-xl text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 transition-all text-sm font-medium flex items-center gap-2">
                    <i class="fas fa-plus"></i>
                    <span class="hidden md:inline">Invite</span>
                </a>
                
                <div class="account-dropdown" x-data="{ open: false }">
                    <button @click="open = !open" @click.away="open = false" class="flex items-center gap-2 p-1 rounded-xl hover:bg-white/10 transition-all">
                        <img :src="userAvatar" class="w-8 h-8 rounded-full border-2 border-indigo-500">
                        <i class="fas fa-chevron-down text-xs text-slate-400"></i>
                    </button>
                    <div x-show="open" 
                         x-transition:enter="transition ease-out duration-200"
                         x-transition:enter-start="opacity-0 translate-y-2"
                         x-transition:enter-end="opacity-100 translate-y-0"
                         x-transition:leave="transition ease-in duration-150"
                         x-transition:leave-start="opacity-100 translate-y-0"
                         x-transition:leave-end="opacity-0 translate-y-2"
                         class="account-menu"
                         @click.away="open = false">
                        <div class="px-4 py-3 border-b border-white/10 mb-2">
                            <p class="text-sm font-bold text-white" x-text="user.global_name || user.username"></p>
                            <p class="text-xs text-slate-400" x-text="'#' + user.discriminator"></p>
                        </div>
                        <button @click="open = false; activePanel = 'premium'" class="account-menu-item">
                            <i class="fas fa-crown text-yellow-400"></i>
                            <span class="text-sm text-white">Premium Plans</span>
                        </button>
                        <a href="/logout" class="account-menu-item text-red-400 hover:bg-red-500/10">
                            <i class="fas fa-sign-out-alt"></i>
                            <span class="text-sm">Logout</span>
                        </a>
                    </div>
                </div>
            </div>
        </header>

        <main class="flex-1 overflow-y-auto no-scrollbar p-4 pb-28" style="-webkit-overflow-scrolling: touch;">
            
            <div x-show="activePanel === 'home' && selectedGuild" class="space-y-6">
                <div class="glass p-5 bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border-emerald-500/30">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-3">
                            <div class="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-xl"><i class="fas fa-bolt"></i></div>
                            <div>
                                <h3 class="text-lg font-bold text-white">1-Click Setup</h3>
                                <p class="text-xs text-slate-400">Auto-configure your server</p>
                            </div>
                        </div>
                        <button @click="runSetup()" class="btn-primary px-5 py-2.5 rounded-xl text-white font-bold text-sm">Setup Now</button>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div class="glass p-4 border-l-4 border-l-indigo-500">
                        <i class="fas fa-users text-indigo-400 text-xl mb-2"></i>
                        <p class="text-2xl font-bold text-white" x-text="selectedGuild.members"></p>
                        <p class="text-xs text-slate-400">Members</p>
                    </div>
                    <div class="glass p-4 border-l-4 border-l-purple-500">
                        <i class="fas fa-shield-alt text-purple-400 text-xl mb-2"></i>
                        <p class="text-2xl font-bold text-white">Active</p>
                        <p class="text-xs text-slate-400">Protection</p>
                    </div>
                </div>
                <div>
                    <h3 class="text-lg font-bold text-white mb-3">Quick Actions</h3>
                    <div class="grid grid-cols-2 gap-3">
                        <button @click="activePanel = 'antinuke'" class="glass p-4 flex flex-col items-center gap-2 border-t-4 border-t-amber-500">
                            <i class="fas fa-shield-alt text-amber-400 text-2xl"></i><span class="text-sm font-medium text-white">Antinuke</span>
                        </button>
                        <button @click="executeCommand('ban')" class="glass p-4 flex flex-col items-center gap-2 border-t-4 border-t-red-500">
                            <i class="fas fa-gavel text-red-400 text-2xl"></i><span class="text-sm font-medium text-white">Moderation</span>
                        </button>
                        <button @click="executeCommand('balance')" class="glass p-4 flex flex-col items-center gap-2 border-t-4 border-t-emerald-500">
                            <i class="fas fa-coins text-emerald-400 text-2xl"></i><span class="text-sm font-medium text-white">Economy</span>
                        </button>
                        <button @click="open = false; activePanel = 'premium'" class="glass p-4 flex flex-col items-center gap-2 border-t-4 border-t-purple-500">
                            <i class="fas fa-crown text-purple-400 text-2xl"></i><span class="text-sm font-medium text-white">Premium</span>
                        </button>
                    </div>
                </div>
            </div>

            <div x-show="activePanel === 'antinuke'" class="space-y-6">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-2xl font-bold text-white">🛡️ Antinuke System</h2>
                    <button @click="activePanel = 'home'" class="text-slate-400 hover:text-white"><i class="fas fa-arrow-left mr-2"></i>Back</button>
                </div>
                <div class="glass p-5 bg-gradient-to-br from-amber-500/10 to-orange-500/10 border-amber-500/30 mb-6">
                    <p class="text-sm text-slate-300">Protect your server from malicious users and unauthorized actions</p>
                </div>
                <div class="space-y-4">
                    <template x-for="setting in antinukeSettings" :key="setting.id">
                        <div class="config-card flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-xl flex items-center justify-center" :class="setting.bgColor"><i :class="setting.icon" :class="setting.color"></i></div>
                                <div>
                                    <p class="font-medium text-white" x-text="setting.name"></p>
                                    <p class="text-xs text-slate-400" x-text="setting.description"></p>
                                </div>
                            </div>
                            <div class="toggle-switch" :class="setting.enabled ? 'active' : ''" @click="toggleAntinuke(setting.id)"></div>
                        </div>
                    </template>
                </div>
                <div class="glass p-5 mt-6">
                    <h3 class="font-bold text-white mb-3">👥 Whitelisted Users</h3>
                    <p class="text-sm text-slate-400 mb-4">These users can use commands without prefix</p>
                    <div class="space-y-2">
                        <template x-for="user in whitelistUsers" :key="user.id">
                            <div class="flex items-center justify-between p-3 rounded-xl bg-slate-800/50">
                                <div class="flex items-center gap-3">
                                    <img :src="user.avatar" class="w-8 h-8 rounded-full">
                                    <div>
                                        <p class="text-sm font-medium text-white" x-text="user.name"></p>
                                        <p class="text-xs text-slate-500" x-text="'ID: ' + user.id"></p>
                                    </div>
                                </div>
                                <button @click="removeFromWhitelist(user.id)" class="text-red-400 hover:text-red-300 p-2"><i class="fas fa-trash"></i></button>
                            </div>
                        </template>
                        <div x-show="whitelistUsers.length === 0" class="text-center py-4 text-slate-500">No whitelisted users</div>
                    </div>
                    <div class="mt-4 p-3 rounded-xl bg-slate-800/50">
                        <p class="text-xs text-slate-400 mb-2">Add user by ID:</p>
                        <div class="flex gap-2">
                            <input type="text" x-model="newWhitelistId" placeholder="User ID" class="flex-1 bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-sm text-white">
                            <button @click="addToWhitelist()" class="btn-primary px-4 py-2 rounded-lg text-white text-sm font-medium">Add</button>
                        </div>
                    </div>
                </div>
            </div>

            <div x-show="activePanel === 'premium'" class="space-y-6 pb-28">
                <div class="text-center mb-6">
                    <h2 class="text-3xl font-bold gradient-text mb-2">Premium Plans</h2>
                    <p class="text-slate-400 text-sm">Choose the perfect plan for your server</p>
                </div>
                
                <div class="glass p-6 border-2 border-slate-400/30">
                    <div class="flex items-center gap-3 mb-4">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-slate-400 to-slate-600 flex items-center justify-center text-2xl">🥈</div>
                        <div>
                            <h3 class="text-2xl font-bold text-slate-300">Silver</h3>
                            <p class="text-xs text-slate-400">Perfect for small servers</p>
                        </div>
                    </div>
                    <ul class="text-sm text-slate-300 space-y-2 mb-6">
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>No-prefix mode</li>
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>+10% drop rates</li>
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>Priority support</li>
                    </ul>
                    <div class="grid grid-cols-2 gap-3 mb-6">
                        <template x-for="(plan, duration) in pricing.silver" :key="duration">
                            <button 
                                @click="selectPlan('silver', duration)"
                                class="duration-btn w-full"
                                :class="selectedPlan.tier === 'silver' && selectedPlan.duration === duration ? 'active' : ''"
                            >
                                <div x-text="plan.label"></div>
                                <div class="text-xs font-bold" x-text="'₹' + plan.price"></div>
                            </button>
                        </template>
                    </div>
                    <button @click="openPayment('silver')" class="w-full py-3 rounded-xl bg-gradient-to-r from-slate-500/20 to-slate-600/20 text-slate-300 font-bold border border-slate-400/30 hover:from-slate-500/30 hover:to-slate-600/30 transition-all">Purchase Now</button>
                </div>

                <div class="glass p-6 border-2 border-yellow-500/50 relative">
                    <div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-yellow-500 to-amber-500 text-white text-xs font-bold px-4 py-1 rounded-full">POPULAR</div>
                    <div class="flex items-center gap-3 mb-4">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-yellow-400 to-amber-600 flex items-center justify-center text-2xl">🥇</div>
                        <div>
                            <h3 class="text-2xl font-bold text-yellow-400">Gold</h3>
                            <p class="text-xs text-slate-400">Best for growing servers</p>
                        </div>
                    </div>
                    <ul class="text-sm text-slate-300 space-y-2 mb-6">
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>All Silver features</li>
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>Server-wide no-prefix</li>
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>+25% drop rates</li>
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>Custom commands</li>
                    </ul>
                    <div class="grid grid-cols-2 gap-3 mb-6">
                        <template x-for="(plan, duration) in pricing.gold" :key="duration">
                            <button 
                                @click="selectPlan('gold', duration)"
                                class="duration-btn w-full"
                                :class="selectedPlan.tier === 'gold' && selectedPlan.duration === duration ? 'active' : ''"
                            >
                                <div x-text="plan.label"></div>
                                <div class="text-xs font-bold" x-text="'₹' + plan.price"></div>
                            </button>
                        </template>
                    </div>
                    <button @click="openPayment('gold')" class="w-full py-3 rounded-xl bg-gradient-to-r from-yellow-500 to-amber-600 text-white font-bold hover:shadow-lg hover:shadow-yellow-500/30 transition-all">Purchase Now</button>
                </div>

                <div class="glass p-6 border-2 border-purple-500/30">
                    <div class="flex items-center gap-3 mb-4">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-600 to-black flex items-center justify-center text-2xl">👑</div>
                        <div>
                            <h3 class="text-2xl font-bold text-purple-400">Black</h3>
                            <p class="text-xs text-slate-400">Ultimate power for large servers</p>
                        </div>
                    </div>
                    <ul class="text-sm text-slate-300 space-y-2 mb-6">
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>All Gold features</li>
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>Unlimited auto-hunt</li>
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>VIP badge</li>
                        <li class="flex items-center gap-2"><i class="fas fa-check text-emerald-400"></i>24/7 priority support</li>
                    </ul>
                    <div class="grid grid-cols-2 gap-3 mb-6">
                        <template x-for="(plan, duration) in pricing.black" :key="duration">
                            <button 
                                @click="selectPlan('black', duration)"
                                class="duration-btn w-full"
                                :class="selectedPlan.tier === 'black' && selectedPlan.duration === duration ? 'active' : ''"
                            >
                                <div x-text="plan.label"></div>
                                <div class="text-xs font-bold" x-text="'₹' + plan.price"></div>
                            </button>
                        </template>
                    </div>
                    <button @click="openPayment('black')" class="w-full py-3 rounded-xl bg-gradient-to-r from-purple-600 to-black text-white font-bold border border-purple-500/30 hover:from-purple-600/80 hover:to-black/80 transition-all">Purchase Now</button>
                </div>
            </div>
        </main>

        <nav class="bottom-nav fixed bottom-0 left-0 right-0 z-50">
            <div class="flex justify-around items-center h-16">
                <button @click="activePanel = 'home'; showMenu = false" class="flex flex-col items-center justify-center w-full h-full space-y-1" :class="activePanel === 'home' ? 'text-indigo-400' : 'text-slate-500'">
                    <i class="fas fa-home text-xl"></i><span class="text-[10px] font-medium">Home</span>
                </button>
                <button @click="activePanel = 'antinuke'" class="flex flex-col items-center justify-center w-full h-full space-y-1" :class="activePanel === 'antinuke' ? 'text-amber-400' : 'text-slate-500'">
                    <i class="fas fa-shield-alt text-xl"></i><span class="text-[10px] font-medium">Antinuke</span>
                </button>
            </div>
        </nav>
    </div>

    <script>
        function appData() {
            return {
                inviteUrl: 'https://discord.com/api/oauth2/authorize?client_id=' + '{{ CLIENT_ID }}' + '&permissions=8&scope=bot%20applications.commands',
                loading: true, isLoggedIn: false, user: null, guilds: [], selectedGuild: null,
                activePanel: 'home', showMenu: false, activeCategory: 'moderation', expandedCategory: 'moderation',
                showPayment: false,
                selectedPlan: { 
                    tier: 'silver', 
                    duration: 'monthly', 
                    name: 'Silver', 
                    durationLabel: 'Monthly', 
                    price: 125,
                    link: 'https://imjo.in/FMXmx4'
                },
                toasts: [],
                pricing: {
                    silver: {
                        monthly: { price: 125, days: 30, label: 'Monthly', link: 'https://imjo.in/FMXmx4' },
                        '3months': { price: 325, days: 90, label: '3 Months', link: 'https://imjo.in/hzyJZV' },
                        '6months': { price: 599, days: 180, label: '6 Months', link: 'https://imjo.in/py7b5W' },
                        yearly: { price: 999, days: 365, label: 'Yearly', link: 'https://imjo.in/K9JgCV' }
                    },
                    gold: {
                        monthly: { price: 249, days: 30, label: 'Monthly', link: 'https://imjo.in/Nzmnky' },
                        '3months': { price: 649, days: 90, label: '3 Months', link: 'https://imjo.in/XZZtKx' },
                        '6months': { price: 1199, days: 180, label: '6 Months', link: 'https://imjo.in/hTWGMm' },
                        yearly: { price: 1999, days: 365, label: 'Yearly', link: 'https://imjo.in/bptbjB' }
                    },
                    black: {
                        monthly: { price: 499, days: 30, label: 'Monthly', link: 'https://imjo.in/YT9Vgz' },
                        '3months': { price: 1299, days: 90, label: '3 Months', link: 'https://imjo.in/K4e44A' },
                        '6months': { price: 2399, days: 180, label: '6 Months', link: 'https://imjo.in/5qJwZp' },
                        yearly: { price: 3999, days: 365, label: 'Yearly', link: 'https://imjo.in/RdFkFq' }
                    }
                },
                antinukeSettings: [
                    { id: 'anti_ban', name: 'Anti-Ban', description: 'Prevent unauthorized bans', icon: 'fa-user-shield', color: 'text-red-400', bgColor: 'bg-red-500/20', enabled: false },
                    { id: 'anti_kick', name: 'Anti-Kick', description: 'Prevent unauthorized kicks', icon: 'fa-user-slash', color: 'text-orange-400', bgColor: 'bg-orange-500/20', enabled: false },
                    { id: 'anti_channel_delete', name: 'Anti-Channel Delete', description: 'Prevent channel deletion', icon: 'fa-trash-alt', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', enabled: false },
                    { id: 'anti_role_create', name: 'Anti-Role Create', description: 'Prevent role creation', icon: 'fa-user-tag', color: 'text-purple-400', bgColor: 'bg-purple-500/20', enabled: false },
                    { id: 'anti_bot_add', name: 'Anti-Bot Add', description: 'Prevent bot additions', icon: 'fa-robot', color: 'text-blue-400', bgColor: 'bg-blue-500/20', enabled: false }
                ],
                whitelistUsers: [], newWhitelistId: '',
                categories: [
                    { id: 'moderation', name: 'Moderation & Security', icon: 'fa-shield-alt', color: 'text-red-400', bgColor: 'bg-red-500/20', commands: [
                        { name: 'antinuke', label: 'Antinuke Panel', icon: 'fa-shield-alt', color: 'text-red-400', bgColor: 'bg-red-500/20' },
                        { name: 'antinuke_enable', label: 'Enable Antinuke', icon: 'fa-check-circle', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
                        { name: 'antinuke_disable', label: 'Disable Antinuke', icon: 'fa-times-circle', color: 'text-red-400', bgColor: 'bg-red-500/20' },
                        { name: 'ban', label: 'Ban Member', icon: 'fa-ban', color: 'text-red-400', bgColor: 'bg-red-500/20' },
                        { name: 'kick', label: 'Kick Member', icon: 'fa-user-slash', color: 'text-orange-400', bgColor: 'bg-orange-500/20' },
                        { name: 'clear', label: 'Clear Messages', icon: 'fa-trash', color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
                        { name: 'warn', label: 'Warn Member', icon: 'fa-exclamation-triangle', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' },
                        { name: 'timeout', label: 'Timeout Member', icon: 'fa-clock', color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
                        { name: 'unban', label: 'Unban User', icon: 'fa-user-check', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
                        { name: 'lock', label: 'Lock Channel', icon: 'fa-lock', color: 'text-red-400', bgColor: 'bg-red-500/20' },
                        { name: 'unlock', label: 'Unlock Channel', icon: 'fa-unlock', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' }
                    ]},
                    { id: 'logging', name: 'Logging System', icon: 'fa-clipboard-list', color: 'text-blue-400', bgColor: 'bg-blue-500/20', commands: [
                        { name: 'logging_enable', label: 'Enable Logging', icon: 'fa-check-circle', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
                        { name: 'logging_disable', label: 'Disable Logging', icon: 'fa-times-circle', color: 'text-red-400', bgColor: 'bg-red-500/20' },
                        { name: 'logging_autosetup', label: 'Auto Setup Logs', icon: 'fa-cog', color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
                        { name: 'setlogs', label: 'Set Log Channel', icon: 'fa-hashtag', color: 'text-blue-400', bgColor: 'bg-blue-500/20' }
                    ]},
                    { id: 'levelling', name: 'Levelling System', icon: 'fa-chart-line', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20', commands: [
                        { name: 'rank', label: 'Check Rank', icon: 'fa-trophy', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' },
                        { name: 'leaderboard', label: 'Leaderboard', icon: 'fa-list-ol', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
                        { name: 'leveling_channel', label: 'Set Level Channel', icon: 'fa-hashtag', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
                        { name: 'xp_add', label: 'Add XP', icon: 'fa-plus-circle', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
                        { name: 'xp_remove', label: 'Remove XP', icon: 'fa-minus-circle', color: 'text-red-400', bgColor: 'bg-red-500/20' },
                        { name: 'xp_reset', label: 'Reset XP', icon: 'fa-redo', color: 'text-orange-400', bgColor: 'bg-orange-500/20' }
                    ]},
                    { id: 'economy', name: 'Economy & Games', icon: 'fa-coins', color: 'text-amber-400', bgColor: 'bg-amber-500/20', commands: [
                        { name: 'balance', label: 'Check Balance', icon: 'fa-wallet', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
                        { name: 'daily', label: 'Daily Reward', icon: 'fa-gift', color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
                        { name: 'work', label: 'Work', icon: 'fa-briefcase', color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
                        { name: 'mature', label: 'Hunt Animals', icon: 'fa-paw', color: 'text-amber-400', bgColor: 'bg-amber-500/20' },
                        { name: 'leaderboard', label: 'Rich List', icon: 'fa-crown', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' }
                    ]},
                    { id: 'utility', name: 'Utility & Info', icon: 'fa-tools', color: 'text-purple-400', bgColor: 'bg-purple-500/20', commands: [
                        { name: 'avatar', label: 'Get Avatar', icon: 'fa-image', color: 'text-pink-400', bgColor: 'bg-pink-500/20' },
                        { name: 'serverinfo', label: 'Server Info', icon: 'fa-server', color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
                        { name: 'userinfo', label: 'User Info', icon: 'fa-user', color: 'text-cyan-400', bgColor: 'bg-cyan-500/20' },
                        { name: 'ping', label: 'Check Ping', icon: 'fa-signal', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
                        { name: 'uptime', label: 'Bot Uptime', icon: 'fa-clock', color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
                        { name: 'help', label: 'Help Menu', icon: 'fa-question-circle', color: 'text-blue-400', bgColor: 'bg-blue-500/20' }
                    ]},
                    { id: 'fun', name: 'Fun & Social', icon: 'fa-laugh-beam', color: 'text-pink-400', bgColor: 'bg-pink-500/20', commands: [
                        { name: 'poll', label: 'Create Poll', icon: 'fa-poll', color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
                        { name: 'giveaway', label: 'Start Giveaway', icon: 'fa-gift', color: 'text-pink-400', bgColor: 'bg-pink-500/20' },
                        { name: 'ticket', label: 'Create Ticket', icon: 'fa-ticket-alt', color: 'text-blue-400', bgColor: 'bg-blue-500/20' }
                    ]},
                    { id: 'backup', name: 'Backup & Restore', icon: 'fa-database', color: 'text-indigo-400', bgColor: 'bg-indigo-500/20', commands: [
                        { name: 'fullbackup', label: 'Create Backup', icon: 'fa-save', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
                        { name: 'restorebackup', label: 'Restore Backup', icon: 'fa-undo', color: 'text-blue-400', bgColor: 'bg-blue-500/20' }
                    ]},
                    { id: 'premium_purchase', name: 'Premium Purchase', icon: 'fa-crown', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', commands: [
                        { name: 'view_plans', label: 'View Plans', icon: 'fa-list', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' }
                    ]}
                ],
                get userAvatar() { if (!this.user) return 'https://cdn.discordapp.com/embed/avatars/0.png'; const ext = this.user.avatar && this.user.avatar.startsWith('a_') ? 'gif' : 'png'; return `https://cdn.discordapp.com/avatars/${this.user.id}/${this.user.avatar}.${ext}`; },
                showToast(msg, type = 'success') { const id = Date.now(); this.toasts.push({ id, msg, type, show: true }); setTimeout(() => { const t = this.toasts.find(x => x.id === id); if (t) t.show = false; setTimeout(() => this.toasts = this.toasts.filter(x => x.id !== id), 300); }, 3000); },
                async init() { try { const res = await fetch('/api/user'); if (res.ok) { this.user = await res.json(); this.isLoggedIn = true; const gRes = await fetch('/api/guilds'); if (gRes.ok) this.guilds = await gRes.json(); if (this.guilds.length === 1) this.selectGuild(this.guilds[0]); } } catch (e) { this.showToast('Failed to load session', 'error'); } this.loading = false; },
                async selectGuild(g) { this.selectedGuild = g; await this.loadAntinukeSettings(); await this.loadWhitelist(); this.showToast(`Loaded ${g.name}`); },
                async loadAntinukeSettings() { if (!this.selectedGuild) return; try { const res = await fetch(`/api/antinuke/${this.selectedGuild.id}`); if (res.ok) { const settings = await res.json(); this.antinukeSettings.forEach(setting => { const s = settings.find(x => x.program === setting.id); if (s) setting.enabled = s.enabled; }); } } catch (e) { console.error('Failed to load antinuke settings:', e); } },
                async toggleAntinuke(settingId) { if (!this.selectedGuild) return; const setting = this.antinukeSettings.find(s => s.id === settingId); if (!setting) return; try { const res = await fetch(`/api/antinuke/${this.selectedGuild.id}/${settingId}`, { method: 'POST' }); if (res.ok) { setting.enabled = !setting.enabled; this.showToast(`${setting.name} ${setting.enabled ? 'enabled' : 'disabled'}`); } } catch (e) { this.showToast('Failed to update setting', 'error'); } },
                async loadWhitelist() { if (!this.selectedGuild) return; try { const res = await fetch(`/api/whitelist/${this.selectedGuild.id}`); if (res.ok) this.whitelistUsers = await res.json(); } catch (e) { console.error('Failed to load whitelist:', e); } },
                async addToWhitelist() { if (!this.newWhitelistId || !this.selectedGuild) return; try { const res = await fetch(`/api/whitelist/${this.selectedGuild.id}`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({user_id: this.newWhitelistId}) }); if (res.ok) { this.showToast('User added to whitelist'); this.newWhitelistId = ''; await this.loadWhitelist(); } else { const data = await res.json(); this.showToast(data.error || 'Failed to add user', 'error'); } } catch (e) { this.showToast('Failed to add user', 'error'); } },
                async removeFromWhitelist(userId) { if (!this.selectedGuild) return; try { const res = await fetch(`/api/whitelist/${this.selectedGuild.id}/${userId}`, { method: 'DELETE' }); if (res.ok) { this.showToast('User removed from whitelist'); await this.loadWhitelist(); } } catch (e) { this.showToast('Failed to remove user', 'error'); } },
                toggleCategory(catId) { if (this.expandedCategory === catId) this.expandedCategory = null; else { this.expandedCategory = catId; this.activeCategory = catId; } },
                async executeCommand(cmdName) { this.showMenu = false; if (!this.selectedGuild) { this.showToast('Please select a server first', 'error'); return; } try { const res = await fetch('/api/command', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ guild_id: this.selectedGuild.id, command: '!' + cmdName }) }); const data = await res.json(); if (data.success) this.showToast(data.message || 'Command executed'); else this.showToast(data.error || 'Command failed', 'error'); } catch (e) { this.showToast('Failed to execute command', 'error'); } },
                runSetup() { this.executeCommand('quicksetup'); },
                selectPlan(tier, duration) { const plan = this.pricing[tier][duration]; this.selectedPlan = { tier: tier, duration: duration, name: tier.charAt(0).toUpperCase() + tier.slice(1), durationLabel: plan.label, price: plan.price, link: plan.link }; },
                openPayment(tier) { this.selectPlan(tier, this.selectedPlan.duration); this.showPayment = true; }
            }
        }
    </script>
</body>
</html>
"""

@app.route('/login')
def login():
    return redirect(f"{DISCORD_API}/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return "Error", 400
    r = requests.post(f"{DISCORD_API}/oauth2/token", data={
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI
    }, headers={'Content-Type': 'application/x-www-form-urlencoded'})
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
        if obj: g['members'] = obj.member_count
    return jsonify(guilds)

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
            if count >= 10: return {"success": False, "error": "Limit of 10 users reached"}
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
            return {"success": False, "error": f"Error: {type(e).__name__}: {str(e)}"}
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run())
        return jsonify(result)
    finally:
        loop.close()

@app.route('/', methods=['GET'])
def index():
    return render_template_string(DASHBOARD_TEMPLATE, CLIENT_ID=CLIENT_ID)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def run_dashboard():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)), threaded=True)

def set_bot_instance(bot):
    global bot_instance
    bot_instance = bot