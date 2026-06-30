from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import requests
from dotenv import load_dotenv
from flask_session import Session
import functools

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.getenv("SECRET_KEY", "fallback")
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

app.bot = None  # Will be set by mature.py

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/login')
def login():
    client_id = os.getenv("CLIENT_ID")
    redirect_uri = os.getenv("REDIRECT_URI")
    return redirect(f"https://discord.com/api/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify%20guilds")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "No code.", 400
    data = {
        'client_id': os.getenv("CLIENT_ID"),
        'client_secret': os.getenv("CLIENT_SECRET"),
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': os.getenv("REDIRECT_URI")
    }
    resp = requests.post('https://discord.com/api/oauth2/token', data=data)
    if resp.status_code != 200:
        return "Auth failed.", 400
    token_data = resp.json()
    access_token = token_data['access_token']
    user_resp = requests.get('https://discord.com/api/users/@me', headers={'Authorization': f'Bearer {access_token}'})
    user = user_resp.json()
    session['user'] = user
    session['access_token'] = access_token
    owner_id = int(os.getenv("OWNER_ID", 0))
    developer_id = int(os.getenv("DEVELOPER_USER_ID", 0))
    session['is_owner'] = str(user['id']) == str(owner_id) or str(user['id']) == str(developer_id)
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    access_token = session.get('access_token')
    guilds = []
    if access_token:
        resp = requests.get('https://discord.com/api/users/@me/guilds', headers={'Authorization': f'Bearer {access_token}'})
        if resp.status_code == 200:
            guilds = resp.json()
    bot_guilds = []
    if app.bot:
        bot_guilds = [{'id': str(g.id), 'name': g.name, 'icon': g.icon.url if g.icon else None} for g in app.bot.guilds]
    display = []
    if session.get('is_owner') and session.get('developer_mode', False):
        display = bot_guilds
    else:
        user_guild_ids = [str(g['id']) for g in guilds]
        display = [g for g in bot_guilds if g['id'] in user_guild_ids]
    commands_by_category = {}
    if app.bot:
        for cog in app.bot.cogs.values():
            cog_commands = [cmd for cmd in cog.get_commands() if not cmd.hidden]
            if cog_commands:
                commands_by_category[cog.__class__.__name__] = [cmd.name for cmd in cog_commands]
    return render_template('dashboard.html', user=session['user'], guilds=display, commands_by_category=commands_by_category)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/toggle_dev_mode', methods=['POST'])
@login_required
def toggle_dev_mode():
    if not session.get('is_owner'):
        return jsonify({'error': 'Unauthorized'}), 403
    current = session.get('developer_mode', False)
    session['developer_mode'] = not current
    return jsonify({'developer_mode': session['developer_mode']})

@app.route('/run_command', methods=['POST'])
@login_required
async def run_command():
    # Placeholder – actual execution would need more logic
    return jsonify({'success': 'Command executed (placeholder)'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
