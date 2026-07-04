from flask import Flask, request, jsonify, session, redirect, make_response
import requests
import os
import discord
import aiosqlite
import asyncio
import random
import string
import razorpay
import hmac
import hashlib
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

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_xxxxxxxxxxxxx")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "xxxxxxxxxxxxxxxxxxxxxxxx")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "xxxxxxxxxxxx")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

DISCORD_API = "https://discord.com/api/v10"
INVITE_URL = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot%20applications.commands"
DB_PATH = "mature_bot.db"

PRICING = {
    'gold': {
        'monthly': {'price': 125, 'days': 30, 'label': 'Monthly'},
        '3months': {'price': 325, 'days': 90, 'label': '3 Months'},
        '6months': {'price': 599, 'days': 180, 'label': '6 Months'},
        'yearly': {'price': 999, 'days': 365, 'label': 'Yearly'}
    },
    'platinum': {
        'monthly': {'price': 249, 'days': 30, 'label': 'Monthly'},
        '3months': {'price': 649, 'days': 90, 'label': '3 Months'},
        '6months': {'price': 1199, 'days': 180, 'label': '6 Months'},
        'yearly': {'price': 1999, 'days': 365, 'label': 'Yearly'}
    },
    'ultimate': {
        'monthly': {'price': 499, 'days': 30, 'label': 'Monthly'},
        '3months': {'price': 1299, 'days': 90, 'label': '3 Months'},
        '6months': {'price': 2399, 'days': 180, 'label': '6 Months'},
        'yearly': {'price': 3999, 'days': 365, 'label': 'Yearly'}
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
    tier = data.get('tier', 'gold')
    duration = data.get('duration', 'monthly')
    
    if tier not in PRICING or duration not in PRICING[tier]:
        return jsonify({'success': False, 'error': 'Invalid plan'}), 400
    
    plan = PRICING[tier][duration]
    amount = plan['price'] * 100
    
    try:
        order = razorpay_client.order.create({
            'amount': amount,
            'currency': 'INR',
            'receipt': f'receipt_{random.randint(1000, 9999)}',
            'notes': {
                'user_id': session['user']['id'],
                'tier': tier,
                'duration': duration
            }
        })
        
        asyncio.run(save_payment(order['id'], int(session['user']['id']), amount, tier, duration))
        
        return jsonify({
            'success': True,
            'order_id': order['id'],
            'amount': amount,
            'currency': 'INR',
            'key_id': RAZORPAY_KEY_ID
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    data = request.json
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    
    message = razorpay_order_id + "|" + razorpay_payment_id
    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if expected_signature == razorpay_signature:
        asyncio.run(update_payment_status(razorpay_order_id, 'completed'))
        
        code = generate_premium_code()
        
        payment_info = asyncio.run(get_payment_info(razorpay_order_id))
        if payment_info:
            tier, duration = payment_info
            days = PRICING[tier][duration]['days']
            
            asyncio.run(create_premium_code(code, tier, duration, days))
            
            if bot_instance:
                async def send_dm():
                    user_id = int(session.get('user', {}).get('id', 0))
                    if user_id:
                        user = await bot_instance.fetch_user(user_id)
                        if user:
                            embed = discord.Embed(
                                title="🎉 Payment Successful!",
                                description=f"Your premium code is: `{code}`\n\n**Tier:** {tier.title()}\n**Duration:** {PRICING[tier][duration]['label']}\n\nUse `!premium {code}` in any server to activate!",
                                color=0x10b981
                            )
                            try:
                                await user.send(embed=embed)
                            except:
                                pass
                
                asyncio.run_coroutine_threadsafe(send_dm(), bot_instance.loop).result(timeout=5)
        
        return jsonify({'success': True, 'code': code})
    else:
        return jsonify({'success': False, 'error': 'Invalid signature'}), 400

@app.route('/api/payment/webhook', methods=['POST'])
def payment_webhook():
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    body = request.get_data()
    
    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if expected_signature == webhook_signature:
        payload = request.json
        event = payload.get('event')
        
        if event == 'payment.captured':
            payment = payload['payload']['payment']['entity']
            order_id = payment['order_id']
            
            asyncio.run(update_payment_status(order_id, 'completed'))
            
            code = generate_premium_code()
            tier = payment['notes'].get('tier', 'platinum')
            duration = payment['notes'].get('duration', 'monthly')
            days = PRICING[tier][duration]['days']
            
            asyncio.run(create_premium_code(code, tier, duration, days))
            
            if bot_instance:
                async def send_dm():
                    user_id = int(payment['notes'].get('user_id', 0))
                    if user_id:
                        user = await bot_instance.fetch_user(user_id)
                        if user:
                            embed = discord.Embed(
                                title="🎉 Payment Successful!",
                                description=f"Your premium code is: `{code}`\n\n**Tier:** {tier.title()}\n**Duration:** {PRICING[tier][duration]['label']}\n\nUse `!premium {code}` in any server to activate!",
                                color=0x10b981
                            )
                            try:
                                await user.send(embed=embed)
                            except:
                                pass
                
                asyncio.run_coroutine_threadsafe(send_dm(), bot_instance.loop).result(timeout=5)
        
        return jsonify({'status': 'ok'}), 200
    else:
        return jsonify({'error': 'Invalid signature'}), 400

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
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
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
        .category-menu { position: fixed; top: 0; left: -320px; width: 320px; height: 100vh; background: linear-gradient(180deg, rgba(15, 15, 35, 0.98), rgba(30, 27, 75, 0.98)); backdrop-filter: blur(20px); z-index: 100; transition: left 0.3s ease; overflow-y: auto; }
        .category-menu.open { left: 0; }
        .category-item { padding: 12px 20px; margin: 4px 12px; border-radius: 12px; cursor: pointer; transition: all 0.2s; }
        .category-item:hover { background: linear-gradient(90deg, rgba(99, 102, 241, 0.2), transparent); }
        .category-item.active { background: linear-gradient(90deg, rgba(99, 102, 241, 0.3), rgba(168, 85, 247, 0.2)); border-left: 3px solid #6366f1; }
        .submenu { margin-left: 20px; margin-top: 8px; }
        .submenu-item { padding: 10px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; transition: all 0.2s; }
        .submenu-item:hover { background: rgba(255, 255, 255, 0.05); }
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
        .feature-card { background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.8)); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 20px; padding: 24px; transition: all 0.3s ease; }
        .feature-card:hover { transform: translateY(-8px); border-color: rgba(99, 102, 241, 0.5); box-shadow: 0 20px 40px rgba(99, 102, 241, 0.3); }
        .feature-icon { width: 64px; height: 64px; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 28px; margin-bottom: 16px; }
        .stats-counter { font-size: 48px; font-weight: 800; background: linear-gradient(135deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
</head>
<body class="h-screen flex flex-col overflow-hidden" x-data="appData()" x-cloak>

    <div class="overlay" :class="showMenu ? 'show' : ''" @click="showMenu = false"></div>
    <div class="overlay" :class="showPayment ? 'show' : ''" @click="showPayment = false"></div>

    <div class="category-menu" :class="showMenu ? 'open' : ''">
        <div class="p-6 border-b border-white/10">
            <div class="flex items-center justify-between">
                <h2 class="text-xl font-bold text-white">Categories</h2>
                <button @click="showMenu = false" class="text-slate-400 hover:text-white"><i class="fas fa-times text-xl"></i></button>
            </div>
        </div>
        <div class="p-4 space-y-2">
            <template x-for="cat in categories" :key="cat.id">
                <div>
                    <div class="category-item flex items-center justify-between" :class="activeCategory === cat.id ? 'active' : ''" @click="toggleCategory(cat.id)">
                        <div class="flex items-center gap-3">
                            <i :class="cat.icon" class="text-lg" :class="cat.color"></i>
                            <span class="font-medium" x-text="cat.name"></span>
                        </div>
                        <i class="fas fa-chevron-down text-sm transition-transform" :class="expandedCategory === cat.id ? 'rotate-180' : ''"></i>
                    </div>
                    <div x-show="expandedCategory === cat.id" class="submenu space-y-1" x-transition>
                        <template x-for="cmd in cat.commands" :key="cmd.name">
                            <div class="submenu-item flex items-center justify-between text-slate-300 hover:text-white" @click="executeCommand(cmd.name)">
                                <div class="flex items-center gap-2">
                                    <i :class="cmd.icon" class="text-sm w-5"></i>
                                    <span x-text="cmd.label"></span>
                                </div>
                                <i class="fas fa-chevron-right text-xs text-slate-600"></i>
                            </div>
                        </template>
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

            <div class="space-y-4">
                <p class="text-sm font-medium text-white mb-3">Select Payment Method:</p>
                
                <div class="payment-card" @click="processPayment()">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center text-purple-400 text-xl">
                            <i class="fas fa-credit-card"></i>
                        </div>
                        <div class="flex-1">
                            <p class="font-medium text-white">Pay with Razorpay</p>
                            <p class="text-xs text-slate-400">UPI, Cards, Net Banking</p>
                        </div>
                        <i class="fas fa-chevron-right text-slate-600"></i>
                    </div>
                </div>
            </div>

            <div class="mt-6 p-4 rounded-xl bg-slate-800/50 border border-slate-700">
                <p class="text-xs text-slate-400 mb-2"><i class="fas fa-info-circle mr-1"></i> After payment, you'll receive a premium code via DM</p>
                <p class="text-xs text-slate-500">Use <code class="bg-slate-700 px-1 rounded">!premium</code> command to activate</p>
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
                <button @click="showMenu = true" class="p-2 rounded-xl hover:bg-white/10 transition-colors"><i class="fas fa-ellipsis-v text-xl text-white"></i></button>
                <div x-show="selectedGuild" class="flex items-center gap-3">
                    <img :src="selectedGuild.icon || 'https://cdn.discordapp.com/embed/avatars/0.png'" class="w-10 h-10 rounded-xl object-cover border border-white/20">
                    <div>
                        <p class="font-bold text-white text-sm" x-text="selectedGuild.name"></p>
                        <span class="status-badge status-online"><i class="fas fa-circle text-[6px]"></i> Online</span>
                    </div>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <a :href="inviteUrl" target="_blank" class="glass px-4 py-2 rounded-xl text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 transition-all text-sm font-medium flex items-center gap-2">
                    <i class="fas fa-plus"></i>
                    <span class="hidden md:inline">Invite Me</span>
                </a>
                <a href="/logout" class="text-slate-400 hover:text-red-400 p-2"><i class="fas fa-sign-out-alt text-lg"></i></a>
            </div>
        </header>

        <main class="flex-1 overflow-y-auto no-scrollbar p-4 pb-28" style="-webkit-overflow-scrolling: touch;">
            
            <div x-show="activePanel === 'home' && !selectedGuild" class="space-y-8">
                <div class="text-center py-12">
                    <div class="w-32 h-32 rounded-3xl premium-gradient flex items-center justify-center text-6xl shadow-2xl mx-auto mb-6">🧠</div>
                    <h1 class="text-5xl font-bold gradient-text mb-4">Mature Bot</h1>
                    <p class="text-xl text-slate-400 mb-8 max-w-2xl mx-auto">The most advanced Discord bot for moderation, economy, music, and server management with premium features.</p>
                    <div class="flex gap-4 justify-center">
                        <a href="/login" class="btn-primary px-8 py-4 rounded-2xl text-white font-bold text-lg shadow-lg">
                            <i class="fas fa-rocket mr-2"></i>Get Started
                        </a>
                        <a :href="inviteUrl" target="_blank" class="glass px-8 py-4 rounded-2xl text-white font-bold text-lg hover:bg-indigo-500/10 transition-all">
                            <i class="fas fa-plus mr-2"></i>Invite Bot
                        </a>
                    </div>
                </div>

                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
                    <div class="glass p-6 text-center">
                        <div class="stats-counter">88+</div>
                        <p class="text-slate-400 mt-2">Commands</p>
                    </div>
                    <div class="glass p-6 text-center">
                        <div class="stats-counter">100+</div>
                        <p class="text-slate-400 mt-2">Servers</p>
                    </div>
                    <div class="glass p-6 text-center">
                        <div class="stats-counter">24/7</div>
                        <p class="text-slate-400 mt-2">Uptime</p>
                    </div>
                    <div class="glass p-6 text-center">
                        <div class="stats-counter">99%</div>
                        <p class="text-slate-400 mt-2">Satisfaction</p>
                    </div>
                </div>

                <div class="mb-12">
                    <h2 class="text-3xl font-bold text-center mb-8 gradient-text">Powerful Features</h2>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        <div class="feature-card">
                            <div class="feature-icon bg-gradient-to-br from-red-500/20 to-orange-500/20 text-red-400">
                                <i class="fas fa-shield-alt"></i>
                            </div>
                            <h3 class="text-xl font-bold text-white mb-2">Advanced Moderation</h3>
                            <p class="text-slate-400 text-sm">Ban, kick, warn, timeout, and auto-moderation tools to keep your server safe and clean.</p>
                        </div>

                        <div class="feature-card">
                            <div class="feature-icon bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 text-emerald-400">
                                <i class="fas fa-coins"></i>
                            </div>
                            <h3 class="text-xl font-bold text-white mb-2">Economy System</h3>
                            <p class="text-slate-400 text-sm">Complete economy with balance, daily rewards, work commands, and leaderboard system.</p>
                        </div>

                        <div class="feature-card">
                            <div class="feature-icon bg-gradient-to-br from-amber-500/20 to-yellow-500/20 text-amber-400">
                                <i class="fas fa-shield-virus"></i>
                            </div>
                            <h3 class="text-xl font-bold text-white mb-2">Antinuke Protection</h3>
                            <p class="text-slate-400 text-sm">Protect your server from raids, mass bans, and unauthorized changes with advanced antinuke.</p>
                        </div>

                        <div class="feature-card">
                            <div class="feature-icon bg-gradient-to-br from-cyan-500/20 to-blue-500/20 text-cyan-400">
                                <i class="fas fa-music"></i>
                            </div>
                            <h3 class="text-xl font-bold text-white mb-2">Music Player</h3>
                            <p class="text-slate-400 text-sm">High-quality music playback with queue, loop, shuffle, and volume controls.</p>
                        </div>

                        <div class="feature-card">
                            <div class="feature-icon bg-gradient-to-br from-purple-500/20 to-pink-500/20 text-purple-400">
                                <i class="fas fa-chart-line"></i>
                            </div>
                            <h3 class="text-xl font-bold text-white mb-2">Leveling System</h3>
                            <p class="text-slate-400 text-sm">Engage members with XP system, ranks, and customizable leveling channels.</p>
                        </div>

                        <div class="feature-card">
                            <div class="feature-icon bg-gradient-to-br from-indigo-500/20 to-violet-500/20 text-indigo-400">
                                <i class="fas fa-database"></i>
                            </div>
                            <h3 class="text-xl font-bold text-white mb-2">Server Backups</h3>
                            <p class="text-slate-400 text-sm">Create and restore complete server backups with roles, channels, and permissions.</p>
                        </div>
                    </div>
                </div>

                <div class="glass p-8 text-center mb-8 border-2 border-indigo-500/30">
                    <h2 class="text-3xl font-bold gradient-text mb-4">Upgrade to Premium</h2>
                    <p class="text-slate-400 mb-6">Unlock exclusive features like no-prefix mode, custom commands, and priority support.</p>
                    <button @click="activePanel = 'premium'" class="btn-primary px-8 py-4 rounded-2xl text-white font-bold text-lg">
                        <i class="fas fa-crown mr-2"></i>View Premium Plans
                    </button>
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
                        <button @click="activePanel = 'premium'" class="glass p-4 flex flex-col items-center gap-2 border-t-4 border-t-pink-500">
                            <i class="fas fa-crown text-pink-400 text-2xl"></i><span class="text-sm font-medium text-white">Premium</span>
                        </button>
                    </div>
                </div>
            </div>

            <div x-show="activePanel === 'premium'" class="space-y-6">
                <div class="text-center mb-6">
                    <h2 class="text-3xl font-bold gradient-text mb-2">Unlock Premium</h2>
                    <p class="text-slate-400 text-sm">Get exclusive features for your server</p>
                </div>
                
                <div class="glass p-5 border-2 border-amber-500/30">
                    <div class="flex justify-between items-center mb-3">
                        <h3 class="text-xl font-bold text-amber-400">🥇 Gold</h3>
                    </div>
                    <ul class="text-sm text-slate-300 space-y-2 mb-4">
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>No-prefix mode</li>
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>+10% drop rates</li>
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>Priority support</li>
                    </ul>
                    <div class="grid grid-cols-2 gap-2 mb-4">
                        <template x-for="(plan, duration) in pricing.gold" :key="duration">
                            <button 
                                @click="selectPlan('gold', duration)"
                                class="duration-btn w-full"
                                :class="selectedPlan.tier === 'gold' && selectedPlan.duration === duration ? 'active' : ''"
                            >
                                <div x-text="plan.label"></div>
                                <div class="text-xs" x-text="'₹' + plan.price"></div>
                            </button>
                        </template>
                    </div>
                    <button @click="openPayment('gold')" class="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-400 font-bold border border-amber-500/30 hover:from-amber-500/30 hover:to-orange-500/30 transition-all">Purchase Now</button>
                </div>

                <div class="glass p-5 border-2 border-indigo-500 relative">
                    <div class="absolute -top-3 left-1/2 -translate-x-1/2 premium-gradient text-white text-xs font-bold px-3 py-1 rounded-full">POPULAR</div>
                    <div class="flex justify-between items-center mb-3">
                        <h3 class="text-xl font-bold text-indigo-400">💎 Platinum</h3>
                    </div>
                    <ul class="text-sm text-slate-300 space-y-2 mb-4">
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>All Gold features</li>
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>Server-wide no-prefix</li>
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>+25% drop rates</li>
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>Custom commands</li>
                    </ul>
                    <div class="grid grid-cols-2 gap-2 mb-4">
                        <template x-for="(plan, duration) in pricing.platinum" :key="duration">
                            <button 
                                @click="selectPlan('platinum', duration)"
                                class="duration-btn w-full"
                                :class="selectedPlan.tier === 'platinum' && selectedPlan.duration === duration ? 'active' : ''"
                            >
                                <div x-text="plan.label"></div>
                                <div class="text-xs" x-text="'₹' + plan.price"></div>
                            </button>
                        </template>
                    </div>
                    <button @click="openPayment('platinum')" class="w-full py-3 rounded-xl btn-primary text-white font-bold">Purchase Now</button>
                </div>

                <div class="glass p-5 border-2 border-purple-500/30">
                    <div class="flex justify-between items-center mb-3">
                        <h3 class="text-xl font-bold text-purple-400">👑 Ultimate</h3>
                    </div>
                    <ul class="text-sm text-slate-300 space-y-2 mb-4">
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>All Platinum features</li>
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>Unlimited auto-hunt</li>
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>VIP badge</li>
                        <li><i class="fas fa-check text-emerald-400 mr-2"></i>24/7 priority support</li>
                    </ul>
                    <div class="grid grid-cols-2 gap-2 mb-4">
                        <template x-for="(plan, duration) in pricing.ultimate" :key="duration">
                            <button 
                                @click="selectPlan('ultimate', duration)"
                                class="duration-btn w-full"
                                :class="selectedPlan.tier === 'ultimate' && selectedPlan.duration === duration ? 'active' : ''"
                            >
                                <div x-text="plan.label"></div>
                                <div class="text-xs" x-text="'₹' + plan.price"></div>
                            </button>
                        </template>
                    </div>
                    <button @click="openPayment('ultimate')" class="w-full py-3 rounded-xl bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-400 font-bold border border-purple-500/30 hover:from-purple-500/30 hover:to-pink-500/30 transition-all">Purchase Now</button>
                </div>
            </div>
        </main>

        <nav class="bottom-nav fixed bottom-0 left-0 right-0 z-50">
            <div class="flex justify-around items-center h-16">
                <button @click="activePanel = 'home'; showMenu = false" class="flex flex-col items-center justify-center w-full h-full space-y-1" :class="activePanel === 'home' ? 'text-indigo-400' : 'text-slate-500'">
                    <i class="fas fa-home text-xl"></i><span class="text-[10px] font-medium">Home</span>
                </button>
                <button @click="activePanel = 'premium'" class="flex flex-col items-center justify-center w-full h-full space-y-1" :class="activePanel === 'premium' ? 'text-indigo-400' : 'text-slate-500'">
                    <i class="fas fa-crown text-xl"></i><span class="text-[10px] font-medium">Premium</span>
                </button>
            </div>
        </nav>
    </div>

    <script>
        function appData() {
            return {
                inviteUrl: 'https://discord.com/api/oauth2/authorize?client_id={{ CLIENT_ID }}&permissions=8&scope=bot%20applications.commands',
                loading: true, isLoggedIn: false, user: null, guilds: [], selectedGuild: null,
                activePanel: 'home', showMenu: false, showFeatures: false, activeCategory: 'moderation', expandedCategory: 'moderation',
                showPayment: false,
                selectedPlan: { tier: 'gold', duration: 'monthly', name: 'Gold', durationLabel: 'Monthly', price: 125 },
                toasts: [],
                pricing: {
                    gold: {
                        monthly: { price: 125, days: 30, label: 'Monthly' },
                        '3months': { price: 325, days: 90, label: '3 Months' },
                        '6months': { price: 599, days: 180, label: '6 Months' },
                        yearly: { price: 999, days: 365, label: 'Yearly' }
                    },
                    platinum: {
                        monthly: { price: 249, days: 30, label: 'Monthly' },
                        '3months': { price: 649, days: 90, label: '3 Months' },
                        '6months': { price: 1199, days: 180, label: '6 Months' },
                        yearly: { price: 1999, days: 365, label: 'Yearly' }
                    },
                    ultimate: {
                        monthly: { price: 499, days: 30, label: 'Monthly' },
                        '3months': { price: 1299, days: 90, label: '3 Months' },
                        '6months': { price: 2399, days: 180, label: '6 Months' },
                        yearly: { price: 3999, days: 365, label: 'Yearly' }
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
                    { id: 'moderation', name: 'Moderation & Security', icon: 'fa-shield-alt', color: 'text-red-400', commands: [
                        { name: 'antinuke', label: 'Antinuke Panel', icon: 'fa-shield-alt' },
                        { name: 'antinuke_enable', label: 'Enable Antinuke', icon: 'fa-check-circle' },
                        { name: 'antinuke_disable', label: 'Disable Antinuke', icon: 'fa-times-circle' },
                        { name: 'ban', label: 'Ban Member', icon: 'fa-ban' },
                        { name: 'kick', label: 'Kick Member', icon: 'fa-user-slash' },
                        { name: 'clear', label: 'Clear Messages', icon: 'fa-trash' },
                        { name: 'warn', label: 'Warn Member', icon: 'fa-exclamation-triangle' },
                        { name: 'timeout', label: 'Timeout Member', icon: 'fa-clock' },
                        { name: 'unban', label: 'Unban User', icon: 'fa-user-check' },
                        { name: 'lock', label: 'Lock Channel', icon: 'fa-lock' },
                        { name: 'unlock', label: 'Unlock Channel', icon: 'fa-unlock' }
                    ]},
                    { id: 'logging', name: 'Logging System', icon: 'fa-clipboard-list', color: 'text-blue-400', commands: [
                        { name: 'logging_enable', label: 'Enable Logging', icon: 'fa-check-circle' },
                        { name: 'logging_disable', label: 'Disable Logging', icon: 'fa-times-circle' },
                        { name: 'logging_autosetup', label: 'Auto Setup Logs', icon: 'fa-cog' },
                        { name: 'setlogs', label: 'Set Log Channel', icon: 'fa-hashtag' }
                    ]},
                    { id: 'levelling', name: 'Levelling System', icon: 'fa-chart-line', color: 'text-emerald-400', commands: [
                        { name: 'rank', label: 'Check Rank', icon: 'fa-trophy' },
                        { name: 'leaderboard', label: 'Leaderboard', icon: 'fa-list-ol' },
                        { name: 'leveling_channel', label: 'Set Level Channel', icon: 'fa-hashtag' },
                        { name: 'xp_add', label: 'Add XP', icon: 'fa-plus-circle' },
                        { name: 'xp_remove', label: 'Remove XP', icon: 'fa-minus-circle' },
                        { name: 'xp_reset', label: 'Reset XP', icon: 'fa-redo' }
                    ]},
                    { id: 'economy', name: 'Economy & Games', icon: 'fa-coins', color: 'text-amber-400', commands: [
                        { name: 'balance', label: 'Check Balance', icon: 'fa-wallet' },
                        { name: 'daily', label: 'Daily Reward', icon: 'fa-gift' },
                        { name: 'work', label: 'Work', icon: 'fa-briefcase' },
                        { name: 'mature', label: 'Hunt Animals', icon: 'fa-paw' },
                        { name: 'leaderboard', label: 'Rich List', icon: 'fa-crown' }
                    ]},
                    { id: 'utility', name: 'Utility & Info', icon: 'fa-tools', color: 'text-purple-400', commands: [
                        { name: 'avatar', label: 'Get Avatar', icon: 'fa-image' },
                        { name: 'serverinfo', label: 'Server Info', icon: 'fa-server' },
                        { name: 'userinfo', label: 'User Info', icon: 'fa-user' },
                        { name: 'ping', label: 'Check Ping', icon: 'fa-signal' },
                        { name: 'uptime', label: 'Bot Uptime', icon: 'fa-clock' },
                        { name: 'help', label: 'Help Menu', icon: 'fa-question-circle' }
                    ]},
                    { id: 'fun', name: 'Fun & Social', icon: 'fa-laugh-beam', color: 'text-pink-400', commands: [
                        { name: 'poll', label: 'Create Poll', icon: 'fa-poll' },
                        { name: 'giveaway', label: 'Start Giveaway', icon: 'fa-gift' },
                        { name: 'ticket', label: 'Create Ticket', icon: 'fa-ticket-alt' }
                    ]},
                    { id: 'backup', name: 'Backup & Restore', icon: 'fa-database', color: 'text-indigo-400', commands: [
                        { name: 'fullbackup', label: 'Create Backup', icon: 'fa-save' },
                        { name: 'restorebackup', label: 'Restore Backup', icon: 'fa-undo' }
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
                selectPlan(tier, duration) { this.selectedPlan = { tier: tier, duration: duration, name: tier.charAt(0).toUpperCase() + tier.slice(1), durationLabel: this.pricing[tier][duration].label, price: this.pricing[tier][duration].price }; },
                openPayment(tier) { this.selectPlan(tier, this.selectedPlan.duration); this.showPayment = true; },
                async processPayment() {
                    try {
                        const res = await fetch('/api/payment/create', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ tier: this.selectedPlan.tier, duration: this.selectedPlan.duration }) });
                        const data = await res.json();
                        if (data.success) {
                            const options = {
                                key: data.key_id,
                                amount: data.amount,
                                currency: data.currency,
                                name: 'Mature Bot',
                                description: `${this.selectedPlan.name} ${this.selectedPlan.durationLabel}`,
                                order_id: data.order_id,
                                handler: async (response) => {
                                    const verifyRes = await fetch('/api/payment/verify', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ razorpay_order_id: response.razorpay_order_id, razorpay_payment_id: response.razorpay_payment_id, razorpay_signature: response.razorpay_signature }) });
                                    const verifyData = await verifyRes.json();
                                    if (verifyData.success) {
                                        this.showToast('Payment successful! Check your DM for premium code.', 'success');
                                        this.showPayment = false;
                                    }
                                },
                                prefill: { name: this.user.global_name || this.user.username, email: '', contact: '' },
                                theme: { color: '#6366f1' }
                            };
                            const rzp = new Razorpay(options);
                            rzp.open();
                        } else {
                            this.showToast(data.error || 'Failed to create payment', 'error');
                        }
                    } catch (e) {
                        this.showToast('Payment failed', 'error');
                    }
                }
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
    
    if not command_name.startswith('!'):
        command_name = '!' + command_name
    
    guild = bot_instance.get_guild(guild_id)
    if not guild: return jsonify({"success": False, "error": "Guild not found"}), 404
    
    channel = guild.text_channels[0] if guild.text_channels else None
    if not channel: return jsonify({"success": False, "error": "No text channels"}), 400
    
    user_id = int(session['user']['id'])
    member = guild.get_member(user_id)
    
    class FakeUser:
        id = user_id
        name = session['user']['username']
        display_name = name
        bot = False
        guild_permissions = member.guild_permissions if member else discord.Permissions(administrator=True)
        top_role = member.top_role if member else guild.default_role
    
    class FakeMessage:
        content = command_name
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
    
    async def run():
        try:
            ctx = await bot_instance.get_context(FakeMessage())
            
            if ctx.command is None:
                return {"success": False, "error": f"Command '{command_name}' not found"}
            
            if ctx.valid:
                await bot_instance.invoke(ctx)
                return {"success": True, "message": f"Command '{command_name}' executed successfully"}
            else:
                return {"success": False, "error": f"Command '{command_name}' is invalid"}
                
        except discord.errors.Forbidden:
            return {"success": False, "error": "Bot doesn't have permission to execute this command"}
        except discord.errors.HTTPException as e:
            return {"success": False, "error": f"HTTP Error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error: {str(e)}"}
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run())
        return jsonify(result)
    finally:
        loop.close()

@app.route('/', methods=['GET'])
def index():
    return DASHBOARD_TEMPLATE

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def run_dashboard():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)), threaded=True)

def set_bot_instance(bot):
    global bot_instance
    bot_instance = bot