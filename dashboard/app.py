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
from utils.database import create_premium_code, save_payment, update_payment_status, get_payment_info

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "MATURE_BOT_SECRET_2026")

bot_instance = None
DEVELOPER_USER_ID = int(os.getenv("DEVELOPER_USER_ID", "0"))
CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://mature-bot.onrender.com/callback")

DISCORD_API = "https://discord.com/api/v10"
DB_PATH = "mature_bot.db"

UPI_ID = "navneet260211@fam"
UPI_NAME = "Navneet Kumar"

PAYMENT_LINKS = {
    'global_noprefix': {'monthly': {'price': 99, 'days': 30, 'label': 'Monthly'}, '3months': {'price': 249, 'days': 90, 'label': '3 Months'}, '6months': {'price': 449, 'days': 180, 'label': '6 Months'}, 'yearly': {'price': 799, 'days': 365, 'label': 'Yearly'}},
    'silver': {'monthly': {'price': 125, 'days': 30, 'label': 'Monthly'}, '3months': {'price': 325, 'days': 90, 'label': '3 Months'}, '6months': {'price': 599, 'days': 180, 'label': '6 Months'}, 'yearly': {'price': 999, 'days': 365, 'label': 'Yearly'}},
    'gold': {'monthly': {'price': 249, 'days': 30, 'label': 'Monthly'}, '3months': {'price': 649, 'days': 90, 'label': '3 Months'}, '6months': {'price': 1199, 'days': 180, 'label': '6 Months'}, 'yearly': {'price': 1999, 'days': 365, 'label': 'Yearly'}},
    'black': {'monthly': {'price': 499, 'days': 30, 'label': 'Monthly'}, '3months': {'price': 1299, 'days': 90, 'label': '3 Months'}, '6months': {'price': 2399, 'days': 180, 'label': '6 Months'}, 'yearly': {'price': 3999, 'days': 365, 'label': 'Yearly'}}
}

def is_developer(user_id): return int(user_id) == DEVELOPER_USER_ID

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session: return jsonify({"error": "Not logged in"}), 401
        return f(*args, **kwargs)
    return decorated_function

def generate_premium_code(): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def run_async(coro):
    if bot_instance and bot_instance.loop:
        future = asyncio.run_coroutine_threadsafe(coro, bot_instance.loop)
        return future.result(timeout=15)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: return loop.run_until_complete(coro)
    finally: loop.close()

@app.route('/api/payment/submit', methods=['POST'])
@login_required
def submit_payment():
    data = request.json
    tier = data.get('tier', 'silver')
    duration = data.get('duration', 'monthly')
    if tier not in PAYMENT_LINKS or duration not in PAYMENT_LINKS[tier]:
        return jsonify({'success': False, 'error': 'Invalid plan'}), 400
    plan = PAYMENT_LINKS[tier][duration]
    payment_id = f"payment_{random.randint(100000, 999999)}"
    try:
        run_async(save_payment(payment_id, int(session['user']['id']), plan['price'] * 100, tier, duration))
        return jsonify({'success': True, 'payment_id': payment_id, 'amount': plan['price'], 'tier': tier, 'upi_id': UPI_ID, 'message': 'Payment submitted. Send screenshot to support.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/login')
def login():
    return redirect(f"{DISCORD_API}/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return "Error", 400
    r = requests.post(f"{DISCORD_API}/oauth2/token", data={'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT_URI}, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if r.status_code != 200: return f"Error: {r.text}", 500
    tokens = r.json()
    headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
    user = requests.get(f"{DISCORD_API}/users/@me", headers=headers).json()
    guilds_req = requests.get(f"{DISCORD_API}/users/@me/guilds", headers=headers).json()
    bot_guilds = {str(g.id) for g in bot_instance.guilds} if bot_instance else set()
    valid = []
    for g in guilds_req:
        if g['id'] in bot_guilds:
            perms = int(g.get('permissions', 0))
            if is_developer(user['id']) or (perms & 0x8) or (perms & 0x20):
                valid.append({'id': g['id'], 'name': g['name'], 'icon': f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png" if g.get('icon') else None, 'members': 0})
    session['user'] = user
    session['guilds'] = valid
    session['access_token'] = tokens['access_token']
    return redirect('/')

@app.route('/api/user')
@login_required
def api_user(): return jsonify(session['user'])

@app.route('/api/guilds')
@login_required
def api_guilds():
    guilds = session.get('guilds', [])
    for g in guilds:
        obj = bot_instance.get_guild(int(g['id']))
        if obj: g['members'] = obj.member_count
    return jsonify(guilds)

@app.route('/api/stats')
def api_stats():
    if not bot_instance: return jsonify({'error': 'Bot not ready'}), 503
    if hasattr(bot_instance, 'start_time'):
        delta = datetime.utcnow() - bot_instance.start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_formatted = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
    else: uptime_formatted = "0h 0m"
    total_guilds = len(bot_instance.guilds)
    total_users = sum(g.member_count for g in bot_instance.guilds)
    latency = round(bot_instance.latency * 1000)
    response = jsonify({'servers': total_guilds, 'users': total_users, 'latency': latency, 'uptime': uptime_formatted, 'ping': latency, 'commands': 76, 'timestamp': datetime.utcnow().isoformat()})
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/', methods=['GET'])
def index():
    return render_template_string(DASHBOARD_TEMPLATE, CLIENT_ID=CLIENT_ID, UPI_ID=UPI_ID, UPI_NAME=UPI_NAME)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/privacy')
def privacy(): return render_template_string(PRIVACY_TEMPLATE)

@app.route('/terms')
def terms(): return render_template_string(TERMS_TEMPLATE)

def run_dashboard():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)), threaded=True)

def set_bot_instance(bot):
    global bot_instance
    bot_instance = bot

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
        body { font-family: 'Inter', sans-serif; background: #0a0a0f; color: #e2e8f0; }
        .gradient-text { background: linear-gradient(135deg, #8b5cf6, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; }
        .btn-primary { background: linear-gradient(135deg, #8b5cf6, #a855f7); transition: all 0.3s; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(139, 92, 246, 0.4); }
        .btn-secondary { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); transition: all 0.3s; }
        .btn-secondary:hover { background: rgba(255, 255, 255, 0.15); }
    </style>
</head>
<body x-data="appData()" x-cloak class="min-h-screen">
    <div x-show="loading" class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0a0a0f]">
        <div class="w-24 h-24 rounded-3xl bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center text-5xl animate-pulse">🧠</div>
        <p class="text-slate-400 font-semibold mt-6 text-lg">Loading Mature Bot...</p>
    </div>

    <div x-show="!loading && !isLoggedIn" class="min-h-screen">
        <nav class="sticky top-0 z-50 glass border-b border-white/10 px-4 py-4">
            <div class="max-w-7xl mx-auto flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center text-2xl">🧠</div>
                    <h1 class="text-2xl font-black gradient-text">MATURE BOT</h1>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/login" class="btn-secondary px-5 py-2.5 rounded-xl text-sm font-semibold">Login</a>
                    <a :href="'https://discord.com/api/oauth2/authorize?client_id={{CLIENT_ID}}&permissions=8&scope=bot%20applications.commands'" target="_blank" class="btn-primary px-5 py-2.5 rounded-xl text-sm font-bold">Invite</a>
                </div>
            </div>
        </nav>
        <section class="py-24 px-4 text-center">
            <div class="max-w-5xl mx-auto">
                <h1 class="text-6xl md:text-8xl font-black mb-8"><span class="gradient-text">Advanced</span><br><span class="text-white">Discord Platform</span></h1>
                <p class="text-xl text-slate-400 mb-12 max-w-3xl mx-auto">Next-generation security, intelligent moderation, and seamless community management.</p>
                <div class="flex flex-col sm:flex-row gap-4 justify-center">
                    <a :href="'https://discord.com/api/oauth2/authorize?client_id={{CLIENT_ID}}&permissions=8&scope=bot%20applications.commands'" target="_blank" class="btn-primary px-10 py-5 rounded-2xl text-white font-bold text-lg">Add to Discord</a>
                    <a href="/login" class="btn-secondary px-10 py-5 rounded-2xl text-white font-bold text-lg">Dashboard</a>
                </div>
            </div>
        </section>
        <footer class="py-12 px-4 border-t border-white/10">
            <div class="max-w-7xl mx-auto text-center">
                <div class="flex justify-center gap-6 mb-4">
                    <a href="/privacy" class="text-slate-400 hover:text-white">Privacy Policy</a>
                    <a href="/terms" class="text-slate-400 hover:text-white">Terms of Service</a>
                    <a href="https://discord.gg/YxeeaEg9V6" target="_blank" class="text-slate-400 hover:text-white">Support</a>
                </div>
                <p class="text-slate-500 text-sm">© 2026 Mature Bot. All rights reserved.</p>
            </div>
        </footer>
    </div>

    <div x-show="!loading && isLoggedIn" class="min-h-screen pb-20">
        <header class="glass border-b border-white/10 px-4 py-3 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center text-xl">🧠</div>
                <h1 class="text-xl font-black gradient-text">MATURE BOT</h1>
            </div>
            <div class="flex items-center gap-3">
                <a href="/logout" class="btn-secondary px-3 py-2 rounded-xl text-sm text-red-400">Logout</a>
            </div>
        </header>
        <main class="p-4 max-w-7xl mx-auto space-y-6">
            <div class="glass p-6">
                <h2 class="text-2xl font-bold text-white mb-2">Welcome to Mature Bot Dashboard</h2>
                <p class="text-slate-400">Manage your servers with powerful tools.</p>
            </div>
            <div class="space-y-6">
                <h2 class="text-3xl font-bold gradient-text text-center">Premium Plans</h2>
                <div class="glass p-8 border-2 border-cyan-500/50">
                    <div class="flex items-center justify-between mb-6">
                        <div><h3 class="text-2xl font-bold text-cyan-400">Global No-Prefix</h3><p class="text-slate-400 text-sm">Use commands anywhere without '!'</p></div>
                        <i class="fas fa-globe text-4xl text-cyan-400"></i>
                    </div>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <button @click="selectPlan('global_noprefix', 'monthly', 99)" class="btn-secondary py-3 rounded-xl text-white font-semibold">₹99/mo</button>
                        <button @click="selectPlan('global_noprefix', '3months', 249)" class="btn-secondary py-3 rounded-xl text-white font-semibold">₹249/3mo</button>
                        <button @click="selectPlan('global_noprefix', '6months', 449)" class="btn-secondary py-3 rounded-xl text-white font-semibold">₹449/6mo</button>
                        <button @click="selectPlan('global_noprefix', 'yearly', 799)" class="btn-secondary py-3 rounded-xl text-white font-semibold">₹799/yr</button>
                    </div>
                </div>
                <div class="glass p-8 border-2 border-yellow-500/50">
                    <h3 class="text-2xl font-bold text-yellow-400 mb-4">Gold</h3>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <button @click="selectPlan('gold', 'monthly', 249)" class="btn-secondary py-3 rounded-xl text-white font-semibold">249/mo</button>
                        <button @click="selectPlan('gold', '3months', 649)" class="btn-secondary py-3 rounded-xl text-white font-semibold">₹649/3mo</button>
                        <button @click="selectPlan('gold', '6months', 1199)" class="btn-secondary py-3 rounded-xl text-white font-semibold">₹1199/6mo</button>
                        <button @click="selectPlan('gold', 'yearly', 1999)" class="btn-secondary py-3 rounded-xl text-white font-semibold">₹1999/yr</button>
                    </div>
                </div>
            </div>
            <div x-show="showPayment" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" @click.self="showPayment = false">
                <div class="glass p-6 rounded-2xl max-w-lg w-full">
                    <h3 class="text-2xl font-bold gradient-text mb-4">Complete Payment</h3>
                    <p class="text-slate-400 mb-4" x-text="'Plan: ' + selectedPlan.tier + ' - ₹' + selectedPlan.price"></p>
                    <div class="text-center p-6 rounded-xl bg-white mb-4">
                        <img :src="'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi://pay?pa=' + '{{UPI_ID}}' + '&pn={{UPI_NAME}}&am=' + selectedPlan.price + '&cu=INR'" alt="UPI QR" class="w-48 h-48 mx-auto">
                        <p class="text-sm text-slate-600 mt-3">UPI ID: <span class="font-bold">{{UPI_ID}}</span></p>
                    </div>
                    <button @click="submitPayment()" class="btn-primary w-full py-4 rounded-xl text-white font-bold">I Have Paid - Submit</button>
                </div>
            </div>
        </main>
    </div>
    <script>
        function appData() {
            return {
                loading: true, isLoggedIn: false, showPayment: false, selectedPlan: { tier: '', price: 0 },
                async init() { try { const res = await fetch('/api/user'); if (res.ok) this.isLoggedIn = true; } catch (e) { console.error(e); } this.loading = false; },
                selectPlan(tier, price) { this.selectedPlan = { tier, price }; this.showPayment = true; },
                async submitPayment() {
                    try {
                        const res = await fetch('/api/payment/submit', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ tier: this.selectedPlan.tier, duration: 'monthly', reference_id: 'UPI' + Date.now() }) });
                        const data = await res.json();
                        if (data.success) { alert('Payment submitted! Check your DMs for the code.'); this.showPayment = false; }
                    } catch (e) { alert('Error submitting payment'); }
                }
            }
        }
    </script>
</body>
</html>
"""

PRIVACY_TEMPLATE = """<!DOCTYPE html><html><head><title>Privacy</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-[#0a0a0f] text-white p-8"><div class="max-w-4xl mx-auto glass p-8 rounded-2xl"><h1 class="text-4xl font-bold mb-6">Privacy Policy</h1><p class="text-slate-300">Mature Bot collects minimal data to provide services. <a href="/" class="text-violet-400">Back</a></p></div></body></html>"""
TERMS_TEMPLATE = """<!DOCTYPE html><html><head><title>Terms</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-[#0a0a0f] text-white p-8"><div class="max-w-4xl mx-auto glass p-8 rounded-2xl"><h1 class="text-4xl font-bold mb-6">Terms of Service</h1><p class="text-slate-300">By using Mature Bot, you agree to our terms. <a href="/" class="text-violet-400">Back</a></p></div></body></html>"""
